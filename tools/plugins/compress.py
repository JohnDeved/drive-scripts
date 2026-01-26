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
from tools.shared.utils import fmt_bytes


KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]


def _load_compress_deps(key_path: str | None = None) -> None:
    """Lazy-load nsz and its dependencies."""
    ensure_python_modules(["nsz"])

    # Import Keys to ensure they are loaded (requires prod.keys in ~/.switch)
    from nsz.nut import Keys  # type: ignore

    if key_path:
        try:
            Keys.load(key_path)
        except Exception:
            pass  # Fallback to default loading if this fails or already loaded


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
                    pleaseNoPrint=None,
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
                pleaseNoPrint=None,
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


def _verify_file(
    path: str, on_progress: Callable[[int, int], None]
) -> Tuple[bool, str]:
    """Verify compressed file using nsz API."""
    from nsz.NszDecompressor import VerificationException, verify  # type: ignore

    file_path = Path(path)
    total_size = file_path.stat().st_size

    # Use Manager to create a shared list for status reporting
    with Manager() as manager:
        status_report = manager.list()
        # [read, written, total, step]
        status_report.append([0, 0, total_size, "Verifying"])

        error: List[Exception | None] = [None]

        def worker() -> None:
            try:
                verify(
                    filePath=file_path,
                    fixPadding=False,
                    raiseVerificationException=True,
                    raisePfs0Exception=True,
                    originalFilePath=None,  # quick verify
                    statusReportInfo=[status_report, 0],
                    pleaseNoPrint=None,
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
                    read, _, _, _ = status_report[0]
                    on_progress(read, total_size)
                except (ValueError, IndexError):
                    pass
            time.sleep(0.1)

        thread.join()

        if error[0]:
            if isinstance(error[0], VerificationException):
                return False, str(error[0])
            return False, str(error[0])

    return True, ""


def run_compression(
    files: List[str],
    progress: ProgressUI,
    verify_after: bool,
    ask_confirm: bool,
) -> None:
    """Main compression pipeline."""
    # Stage keys first
    progress.set_step("[0/4] Staging keys")
    ok, path = _stage_keys()
    if not ok:
        raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")

    # Load dependencies after keys are staged (nsz checks keys on import/load)
    _load_compress_deps(path)

    compressed_count = failed_count = 0
    total_files = len(files)

    for i, src in enumerate(files, 1):
        basename = os.path.basename(src)
        # Calculate expected output name for tracking
        ext = os.path.splitext(src)[1].lower()
        out_ext = ".nsz" if ext == ".nsp" else ".xcz"
        local_input = os.path.join(config.temp_dir, basename)
        drive_output = os.path.splitext(src)[0] + out_ext

        # Clean start
        shutil.rmtree(config.temp_dir, ignore_errors=True)
        os.makedirs(config.temp_dir, exist_ok=True)

        try:
            # [1/5] Copy to local
            progress.set_step(f"[1/5] Copying ({i}/{total_files})")
            copy_with_progress(
                src, local_input, lambda d, t: progress.set_progress(d, t, basename)
            )

            # [2/5] Compress
            progress.set_step(f"[2/5] Compressing ({i}/{total_files})")
            ok, err, local_output = _compress_file(
                local_input,
                config.temp_dir,
                lambda d, t: progress.set_progress(d, t, basename),
            )
            if not ok:
                raise RuntimeError(err)

            # Confirmation Step
            if ask_confirm:
                progress.set_step(f"Waiting for confirmation ({i}/{total_files})")
                original_size = os.path.getsize(local_input)
                new_size = os.path.getsize(local_output)

                # Block until user confirms
                keep = progress.request_confirmation(
                    {
                        "orig_size": original_size,
                        "new_size": new_size,
                        "filename": basename,
                    }
                )

                if not keep:
                    progress.log(f"SKIPPED {basename} (User discarded)")
                    # Skip to next file
                    continue

            # [3/5] Verify (Optional)
            if verify_after:
                progress.set_step(f"[3/5] Verifying ({i}/{total_files})")
                # Verify progress is indefinite/spinner mostly, so we just set indeterminate
                progress.set_progress(0, 1, os.path.basename(local_output))
                ok, err = _verify_file(
                    local_output,
                    lambda d, t: progress.set_progress(
                        d, t, os.path.basename(local_output)
                    ),
                )
                if not ok:
                    raise RuntimeError(f"Verify failed: {err}")
            else:
                progress.log(f"Skipped verification for {basename}")

            # [4/5] Upload + Cleanup
            progress.set_step(f"[4/5] Uploading ({i}/{total_files})")
            copy_with_progress(
                local_output,
                drive_output,
                lambda d, t: progress.set_progress(
                    d, t, os.path.basename(drive_output)
                ),
            )

            # Verify upload before deleting original
            local_size = os.path.getsize(local_output)
            if not os.path.exists(drive_output):
                raise RuntimeError("Upload failed: output file not found on Drive")
            uploaded_size = os.path.getsize(drive_output)
            if uploaded_size != local_size:
                raise RuntimeError(
                    f"Upload size mismatch: expected {local_size}, got {uploaded_size}"
                )

            # Safe to delete original from Drive
            if os.path.exists(src):
                os.remove(src)

            progress.log(f"OK    {basename} → {os.path.basename(drive_output)}")
            compressed_count += 1

        except Exception as e:
            progress.log(f"FAIL  {basename} - {e}")
            failed_count += 1
            # Clean up partial upload on Drive (but don't touch original!)
            if os.path.exists(drive_output):
                try:
                    os.remove(drive_output)
                    progress.log(
                        f"       Cleaned up partial: {os.path.basename(drive_output)}"
                    )
                except OSError as cleanup_err:
                    progress.log(
                        f"       Warning: couldn't clean up partial: {cleanup_err}"
                    )

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

        # Options
        verify_chk = w.Checkbox(
            value=True, description="Verify integrity after compression"
        )
        confirm_chk = w.Checkbox(
            value=True, description="Ask before saving (check size)"
        )
        options_box = w.VBox(
            [verify_chk, confirm_chk], layout=w.Layout(margin="10px 0")
        )

        # Initial load
        files = _find_uncompressed_games(config.switch_dir)
        selection.set_items(files)

        progress = ProgressUI("Compress NSZ", run_label="Compress", show_bytes=True)

        # Confirmation Dialog Widget (Hidden by default)
        confirm_ui = w.VBox(
            [],
            layout=w.Layout(
                display="none", border="1px solid #888", padding="10px", margin="10px 0"
            ),
        )
        progress.set_confirm_ui(confirm_ui)

        def on_run(selected: List[str]) -> None:
            if not selected:
                return
            selection.set_running(True)
            verify_chk.disabled = True
            confirm_chk.disabled = True

            # Ensure deps before running (though run_compression loads them too)
            self.ensure_deps()

            def worker() -> None:
                # Capture stdout/stderr to the log widget to confine spammy output
                with progress.log_out:
                    run_compression(
                        selected,
                        progress,
                        verify_after=verify_chk.value,
                        ask_confirm=confirm_chk.value,
                    )

            def on_complete() -> None:
                selection.set_running(False)
                verify_chk.disabled = False
                confirm_chk.disabled = False
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

        # Layout: Title, Selection, Options, Progress (contains logs), Confirmation overlay (inside VBox)
        ui = w.VBox(
            [
                progress.title,
                selection.widget,
                options_box,
                confirm_ui,
                progress.progress_box,
            ]
        )
        clear_output(wait=True)
        display(ui)
