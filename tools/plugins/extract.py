"""Extract Tool: Extract archives from Drive, upload extracted files back."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import time
import zipfile
from types import ModuleType
from typing import Callable, List, Optional, Tuple

import ipywidgets as w
from IPython.display import clear_output, display

from config import config
from tools.base import BaseTool
from tools.shared import (
    ProgressUI,
    SelectionUI,
    copy_with_progress,
    ensure_bins,
    ensure_drive_ready,
    ensure_python_modules,
    find_archives,
    fmt_bytes,
    short,
)

# Lazy-loaded modules
_py7zr: Optional[ModuleType] = None
_rarfile: Optional[ModuleType] = None


ProgressCallback = Callable[[int, int, str], None]


def _load_extraction_deps() -> Tuple[ModuleType, ModuleType]:
    """Lazy-load extraction dependencies."""
    global _py7zr, _rarfile
    if _py7zr is None:
        ensure_bins({"7z": "p7zip-full", "unrar": "unrar", "unzip": "unzip"})
        ensure_python_modules(["py7zr", "rarfile"])
        import py7zr
        import rarfile

        _py7zr, _rarfile = py7zr, rarfile
    return _py7zr, _rarfile  # type: ignore[return-value]


# --- Extractors ---


def _extract_zip(archive: str, out_dir: str, on_prog: ProgressCallback) -> None:
    """Stream-extract zip (works directly on Drive paths)."""
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


def _extract_7z(archive: str, out_dir: str, on_prog: ProgressCallback) -> None:
    """Extract 7z using CLI with file-size polling for progress."""
    py7zr, _ = _load_extraction_deps()
    with py7zr.SevenZipFile(archive, "r") as zf:
        items = [(i.filename, i.uncompressed) for i in zf.list() if not i.is_directory]
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
    _, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(err.decode("utf-8", "ignore").strip() or "7z failed")
    on_prog(total, total, "")


def _extract_rar(archive: str, out_dir: str, on_prog: ProgressCallback) -> None:
    """Stream-extract rar."""
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


def extract(archive: str, out_dir: str, on_prog: ProgressCallback) -> None:
    """Extract archive based on extension."""
    ext = os.path.splitext(archive)[1].lower()
    if ext == ".zip":
        _extract_zip(archive, out_dir, on_prog)
    elif ext == ".7z":
        _extract_7z(archive, out_dir, on_prog)
    elif ext == ".rar":
        _extract_rar(archive, out_dir, on_prog)
    else:
        raise ValueError(f"Unsupported: {ext}")


# --- Upload ---


def upload_all(
    src_root: str,
    dst_root: str,
    on_prog: Callable[[int, int, str], None],
) -> None:
    """Upload all files from src_root to dst_root with progress."""
    items: List[Tuple[str, str, int]] = []
    for r, _, files in os.walk(src_root):
        rel = os.path.relpath(r, src_root)
        for f in files:
            src = os.path.join(r, f)
            items.append((src, os.path.join(dst_root, rel, f), os.path.getsize(src)))
    total, done = sum(s for *_, s in items), 0
    for src, dst, sz in items:
        fname = os.path.basename(src)
        on_prog(done, total, fname)
        # Capture done and fname in closure defaults to avoid reference bugs
        done_start = done
        copy_with_progress(
            src, dst, lambda d, t, _d=done_start, _f=fname: on_prog(_d + d, total, _f)
        )
        done += sz
    on_prog(total, total, "")


# --- Worker ---


def run_extraction(
    archive: str,
    out_dir: str,
    drive_dest: str,
    progress_ui: ProgressUI,
) -> None:
    """Main extraction pipeline."""
    ext = os.path.splitext(archive)[1].lower()
    local_archive = os.path.join(config.temp_dir, os.path.basename(archive))
    is_zip = ext == ".zip"

    # Step 1: Copy (skip for zip - streams directly from Drive)
    if not is_zip:
        progress_ui.set_step("[1/3] Copying to local")
        copy_with_progress(
            archive,
            local_archive,
            lambda d, t: progress_ui.set_progress(d, t, os.path.basename(archive)),
        )
        progress_ui.log("Copied to local.")

    # Step 2: Extract main + nested
    progress_ui.set_step("[1/2] Extracting" if is_zip else "[2/3] Extracting")
    extract(
        archive if is_zip else local_archive,
        out_dir,
        lambda d, t, f: progress_ui.set_progress(d, t, f),
    )
    progress_ui.log("Main archive extracted.")

    for rnd in range(1, config.max_nested_depth + 1):
        nested = find_archives(out_dir)
        if not nested:
            break
        for i, f in enumerate(nested, 1):
            progress_ui.set_progress(
                i - 1, len(nested), f"Nested: {os.path.basename(f)}"
            )
            extract(
                f,
                os.path.dirname(f),
                lambda d, t, n: progress_ui.set_progress(i - 1, len(nested), n),
            )
            os.remove(f)
        progress_ui.log(f"Nested round {rnd}: {len(nested)} archives.")

    # Step 3: Upload
    progress_ui.set_step("[2/2] Uploading" if is_zip else "[3/3] Uploading")
    upload_all(out_dir, drive_dest, lambda d, t, f: progress_ui.set_progress(d, t, f))
    progress_ui.log("Upload complete.")

    # Cleanup
    os.remove(archive)
    shutil.rmtree(config.temp_dir, ignore_errors=True)
    progress_ui.log("Cleanup done.")


# --- Plugin ---


class ExtractTool(BaseTool):
    """Extract archives from Drive and upload extracted files back."""

    name = "extract"
    title = "Extract Archives"
    description = "Extract ZIP, 7z, and RAR archives with nested archive support"
    icon = "file-archive-o"
    button_style = "primary"
    order = 1

    def ensure_deps(self) -> None:
        """Load extraction dependencies."""
        _load_extraction_deps()

    def main(self) -> None:
        """Display extraction UI."""
        ensure_drive_ready()

        def load_opts() -> dict[str, str]:
            archives = sorted(
                f
                for ext in config.archive_exts
                for f in glob.glob(f"{config.switch_dir}/*{ext}")
            )
            return {
                f"{short(os.path.basename(z), 45)} ({fmt_bytes(os.path.getsize(z))})": z
                for z in archives
            }

        # Create UI components
        selection = SelectionUI("Archive:", load_opts, "Extract")
        progress = ProgressUI("Extract Archives", run_label="Extract", show_bytes=True)

        def on_run(archive: str) -> None:
            self.ensure_deps()

            selection.set_running(True)

            name = os.path.splitext(os.path.basename(archive))[0]
            out_dir = os.path.join(config.temp_dir, name)
            drive_dest = os.path.join(config.switch_dir, name)
            shutil.rmtree(config.temp_dir, ignore_errors=True)
            os.makedirs(out_dir, exist_ok=True)

            def worker() -> None:
                run_extraction(archive, out_dir, drive_dest, progress)

            def on_complete() -> None:
                selection.set_running(False)
                if progress.had_error():
                    progress.finish(success=False)
                else:
                    progress.finish(success=True)
                    selection.refresh()
                    progress.hide()

            progress.on_complete(on_complete)
            progress.run_loop(worker)

        selection.on_run(on_run)

        # Layout
        ui = w.VBox(
            [
                progress.title,
                selection.dropdown,
                selection.widget,
                progress.progress_box,
            ]
        )

        clear_output(wait=True)
        display(ui)


# Backwards compatibility - allow `from tools.plugins.extract import main`
def main() -> None:
    """Entry point for backwards compatibility."""
    ExtractTool().main()
