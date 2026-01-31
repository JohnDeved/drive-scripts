"""Drive Scripts Loader - Run in Google Colab to access Web GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from typing import List

REPO_URL = "https://github.com/JohnDeved/drive-scripts.git"
REPO_DIR = "/content/drive-scripts"
DRIVE_ROOT = "/content/drive"
PORT = 8000


def ensure_repo() -> None:
    """Clone or pull the repository."""
    if os.path.exists(REPO_DIR):
        print("Pulling latest...", flush=True)
        subprocess.run(["git", "-C", REPO_DIR, "pull"], check=False)
    else:
        print("Cloning repository...", flush=True)
        subprocess.run(["git", "clone", "--depth=1", REPO_URL, REPO_DIR], check=False)

    if REPO_DIR not in sys.path:
        sys.path.insert(0, REPO_DIR)


def ensure_drive() -> bool:
    """Mount Google Drive."""
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
    """Install dependencies."""
    print("Installing dependencies...", end=" ", flush=True)
    req_file = os.path.join(REPO_DIR, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run(["pip", "install", "-q", "-r", req_file], check=False)
    print("done")


def run_server():
    """Run FastAPI server in background."""
    os.chdir(REPO_DIR)
    # Using uvicorn to start the app
    cmd = [
        "uvicorn",
        "server.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
        "--log-level",
        "error",
    ]
    subprocess.Popen(cmd)


def main() -> None:
    """Bootstrap and launch Web GUI."""
    ensure_repo()
    drive_ok = ensure_drive()
    ensure_deps()

    # Start server
    print(f"Starting Web Server on port {PORT}...", end=" ", flush=True)
    run_server()
    time.sleep(2)  # Give it a moment to start
    print("done")

    try:
        from google.colab import output
        from IPython.display import HTML, display, clear_output

        clear_output(wait=True)

        # Display launch UI
        display(
            HTML(f"""
            <div style="background-color: #0f172a; color: white; padding: 20px; border-radius: 15px; font-family: sans-serif; max-width: 500px; border: 1px solid #1e293b; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
                <h2 style="margin-top: 0; color: #38bdf8;">Drive Scripts Web GUI</h2>
                <p style="color: #94a3b8; font-size: 14px;">The server is running. Click the button below to open the interface in a new window.</p>
                <div style="margin-top: 20px; display: flex; align-items: center; justify-content: space-between;">
                    <div style="font-size: 12px; color: #64748b;">
                        Status: <span style="color: #10b981;">● Online</span>
                    </div>
                </div>
            </div>
        """)
        )

        # This will open the URL in a new window/tab in Colab
        output.serve_kernel_port_as_window(PORT)

    except ImportError:
        print(f"\nWeb GUI running locally at http://localhost:{PORT}")
        print(
            "Note: If you are in Colab, this should have opened a window automatically."
        )


if __name__ == "__main__":
    main()
