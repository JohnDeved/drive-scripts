"""Shared utilities for drive-scripts tools."""

import importlib.util
import os
import shutil
import subprocess

# Constants
DRIVE_ROOT = "/content/drive"
SHARED_DRIVES = os.path.join(DRIVE_ROOT, "Shareddrives")
SWITCH_DIR = os.path.join(SHARED_DRIVES, "Gaming", "Switch")
ARCHIVE_EXTS = {".zip", ".7z", ".rar"}
GAME_EXTS = {".nsp", ".nsz", ".xci", ".xcz"}


def ensure_drive_ready():
    """Check that Google Drive is mounted."""
    if not os.path.exists(SHARED_DRIVES):
        raise RuntimeError(
            "Drive not mounted. Run the loader cell first to mount Drive."
        )


def ensure_bins(bins_to_packages):
    """Install missing apt packages for required binaries.

    Args:
        bins_to_packages: dict mapping binary name to apt package name
    """
    missing = [
        pkg for cmd, pkg in bins_to_packages.items() if shutil.which(cmd) is None
    ]
    if missing:
        subprocess.run(["apt-get", "install", "-qq"] + missing, capture_output=True)


def ensure_python_modules(modules):
    """Install missing Python modules via pip."""
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    if missing:
        subprocess.run(["pip", "install", "-q"] + missing, capture_output=True)


def fmt_bytes(b):
    """Format bytes as human-readable string."""
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def fmt_time(s):
    """Format seconds as HH:MM:SS."""
    s = int(max(0, s))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def short(name, n=55):
    """Truncate string with ellipsis if too long."""
    return name[: n - 3] + "..." if len(name) > n else name


def find_archives(root):
    """Find all archive files recursively under root."""
    out = []
    for r, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in ARCHIVE_EXTS:
                out.append(os.path.join(r, f))
    return out


def find_games(root):
    """Find all game files (NSP/NSZ/XCI/XCZ) recursively under root."""
    out = []
    for r, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in GAME_EXTS:
                out.append(os.path.join(r, f))
    return sorted(out)


def copy_with_progress(src, dst, on_prog=None):
    """Copy file with progress callback.

    Args:
        src: source file path
        dst: destination file path
        on_prog: callback(done_bytes, total_bytes)

    Returns:
        Total bytes copied
    """
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    total = os.path.getsize(src)
    done = 0
    with open(src, "rb") as r, open(dst, "wb") as w:
        while buf := r.read(8 * 1024 * 1024):
            w.write(buf)
            done += len(buf)
            if on_prog:
                on_prog(done, total)
    return total
