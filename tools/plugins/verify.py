"""Verify Tool: Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

import ipywidgets as w
from IPython.display import display

from config import config
from tools.base import BaseTool
from tools.shared import (
    ProgressUI,
    RangeSelectionUI,
    ensure_drive_ready,
    ensure_python_modules,
    find_games,
    short,
)

KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]

_DEPS_READY = False


def _ensure_nsz_deps() -> None:
    """Lazy-load NSZ dependency."""
    global _DEPS_READY
    if _DEPS_READY:
        return
    ensure_python_modules(["nsz"])
    _DEPS_READY = True


def _short_msg(msg: str, n: int = 120) -> str:
    """Truncate message with ellipsis."""
    return msg[: n - 3] + "..." if msg and len(msg) > n else msg


def _first_line(text: str) -> str:
    """Get first non-empty line from text."""
    if not text:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _extract_error_message(result: subprocess.CompletedProcess[str]) -> str:
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


def _key_status() -> Tuple[bool, str]:
    """Check and stage key files from Drive to local."""
    os.makedirs(config.local_keys_dir, exist_ok=True)
    for name in KEY_FILES:
        drive_path = os.path.join(config.keys_dir, name)
        local_path = os.path.join(config.local_keys_dir, name)
        if os.path.exists(drive_path):
            shutil.copy2(drive_path, local_path)
    prod_path = os.path.join(config.local_keys_dir, "prod.keys")
    prod_ok = os.path.exists(prod_path) and os.path.getsize(prod_path) > 0
    return prod_ok, prod_path


def _classify_key_result(
    result: subprocess.CompletedProcess[str],
) -> Tuple[str, str, bool]:
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


def run_verification(
    files: List[str],
    progress_ui: ProgressUI,
    keys_check_widget: w.HTML,
) -> None:
    """Run verification on a list of files."""
    pass_count = 0
    fail_count = 0

    # Pre-check keys with first file
    prefile = files[0]
    pre_result = subprocess.run(
        ["nsz", "--quick-verify", prefile], capture_output=True, text=True
    )
    status_tag, check_msg, keys_bad = _classify_key_result(pre_result)
    keys_check_widget.value = check_msg

    if keys_bad:
        progress_ui.log(check_msg)
        return

    prefirst = {"path": prefile, "result": pre_result}

    for idx, f in enumerate(files, 1):
        progress_ui.set_progress(idx, len(files), os.path.basename(f))

        if prefirst and f == prefirst["path"]:
            result = prefirst["result"]
        else:
            result = subprocess.run(
                ["nsz", "--quick-verify", f], capture_output=True, text=True
            )

        if result.returncode == 0:
            pass_count += 1
            progress_ui.set_extra(passed=pass_count)
            progress_ui.log(f"OK    {os.path.basename(f)}")
        else:
            fail_count += 1
            progress_ui.set_extra(failed=fail_count)
            err = _extract_error_message(result)
            if err:
                err = _short_msg(err, 140)
                progress_ui.log(
                    f"FAIL  {os.path.basename(f)} (exit {result.returncode}) - {err}"
                )
            else:
                progress_ui.log(
                    f"FAIL  {os.path.basename(f)} (exit {result.returncode})"
                )

    progress_ui.log(
        f"Summary: {len(files)} checked | {pass_count} OK | {fail_count} failed"
    )


# --- Plugin ---


class VerifyTool(BaseTool):
    """Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify."""

    name = "verify"
    title = "Verify NSZ"
    description = "Verify Nintendo Switch game files using NSZ quick verify"
    icon = "check-circle"
    button_style = "info"
    order = 2

    def ensure_deps(self) -> None:
        """Load NSZ dependency."""
        _ensure_nsz_deps()

    def main(self) -> None:
        """Display verification UI."""
        ensure_drive_ready()
        files = find_games(config.switch_dir)

        if not files:
            print("No NSP/NSZ/XCI/XCZ files found.")
            return

        # Header widgets
        title = w.HTML("<h3>Verify NSZ</h3>")
        scan_lbl = w.HTML(f'<span style="color:#666">Scan: {config.switch_dir}</span>')

        key_ok, key_path = _key_status()
        key_line = w.HTML("")
        if key_ok:
            key_line.value = (
                f'<span style="color:#1a7f37">Keys staged: {key_path}</span>'
            )
        else:
            key_line.value = (
                f'<span style="color:#b42318">'
                f"prod.keys missing - place it in {config.keys_dir}/"
                f"</span>"
            )
        keys_check = w.HTML("Keys check: Not run")

        # Range selection
        range_sel = RangeSelectionUI("From:", "To:", "Verify range")
        range_sel.set_files(files)

        # Progress UI
        progress = ProgressUI("Verify NSZ", run_label="Verify", show_bytes=False)

        # Custom stats formatter for verify
        def format_stats(snap: Dict[str, Any], elapsed: float) -> str:
            done, total = snap["done"], snap["total"]
            extra = snap.get("extra", {})
            rate = done / elapsed if elapsed > 0 else 0
            parts = [
                f"Done: {done}/{total}",
                f"Pass: {extra.get('passed', 0)}",
                f"Fail: {extra.get('failed', 0)}",
                f"Rate: {rate:.2f} files/s",
            ]
            return " | ".join(parts)

        progress.set_stats_formatter(format_stats)

        def on_run(selected_files: List[str]) -> None:
            self.ensure_deps()

            # Check keys
            ok, path = _key_status()
            if ok:
                key_line.value = (
                    f'<span style="color:#1a7f37">Keys staged: {path}</span>'
                )
            else:
                key_line.value = (
                    f'<span style="color:#b42318">'
                    f"prod.keys missing - place it in {config.keys_dir}/"
                    f"</span>"
                )
                keys_check.value = "Keys check: Not run (prod.keys missing)"
                return

            range_sel.set_running(True)
            keys_check.value = '<span style="color:#666">Keys check: Running...</span>'

            def worker() -> None:
                run_verification(selected_files, progress, keys_check)

            def on_complete() -> None:
                range_sel.set_running(False)
                if progress.had_error():
                    progress.finish(success=False)
                else:
                    progress.finish(success=True)
                    # Refresh file list
                    new_files = find_games(config.switch_dir)
                    range_sel.set_files(new_files)

            progress.on_complete(on_complete)
            progress.run_loop(worker, poll_interval=1.0)

        range_sel.on_run(on_run)

        # Layout
        selection_box = w.VBox(
            [
                title,
                scan_lbl,
                key_line,
                keys_check,
                range_sel.widget,
            ]
        )

        ui = w.VBox([selection_box, progress.progress_box])

        display(ui)


# Backwards compatibility - allow `from tools.plugins.verify import main`
def main() -> None:
    """Entry point for backwards compatibility."""
    VerifyTool().main()
