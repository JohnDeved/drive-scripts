"""Extract Tool: Extract archives from Drive, upload extracted files back."""

import glob
import os
import shutil
import subprocess
import time
import zipfile

from IPython.display import clear_output, display
import ipywidgets as w

from .shared import (
    ARCHIVE_EXTS,
    SWITCH_DIR,
    copy_with_progress,
    ensure_bins,
    ensure_drive_ready,
    ensure_python_modules,
    find_archives,
    fmt_bytes,
    short,
)
from .ui import ProgressUI, SelectionUI

LOCAL_DIR = "/content/extract_temp"
MAX_NESTED = 5

_py7zr = None
_rarfile = None


def _ensure_deps():
    """Lazy-load extraction dependencies."""
    global _py7zr, _rarfile
    if _py7zr is None:
        ensure_bins({"7z": "p7zip-full", "unrar": "unrar", "unzip": "unzip"})
        ensure_python_modules(["py7zr", "rarfile"])
        import py7zr
        import rarfile

        _py7zr, _rarfile = py7zr, rarfile


# --- Extractors ---


def _extract_zip(archive, out_dir, on_prog):
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


def _extract_7z(archive, out_dir, on_prog):
    """Extract 7z using CLI with file-size polling for progress."""
    with _py7zr.SevenZipFile(archive, "r") as zf:
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


def _extract_rar(archive, out_dir, on_prog):
    """Stream-extract rar."""
    with _rarfile.RarFile(archive) as rf:
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


def extract(archive, out_dir, on_prog):
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


def upload_all(src_root, dst_root, on_prog):
    """Upload all files from src_root to dst_root with progress."""
    items = []
    for r, _, files in os.walk(src_root):
        rel = os.path.relpath(r, src_root)
        for f in files:
            src = os.path.join(r, f)
            items.append((src, os.path.join(dst_root, rel, f), os.path.getsize(src)))
    total, done = sum(s for *_, s in items), 0
    for src, dst, sz in items:
        on_prog(done, total, os.path.basename(src))
        copy_with_progress(src, dst, lambda d, t: on_prog(done + d, total))
        done += sz
    on_prog(total, total, "")


# --- Worker ---


def run_extraction(archive, out_dir, drive_dest, progress_ui):
    """Main extraction pipeline."""
    ext = os.path.splitext(archive)[1].lower()
    local_archive = os.path.join(LOCAL_DIR, os.path.basename(archive))
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

    for rnd in range(1, MAX_NESTED + 1):
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
    shutil.rmtree(LOCAL_DIR, ignore_errors=True)
    progress_ui.log("Cleanup done.")


# --- UI ---


def main():
    """Main entry point - displays extraction UI."""
    ensure_drive_ready()

    def load_opts():
        archives = sorted(
            f for ext in ARCHIVE_EXTS for f in glob.glob(f"{SWITCH_DIR}/*{ext}")
        )
        return {
            f"{short(os.path.basename(z), 45)} ({fmt_bytes(os.path.getsize(z))})": z
            for z in archives
        }

    # Create UI components
    selection = SelectionUI("Archive:", load_opts, "Extract")
    progress = ProgressUI("Extract Archives", run_label="Extract", show_bytes=True)

    def on_run(archive):
        _ensure_deps()

        selection.set_running(True)

        name = os.path.splitext(os.path.basename(archive))[0]
        out_dir = os.path.join(LOCAL_DIR, name)
        drive_dest = os.path.join(SWITCH_DIR, name)
        shutil.rmtree(LOCAL_DIR, ignore_errors=True)
        os.makedirs(out_dir, exist_ok=True)

        def worker():
            run_extraction(archive, out_dir, drive_dest, progress)

        def on_complete():
            progress.finish()
            selection.set_running(False)
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
