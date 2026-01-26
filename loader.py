"""Drive Scripts Loader - Run in Google Colab to access tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Callable, List

import ipywidgets as w

if TYPE_CHECKING:
    from tools.base import BaseTool
from IPython.display import clear_output, display

REPO_URL = "https://github.com/JohnDeved/drive-scripts.git"
REPO_DIR = "/content/drive-scripts"
DRIVE_ROOT = "/content/drive"


def cleanup_stale_files() -> None:
    """Remove stale .py files that conflict with new package structure."""
    stale_files = [
        os.path.join(REPO_DIR, "tools", "shared.py"),
        os.path.join(REPO_DIR, "tools", "ui.py"),
        os.path.join(REPO_DIR, "tools", "extract.py"),
        os.path.join(REPO_DIR, "tools", "verify.py"),
    ]
    for f in stale_files:
        if os.path.isfile(f):
            os.remove(f)

    # Clear Python cache
    for cache_dir in ["__pycache__", ".pyc"]:
        cache_path = os.path.join(REPO_DIR, "tools", cache_dir)
        if os.path.isdir(cache_path):
            shutil.rmtree(cache_path, ignore_errors=True)

    # Clear tools from sys.modules to force reimport
    for name in list(sys.modules.keys()):
        if name.startswith("tools"):
            del sys.modules[name]


def ensure_repo() -> None:
    """Clone or pull the repository with visible output."""
    if os.path.exists(REPO_DIR):
        print("Pulling latest...", flush=True)
        subprocess.run(["git", "-C", REPO_DIR, "pull"], check=False)
        # Clean up stale files after pull
        cleanup_stale_files()
    else:
        print("Cloning repository...", flush=True)
        subprocess.run(["git", "clone", "--depth=1", REPO_URL, REPO_DIR], check=False)

    # Ensure repo is in path
    if REPO_DIR not in sys.path:
        sys.path.insert(0, REPO_DIR)


def ensure_drive() -> bool:
    """Mount Google Drive with status message."""
    print("Mounting Drive...", end=" ", flush=True)
    if os.path.exists(f"{DRIVE_ROOT}/Shareddrives"):
        print("already mounted")
        return True
    try:
        from google.colab import drive

        drive.mount(DRIVE_ROOT)
        ok = os.path.exists(f"{DRIVE_ROOT}/Shareddrives")
        print("done" if ok else "failed")
        return ok
    except ImportError:
        print("skipped (not in Colab)")
        return False


def ensure_deps() -> None:
    """Install apt packages and Python modules."""
    print("Installing dependencies...", end=" ", flush=True)

    # apt packages (silent install)
    bins = {"7z": "p7zip-full", "unrar": "unrar", "unzip": "unzip"}
    missing = [pkg for cmd, pkg in bins.items() if shutil.which(cmd) is None]
    if missing:
        subprocess.run(
            ["apt-get", "install", "-qq", *missing],
            capture_output=True,
            check=False,
        )

    # Python packages from requirements.txt
    req_file = os.path.join(REPO_DIR, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run(
            ["pip", "install", "-q", "-r", req_file],
            capture_output=True,
            check=False,
        )

    print("done")


def get_version() -> str:
    """Get current git commit hash."""
    result = subprocess.run(
        ["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "dev"


def main() -> None:
    """Bootstrap and display tool selection menu."""
    # Setup with visible logging
    ensure_repo()
    drive_ok = ensure_drive()
    ensure_deps()

    # Clear setup logs and show clean UI
    clear_output(wait=True)

    version = get_version()

    # Import registry after ensuring repo is in path
    from tools.registry import reload_tools

    # Discover available tools
    tools = reload_tools()

    # Import tool switch functions
    from tools.shared import clear_tool_switch, request_tool_switch

    # UI
    title = w.HTML(
        f'<h2>Drive Scripts</h2><small style="color:#666">v{version}</small>'
    )
    status = w.HTML(
        f'<span style="color:{"#1a7f37" if drive_ok else "#b42318"}">'
        f"Drive: {'Mounted' if drive_ok else 'Not mounted'}</span>"
    )

    output = w.Output()

    # Track active button state for cleanup
    active_button: List[w.Button | None] = [None]
    button_originals: dict[int, tuple[str, str]] = {}  # id -> (icon, description)

    # Create buttons dynamically from discovered tools
    buttons: List[w.Button] = []
    for tool in tools:
        btn = w.Button(
            description=tool.title,
            button_style=tool.button_style,
            icon=tool.icon,
            layout=w.Layout(width="180px", height="40px"),
        )
        buttons.append(btn)
        # Store original state
        button_originals[id(btn)] = (btn.icon, btn.description)

        def make_handler(t: "BaseTool", b: w.Button) -> "Callable[[w.Button], None]":
            """Create click handler with proper closure."""

            def handler(_: w.Button) -> None:
                # Signal any running tool to exit
                request_tool_switch()

                # Reset previous active button if any
                if active_button[0] is not None and active_button[0] is not b:
                    prev = active_button[0]
                    orig = button_originals.get(id(prev))
                    if orig:
                        prev.icon, prev.description = orig
                    prev.disabled = False

                # Set this button as active
                active_button[0] = b
                b.disabled = True
                b.icon = "spinner"
                b.description = "Loading..."

                # Clear the switch flag before starting new tool
                clear_tool_switch()

                output.clear_output()
                with output:
                    try:
                        # Reload tools to pick up any updates
                        from tools.registry import reload_tools as _reload

                        _reload()
                        t.main()
                    except Exception as e:
                        print(f"Error: {e}")

                # Only reset if still the active button (not switched away)
                if active_button[0] is b:
                    orig = button_originals.get(id(b))
                    if orig:
                        b.icon, b.description = orig
                    b.disabled = False
                    active_button[0] = None

            return handler

        btn.on_click(make_handler(tool, btn))

    # Layout
    header = w.VBox([title, status], layout=w.Layout(margin="0 0 10px 0"))
    button_row = w.HBox(buttons, layout=w.Layout(gap="10px"))
    ui = w.VBox([header, button_row, output])

    display(ui)


# Run when executed
if __name__ == "__main__" or "get_ipython" in dir():
    main()
