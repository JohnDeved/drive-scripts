import os
import shutil
import zipfile
import subprocess
import asyncio
import time
from typing import Callable, Optional, Tuple, List
from types import ModuleType

from config import config
from tools.shared.utils import (
    copy_with_progress,
    ensure_bins,
    ensure_python_modules,
    find_archives,
)
from server.services.sse_service import sse_service

# Lazy-loaded modules
_py7zr: Optional[ModuleType] = None
_rarfile: Optional[ModuleType] = None


def _load_extraction_deps() -> Tuple[ModuleType, ModuleType]:
    """Lazy-load extraction dependencies."""
    global _py7zr, _rarfile
    if _py7zr is None:
        ensure_bins({"7z": "p7zip-full", "unrar": "unrar", "unzip": "unzip"})
        ensure_python_modules(["py7zr", "rarfile"])
        import py7zr
        import rarfile

        _py7zr, _rarfile = py7zr, rarfile
    return _py7zr, _rarfile  # type: ignore


class ExtractService:
    @staticmethod
    async def run_extraction(job_id: str, archive_path: str):
        """Main extraction pipeline with SSE reporting."""
        try:
            await sse_service.create_job(job_id)

            ext = os.path.splitext(archive_path)[1].lower()
            name = os.path.splitext(os.path.basename(archive_path))[0]
            out_dir = os.path.join(config.temp_dir, name)
            drive_dest = os.path.join(config.switch_dir, name)
            local_archive = os.path.join(
                config.temp_dir, os.path.basename(archive_path)
            )
            is_zip = ext == ".zip"

            shutil.rmtree(config.temp_dir, ignore_errors=True)
            os.makedirs(out_dir, exist_ok=True)

            # Progress callback for SSE
            async def on_progress(done: int, total: int, message: str, step: str):
                percent = (done / total * 100) if total > 0 else 0
                await sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": step,
                        "current": done,
                        "total": total,
                        "percent": round(percent, 2),
                        "message": message,
                    },
                )

            # Step 1: Copy (skip for zip)
            if not is_zip:
                await sse_service.send_event(
                    job_id, "log", {"message": "Copying to local storage..."}
                )

                # Wrap sync copy_with_progress in thread
                def do_copy():
                    def _prog(d: int, t: int):
                        asyncio.run_coroutine_threadsafe(
                            on_progress(
                                d, t, os.path.basename(archive_path), "[1/3] Copying"
                            ),
                            asyncio.get_event_loop(),
                        )

                    copy_with_progress(archive_path, local_archive, _prog)

                await asyncio.to_thread(do_copy)
                await sse_service.send_event(
                    job_id, "log", {"message": "Copied to local."}
                )

            # Step 2: Extract
            step_name = "[1/2] Extracting" if is_zip else "[2/3] Extracting"
            await sse_service.send_event(
                job_id, "log", {"message": "Extracting main archive..."}
            )

            def do_extract():
                def _prog(d: int, t: int, f: str):
                    asyncio.run_coroutine_threadsafe(
                        on_progress(d, t, f, step_name), asyncio.get_event_loop()
                    )

                ExtractService._extract(
                    archive_path if is_zip else local_archive, out_dir, _prog
                )

            await asyncio.to_thread(do_extract)
            await sse_service.send_event(
                job_id, "log", {"message": "Main archive extracted."}
            )

            # Nested extraction
            for rnd in range(1, config.max_nested_depth + 1):
                nested = find_archives(out_dir)
                if not nested:
                    break
                await sse_service.send_event(
                    job_id,
                    "log",
                    {"message": f"Round {rnd}: Found {len(nested)} nested archives."},
                )
                for i, f in enumerate(nested, 1):

                    def extract_nested():
                        def _prog(d: int, t: int, n: str):
                            asyncio.run_coroutine_threadsafe(
                                on_progress(
                                    i - 1, len(nested), n, f"Nested Round {rnd}"
                                ),
                                asyncio.get_event_loop(),
                            )

                        ExtractService._extract(f, os.path.dirname(f), _prog)

                    await asyncio.to_thread(extract_nested)
                    os.remove(f)
                await sse_service.send_event(
                    job_id, "log", {"message": f"Nested round {rnd} complete."}
                )

            # Step 3: Upload
            step_name = "[2/2] Uploading" if is_zip else "[3/3] Uploading"
            await sse_service.send_event(
                job_id, "log", {"message": "Uploading to Drive..."}
            )

            def do_upload():
                def _prog(d: int, t: int, f: str):
                    asyncio.run_coroutine_threadsafe(
                        on_progress(d, t, f, step_name), asyncio.get_event_loop()
                    )

                ExtractService._upload_all(out_dir, drive_dest, _prog)

            await asyncio.to_thread(do_upload)

            await sse_service.send_event(job_id, "log", {"message": "Upload complete."})

            # Cleanup
            if os.path.exists(archive_path):
                os.remove(archive_path)
            shutil.rmtree(config.temp_dir, ignore_errors=True)

            await sse_service.send_event(
                job_id, "complete", {"message": "Extraction successful"}
            )

        except Exception as e:
            await sse_service.send_event(job_id, "error", {"message": str(e)})

    @staticmethod
    def _extract(archive: str, out_dir: str, on_prog: Callable[[int, int, str], None]):
        ext = os.path.splitext(archive)[1].lower()
        if ext == ".zip":
            with zipfile.ZipFile(archive, "r") as zf:
                items = [(i, i.file_size) for i in zf.infolist() if not i.is_dir()]
                total, done = sum(s for _, s in items), 0
                for info, _ in items:
                    out = os.path.join(out_dir, info.filename)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with zf.open(info) as src, open(out, "wb") as dst:
                        while buf := src.read(8 << 20):
                            dst.write(buf)
                            done += len(buf)
                            on_prog(done, total, info.filename)
        elif ext == ".7z":
            py7zr, _ = _load_extraction_deps()
            with py7zr.SevenZipFile(archive, "r") as zf:
                items = [
                    (i.filename, i.uncompressed)
                    for i in zf.list()
                    if not i.is_directory
                ]
            total = sum(s for _, s in items)
            cmd = ["7z", "x", "-aoa", "-bso0", "-bsp0", f"-o{out_dir}", archive]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while proc.poll() is None:
                done = sum(
                    min(os.path.getsize(p), sz)
                    for fn, sz in items
                    if os.path.exists(p := os.path.join(out_dir, fn))
                )
                on_prog(done, total, os.path.basename(archive))
                time.sleep(0.1)
            if proc.returncode != 0:
                _, err = proc.communicate()
                raise RuntimeError(err.decode("utf-8", "ignore").strip() or "7z failed")
            on_prog(total, total, "")
        elif ext == ".rar":
            _, rarfile = _load_extraction_deps()
            with rarfile.RarFile(archive) as rf:
                items = [(i, i.file_size) for i in rf.infolist() if not i.is_dir()]
                total, done = sum(s for _, s in items), 0
                for info, _ in items:
                    out = os.path.join(out_dir, info.filename)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with rf.open(info) as src, open(out, "wb") as dst:
                        while buf := src.read(8 << 20):
                            dst.write(buf)
                            done += len(buf)
                            on_prog(done, total, info.filename)
        else:
            raise ValueError(f"Unsupported: {ext}")

    @staticmethod
    def _upload_all(
        src_root: str, dst_root: str, on_prog: Callable[[int, int, str], None]
    ):
        items: List[Tuple[str, str, int]] = []
        for r, _, files in os.walk(src_root):
            rel = os.path.relpath(r, src_root)
            for f in files:
                src = os.path.join(r, f)
                items.append(
                    (src, os.path.join(dst_root, rel, f), os.path.getsize(src))
                )
        total, done = sum(s for *_, s in items), 0
        for src, dst, sz in items:
            fname = os.path.basename(src)
            on_prog(done, total, fname)
            done_start = done
            copy_with_progress(
                src,
                dst,
                lambda d, t, _d=done_start, _f=fname: on_prog(_d + d, total, _f),
            )
            done += sz
        on_prog(total, total, "")
