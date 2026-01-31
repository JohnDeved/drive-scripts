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
        sys.stdout.write("Pulling latest... ")
        sys.stdout.flush()
        subprocess.run(
            ["git", "-C", REPO_DIR, "pull"], capture_output=True, check=False
        )
    else:
        sys.stdout.write("Cloning repository... ")
        sys.stdout.flush()
        subprocess.run(
            ["git", "clone", "--depth=1", REPO_URL, REPO_DIR],
            capture_output=True,
            check=False,
        )

    # Immediately print hash on the same line
    print(get_git_hash())

    if REPO_DIR not in sys.path:
        sys.path.insert(0, REPO_DIR)


def get_git_hash() -> str:
    """Get current git commit hash."""
    try:
        return subprocess.check_output(
            ["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


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


def cleanup_port(port: int) -> None:
    """Kill any process using the specified port."""
    # Method 1: lsof
    try:
        output = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True)
        pids = output.strip().split("\n")
        for pid in pids:
            if pid:
                subprocess.run(["kill", "-9", pid], check=False)
    except Exception:
        pass

    # Method 2: fuser
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, check=False)
    except Exception:
        pass


def run_server():
    """Run FastAPI server in background and pipe logs to stdout via thread."""
    os.chdir(REPO_DIR)

    # Construct the command
    cmd = [
        "uvicorn",
        "server.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
        "--log-level",
        "info",
    ]

    # Use PIPE for all streams and close_fds=True to avoid fileno() error in Colab
    # We must explicitly set stdin as well
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        close_fds=True,
    )

    def log_reader():
        try:
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        print(line, end="", flush=True)
        except Exception as e:
            print(f"\n[Log Reader Error] {e}")

    # Start thread to read logs
    thread = threading.Thread(target=log_reader, daemon=True)
    thread.start()

    return process


def wait_for_server(port: int, timeout: int = 10) -> bool:
    """Wait for the server to be ready by polling /health."""
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(
                f"http://localhost:{port}/health", timeout=1
            ) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def main() -> None:
    """Bootstrap and launch Web GUI."""
    ensure_repo()
    drive_ok = ensure_drive()
    ensure_deps()

    # Clean up any existing server on the same port
    cleanup_port(PORT)

    # Start server
    print(f"Starting Web Server on port {PORT}...", end=" ", flush=True)
    server_proc = run_server()

    if wait_for_server(PORT):
        print("done")
    else:
        if server_proc.poll() is not None:
            print("\nERROR: Web server failed to start. Check logs above.")
        else:
            print("\nWARNING: Web server started but health check timed out.")

    try:
        from google.colab import output
        from IPython.display import HTML, display, clear_output

        clear_output(wait=True)

        # Correct way to get the proxy URL in Colab
        proxy_url = output.eval_js(f"google.colab.kernel.proxyPort({PORT})")
        if not proxy_url.endswith("/"):
            proxy_url += "/"

        # Display launch UI with a clear button and iframe fallback

        display(
            HTML(f'''
            <div style="background-color: #0f172a; color: white; padding: 25px; border-radius: 15px; font-family: sans-serif; max-width: 600px; border: 1px solid #1e293b; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
                <h2 style="margin-top: 0; color: #38bdf8; font-size: 24px;">Drive Scripts Web GUI</h2>
                <p style="color: #94a3b8; font-size: 15px; margin-bottom: 20px;">The server is online. Use the button below to open the interface.</p>
                
                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <a href="{proxy_url}" target="_blank" style="background-color: #0ea5e9; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; transition: background-color 0.2s;">
                        Launch Web GUI
                    </a>
                </div>

                <div style="font-size: 12px; color: #64748b; border-top: 1px solid #1e293b; pt: 15px;">
                    Status: <span style="color: #10b981;">● Online</span> | Port: {PORT}
                </div>
            </div>
        ''')
        )

        # Also provide the iframe version below for quick access
        print("\nEmbedded View (Experimental):")
        output.serve_kernel_port_as_iframe(PORT, height="600")

    except ImportError:
        print(f"\nWeb GUI running locally at http://localhost:{PORT}")
        print(
            "Note: If you are in Colab, this should have opened a window automatically."
        )


if __name__ == "__main__":
    main()
