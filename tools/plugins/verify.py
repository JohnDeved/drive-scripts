"""Verify Tool: Verify game files using NSZ quick verify."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Tuple

import ipywidgets as w
from IPython.display import clear_output, display

from config import config
from tools.base import BaseTool
from tools.shared import (
    CheckboxListUI,
    ProgressUI,
    ensure_drive_ready,
    ensure_python_modules,
    find_games,
    find_games_progressive,
    short,
)

KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]


def _stage_keys() -> Tuple[bool, str]:
    """Copy keys from Drive to ~/.switch.

    Returns:
        Tuple of (success, path_to_prod_keys).
    """
    os.makedirs(config.local_keys_dir, exist_ok=True)
    for name in KEY_FILES:
        src = os.path.join(config.keys_dir, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(config.local_keys_dir, name))
    prod = os.path.join(config.local_keys_dir, "prod.keys")
    return os.path.isfile(prod) and os.path.getsize(prod) > 0, prod


def _verify_file(path: str) -> Tuple[bool, str]:
    """Run nsz --quick-verify on a single file.

    Returns:
        Tuple of (passed, error_message).
    """
    result = subprocess.run(
        ["nsz", "--quick-verify", path], capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, ""
    # Extract error (simplified)
    err = result.stderr.strip() or result.stdout.strip()
    if err:
        err = err.split("\n")[-1]  # Take last line usually containing the error
    return False, short(err, 100)


def run_verification(files: List[str], progress: ProgressUI) -> None:
    """Verify files with progress updates.

    Args:
        files: List of file paths to verify.
        progress: ProgressUI instance for updates.
    """
    # Stage keys
    progress.set_step("[1/2] Staging keys")
    ok, path = _stage_keys()
    if not ok:
        raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")
    progress.log(f"Keys staged: {path}")

    # Verify
    progress.set_step("[2/2] Verifying")
    passed = failed = 0
    total = len(files)

    for i, f in enumerate(files, 1):
        progress.set_progress(i, total, os.path.basename(f))
        ok, err = _verify_file(f)
        if ok:
            passed += 1
            progress.log(f"OK    {os.path.basename(f)}")
        else:
            failed += 1
            progress.log(f"FAIL  {os.path.basename(f)} - {err}")
        progress.set_extra(passed=passed, failed=failed)

    progress.log(f"Done: {passed} OK | {failed} failed | {total} total")


class VerifyTool(BaseTool):
    """Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify."""

    name = "verify"
    title = "Verify NSZ"
    description = "Verify game files using NSZ quick verify"
    icon = "check-circle"
    button_style = "info"
    order = 2

    def ensure_deps(self) -> None:
        """Load NSZ dependency."""
        ensure_python_modules(["nsz"])

    def main(self) -> None:
        """Display verification UI."""
        ensure_drive_ready()

        # UI Components
        selection = CheckboxListUI(run_label="Verify")
        progress = ProgressUI("Verify NSZ", run_label="Verify", show_bytes=False)

        # Progressive load files (max 3 levels deep)
        selection.load_items_progressive(
            lambda cb: find_games_progressive(config.switch_dir, cb, max_depth=3)
        )

        def on_run(selected: List[str]) -> None:
            if not selected:
                return
            self.ensure_deps()
            selection.set_running(True)

            def worker() -> None:
                run_verification(selected, progress)

            def on_complete() -> None:
                selection.set_running(False)
                progress.finish(success=not progress.had_error())

            progress.on_complete(on_complete)
            progress.run_loop(worker)

        def on_rescan() -> None:
            selection.load_items_progressive(
                lambda cb: find_games_progressive(config.switch_dir, cb, max_depth=3)
            )

        selection.on_run(on_run)
        selection.on_rescan(on_rescan)

        ui = w.VBox([progress.title, selection.widget, progress.progress_box])
        clear_output(wait=True)
        display(ui)


# Backwards compatibility
def main() -> None:
    VerifyTool().main()
