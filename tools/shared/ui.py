"""Shared UI components for drive-scripts tools."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import ipywidgets as w
from IPython.display import display

try:
    from jupyter_ui_poll import ui_events

    HAS_UI_POLL = True
except ImportError:
    HAS_UI_POLL = False
    ui_events = None  # type: ignore

from .utils import fmt_bytes, fmt_time, short

# Debug flag - set to True to see polling messages
_DEBUG_POLL = False

# Global flag to signal all tools to exit their polling loops
_tool_switch_requested = False


def request_tool_switch() -> None:
    """Signal all active tools to exit their polling loops."""
    global _tool_switch_requested
    _tool_switch_requested = True


def clear_tool_switch() -> None:
    """Clear the tool switch flag after switching."""
    global _tool_switch_requested
    _tool_switch_requested = False


def is_tool_switch_requested() -> bool:
    """Check if a tool switch has been requested."""
    return _tool_switch_requested


def _poll_with_events(interval: float = 0.1) -> None:
    """Sleep while processing UI events.

    Uses jupyter_ui_poll if available, otherwise falls back to time.sleep.
    """
    if HAS_UI_POLL and ui_events is not None:
        try:
            with ui_events() as poll:
                poll(10)  # Process up to 10 pending UI events
        except Exception as e:
            if _DEBUG_POLL:
                print(f"[poll] Error: {e}")
        time.sleep(interval)
    else:
        if _DEBUG_POLL:
            print("[poll] jupyter_ui_poll not available, using time.sleep")
        time.sleep(interval)


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

        # Confirmation state (for cross-thread communication)
        self._confirm_request: Optional[Dict[str, Any]] = None  # Request from worker
        self._confirm_response: Optional[bool] = None  # Response to worker
        self._confirm_event = threading.Event()  # Worker waits on this
        self._confirm_ui: Optional[w.VBox] = None  # UI container (set by caller)

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
                f"{fmt_bytes(rate)}/s | ETA: {fmt_time(eta)} | "
                f"Runtime: {fmt_time(elapsed)}"
            )
        else:
            rate = done / elapsed if elapsed > 0 else 0
            extra = snap.get("extra", {})
            parts = [f"Done: {done}/{total}"]
            if "passed" in extra:
                parts.append(f"Pass: {extra['passed']}")
            if "failed" in extra:
                parts.append(f"Fail: {extra['failed']}")
            parts.append(f"Runtime: {fmt_time(elapsed)}")
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

        Uses jupyter_ui_poll to process widget events while polling.

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
            _poll_with_events(poll_interval)
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

            # Check for tool switch request - exit immediately
            if is_tool_switch_requested():
                return

            # Check for confirmation request
            confirm_req = None
            with self._lock:
                if self._confirm_request:
                    confirm_req = self._confirm_request
                    self._confirm_request = None

            if confirm_req:
                # Show dialog and wait for response
                self._show_confirmation_dialog_blocking(confirm_req)
                continue

            if not snap["running"]:
                # Done - call completion
                if self._error:
                    self.progress.bar_style = "danger"
                if self._on_complete:
                    self._on_complete()
                return

    def _show_confirmation_dialog_blocking(self, data: Dict[str, Any]) -> None:
        """Show confirmation dialog and wait for response using ui_poll."""
        orig_size = data["orig_size"]
        new_size = data["new_size"]
        filename = data["filename"]
        saved = orig_size - new_size
        percent = (saved / orig_size) * 100 if orig_size > 0 else 0

        html = w.HTML(
            f"<h4>Confirm Compression</h4>"
            f"<p><b>File:</b> {filename}</p>"
            f"<p>Original: {fmt_bytes(orig_size)}<br>"
            f"Compressed: {fmt_bytes(new_size)}<br>"
            f"<span style='color: #4caf50'>Saved: {fmt_bytes(saved)} ({percent:.1f}%)</span></p>"
        )

        btn_keep = w.Button(
            description="Keep & Upload", button_style="success", icon="check"
        )
        btn_discard = w.Button(
            description="Discard", button_style="danger", icon="times"
        )

        responded = [False]

        def on_keep(_):
            with self._lock:
                self._confirm_response = True
            responded[0] = True

        def on_discard(_):
            with self._lock:
                self._confirm_response = False
            responded[0] = True

        btn_keep.on_click(on_keep)
        btn_discard.on_click(on_discard)

        if self._confirm_ui:
            self._confirm_ui.children = [html, w.HBox([btn_keep, btn_discard])]
            self._confirm_ui.layout.display = "block"

        # Poll until user responds
        while not responded[0]:
            _poll_with_events(0.1)

        # Hide dialog
        if self._confirm_ui:
            self._confirm_ui.layout.display = "none"
            self._confirm_ui.children = []

        self._confirm_event.set()

    def on_complete(self, func: Callable[[], None]) -> None:
        """Set callback for when run_loop completes."""
        self._on_complete = func

    def set_confirm_ui(self, container: w.VBox) -> None:
        """Set the VBox container for confirmation dialogs."""
        self._confirm_ui = container

    def request_confirmation(self, data: Dict[str, Any]) -> bool:
        """Request confirmation from user (call from worker thread).

        Args:
            data: Dict with keys 'orig_size', 'new_size', 'filename'

        Returns:
            True if user confirmed, False if discarded.
        """
        with self._lock:
            self._confirm_request = data
            self._confirm_response = None
        self._confirm_event.clear()
        self._event.set()  # Wake up main loop

        # Wait for response (with timeout to prevent permanent hang)
        if not self._confirm_event.wait(timeout=300):  # 5 min timeout
            return False  # Timeout = discard

        with self._lock:
            return self._confirm_response or False


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


class CheckboxListUI:
    """Paginated checkbox list for selecting multiple items.

    Attributes:
        PAGE_SIZE: Number of items per page (default 5).
    """

    PAGE_SIZE: int = 5

    def __init__(self, run_label: str = "Run") -> None:
        """Initialize checkbox list UI.

        Args:
            run_label: Label for run button.
        """
        self._items: List[str] = []
        self._filtered_indices: List[int] = []
        self._selected: Set[int] = set()
        self._file_meta: Dict[int, Tuple[int, float]] = {}  # idx -> (size, mtime)
        self._page: int = 0
        self._run_label = run_label
        self._on_run_callback: Optional[Callable[[List[str]], None]] = None
        self._on_rescan_callback: Optional[Callable[[], None]] = None
        self._is_loading: bool = False
        self._cancel_requested: bool = False

        # Header
        self.header = w.HTML(
            "<b>Files (0)</b>",
            layout=w.Layout(margin="0 0 0 10px"),
        )
        self.btn_all = w.Button(description="All", layout=w.Layout(width="60px"))
        self.btn_none = w.Button(description="None", layout=w.Layout(width="60px"))
        self.btn_invert = w.Button(description="Invert", layout=w.Layout(width="70px"))

        self.btn_all.on_click(self._on_select_all)
        self.btn_none.on_click(self._on_select_none)
        self.btn_invert.on_click(self._on_invert)

        # Loading indicator (inline with header)
        self.loading_status = w.HTML("")

        # Search
        self.search_input = w.Text(
            placeholder="Type to filter...",
            continuous_update=True,
            layout=w.Layout(width="100%"),
        )
        self.search_input.observe(self._on_search_change, names="value")

        # Checkboxes (fixed pool) with metadata labels
        self._cb_items: List[Tuple[w.Checkbox, w.HTML, w.HBox]] = []
        self._checkboxes: List[w.Checkbox] = []  # For observers logic compatibility

        for _ in range(self.PAGE_SIZE):
            # Checkbox
            cb = w.Checkbox(
                value=False,
                indent=False,
                layout=w.Layout(width="30px", margin="2px 0 0 0"),
            )
            # Info block (HTML)
            info = w.HTML(layout=w.Layout(width="100%"))

            # Container: Row with Checkbox + Info
            # Use rgba for border to work on both light/dark backgrounds
            container = w.HBox(
                [cb, info],
                layout=w.Layout(
                    border="1px solid rgba(128, 128, 128, 0.4)",
                    border_radius="4px",
                    padding="8px 12px",
                    margin="0 0 6px 0",
                    align_items="flex-start",
                    width="98%",
                ),
            )
            self._cb_items.append((cb, info, container))
            self._checkboxes.append(cb)

        # Cache handlers to avoid creating new closures constantly
        self._cb_handlers = [self._make_cb_handler(i) for i in range(self.PAGE_SIZE)]

        # Attach observers
        for i, cb in enumerate(self._checkboxes):
            cb.observe(self._cb_handlers[i], names="value")

        self._cb_container = w.VBox([item[2] for item in self._cb_items])

        # Pagination
        self.btn_prev = w.Button(description="◀", layout=w.Layout(width="40px"))
        self.btn_next = w.Button(description="▶", layout=w.Layout(width="40px"))
        self.btn_prev.on_click(self._on_prev)
        self.btn_next.on_click(self._on_next)

        self._page_btns: List[w.Button] = []
        self._page_container = w.HBox([])

        # Footer
        self.selection_info = w.HTML("Selected: 0 / 0")
        self.btn_run = w.Button(description=run_label, button_style="info")
        self.btn_rescan = w.Button(description="Rescan")

        self.btn_run.on_click(self._handle_run)
        self.btn_rescan.on_click(self._handle_rescan)

        # Build main container (cached for hide/show)
        self._container = w.VBox(
            [
                w.HBox(
                    [
                        self.btn_all,
                        self.btn_none,
                        self.btn_invert,
                        self.header,
                        self.loading_status,
                    ],
                    layout=w.Layout(align_items="center", margin="0 0 10px 0"),
                ),
                self.search_input,
                self._cb_container,
                w.HBox(
                    [self._page_container],
                    layout=w.Layout(justify_content="center", margin="10px 0"),
                ),
                self.selection_info,
                w.HBox([self.btn_run, self.btn_rescan]),
            ]
        )

    def _make_cb_handler(self, index: int) -> Callable[[Any], None]:
        """Create handler for checkbox at specific index in pool."""

        def handler(change: Any) -> None:
            if not change["new"] and not change["old"]:
                return  # Filter out irrelevant changes

            idx_in_filtered = self._page * self.PAGE_SIZE + index
            if idx_in_filtered < len(self._filtered_indices):
                real_idx = self._filtered_indices[idx_in_filtered]
                if change["new"]:
                    self._selected.add(real_idx)
                else:
                    self._selected.discard(real_idx)
                self._update_footer()

        return handler

    def set_items(self, items: List[str]) -> None:
        """Set file list and reset selection."""
        self._items = list(items)
        self._filtered_indices = list(range(len(items)))
        self._selected = set()
        self._page = 0
        self.search_input.value = ""

        # Reset metadata cache
        self._file_meta = {}
        self._update_display()

    def set_loading(self, loading: bool) -> None:
        """Show/hide loading spinner."""
        self._is_loading = loading
        # Always show the checkbox container if we have items
        if self._items:
            self._cb_container.layout.display = "block"
        else:
            self._cb_container.layout.display = "none" if loading else "block"
        # Only disable rescan during loading, allow other interactions
        self.btn_rescan.disabled = loading
        # Run button depends on selection, not loading state
        self.btn_run.disabled = len(self._selected) == 0
        if not loading:
            self.loading_status.value = ""
            self._cancel_requested = False

    def cancel_loading(self) -> None:
        """Cancel any ongoing loading operation (call when switching tools)."""
        self._cancel_requested = True

    def load_items_async(
        self,
        loader_func: Callable[[], List[str]],
        on_complete: Optional[Callable] = None,
    ) -> None:
        """Load items in background thread.

        Args:
            loader_func: Function returning list of paths.
            on_complete: Optional callback when done.
        """
        self._items = []
        self._filtered_indices = []
        self._selected = set()
        self.set_loading(True)

        def worker():
            try:
                items = loader_func()
                # Use a small delay to ensure UI updates don't collide too fast
                time.sleep(0.1)
                self.set_items(items)
            finally:
                self.set_loading(False)
                if on_complete:
                    on_complete()

        threading.Thread(target=worker, daemon=True).start()

    def load_items_progressive(
        self,
        loader_func: Callable[
            [
                Callable[[str], None],
                Optional[Callable[[str], None]],
                Optional[Callable[[], bool]],
            ],
            List[str],
        ],
        on_complete: Optional[Callable] = None,
    ) -> None:
        """Load items progressively using timer-based polling (non-blocking).

        Args:
            loader_func: Function taking on_found(path), on_scanning(path),
                         and is_cancelled() callbacks.
            on_complete: Optional callback when done.
        """
        # Cancel any previous loading
        self._cancel_requested = False

        self._items = []
        self._filtered_indices = []
        self._selected = set()
        self._file_meta = {}
        self.set_loading(True)

        # Shared state between worker and main thread
        state = {"current_dir": "", "running": True, "needs_refresh": False, "dots": 0}
        state_lock = threading.Lock()

        def on_found(path: str):
            if self._cancel_requested:
                return
            self._items.append(path)
            term = self.search_input.value.lower()
            real_idx = len(self._items) - 1
            if not term or term in os.path.basename(path).lower():
                self._filtered_indices.append(real_idx)

            with state_lock:
                state["needs_refresh"] = True

        def on_scanning(dir_name: str):
            with state_lock:
                state["current_dir"] = dir_name

        def is_cancelled() -> bool:
            return self._cancel_requested

        def worker():
            try:
                loader_func(on_found, on_scanning, is_cancelled)
            finally:
                with state_lock:
                    state["running"] = False
                    state["current_dir"] = ""

        def do_poll_update():
            """Single poll iteration. Returns True to continue, False to stop."""
            # Check for cancellation
            if self._cancel_requested:
                with state_lock:
                    state["running"] = False
                self._update_display()
                self.set_loading(False)
                if on_complete:
                    on_complete()
                return False  # Stop polling

            with state_lock:
                state["dots"] = (state["dots"] + 1) % 4
                dots = state["dots"]
                count = len(self._items)
                current_dir = state.get("current_dir", "")
                running = state["running"]
                needs_refresh = state["needs_refresh"]
                state["needs_refresh"] = False

            # Animate dots
            left_dots = "." * dots
            right_dots = "." * (3 - dots)

            # Build status text
            count_str = f"Found {count}" if count > 0 else ""
            scan_str = f"{left_dots}Scanning{right_dots}"
            dir_str = f"| {current_dir}" if current_dir else ""

            if count_str:
                status = f"{count_str} | {scan_str} {dir_str}"
            else:
                status = f"{scan_str} {dir_str}"

            # Update loading status in header
            self.loading_status.value = (
                f"<span style='color: #888; font-size: 0.85em; margin-left: 10px; white-space: nowrap;'>"
                f"<i class='fa fa-spinner fa-spin' style='margin-right: 6px;'></i>"
                f"{status}</span>"
            )

            # Refresh the file list display if new items were found
            if needs_refresh:
                self._update_display()
                self._cb_container.layout.display = "block"

            # Check for tool switch request - exit immediately
            if is_tool_switch_requested():
                self._cancel_requested = True
                self.set_loading(False)
                return False  # Stop polling

            if not running:
                # Done
                self._update_display()
                self.set_loading(False)
                if on_complete:
                    on_complete()
                return False  # Stop polling

            return True  # Continue polling

        # Start worker thread
        threading.Thread(target=worker, daemon=True).start()

        # Poll loop with UI events processing
        while do_poll_update():
            _poll_with_events(0.2)

    def _ensure_metadata(self, indices: List[int]) -> None:
        """Fetch metadata for specific indices if missing."""
        for idx in indices:
            if idx not in self._file_meta:
                try:
                    path = self._items[idx]
                    st = os.stat(path)
                    self._file_meta[idx] = (st.st_size, st.st_mtime)
                except OSError:
                    self._file_meta[idx] = (0, 0.0)

    def get_selected(self) -> List[str]:
        """Return list of selected file paths."""
        return [self._items[i] for i in sorted(self._selected)]

    def _on_search_change(self, change: Any) -> None:
        """Filter items based on search term."""
        term = change["new"].lower()
        if not term:
            self._filtered_indices = list(range(len(self._items)))
        else:
            self._filtered_indices = [
                i
                for i, item in enumerate(self._items)
                if term in os.path.basename(item).lower()
            ]
        self._page = 0
        self._update_display()

    def _update_display(self) -> None:
        """Sync widgets with current state."""
        total = len(self._items)
        filtered_count = len(self._filtered_indices)

        if total == filtered_count:
            self.header.value = f"<b>Files ({total})</b>"
        else:
            self.header.value = f"<b>Files ({filtered_count} / {total})</b>"

        # Update checkboxes
        start = self._page * self.PAGE_SIZE

        # Ensure metadata for current page is loaded
        visible_indices = [
            self._filtered_indices[i]
            for i in range(start, min(start + self.PAGE_SIZE, filtered_count))
        ]
        self._ensure_metadata(visible_indices)

        for i, (cb, info, container) in enumerate(self._cb_items):
            idx_in_filtered = start + i
            if idx_in_filtered < filtered_count:
                real_idx = self._filtered_indices[idx_in_filtered]
                container.layout.display = "flex"

                # Update checkbox state
                cb.unobserve(self._cb_handlers[i], names="value")
                cb.value = real_idx in self._selected
                cb.observe(self._cb_handlers[i], names="value")

                # Get data
                filename = os.path.basename(self._items[real_idx])
                size, mtime = self._file_meta.get(real_idx, (0, 0.0))
                size_str = fmt_bytes(size)
                date_str = (
                    datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    if mtime > 0
                    else "unknown"
                )

                # Set HTML content
                # Use inherit colors and opacity for dark mode compatibility
                # CSS ellipsis for text overflow
                info.value = (
                    f"<div style='line-height: 1.4; color: inherit; overflow: hidden;'>"
                    f"<div style='font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{filename}</div>"
                    f"<div style='font-size: 0.85em; opacity: 0.7;'>{size_str} &middot; {date_str}</div>"
                    f"</div>"
                )
            else:
                container.layout.display = "none"

        # Update pagination buttons
        num_pages = (filtered_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        self.btn_prev.disabled = self._page <= 0
        self.btn_next.disabled = self._page >= num_pages - 1

        self._update_page_buttons(num_pages)
        self._update_footer()

    def _update_page_buttons(self, num_pages: int) -> None:
        """Update page number buttons."""
        self._page_container.children = [
            self.btn_prev,
            w.HTML(
                f"&nbsp;&nbsp;Page {self._page + 1} / {max(1, num_pages)}&nbsp;&nbsp;"
            ),
            self.btn_next,
        ]

    def _update_footer(self) -> None:
        """Update selection count."""
        count = len(self._selected)
        total = len(self._items)
        self.selection_info.value = f"Selected: {count} / {total}"
        self.btn_run.disabled = count == 0

    def _on_prev(self, _: Any) -> None:
        if self._page > 0:
            self._page -= 1
            self._update_display()

    def _on_next(self, _: Any) -> None:
        total = len(self._items)
        num_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        if self._page < num_pages - 1:
            self._page += 1
            self._update_display()

    def _on_select_all(self, _: Any) -> None:
        self._selected.update(self._filtered_indices)
        self._update_display()

    def _on_select_none(self, _: Any) -> None:
        self._selected.difference_update(self._filtered_indices)
        self._update_display()

    def _on_invert(self, _: Any) -> None:
        for idx in self._filtered_indices:
            if idx in self._selected:
                self._selected.remove(idx)
            else:
                self._selected.add(idx)
        self._update_display()

    def _handle_run(self, _: Any) -> None:
        # Cancel any ongoing scan before running
        self.cancel_loading()
        if self._on_run_callback:
            files = self.get_selected()
            if files:
                self._on_run_callback(files)

    def _handle_rescan(self, _: Any) -> None:
        if self._on_rescan_callback:
            self.btn_rescan.description = "Scanning..."
            self.btn_rescan.disabled = True
            self._on_rescan_callback()
            self.btn_rescan.description = "Rescan"
            self.btn_rescan.disabled = False

    def on_run(self, callback: Callable[[List[str]], None]) -> None:
        """Register run callback."""
        self._on_run_callback = callback

    def on_rescan(self, callback: Callable[[], None]) -> None:
        """Register rescan callback."""
        self._on_rescan_callback = callback

    def set_running(self, running: bool) -> None:
        """Lock/unlock UI during operation."""
        disabled = running
        self.btn_all.disabled = disabled
        self.btn_none.disabled = disabled
        self.btn_invert.disabled = disabled
        for cb in self._checkboxes:
            cb.disabled = disabled
        self.btn_prev.disabled = disabled or self._page <= 0
        self.btn_next.disabled = disabled  # Logic in update_display handles bound check
        self.btn_run.disabled = disabled
        self.btn_rescan.disabled = disabled

        if running:
            self.btn_run.description = "Running..."
            self.btn_run.icon = "spinner"
        else:
            self.btn_run.description = self._run_label
            self.btn_run.icon = ""
            self._update_display()  # Re-enable correct buttons

    def hide(self) -> None:
        """Hide the selection widget."""
        self._container.layout.display = "none"

    def show(self) -> None:
        """Show the selection widget."""
        self._container.layout.display = "block"

    @property
    def widget(self) -> w.VBox:
        """Get the main widget container."""
        return self._container
