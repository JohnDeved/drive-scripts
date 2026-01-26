"""Verify Tool: Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify."""

import os
import shutil
import subprocess
import threading
import time

import ipywidgets as w
from IPython.display import display

from .shared import (
    SWITCH_DIR,
    ensure_drive_ready,
    ensure_python_modules,
    find_games,
    fmt_time,
    short,
)

DRIVE_KEYS_DIR = f"{SWITCH_DIR}/.switch"
LOCAL_KEYS_DIR = os.path.expanduser("~/.switch")
KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]
PREVIEW_LIMIT = 10

_DEPS_READY = False


def _ensure_deps():
    """Lazy-load NSZ dependency."""
    global _DEPS_READY
    if _DEPS_READY:
        return
    ensure_python_modules(["nsz"])
    _DEPS_READY = True


def _short_msg(msg, n=120):
    """Truncate message with ellipsis."""
    return msg[: n - 3] + "..." if msg and len(msg) > n else msg


def _first_line(text):
    """Get first non-empty line from text."""
    if not text:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _extract_error_message(result):
    """Extract meaningful error message from subprocess result."""
    text = result.stderr or result.stdout or ""
    if not text:
        return ""
    if "Verification detected hash mismatch!" in text:
        return "Verification detected hash mismatch!"
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    for line in reversed(lines):
        if "VerificationException:" in line:
            msg = line.split("VerificationException:", 1)[1].strip()
            return msg or line
    for line in reversed(lines):
        if "Exception:" in line:
            msg = line.split("Exception:", 1)[1].strip()
            return msg or line
    return lines[-1]


def _key_status():
    """Check and stage key files from Drive to local."""
    os.makedirs(LOCAL_KEYS_DIR, exist_ok=True)
    for name in KEY_FILES:
        drive_path = os.path.join(DRIVE_KEYS_DIR, name)
        local_path = os.path.join(LOCAL_KEYS_DIR, name)
        if os.path.exists(drive_path):
            shutil.copy2(drive_path, local_path)
    prod_path = os.path.join(LOCAL_KEYS_DIR, "prod.keys")
    prod_ok = os.path.exists(prod_path) and os.path.getsize(prod_path) > 0
    return prod_ok, prod_path


def _classify_key_result(result):
    """Classify verification result for key issues."""
    combined = (result.stderr or "") + "\n" + (result.stdout or "")
    low = combined.lower()
    reason = _first_line(result.stderr) or _first_line(result.stdout)
    if result.returncode == 0:
        return "ok", "Keys check: OK", False
    key_hint = any(
        token in low for token in ["prod.keys", "title.keys", "keys.txt", "keys"]
    )
    key_bad = key_hint and any(
        token in low for token in ["missing", "not found", "invalid", "no keys"]
    )
    if key_bad:
        msg = reason or "keys missing or invalid"
        return "bad", f"Keys check: FAIL - {msg}", True
    return "unknown", f"Keys check: Unknown (exit {result.returncode})", False


def _clamp_range(start_idx, end_idx, total):
    """Clamp range indices to valid bounds."""
    if total < 1:
        return 1, 0
    start_idx = max(1, min(start_idx, total))
    end_idx = max(1, min(end_idx, total))
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx
    return start_idx, end_idx


def _build_options(files):
    """Build dropdown options from file list."""
    options = []
    for i, f in enumerate(files, 1):
        label = f"{i:04d} {short(os.path.basename(f), 70)}"
        options.append((label, i))
    return options


# --- UI ---


