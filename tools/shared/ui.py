"""Shared UI components for drive-scripts tools."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

import ipywidgets as w
from IPython.display import display

from .utils import fmt_bytes, fmt_time, short


class ProgressUI:
    """Reusable progress UI with step, file, progress bar, stats, and log.

    Usage:
        ui = ProgressUI("Extract Archives")
        ui.display()

        # In worker thread:
        ui.set_step("[1/2] Extracting")
        ui.set_progress(done, total, filename)
        ui.log("Extracted file.zip")

        # In main thread, run update loop:
        ui.run_loop(worker_func)

    Attributes:
        show_bytes: If True, show bytes in stats; if False, show counts.
        run_label: Label for the run button.
    """

    def __init__(
        self,
        title: str,
        run_label: str = "Run",
        show_bytes: bool = True,
    ) -> None:
        """Initialize progress UI.

        Args:
            title: H3 title text.
            run_label: Label for the run button.
            show_bytes: If True, show bytes in stats; if False, show counts.
        """
        self.show_bytes = show_bytes
        self.run_label = run_label

        # State
        self._state: Dict[str, Any] = {
            "step": "",
            "file": "",
            "done": 0,
            "total": 1,
            "logs": [],
            "running": False,
            "start": 0.0,
            "extra": {},  # For custom stats like passed/failed
        }
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._error: Optional[str] = None  # Track error state

        # Widgets
        self.title = w.HTML(f"<h3>{title}</h3>")
        self.step_lbl = w.HTML("")
        self.file_lbl = w.HTML("")
        self.progress = w.FloatProgress(
            value=0, min=0, max=1, bar_style="info", layout=w.Layout(width="100%")
        )
        self.stats_lbl = w.HTML("")
        self.log_out = w.Output(
            layout=w.Layout(
                max_height="150px", overflow="auto", border="1px solid #ccc"
            )
        )
        self.progress_box = w.VBox(
            [self.step_lbl, self.file_lbl, self.progress, self.stats_lbl, self.log_out],
            layout=w.Layout(display="none", padding="10px"),
        )

        # Callbacks
        self._on_complete: Optional[Callable[[], None]] = None
        self._format_stats: Optional[Callable[[Dict[str, Any], float], str]] = None

    def set_state(self, **kw: Any) -> None:
        """Thread-safe state update."""
        with self._lock:
            self._state.update(kw)
        self._event.set()

    def set_step(self, step: str) -> None:
        """Set current step label."""
        self.set_state(step=step)

    def set_progress(self, done: int, total: int, file: str = "") -> None:
        """Set progress values."""
        self.set_state(done=done, total=max(total, 1), file=file)

    def log(self, msg: str) -> None:
        """Append log message."""
        with self._lock:
            self._state["logs"].append(msg)
        self._event.set()

    def set_extra(self, **kw: Any) -> None:
        """Set extra state values (e.g., passed, failed counts)."""
        with self._lock:
            self._state["extra"].update(kw)
        self._event.set()

    def get_extra(self, key: str, default: Any = None) -> Any:
        """Get extra state value."""
        with self._lock:
            return self._state["extra"].get(key, default)

    def start(self) -> None:
        """Reset and show progress UI."""
        self._error = None  # Reset error state
        self.set_state(
            step="",
            file="",
            done=0,
            total=1,
            logs=[],
            running=True,
            start=time.monotonic(),
            extra={},
        )
        self.progress.bar_style = "info"
        self.progress.value = 0
        self.step_lbl.value = ""
        self.file_lbl.value = ""
        self.stats_lbl.value = ""
        self.log_out.clear_output()
        self.progress_box.layout.display = "block"

    def finish(self, success: bool = True) -> None:
        """Mark as complete."""
        self.set_state(running=False)
        self.progress.bar_style = "success" if success else "danger"

    def had_error(self) -> bool:
        """Check if an error occurred during run_loop."""
        return self._error is not None

    def hide(self) -> None:
        """Hide progress box."""
        self.progress_box.layout.display = "none"

    def _default_format_stats(self, snap: Dict[str, Any], elapsed: float) -> str:
        """Default stats formatter."""
        done, total = snap["done"], snap["total"]
        if self.show_bytes:
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            return (
                f"{fmt_bytes(done)} / {fmt_bytes(total)} | "
                f"{fmt_bytes(rate)}/s | ETA {fmt_time(eta)}"
            )
        else:
            rate = done / elapsed if elapsed > 0 else 0
            extra = snap.get("extra", {})
            parts = [f"Done: {done}/{total}"]
            if "passed" in extra:
                parts.append(f"Pass: {extra['passed']}")
            if "failed" in extra:
                parts.append(f"Fail: {extra['failed']}")
            parts.append(f"Rate: {rate:.2f}/s")
            return " | ".join(parts)

    def set_stats_formatter(self, func: Callable[[Dict[str, Any], float], str]) -> None:
        """Set custom stats formatter: func(snap, elapsed) -> str."""
        self._format_stats = func

    def run_loop(
        self,
        worker_func: Callable[[], None],
        poll_interval: float = 0.1,
    ) -> None:
        """Run worker in thread and update UI until complete.

        Args:
            worker_func: Function to run in worker thread.
                         Should call self.set_step(), self.set_progress(), self.log()
            poll_interval: How often to update UI (seconds).
        """
        self.start()

        def wrapped_worker() -> None:
            try:
                worker_func()
            except Exception as e:
                self._error = str(e)
                self.set_step(f"Error: {e}")
                self.log(f"Error: {e}")
            finally:
                self.set_state(running=False)

        threading.Thread(target=wrapped_worker, daemon=True).start()

        format_stats = self._format_stats or self._default_format_stats

        while True:
            self._event.wait(timeout=poll_interval)
            self._event.clear()

            with self._lock:
                snap = dict(self._state)
                logs: List[str] = self._state["logs"]
                self._state["logs"] = []

            self.step_lbl.value = f"<b>{snap['step']}</b>"
            self.file_lbl.value = short(snap["file"], 70)
            self.progress.max = max(snap["total"], 1)
            self.progress.value = snap["done"]

            elapsed = time.monotonic() - snap["start"]
            self.stats_lbl.value = format_stats(snap, elapsed)

            for msg in logs:
                with self.log_out:
                    print(msg)

            if not snap["running"]:
                break

        # Show error state visually before calling on_complete
        if self._error:
            self.progress.bar_style = "danger"

        if self._on_complete:
            self._on_complete()

    def on_complete(self, func: Callable[[], None]) -> None:
        """Set callback for when run_loop completes."""
        self._on_complete = func


class SelectionUI:
    """Dropdown selection with run and rescan buttons.

    Usage:
        def load_items():
            return {"Label": "value", ...}

        sel = SelectionUI("Archive:", load_items, "Extract")
        sel.on_run(lambda value: ...)
        sel.display()

    Attributes:
        dropdown: The dropdown widget.
        btn_run: The run button widget.
        btn_scan: The rescan button widget.
    """

    def __init__(
        self,
        label: str,
        load_func: Callable[[], Dict[str, Any]],
        run_label: str = "Run",
    ) -> None:
        """Initialize selection UI.

        Args:
            label: Dropdown description label.
            load_func: Function returning {display_label: value} dict.
            run_label: Label for run button.
        """
        self.load_func = load_func
        self._run_label = run_label
        self._on_run_callback: Optional[Callable[[Any], None]] = None

        opts = load_func()

        self.dropdown = w.Dropdown(
            options=opts, description=label, layout=w.Layout(width="100%")
        )
        self.btn_run = w.Button(description=run_label, button_style="primary")
        self.btn_scan = w.Button(description="Rescan")

        self.btn_run.on_click(self._handle_run)
        self.btn_scan.on_click(self._handle_rescan)

        if not opts:
            self.btn_run.disabled = True

    def _handle_run(self, _: Any) -> None:
        if self._on_run_callback and self.dropdown.value:
            self._on_run_callback(self.dropdown.value)

    def _handle_rescan(self, _: Any) -> None:
        self.btn_scan.description = "Scanning..."
        self.btn_scan.icon = "spinner"
        self.btn_scan.disabled = True
        self.refresh()
        self.btn_scan.description = "Rescan"
        self.btn_scan.icon = ""
        self.btn_scan.disabled = False

    def on_run(self, callback: Callable[[Any], None]) -> None:
        """Set run callback: callback(selected_value)."""
        self._on_run_callback = callback

    def refresh(self) -> None:
        """Reload options from load_func."""
        opts = self.load_func()
        self.dropdown.options = opts
        self.btn_run.disabled = not opts

    def set_running(self, running: bool) -> None:
        """Enable/disable controls during operation."""
        self.btn_run.disabled = running
        self.btn_scan.disabled = running
        self.dropdown.disabled = running
        if running:
            self.btn_run.description = f"{self._run_label}ing..."
            self.btn_run.icon = "spinner"
        else:
            self.btn_run.description = self._run_label
            self.btn_run.icon = ""

    @property
    def value(self) -> Any:
        """Get currently selected value."""
        return self.dropdown.value

    @property
    def widget(self) -> w.HBox:
        """Get the HBox containing buttons."""
        return w.HBox([self.btn_run, self.btn_scan])


class RangeSelectionUI:
    """Range selection with from/to dropdowns and preview.

    Used for selecting a range of files to process.

    Attributes:
        from_dd: From dropdown widget.
        to_dd: To dropdown widget.
        show_all: Show all checkbox widget.
        preview: Preview output widget.
        btn_run: Run button widget.
    """

    PREVIEW_LIMIT: int = 10

    def __init__(
        self,
        label_from: str = "From:",
        label_to: str = "To:",
        run_label: str = "Run",
    ) -> None:
        """Initialize range selection UI."""
        self._run_label = run_label
        self._on_run_callback: Optional[Callable[[List[str]], None]] = None
        self._files: List[str] = []

        self.from_dd = w.Dropdown(
            options=[], description=label_from, layout=w.Layout(width="100%")
        )
        self.to_dd = w.Dropdown(
            options=[], description=label_to, layout=w.Layout(width="100%")
        )
        self.show_all = w.Checkbox(value=False, description="Show full list")
        self.selection_info = w.HTML("")
        self.preview = w.Output(
            layout=w.Layout(
                max_height="220px",
                overflow="auto",
                border="1px solid #ccc",
                padding="5px",
            )
        )
        self.btn_run = w.Button(description=run_label, button_style="primary")

        self.from_dd.observe(self._update_preview, names="value")
        self.to_dd.observe(self._update_preview, names="value")
        self.show_all.observe(self._update_preview, names="value")
        self.btn_run.on_click(self._handle_run)

    def set_files(self, files: List[str]) -> None:
        """Set the list of files and update UI."""
        self._files = files
        if not files:
            self.from_dd.options = [("0000 (empty)", 1)]
            self.to_dd.options = [("0000 (empty)", 1)]
            self.from_dd.value = 1
            self.to_dd.value = 1
            self.btn_run.disabled = True
            self.selection_info.value = "Selection: 0 - 0 (0 files)"
            self.preview.clear_output()
            return

        options = self._build_options(files)
        self.from_dd.options = options
        self.to_dd.options = options
        self.from_dd.value = 1
        self.to_dd.value = len(files)
        self.btn_run.disabled = False
        self._update_preview()

    def _build_options(self, files: List[str]) -> List[tuple[str, int]]:
        """Build dropdown options from file list."""
        import os

        options: List[tuple[str, int]] = []
        for i, f in enumerate(files, 1):
            label = f"{i:04d} {short(os.path.basename(f), 70)}"
            options.append((label, i))
        return options

    def get_selected_files(self) -> List[str]:
        """Get the currently selected range of files."""
        if not self._files:
            return []
        total = len(self._files)
        start_idx = max(1, min(self.from_dd.value, total))
        end_idx = max(1, min(self.to_dd.value, total))
        if end_idx < start_idx:
            start_idx, end_idx = end_idx, start_idx
        return self._files[start_idx - 1 : end_idx]

    def _update_preview(self, _: Any = None) -> None:
        """Update preview output."""
        import os

        subset = self.get_selected_files()
        count = len(subset)

        if not self._files:
            self.selection_info.value = "Selection: 0 - 0 (0 files)"
            self.preview.clear_output()
            return

        start_idx = self.from_dd.value
        end_idx = self.to_dd.value
        suffix = "s" if count != 1 else ""
        self.selection_info.value = (
            f"Selection: {start_idx} - {end_idx} ({count} file{suffix})"
        )

        self.preview.clear_output()
        with self.preview:
            if not subset:
                print("No files in selection.")
                return
            if self.show_all.value or count <= self.PREVIEW_LIMIT * 2:
                for f in subset:
                    print(os.path.basename(f))
            else:
                for f in subset[: self.PREVIEW_LIMIT]:
                    print(os.path.basename(f))
                print("...")
                for f in subset[-self.PREVIEW_LIMIT :]:
                    print(os.path.basename(f))

    def _handle_run(self, _: Any) -> None:
        if self._on_run_callback:
            files = self.get_selected_files()
            if files:
                self._on_run_callback(files)

    def on_run(self, callback: Callable[[List[str]], None]) -> None:
        """Set run callback: callback(selected_files_list)."""
        self._on_run_callback = callback

    def set_running(self, running: bool) -> None:
        """Enable/disable controls during operation."""
        self.from_dd.disabled = running
        self.to_dd.disabled = running
        self.show_all.disabled = running
        self.btn_run.disabled = running
        if running:
            self.btn_run.description = "Running..."
            self.btn_run.icon = "spinner"
        else:
            self.btn_run.description = self._run_label
            self.btn_run.icon = ""

    @property
    def widget(self) -> w.VBox:
        """Get the VBox containing all selection widgets."""
        return w.VBox(
            [
                self.from_dd,
                self.to_dd,
                self.show_all,
                self.selection_info,
                self.preview,
                self.btn_run,
            ]
        )
