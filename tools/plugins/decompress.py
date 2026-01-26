"""Decompress Tool: Decompress NSZ/XCZ to NSP/XCI format."""

from __future__ import annotations

import os
import shutil
import threading
import time
from multiprocessing import Manager
from pathlib import Path
from typing import Callable, List, Tuple

import ipywidgets as w
from IPython.display import clear_output, display

from config import config
from tools.base import BaseTool
from tools.shared import (
    CheckboxListUI,
    ProgressUI,
    copy_with_progress,
    ensure_drive_ready,
    ensure_python_modules,
)


KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]


def _load_decompress_deps() -> None:
    """Lazy-load nsz and its dependencies."""
    ensure_python_modules(["nsz"])
    from nsz.nut import Keys  # type: ignore

    # load_default() returns True if keys loaded successfully
    if not Keys.load_default():
        raise RuntimeError(
            f"Failed to load Switch keys. Ensure prod.keys exists in {config.keys_dir}/"
        )


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


def _find_compressed_games(root: str) -> List[str]:
    """Find only .nsz and .xcz files."""
    out: List[str] = []
    targets = {".nsz", ".xcz"}
    for r, _, files in os.walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in targets:
                out.append(os.path.join(r, f))
    return sorted(out)


def _decompress_wrapper(
    input_path: str,
    output_dir: str,
    on_progress: Callable[[int, int], None],
) -> Path:
    """Decompress NSZ/XCZ using nsz API with real-time progress."""
    from nsz.NszDecompressor import decompress  # type: ignore

    file_path = Path(input_path)
    out_dir = Path(output_dir)

    # Use Manager to create a shared list for status reporting
    # nsz expects statusReport[id] = [read, written, total, step]
    with Manager() as manager:
        status_report = manager.list()
        status_report.append([0, 0, 1, "Starting"])

        error: List[Exception | None] = [None]

        # We need to determine the output filename to return it.
        # decompress() doesn't return it, but it follows standard naming:
        # file.nsz -> file.nsp
        # file.xcz -> file.xci
        ext = file_path.suffix.lower()
        if ext == ".nsz":
            output_filename = file_path.stem + ".nsp"
        elif ext == ".xcz":
            output_filename = file_path.stem + ".xci"
        else:
            raise ValueError(f"Unsupported extension: {ext}")

        output_path = out_dir / output_filename

        def worker() -> None:
            try:
                decompress(
                    filePath=file_path,
                    outputDir=out_dir,
                    fixPadding=False,
                    statusReportInfo=[status_report, 0],
                    pleaseNoPrint=True,
                )
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=worker)
        thread.start()

        # Poll for progress
        while thread.is_alive():
            if len(status_report) > 0:
                try:
                    # [read, written, total, step]
                    # Decompressor updates index 0 (processed bytes) and index 2 (total bytes)
                    read, _, total, _ = status_report[0]
                    on_progress(read, total)
                except (ValueError, IndexError):
                    pass
            time.sleep(0.1)

        thread.join()

        if error[0]:
            raise error[0]  # type: ignore

        if not output_path.exists():
            raise RuntimeError(
                f"Decompression finished but output file not found: {output_path}"
            )

        return output_path


def _decompress_file(
    input_path: str,
    output_dir: str,
    on_progress: Callable[[int, int], None],
) -> Tuple[bool, str, str]:
    """Decompress a game file.

    Returns:
        Tuple of (success, error_message, output_path).
    """
    try:
        out = _decompress_wrapper(input_path, output_dir, on_progress)
        return True, "", str(out)
    except Exception as e:
        return False, str(e), ""


def run_decompression(files: List[str], progress: ProgressUI) -> None:
    """Main decompression pipeline."""
    # Stage keys first
    progress.set_step("[0/3] Staging keys")
    ok, path = _stage_keys()
    if not ok:
        raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")

    _load_decompress_deps()

    decompressed_count = failed_count = 0
    total_files = len(files)

    for i, src in enumerate(files, 1):
        basename = os.path.basename(src)

        # Predict output name
        ext = os.path.splitext(src)[1].lower()
        out_ext = ".nsp" if ext == ".nsz" else ".xci"

        local_input = os.path.join(config.temp_dir, basename)
        # Prediction for cleanup/tracking
        drive_output = os.path.splitext(src)[0] + out_ext

        # Clean start
        shutil.rmtree(config.temp_dir, ignore_errors=True)
        os.makedirs(config.temp_dir, exist_ok=True)

        try:
            # [1/3] Copy to local
            progress.set_step(f"[1/3] Copying ({i}/{total_files})")
            copy_with_progress(
                src, local_input, lambda d, t: progress.set_progress(d, t, basename)
            )

            # [2/3] Decompress
            progress.set_step(f"[2/3] Decompressing ({i}/{total_files})")
            ok, err, local_output = _decompress_file(
                local_input,
                config.temp_dir,
                lambda d, t: progress.set_progress(d, t, basename),
            )
            if not ok:
                raise RuntimeError(err)

            # [3/3] Upload + Cleanup
            progress.set_step(f"[3/3] Uploading ({i}/{total_files})")
            copy_with_progress(
                local_output,
                drive_output,
                lambda d, t: progress.set_progress(
                    d, t, os.path.basename(drive_output)
                ),
            )

            # Delete original from Drive
            if os.path.exists(src):
                os.remove(src)

            progress.log(f"OK    {basename} → {os.path.basename(drive_output)}")
            decompressed_count += 1

        except Exception as e:
            progress.log(f"FAIL  {basename} - {e}")
            failed_count += 1
            # Cleanup partial upload
            if os.path.exists(drive_output):
                try:
                    os.remove(drive_output)
                except OSError:
                    pass

        finally:
            # Cleanup local temp files
            shutil.rmtree(config.temp_dir, ignore_errors=True)

        progress.set_extra(decompressed=decompressed_count, failed=failed_count)

    progress.log(
        f"Done: {decompressed_count} decompressed | {failed_count} failed | {total_files} total"
    )


class DecompressTool(BaseTool):
    """Decompress NSZ/XCZ files to NSP/XCI format."""

    name = "decompress"
    title = "Decompress NSZ"
    description = "Decompress NSZ/XCZ to NSP/XCI format"
    icon = "expand"  # FontAwesome icon
    button_style = "info"
    order = 4

    def ensure_deps(self) -> None:
        """Load dependencies."""
        ensure_python_modules(["nsz"])

    def main(self) -> None:
        """Display decompression UI."""
        ensure_drive_ready()

        # UI Components
        selection = CheckboxListUI(run_label="Decompress")

        # Initial load
        files = _find_compressed_games(config.switch_dir)
        selection.set_items(files)

        progress = ProgressUI("Decompress NSZ", run_label="Decompress", show_bytes=True)

        def on_run(selected: List[str]) -> None:
            if not selected:
                return
            selection.set_running(True)
            self.ensure_deps()

            def worker() -> None:
                run_decompression(selected, progress)

            def on_complete() -> None:
                selection.set_running(False)
                progress.finish(success=not progress.had_error())
                # Refresh list
                new_files = _find_compressed_games(config.switch_dir)
                selection.set_items(new_files)

            progress.on_complete(on_complete)
            progress.run_loop(worker)

        def on_rescan() -> None:
            new_files = _find_compressed_games(config.switch_dir)
            selection.set_items(new_files)

        selection.on_run(on_run)
        selection.on_rescan(on_rescan)

        ui = w.VBox([progress.title, selection.widget, progress.progress_box])
        clear_output(wait=True)
        display(ui)
