"""Drive Scripts Loader - Run in Google Colab to access tools."""

import importlib
import os
import shutil
import subprocess
import sys

import ipywidgets as w
from IPython.display import clear_output, display

REPO_URL = "https://github.com/JohnDeved/drive-scripts.git"
REPO_DIR = "/content/drive-scripts"
DRIVE_ROOT = "/content/drive"


def ensure_repo():
    """Clone or pull the repository with visible output."""
    if os.path.exists(REPO_DIR):
        print("Pulling latest...", flush=True)
        subprocess.run(["git", "-C", REPO_DIR, "pull"])
    else:
        print("Cloning repository...", flush=True)
        subprocess.run(["git", "clone", "--depth=1", REPO_URL, REPO_DIR])

    # Ensure repo is in path
    if REPO_DIR not in sys.path:
        sys.path.insert(0, REPO_DIR)


def ensure_drive():
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


def ensure_deps():
    """Install apt packages and Python modules."""
    print("Installing dependencies...", end=" ", flush=True)

    # apt packages (silent install)
    bins = {"7z": "p7zip-full", "unrar": "unrar", "unzip": "unzip"}
    missing = [pkg for cmd, pkg in bins.items() if shutil.which(cmd) is None]
    if missing:
        subprocess.run(["apt-get", "install", "-qq"] + missing, capture_output=True)

    # Python packages from requirements.txt
    req_file = os.path.join(REPO_DIR, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run(["pip", "install", "-q", "-r", req_file], capture_output=True)

    print("done")


def get_version():
    """Get current git commit hash."""
    result = subprocess.run(
        ["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "dev"


def main():
    """Bootstrap and display tool selection menu."""
    # Setup with visible logging
    ensure_repo()
    drive_ok = ensure_drive()
    ensure_deps()

    # Clear setup logs and show clean UI
    clear_output(wait=True)

    version = get_version()

    # UI
    title = w.HTML(
        f'<h2>Drive Scripts</h2><small style="color:#666">v{version}</small>'
    )
    status = w.HTML(
        f'<span style="color:{"#1a7f37" if drive_ok else "#b42318"}">'
        f"Drive: {'Mounted' if drive_ok else 'Not mounted'}</span>"
    )

    btn_extract = w.Button(
        description="Extract Archives",
        button_style="primary",
        icon="file-archive-o",
        layout=w.Layout(width="180px", height="40px"),
    )
    btn_verify = w.Button(
        description="Verify NSZ",
        button_style="info",
        icon="check-circle",
        layout=w.Layout(width="180px", height="40px"),
    )

    output = w.Output()

    def run_tool(module_name, func_name, btn):
        """Load and run a tool module."""
        btn.disabled = True
        btn.icon = "spinner"
        original_desc = btn.description
        btn.description = "Loading..."

        output.clear_output()
        with output:
            try:
                # Force reload all tools.* modules to pick up any updates
                for name in list(sys.modules.keys()):
                    if name.startswith("tools."):
                        importlib.reload(sys.modules[name])
                module = importlib.import_module(f"tools.{module_name}")
                getattr(module, func_name)()
            except Exception as e:
                print(f"Error: {e}")

        btn.disabled = False
        btn.icon = "file-archive-o" if module_name == "extract" else "check-circle"
        btn.description = original_desc

    btn_extract.on_click(lambda _: run_tool("extract", "main", btn_extract))
    btn_verify.on_click(lambda _: run_tool("verify", "main", btn_verify))

    # Layout
    header = w.VBox([title, status], layout=w.Layout(margin="0 0 10px 0"))
    buttons = w.HBox(
        [btn_extract, btn_verify],
        layout=w.Layout(gap="10px"),
    )
    ui = w.VBox([header, buttons, output])

    display(ui)


# Run when executed
if __name__ == "__main__" or "get_ipython" in dir():
    main()
