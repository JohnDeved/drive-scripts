"""Compress Tool: Compress NSP/XCI to NSZ/XCZ format."""

from __future__ import annotations

import os
import shutil
import threading
import time
from multiprocessing import Manager, cpu_count
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


def _load_compress_deps() -> None:
    """Lazy-load nsz and its dependencies."""
    ensure_python_modules(["nsz"])
    # Import Keys to ensure they are loaded (requires prod.keys in ~/.switch)
    from nsz.nut import Keys  # type: ignore

    if not Keys.keys_loaded:
        Keys.load_default()


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


def _find_uncompressed_games(root: str) -> List[str]:
    """Find only .nsp and .xci files (not .nsz/.xcz)."""
    out: List[str] = []
    # Filter for uncompressed extensions only
    targets = {".nsp", ".xci"}
    for r, _, files in os.walk(root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in targets:
                out.append(os.path.join(r, f))
    return sorted(out)


def _compress_nsp(
    input_path: str,
    output_dir: str,
    on_progress: Callable[[int, int], None],
) -> Path:
    """Compress NSP using nsz API with real-time progress."""
    from nsz.SolidCompressor import solidCompress  # type: ignore

    file_path = Path(input_path)
    out_dir = Path(output_dir)

    # Use Manager to create a shared list as expected by solidCompress
    # It expects statusReport[id] = [read, written, total, step]
    with Manager() as manager:
        status_report = manager.list()
        status_report.append([0, 0, 1, "Starting"])

        result: List[Path | None] = [None]
        error: List[Exception | None] = [None]

        def worker() -> None:
            try:
                result[0] = solidCompress(
                    filePath=file_path,
                    compressionLevel=18,  # default
                    keep=False,
                    fixPadding=False,
                    useLongDistanceMode=False,
                    outputDir=out_dir,
                    threads=3,  # default for solid
                    statusReport=status_report,
                    id=0,
                    pleaseNoPrint=True,
                )
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=worker)
        thread.start()

        # Poll for progress
        while thread.is_alive():
            if len(status_report) > 0:
                # [read, written, total, step]
                read, _, total, _ = status_report[0]
                on_progress(read, total)
            time.sleep(0.1)

        thread.join()

        if error[0]:
            raise error[0]  # type: ignore

        if result[0] is None:
            raise RuntimeError("Compression returned no result")

        return result[0]


def _compress_xci(
    input_path: str,
    output_dir: str,
    on_progress: Callable[[int, int], None],
) -> Path:
    """Compress XCI using nsz API with file-size polling."""
    from nsz.BlockCompressor import blockCompress  # type: ignore

    file_path = Path(input_path)
    out_dir = Path(output_dir)
    input_size = file_path.stat().st_size
    output_path = out_dir / (file_path.stem + ".xcz")

    result: List[Path | None] = [None]
    error: List[Exception | None] = [None]

    def worker() -> None:
        try:
            result[0] = blockCompress(
                filePath=file_path,
                compressionLevel=18,
                keep=False,
                fixPadding=False,
                useLongDistanceMode=False,
                blockSizeExponent=20,  # 1MB blocks
                outputDir=out_dir,
                threads=cpu_count(),
            )
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=worker)
    thread.start()

    # Poll output file size for progress
    while thread.is_alive():
        if output_path.exists():
            current_size = output_path.stat().st_size
            # Estimate: compressed is ~70% of original.
            # We cap progress at 99% until done to avoid confusion.
            estimated_total = int(input_size * 0.7)
            prog = min(current_size, estimated_total)
            on_progress(prog, estimated_total)
        time.sleep(0.1)

    thread.join()

    if error[0]:
        raise error[0]  # type: ignore

    if result[0] is None:
        raise RuntimeError("Compression returned no result")

    return result[0]


def _compress_file(
    input_path: str,
    output_dir: str,
    on_progress: Callable[[int, int], None],
) -> Tuple[bool, str, str]:
    """Compress a game file (NSP or XCI).

    Returns:
        Tuple of (success, error_message, output_path).
    """
    ext = os.path.splitext(input_path)[1].lower()

    try:
        if ext == ".nsp":
            out = _compress_nsp(input_path, output_dir, on_progress)
        elif ext == ".xci":
            out = _compress_xci(input_path, output_dir, on_progress)
        else:
            return False, f"Unsupported extension: {ext}", ""

        return True, "", str(out)
    except Exception as e:
        return False, str(e), ""