def main():
    """Main entry point - displays verification UI."""
    ensure_drive_ready()
    files = find_games(SWITCH_DIR)
    if not files:
        print("No NSP/NSZ/XCI/XCZ files found.")
        return

    title = w.HTML("<h3>Verify NSZ</h3>")
    scan = w.HTML(f'<span style="color:#666">Scan: {SWITCH_DIR}</span>')
    key_ok, key_path = _key_status()
    key_line = w.HTML("")
    if key_ok:
        key_line.value = f'<span style="color:#1a7f37">Keys staged: {key_path}</span>'
    else:
        key_line.value = f'<span style="color:#b42318">prod.keys missing - place it in {DRIVE_KEYS_DIR}/</span>'
    keys_check = w.HTML("Keys check: Not run")

    options = _build_options(files)
    from_dd = w.Dropdown(
        options=options, value=1, description="From:", layout=w.Layout(width="100%")
    )
    to_dd = w.Dropdown(
        options=options,
        value=len(files),
        description="To:",
        layout=w.Layout(width="100%"),
    )
    show_all = w.Checkbox(value=False, description="Show full list")
    selection_info = w.HTML("Selection: 1 - 1 (1 file)")
    preview = w.Output(
        layout=w.Layout(
            max_height="220px", overflow="auto", border="1px solid #ccc", padding="5px"
        )
    )

    start = w.Button(description="Verify range", button_style="primary")
    selection = w.VBox(
        [
            title,
            scan,
            key_line,
            keys_check,
            from_dd,
            to_dd,
            show_all,
            selection_info,
            preview,
            start,
        ]
    )

    status = w.HTML("Status: Ready")
    elapsed = w.HTML("Elapsed: 00:00:00")
    current = w.HTML("")
    progress = w.IntProgress(
        value=0, min=0, max=100, bar_style="info", layout=w.Layout(width="100%")
    )
    stats = w.HTML("")
    log = w.Output(
        layout=w.Layout(
            max_height="220px", overflow="auto", border="1px solid #ccc", padding="5px"
        )
    )
    ui = w.VBox(
        [status, elapsed, current, progress, stats, log],
        layout=w.Layout(padding="10px"),
    )
    ui.layout.display = "none"

    def set_status(text):
        status.value = f"Status: {text}"

    def set_current(name, idx=None, total=None):
        if idx is None:
            current.value = short(name)
        else:
            current.value = f"Now: {short(name)} [{idx}/{total}]"

    def set_stats(text):
        stats.value = f'<span style="color:#666">{text}</span>'

    def log_msg(msg):
        with log:
            print(msg)

    def selection_range(all_files):
        start_idx, end_idx = _clamp_range(from_dd.value, to_dd.value, len(all_files))
        return start_idx, end_idx, all_files[start_idx - 1 : end_idx]

    def update_preview(_=None):
        all_files = files
        start_idx, end_idx, subset = selection_range(all_files)
        count = len(subset)
        suffix = "s" if count != 1 else ""
        selection_info.value = (
            f"Selection: {start_idx} - {end_idx} ({count} file{suffix})"
        )
        preview.clear_output()
        with preview:
            if not subset:
                print("No files in selection.")
                return
            if show_all.value or count <= PREVIEW_LIMIT * 2:
                for f in subset:
                    print(os.path.basename(f))
            else:
                head = subset[:PREVIEW_LIMIT]
                tail = subset[-PREVIEW_LIMIT:]
                for f in head:
                    print(os.path.basename(f))
                print("...")
                for f in tail:
                    print(os.path.basename(f))

    def refresh_files():
        nonlocal files
        ok, path = _key_status()
        if ok:
            key_line.value = f'<span style="color:#1a7f37">Keys staged: {path}</span>'
        else:
            key_line.value = f'<span style="color:#b42318">prod.keys missing - place it in {DRIVE_KEYS_DIR}/</span>'
        files = find_games(SWITCH_DIR)
        opts = _build_options(files)
        total = len(files)
        if total < 1:
            from_dd.options = [("0000 (empty)", 1)]
            to_dd.options = [("0000 (empty)", 1)]
            from_dd.value = 1
            to_dd.value = 1
            start.disabled = True
            selection_info.value = "Selection: 0 - 0 (0 files)"
            preview.clear_output()
            return files
        from_dd.options = opts
        to_dd.options = opts
        from_dd.value = 1
        to_dd.value = total
        start.disabled = False
        update_preview()
        return files

    def reset_ui():
        progress.bar_style = "info"
        progress.value = 0
        stats.value = ""
        current.value = ""
        elapsed.value = "Elapsed: 00:00:00"
        keys_check.value = "Keys check: Not run"
        log.clear_output()
        set_status("Ready")

    def on_start(_):
        _ensure_deps()
        ok, path = _key_status()
        if ok:
            key_line.value = f'<span style="color:#1a7f37">Keys staged: {path}</span>'
        else:
            key_line.value = f'<span style="color:#b42318">prod.keys missing - place it in {DRIVE_KEYS_DIR}/</span>'
            keys_check.value = "Keys check: Not run (prod.keys missing)"
            set_status("Keys missing")
            return

        reset_ui()
        set_status("Verifying")
        from_dd.disabled = True
        to_dd.disabled = True
        show_all.disabled = True
        start.disabled = True
        start.description = "Running..."

        all_files = find_games(SWITCH_DIR)
        if not all_files:
            set_stats("No NSP/NSZ/XCI/XCZ files found")
            set_status("Ready")
            from_dd.disabled = False
            to_dd.disabled = False
            show_all.disabled = False
            start.disabled = False
            start.description = "Verify range"
            return

        start_idx, end_idx, files_subset = selection_range(all_files)
        if not files_subset:
            set_stats("No files in selected range")
            set_status("Ready")
            from_dd.disabled = False
            to_dd.disabled = False
            show_all.disabled = False
            start.disabled = False
            start.description = "Verify range"
            return

        ui.layout.display = "block"
        keys_check.value = '<span style="color:#666">Keys check: Running...</span>'

        lock = threading.Lock()
        event = threading.Event()
        now = time.monotonic()
        state = {
            "running": True,
            "done": 0,
            "total": len(files_subset),
            "passed": 0,
            "failed": 0,
            "file": "",
            "run_start": now,
            "log": [],
            "keys_check": "Keys check: Running...",
        }

        def set_state(**kwargs):
            with lock:
                state.update(kwargs)
            event.set()

        def push_log(msg):
            with lock:
                state["log"].append(msg)
            event.set()

        def worker():
            pass_count = 0
            fail_count = 0
            prefirst = None
            prefile = files_subset[0]
            pre_result = subprocess.run(
                ["nsz", "--quick-verify", prefile], capture_output=True, text=True
            )
            status_tag, check_msg, keys_bad = _classify_key_result(pre_result)
            set_state(keys_check=check_msg)
            if keys_bad:
                push_log(check_msg)
                with lock:
                    state["running"] = False
                event.set()
                return
            prefirst = {"path": prefile, "result": pre_result}

            for idx, f in enumerate(files_subset, 1):
                set_state(file=f, done=idx)
                if prefirst and f == prefirst["path"]:
                    result = prefirst["result"]
                else:
                    result = subprocess.run(
                        ["nsz", "--quick-verify", f], capture_output=True, text=True
                    )
                if result.returncode == 0:
                    pass_count += 1
                    set_state(passed=pass_count)
                    push_log(f"OK    {os.path.basename(f)}")
                else:
                    fail_count += 1
                    set_state(failed=fail_count)
                    err = _extract_error_message(result)
                    if err:
                        err = _short_msg(err, 140)
                        push_log(
                            f"FAIL  {os.path.basename(f)} (exit {result.returncode}) - {err}"
                        )
                    else:
                        push_log(
                            f"FAIL  {os.path.basename(f)} (exit {result.returncode})"
                        )
            push_log(
                f"Summary: {len(files_subset)} checked | {pass_count} OK | {fail_count} failed"
            )
            with lock:
                state["running"] = False
            event.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        while True:
            event.wait(timeout=1.0)
            with lock:
                snapshot = dict(state)
                log_items = snapshot.get("log", [])
                state["log"] = []
            event.clear()

            elapsed_total = time.monotonic() - snapshot["run_start"]
            elapsed.value = f"Elapsed: {fmt_time(elapsed_total)}"

            total = max(snapshot["total"], 1)
            done = snapshot["done"]
            progress.value = int((done / total) * 100)
            rate = done / elapsed_total if elapsed_total > 0 else 0
            set_current(snapshot["file"], done, total)
            set_stats(
                f"Done: {done}/{total} | Pass: {snapshot['passed']} | Fail: {snapshot['failed']} | Rate: {rate:.2f} files/s"
            )
            keys_check.value = snapshot.get("keys_check", "Keys check: Not run")

            for msg in log_items:
                log_msg(msg)

            if not snapshot["running"]:
                break

        set_status("Complete")
        progress.bar_style = "success"
        start.description = "Verify range"
        start.disabled = False
        from_dd.disabled = False
        to_dd.disabled = False
        show_all.disabled = False
        refresh_files()

    from_dd.observe(update_preview, names="value")
    to_dd.observe(update_preview, names="value")
    show_all.observe(update_preview, names="value")

    start.on_click(on_start)
    display(w.VBox([selection, ui]))
    update_preview()
