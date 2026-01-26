"""Extract Tool: Extract archives from Drive, upload extracted files back."""

import glob
import os
import shutil
import subprocess
import threading
import time
import zipfile

import ipywidgets as w
from IPython.display import clear_output, display

from .shared import (
    ARCHIVE_EXTS,
    SWITCH_DIR,
    copy_with_progress,
    ensure_bins,
    ensure_drive_ready,
    ensure_python_modules,
    find_archives,
    fmt_bytes,
    fmt_time,
    short,
)

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


def run_extraction(archive, out_dir, drive_dest, on_step, on_prog, on_log):
    """Main extraction pipeline."""
    ext = os.path.splitext(archive)[1].lower()
    local_archive = os.path.join(LOCAL_DIR, os.path.basename(archive))
    is_zip = ext == ".zip"

    # Step 1: Copy (skip for zip - streams directly from Drive)
    if not is_zip:
        on_step("[1/3] Copying to local")
        copy_with_progress(
            archive,
            local_archive,
            lambda d, t: on_prog(d, t, os.path.basename(archive)),
        )
        on_log("Copied to local.")

    # Step 2: Extract main + nested
    on_step("[1/2] Extracting" if is_zip else "[2/3] Extracting")
    extract(archive if is_zip else local_archive, out_dir, on_prog)
    on_log("Main archive extracted.")

    for rnd in range(1, MAX_NESTED + 1):
        nested = find_archives(out_dir)
        if not nested:
            break
        for i, f in enumerate(nested, 1):
            on_prog(i - 1, len(nested), f"Nested: {os.path.basename(f)}")
            extract(
                f, os.path.dirname(f), lambda d, t, n: on_prog(i - 1, len(nested), n)
            )
            os.remove(f)
        on_log(f"Nested round {rnd}: {len(nested)} archives.")

    # Step 3: Upload
    on_step("[2/2] Uploading" if is_zip else "[3/3] Uploading")
    upload_all(out_dir, drive_dest, on_prog)
    on_log("Upload complete.")

    # Cleanup
    os.remove(archive)
    shutil.rmtree(LOCAL_DIR, ignore_errors=True)
    on_log("Cleanup done.")


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

    opts = load_opts()

    # Widgets
    title = w.HTML("<h3>Extract Archives</h3>")
    dropdown = w.Dropdown(
        options=opts, description="Archive:", layout=w.Layout(width="100%")
    )
    btn_run = w.Button(description="Extract", button_style="primary")
    btn_scan = w.Button(description="Rescan")
    step_lbl = w.HTML("")
    file_lbl = w.HTML("")
    prog = w.FloatProgress(
        value=0, min=0, max=1, bar_style="info", layout=w.Layout(width="100%")
    )
    stats_lbl = w.HTML("")
    log_out = w.Output(
        layout=w.Layout(max_height="150px", overflow="auto", border="1px solid #ccc")
    )
    prog_box = w.VBox(
        [step_lbl, file_lbl, prog, stats_lbl, log_out],
        layout=w.Layout(display="none", padding="10px"),
    )
    ui = w.VBox([title, dropdown, w.HBox([btn_run, btn_scan]), prog_box])

    state = {
        "step": "",
        "file": "",
        "done": 0,
        "total": 1,
        "logs": [],
        "running": False,
        "start": 0,
    }
    lock = threading.Lock()
    event = threading.Event()

    def set_state(**kw):
        with lock:
            state.update(kw)
        event.set()

    def push_log(msg):
        with lock:
            state["logs"].append(msg)
        event.set()

    def refresh():
        o = load_opts()
        dropdown.options = o
        btn_run.disabled = not o

    def on_run(_):
        archive = dropdown.value
        if not archive:
            return

        # Instant feedback
        btn_run.disabled = btn_scan.disabled = dropdown.disabled = True
        btn_run.description = "Extracting..."
        btn_run.icon = "spinner"
        prog_box.layout.display = "block"
        log_out.clear_output()

        _ensure_deps()

        name = os.path.splitext(os.path.basename(archive))[0]
        out_dir = os.path.join(LOCAL_DIR, name)
        drive_dest = os.path.join(SWITCH_DIR, name)
        shutil.rmtree(LOCAL_DIR, ignore_errors=True)
        os.makedirs(out_dir, exist_ok=True)

        set_state(
            step="",
            file="",
            done=0,
            total=1,
            logs=[],
            running=True,
            start=time.monotonic(),
        )

        def worker():
            try:
                run_extraction(
                    archive,
                    out_dir,
                    drive_dest,
                    on_step=lambda s: set_state(step=s),
                    on_prog=lambda d, t, f="": set_state(
                        done=d, total=max(t, 1), file=f
                    ),
                    on_log=push_log,
                )
            except Exception as e:
                set_state(step=f"Error: {e}")
                push_log(f"Error: {e}")
            finally:
                set_state(running=False)

        threading.Thread(target=worker, daemon=True).start()

        # UI update loop
        while True:
            event.wait(timeout=0.1)
            event.clear()
            with lock:
                snap = dict(state)
                logs, state["logs"] = state["logs"], []

            step_lbl.value = f"<b>{snap['step']}</b>"
            file_lbl.value = short(snap["file"], 70)
            prog.max, prog.value = max(snap["total"], 1), snap["done"]

            elapsed = time.monotonic() - snap["start"]
            rate = snap["done"] / elapsed if elapsed > 0 else 0
            eta = (snap["total"] - snap["done"]) / rate if rate > 0 else 0
            stats_lbl.value = f"{fmt_bytes(snap['done'])} / {fmt_bytes(snap['total'])} | {fmt_bytes(rate)}/s | ETA {fmt_time(eta)}"

            for msg in logs:
                with log_out:
                    print(msg)

            if not snap["running"]:
                break

        prog.bar_style = "success"
        btn_run.description = "Extract"
        btn_run.icon = ""
        btn_run.disabled = btn_scan.disabled = dropdown.disabled = False
        refresh()
        prog_box.layout.display = "none"

    def on_rescan(_):
        btn_scan.description = "Scanning..."
        btn_scan.icon = "spinner"
        btn_scan.disabled = True
        refresh()
        btn_scan.description = "Rescan"
        btn_scan.icon = ""
        btn_scan.disabled = False

    btn_run.on_click(on_run)
    btn_scan.on_click(on_rescan)
    if not opts:
        btn_run.disabled = True

    clear_output(wait=True)
    display(ui)
