"""Organize Tool: Rename and organize files using TitleDB."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import ipywidgets as w
import requests
from IPython.display import clear_output, display

from config import config
from tools.base import BaseTool
from tools.shared import (
    CheckboxListUI,
    ProgressUI,
    ensure_drive_ready,
    ensure_python_modules,
)

TITLEDB_URL = "https://raw.githubusercontent.com/blawar/titledb/master/US.en.json"
KEY_FILES = ["prod.keys", "title.keys", "keys.txt"]


def _sanitize_filename(name: str) -> str:
    """Sanitize filename for filesystem."""
    # Replace invalid chars with -
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    # Remove trailing/leading spaces
    name = name.strip()
    return name


def _stage_keys() -> Tuple[bool, str]:
    """Stage keys for nsz."""
    os.makedirs(config.local_keys_dir, exist_ok=True)
    for name in KEY_FILES:
        src = os.path.join(config.keys_dir, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(config.local_keys_dir, name))
    prod = os.path.join(config.local_keys_dir, "prod.keys")
    return os.path.isfile(prod) and os.path.getsize(prod) > 0, prod


def _load_organize_deps(key_path: str | None = None) -> None:
    """Load dependencies."""
    ensure_python_modules(["nsz", "requests"])
    from nsz.nut import Keys  # type: ignore

    if key_path:
        try:
            Keys.load(key_path)
        except Exception:
            pass


def _download_titledb(progress: ProgressUI) -> Dict[str, str]:
    """Download and parse TitleDB. Returns TitleID -> Name map."""
    cache_path = Path(config.temp_dir) / "titledb.json"
    os.makedirs(config.temp_dir, exist_ok=True)

    if not cache_path.exists() or (time.time() - cache_path.stat().st_mtime > 86400):
        progress.log("Downloading TitleDB...")
        try:
            response = requests.get(TITLEDB_URL, stream=True, timeout=30)
            response.raise_for_status()
            with open(cache_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            progress.log(f"Failed to download TitleDB: {e}")
            if not cache_path.exists():
                return {}

    progress.log("Parsing TitleDB...")
    db: Dict[str, str] = {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Structure: { "NSUID": { "id": "TITLEID", "name": "NAME", ... } }
            for item in data.values():
                if isinstance(item, dict) and "id" in item and "name" in item:
                    tid = item["id"].upper()
                    name = item["name"]
                    if tid and name:
                        db[tid] = name
    except Exception as e:
        progress.log(f"Failed to parse TitleDB: {e}")
        return {}

    return db


def _get_file_info(path: str) -> Tuple[Optional[str], Optional[int]]:
    """Extract TitleID and Version from file."""
    # We must import inside function to ensure deps are loaded
    from nsz.FileExistingChecks import ExtractTitleIDAndVersion  # type: ignore

    class Args:
        parseCnmt = True
        alwaysParseCnmt = False

    try:
        # returns (titleId, version) or None
        res = ExtractTitleIDAndVersion(path, Args())
        if res:
            return res[0], res[1]
    except Exception:
        pass

    return None, None


class OrganizeTool(BaseTool):
    """Organize and rename files using TitleDB."""

    name = "organize"
    title = "Organize & Rename"
    description = "Rename files based on TitleDB (Name [TitleID] [vVersion])"
    icon = "tags"
    button_style = "success"
    order = 5

    def ensure_deps(self) -> None:
        ensure_python_modules(["nsz", "requests"])

    def main(self) -> None:
        ensure_drive_ready()

        # Step 1: Select files
        selection = CheckboxListUI(run_label="Analyze Files")

        # Filter for Switch files
        all_files = []
        for r, _, files in os.walk(config.switch_dir):
            for f in files:
                if f.lower().endswith((".nsp", ".nsz", ".xci", ".xcz")):
                    all_files.append(os.path.join(r, f))

        all_files.sort()
        selection.set_items(all_files)

        output_area = w.Output()

        def show_plan(plan: List[Tuple[str, str]], titledb: Dict[str, str]):
            """Show the rename plan and Confirm button."""
            selection.widget.layout.display = "none"

            # Build plan display
            items = []
            valid_plan = []

            style = "<style>.diff-old { color: #f44336; } .diff-new { color: #4caf50; } .diff-arrow { color: #999; padding: 0 10px; }</style>"
            items.append(w.HTML(style))
            items.append(w.HTML("<h3>Proposed Changes</h3>"))

            if not plan:
                items.append(w.HTML("No files need renaming."))
                btn_cancel = w.Button(description="Back", icon="arrow-left")

                def on_back(_):
                    output_area.clear_output()
                    selection.widget.layout.display = "block"

                btn_cancel.on_click(on_back)
                items.append(btn_cancel)
            else:
                grid = w.GridspecLayout(len(plan) + 1, 1)

                for src, dst in plan:
                    if src != dst:
                        valid_plan.append((src, dst))
                        src_name = os.path.basename(src)
                        dst_name = os.path.basename(dst)

                        html = f"""
                        <div style="padding: 5px; border-bottom: 1px solid #444;">
                            <div class="diff-old">{src_name}</div>
                            <div class="diff-arrow">⬇</div>
                            <div class="diff-new">{dst_name}</div>
                        </div>
                        """
                        items.append(w.HTML(html))

                if not valid_plan:
                    items.append(
                        w.HTML("All selected files are already correctly named.")
                    )

                # Buttons
                btn_box = w.HBox()
                btn_cancel = w.Button(description="Cancel", icon="times")
                btn_apply = w.Button(
                    description="Apply Changes", button_style="success", icon="check"
                )

                def on_cancel(_):
                    output_area.clear_output()
                    selection.widget.layout.display = "block"
                    selection.set_running(False)

                def on_apply(_):
                    output_area.clear_output()
                    _execute_rename(valid_plan)

                btn_cancel.on_click(on_cancel)
                btn_apply.on_click(on_apply)

                if valid_plan:
                    btn_box.children = [btn_cancel, btn_apply]
                else:
                    btn_box.children = [btn_cancel]

                items.append(btn_box)

            ui = w.VBox(items)
            with output_area:
                clear_output(wait=True)
                display(ui)

        def _execute_rename(plan: List[Tuple[str, str]]):
            progress = ProgressUI("Renaming", run_label="Renaming...", show_bytes=False)
            display(progress.title, progress.progress_box)

            success_count = 0
            fail_count = 0

            total = len(plan)
            for i, (src, dst) in enumerate(plan, 1):
                progress.set_step(f"Renaming ({i}/{total})")
                src_name = os.path.basename(src)
                dst_name = os.path.basename(dst)

                try:
                    # Ensure dest dir exists (it's the same usually)
                    # We might handle subdirs later, for now assuming flatten or same dir
                    # But dst is full path
                    os.rename(src, dst)
                    progress.log(f"OK   {src_name} -> {dst_name}")
                    success_count += 1
                except Exception as e:
                    progress.log(f"FAIL {src_name}: {e}")
                    fail_count += 1

                progress.set_progress(i, total, dst_name)

            progress.finish(success=(fail_count == 0))
            progress.log(f"Done: {success_count} renamed, {fail_count} failed.")

            # Return to list
            time.sleep(2)
            selection.set_running(False)
            selection.widget.layout.display = "block"
            # Refresh list
            all_files_new = []
            for r, _, files in os.walk(config.switch_dir):
                for f in files:
                    if f.lower().endswith((".nsp", ".nsz", ".xci", ".xcz")):
                        all_files_new.append(os.path.join(r, f))
            all_files_new.sort()
            selection.set_items(all_files_new)

        def on_analyze(selected: List[str]):
            if not selected:
                return

            selection.set_running(True)
            output_area.clear_output()

            progress = ProgressUI("Analyzing", show_bytes=False)
            with output_area:
                display(progress.title, progress.progress_box)

            try:
                # 1. Setup
                progress.set_step("Loading dependencies...")
                ok, path = _stage_keys()
                _load_organize_deps(path if ok else None)

                # 2. Download DB
                progress.set_step("Loading TitleDB...")
                titledb = _download_titledb(progress)
                if not titledb:
                    progress.log("Warning: Empty TitleDB, renaming might fail for IDs.")

                # 3. Analyze
                plan = []
                total = len(selected)

                for i, path in enumerate(selected, 1):
                    progress.set_step(f"Analyzing ({i}/{total})")
                    progress.set_progress(i, total, os.path.basename(path))

                    tid, ver = _get_file_info(path)

                    if tid:
                        # Find name
                        name = titledb.get(tid)

                        # Fallback: if not found, try base ID for updates
                        # Assuming update ID has flags set
                        if not name:
                            # Try masking: Ends with 000 usually
                            # Simple heuristic: last 3 chars 000
                            # But TID is string hex.
                            pass

                        if name:
                            safe_name = _sanitize_filename(name)
                            ext = os.path.splitext(path)[1].lower()

                            # Format: Name [TitleID] [vVersion].ext
                            # Check if version is valid
                            ver_str = ""
                            if ver is not None:
                                ver_str = f" [v{ver}]"

                            new_name = f"{safe_name} [{tid}]{ver_str}{ext}"
                            new_path = os.path.join(os.path.dirname(path), new_name)

                            if new_path != path:
                                plan.append((path, new_path))
                        else:
                            progress.log(
                                f"Skipping {os.path.basename(path)}: TitleID {tid} not in DB"
                            )
                    else:
                        progress.log(
                            f"Skipping {os.path.basename(path)}: Could not identify"
                        )

                output_area.clear_output()
                show_plan(plan, titledb)

            except Exception as e:
                progress.log(f"Error: {e}")
                progress.finish(success=False)
                selection.set_running(False)

        selection.on_run(on_analyze)

        ui = w.VBox([selection.widget, output_area])
        clear_output(wait=True)
        display(ui)