def _verify_file(path: str) -> Tuple[bool, str]:
    """Verify compressed file using nsz API."""
    from nsz.NszDecompressor import VerificationException, verify  # type: ignore

    # Dummy status report to suppress enlighten progress bars
    # [read, written, total, step]
    status_report = [[0, 0, 1, "Verifying"]]

    try:
        verify(
            filePath=Path(path),
            fixPadding=False,
            raiseVerificationException=True,
            raisePfs0Exception=True,
            originalFilePath=None,  # quick verify
            statusReportInfo=[status_report, 0],
            pleaseNoPrint=True,
        )
        return True, ""
    except VerificationException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def run_compression(files: List[str], progress: ProgressUI) -> None:
    """Main compression pipeline."""
    # Stage keys first
    progress.set_step("[0/4] Staging keys")
    ok, path = _stage_keys()
    if not ok:
        raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")

    # Load dependencies after keys are staged (nsz checks keys on import/load)
    _load_compress_deps()

    compressed_count = failed_count = 0
    total_files = len(files)

    for i, src in enumerate(files, 1):
        basename = os.path.basename(src)
        # Calculate expected output name for tracking
        ext = os.path.splitext(src)[1].lower()
        out_ext = ".nsz" if ext == ".nsp" else ".xcz"
        local_input = os.path.join(config.temp_dir, basename)
        # We don't know the exact local output path until compression runs,
        # but we can predict it for cleanup.
        local_output_pred = os.path.join(
            config.temp_dir, os.path.splitext(basename)[0] + out_ext
        )
        drive_output = os.path.splitext(src)[0] + out_ext

        # Clean start
        shutil.rmtree(config.temp_dir, ignore_errors=True)
        os.makedirs(config.temp_dir, exist_ok=True)

        try:
            # [1/4] Copy to local
            progress.set_step(f"[1/4] Copying ({i}/{total_files})")
            copy_with_progress(
                src, local_input, lambda d, t: progress.set_progress(d, t, basename)
            )

            # [2/4] Compress
            progress.set_step(f"[2/4] Compressing ({i}/{total_files})")
            ok, err, local_output = _compress_file(
                local_input,
                config.temp_dir,
                lambda d, t: progress.set_progress(d, t, basename),
            )
            if not ok:
                raise RuntimeError(err)

            # [3/4] Verify
            progress.set_step(f"[3/4] Verifying ({i}/{total_files})")
            # Verify progress is indefinite/spinner mostly, so we just set indeterminate
            progress.set_progress(0, 1, os.path.basename(local_output))
            ok, err = _verify_file(local_output)
            if not ok:
                raise RuntimeError(f"Verify failed: {err}")

            # [4/4] Upload + Cleanup
            progress.set_step(f"[4/4] Uploading ({i}/{total_files})")
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
            compressed_count += 1

        except Exception as e:
            progress.log(f"FAIL  {basename} - {e}")
            failed_count += 1
            # "Clean everything" is handled by the finally block + rmtree at start of loop
            # But we also ensure we don't leave partial uploads on Drive?
            # copy_with_progress handles file creation, if it fails it might leave partial.
            # We assume copy_with_progress is atomic enough or overwrite is fine.
            if os.path.exists(drive_output):
                # If we failed during upload, try to clean up the partial file
                try:
                    os.remove(drive_output)
                except OSError:
                    pass

        finally:
            # Cleanup local temp files
            shutil.rmtree(config.temp_dir, ignore_errors=True)

        progress.set_extra(compressed=compressed_count, failed=failed_count)

    progress.log(
        f"Done: {compressed_count} compressed | {failed_count} failed | {total_files} total"
    )


class CompressTool(BaseTool):
    """Compress NSP/XCI files to NSZ/XCZ format."""

    name = "compress"
    title = "Compress NSZ"
    description = "Compress NSP/XCI to NSZ/XCZ format"
    icon = "compress"
    button_style = "warning"
    order = 3

    def ensure_deps(self) -> None:
        """Load dependencies."""
        ensure_python_modules(["nsz"])

    def main(self) -> None:
        """Display compression UI."""
        ensure_drive_ready()

        # UI Components
        selection = CheckboxListUI(run_label="Compress")

        # Initial load
        files = _find_uncompressed_games(config.switch_dir)
        selection.set_items(files)

        progress = ProgressUI("Compress NSZ", run_label="Compress", show_bytes=True)

        def on_run(selected: List[str]) -> None:
            if not selected:
                return
            selection.set_running(True)
            # Ensure deps before running (though run_compression loads them too)
            self.ensure_deps()

            def worker() -> None:
                run_compression(selected, progress)

            def on_complete() -> None:
                selection.set_running(False)
                progress.finish(success=not progress.had_error())
                # Refresh list to remove compressed files
                new_files = _find_uncompressed_games(config.switch_dir)
                selection.set_items(new_files)

            progress.on_complete(on_complete)
            progress.run_loop(worker)

        def on_rescan() -> None:
            new_files = _find_uncompressed_games(config.switch_dir)
            selection.set_items(new_files)

        selection.on_run(on_run)
        selection.on_rescan(on_rescan)

        ui = w.VBox([progress.title, selection.widget, progress.progress_box])
        clear_output(wait=True)
        display(ui)
