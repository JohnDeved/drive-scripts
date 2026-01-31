import os
import shutil
import asyncio
import threading
import time
from multiprocessing import Manager, cpu_count
from pathlib import Path
from typing import List, Tuple, Callable, Optional

from config import config
from tools.shared.utils import copy_with_progress, ensure_python_modules, fmt_bytes
from server.services.sse_service import sse_service


class CompressService:
    @staticmethod
    async def run_compression(
        job_id: str, files: List[str], verify_after: bool, ask_confirm: bool
    ):
        """Main compression pipeline with SSE reporting."""
        try:
            await sse_service.create_job(job_id)
            ensure_python_modules(["nsz"])

            # Step 0: Stage keys
            await sse_service.send_event(
                job_id, "log", {"message": "Staging decryption keys..."}
            )
            ok, key_path = CompressService._stage_keys()
            if not ok:
                raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")

            # Load keys into nsz
            from nsz.nut import Keys

            try:
                Keys.load(key_path)
            except Exception:
                pass

            compressed_count = failed_count = 0
            total_files = len(files)

            for i, src in enumerate(files, 1):
                basename = os.path.basename(src)
                ext = os.path.splitext(src)[1].lower()
                out_ext = ".nsz" if ext == ".nsp" else ".xcz"
                local_input = os.path.join(config.temp_dir, basename)
                drive_output = os.path.splitext(src)[0] + out_ext

                shutil.rmtree(config.temp_dir, ignore_errors=True)
                os.makedirs(config.temp_dir, exist_ok=True)

                try:
                    # Step 1: Copy to local
                    await sse_service.send_event(
                        job_id, "log", {"message": f"Copying {basename} to local..."}
                    )

                    def do_copy():
                        copy_with_progress(
                            src,
                            local_input,
                            lambda d, t: asyncio.run_coroutine_threadsafe(
                                sse_service.send_event(
                                    job_id,
                                    "progress",
                                    {
                                        "step": f"[1/4] Copying ({i}/{total_files})",
                                        "current": d,
                                        "total": t,
                                        "percent": round(d / t * 100, 2),
                                        "message": basename,
                                    },
                                ),
                                asyncio.get_event_loop(),
                            ),
                        )

                    await asyncio.to_thread(do_copy)

                    # Step 2: Compress
                    await sse_service.send_event(
                        job_id, "log", {"message": f"Compressing {basename}..."}
                    )

                    def on_compress_prog(d, t):
                        asyncio.run_coroutine_threadsafe(
                            sse_service.send_event(
                                job_id,
                                "progress",
                                {
                                    "step": f"[2/4] Compressing ({i}/{total_files})",
                                    "current": d,
                                    "total": t,
                                    "percent": round(d / t * 100, 2) if t > 0 else 0,
                                    "message": basename,
                                },
                            ),
                            asyncio.get_event_loop(),
                        )

                    local_output = await asyncio.to_thread(
                        CompressService._compress_file,
                        local_input,
                        config.temp_dir,
                        on_compress_prog,
                    )

                    # Confirmation Step
                    if ask_confirm:
                        orig_size = os.path.getsize(local_input)
                        new_size = os.path.getsize(local_output)

                        keep = await sse_service.wait_for_confirmation(
                            job_id,
                            {
                                "filename": basename,
                                "original_size": orig_size,
                                "original_size_str": fmt_bytes(orig_size),
                                "compressed_size": new_size,
                                "compressed_size_str": fmt_bytes(new_size),
                                "savings": fmt_bytes(orig_size - new_size),
                                "percent": round(new_size / orig_size * 100, 2),
                            },
                        )

                        if not keep:
                            await sse_service.send_event(
                                job_id,
                                "log",
                                {"message": f"SKIPPED {basename} (User discarded)"},
                            )
                            continue

                    # Step 3: Verify (Optional)
                    if verify_after:
                        await sse_service.send_event(
                            job_id,
                            "log",
                            {
                                "message": f"Verifying {os.path.basename(local_output)}..."
                            },
                        )

                        def on_verify_prog(d, t):
                            asyncio.run_coroutine_threadsafe(
                                sse_service.send_event(
                                    job_id,
                                    "progress",
                                    {
                                        "step": f"[3/4] Verifying ({i}/{total_files})",
                                        "current": d,
                                        "total": t,
                                        "percent": round(d / t * 100, 2)
                                        if t > 0
                                        else 0,
                                        "message": os.path.basename(local_output),
                                    },
                                ),
                                asyncio.get_event_loop(),
                            )

                        ok, err = await asyncio.to_thread(
                            CompressService._verify_file, local_output, on_verify_prog
                        )
                        if not ok:
                            raise RuntimeError(f"Verify failed: {err}")

                    # Step 4: Upload
                    await sse_service.send_event(
                        job_id, "log", {"message": f"Uploading to {drive_output}..."}
                    )

                    def do_upload():
                        copy_with_progress(
                            local_output,
                            drive_output,
                            lambda d, t: asyncio.run_coroutine_threadsafe(
                                sse_service.send_event(
                                    job_id,
                                    "progress",
                                    {
                                        "step": f"[4/4] Uploading ({i}/{total_files})",
                                        "current": d,
                                        "total": t,
                                        "percent": round(d / t * 100, 2),
                                        "message": os.path.basename(drive_output),
                                    },
                                ),
                                asyncio.get_event_loop(),
                            ),
                        )

                    await asyncio.to_thread(do_upload)

                    # Safe to delete original
                    if os.path.exists(src):
                        os.remove(src)

                    await sse_service.send_event(
                        job_id,
                        "log",
                        {
                            "message": f"OK    {basename} -> {os.path.basename(drive_output)}"
                        },
                    )
                    compressed_count += 1

                except Exception as e:
                    await sse_service.send_event(
                        job_id, "log", {"message": f"FAIL  {basename} - {str(e)}"}
                    )
                    failed_count += 1
                    if os.path.exists(drive_output):
                        os.remove(drive_output)

                finally:
                    shutil.rmtree(config.temp_dir, ignore_errors=True)

                await sse_service.send_event(
                    job_id,
                    "progress",
                    {"stats": {"compressed": compressed_count, "failed": failed_count}},
                )

            await sse_service.send_event(
                job_id,
                "complete",
                {
                    "message": f"Done: {compressed_count} compressed, {failed_count} failed"
                },
            )

        except Exception as e:
            await sse_service.send_event(job_id, "error", {"message": str(e)})

    @staticmethod
    def _stage_keys() -> Tuple[bool, str]:
        os.makedirs(config.local_keys_dir, exist_ok=True)
        key_files = ["prod.keys", "title.keys", "keys.txt"]
        for name in key_files:
            src = os.path.join(config.keys_dir, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(config.local_keys_dir, name))
        prod = os.path.join(config.local_keys_dir, "prod.keys")
        return os.path.isfile(prod) and os.path.getsize(prod) > 0, prod

    @staticmethod
    def _compress_file(
        input_path: str, output_dir: str, on_progress: Callable[[int, int], None]
    ) -> str:
        ext = os.path.splitext(input_path)[1].lower()
        if ext == ".nsp":
            return str(
                CompressService._compress_nsp(input_path, output_dir, on_progress)
            )
        elif ext == ".xci":
            return str(
                CompressService._compress_xci(input_path, output_dir, on_progress)
            )
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    @staticmethod
    def _compress_nsp(
        input_path: str, output_dir: str, on_progress: Callable[[int, int], None]
    ) -> Path:
        from nsz.SolidCompressor import solidCompress

        file_path = Path(input_path)
        out_dir = Path(output_dir)
        with Manager() as manager:
            status_report = manager.list()
            status_report.append([0, 0, 1, "Starting"])
            res = [None]
            err = [None]

            def worker():
                try:
                    res[0] = solidCompress(
                        filePath=file_path,
                        compressionLevel=18,
                        keep=False,
                        outputDir=out_dir,
                        threads=3,
                        statusReport=status_report,
                        id=0,
                    )
                except Exception as e:
                    err[0] = e

            t = threading.Thread(target=worker)
            t.start()
            while t.is_alive():
                if len(status_report) > 0:
                    read, _, total, _ = status_report[0]
                    on_progress(read, total)
                time.sleep(0.1)
            t.join()
            if err[0]:
                raise err[0]
            return res[0]

    @staticmethod
    def _compress_xci(
        input_path: str, output_dir: str, on_progress: Callable[[int, int], None]
    ) -> Path:
        from nsz.BlockCompressor import blockCompress

        file_path = Path(input_path)
        out_dir = Path(output_dir)
        input_size = file_path.stat().st_size
        output_path = out_dir / (file_path.stem + ".xcz")
        res = [None]
        err = [None]

        def worker():
            try:
                res[0] = blockCompress(
                    filePath=file_path,
                    compressionLevel=18,
                    keep=False,
                    blockSizeExponent=20,
                    outputDir=out_dir,
                    threads=cpu_count(),
                )
            except Exception as e:
                err[0] = e

        t = threading.Thread(target=worker)
        t.start()
        while t.is_alive():
            if output_path.exists():
                curr = output_path.stat().st_size
                on_progress(curr, int(input_size * 0.7))
            time.sleep(0.1)
        t.join()
        if err[0]:
            raise err[0]
        return res[0]

    @staticmethod
    def _verify_file(
        path: str, on_progress: Callable[[int, int], None]
    ) -> Tuple[bool, str]:
        from nsz.NszDecompressor import verify

        file_path = Path(path)
        total_size = file_path.stat().st_size
        with Manager() as manager:
            status_report = manager.list()
            status_report.append([0, 0, total_size, "Verifying"])
            err = [None]

            def worker():
                try:
                    verify(
                        filePath=file_path,
                        fixPadding=False,
                        raiseVerificationException=True,
                        originalFilePath=None,
                        statusReportInfo=[status_report, 0],
                    )
                except Exception as e:
                    err[0] = e

            t = threading.Thread(target=worker)
            t.start()
            while t.is_alive():
                if len(status_report) > 0:
                    try:
                        on_progress(status_report[0][0], total_size)
                    except:
                        pass
                time.sleep(0.1)
            t.join()
            if err[0]:
                return False, str(err[0])
        return True, ""
