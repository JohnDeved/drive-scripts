"""Shared utilities for drive-scripts tools."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from typing import Callable, List, Optional, Set

from config import config


def ensure_drive_ready() -> None:
    """Check that Google Drive is mounted.

    Raises:
        RuntimeError: If Drive is not mounted.
    """
    if not os.path.exists(config.shared_drives):
        raise RuntimeError(
            "Drive not mounted. Run the loader cell first to mount Drive."
        )


def ensure_bins(bins_to_packages: dict[str, str]) -> None:
    """Install missing apt packages for required binaries.

    Args:
        bins_to_packages: Mapping of binary name to apt package name.
    """
    missing = [
        pkg for cmd, pkg in bins_to_packages.items() if shutil.which(cmd) is None
    ]
    if missing:
        subprocess.run(
            ["apt-get", "install", "-qq", *missing],
            capture_output=True,
            check=False,
        )


_MODULES_CHECKED: Set[str] = set()


def ensure_python_modules(modules: List[str]) -> None:
    """Install missing Python modules via pip.

    Args:
        modules: List of module names to ensure are installed.
    """
    unchecked = [m for m in modules if m not in _MODULES_CHECKED]
    if not unchecked:
        return
    missing = [m for m in unchecked if importlib.util.find_spec(m) is None]
    if missing:
        subprocess.run(
            ["pip", "install", "-q", *missing],
            capture_output=True,
            check=False,
        )
    _MODULES_CHECKED.update(modules)


def fmt_bytes(b: float) -> str:
    """Format bytes as human-readable string.

    Args:
        b: Number of bytes.

    Returns:
        Formatted string like "1.5 GB".
    """
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def fmt_time(s: float) -> str:
    """Format seconds as HH:MM:SS.

    Args:
        s: Number of seconds.

    Returns:
        Formatted time string like "01:23:45".
    """
    s = int(max(0, s))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def short(name: str, n: int = 55) -> str:
    """Truncate string with ellipsis if too long.

    Args:
        name: String to truncate.
        n: Maximum length including ellipsis.

    Returns:
        Truncated string.
    """
    return name[: n - 3] + "..." if len(name) > n else name


def find_archives(root: str, exts: Optional[Set[str]] = None) -> List[str]:
    """Find all archive files recursively under root.

    Args:
        root: Directory to search.
        exts: Set of extensions to match. Defaults to config.archive_exts.

    Returns:
        List of archive file paths.
    """
    if exts is None:
        exts = config.archive_exts
    out: List[str] = []
    for r, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                out.append(os.path.join(r, f))
    return out


def find_games(root: str, exts: Optional[Set[str]] = None) -> List[str]:
    """Find all game files (NSP/NSZ/XCI/XCZ) recursively under root.

    Args:
        root: Directory to search.
        exts: Set of extensions to match. Defaults to config.game_exts.

    Returns:
        Sorted list of game file paths.
    """
    if exts is None:
        exts = config.game_exts
    out: List[str] = []
    for r, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                out.append(os.path.join(r, f))
    return sorted(out)


def find_games_progressive(
    root: str,
    on_found: Callable[[str], None],
    on_scanning: Optional[Callable[[str], None]] = None,
    exts: Optional[Set[str]] = None,
) -> List[str]:
    """Find game files with progress callbacks using breadth-first search.

    Scans directories level by level (all depth-1 dirs, then depth-2, etc.)
    to ensure files in shallow directories are found quickly.

    Args:
        root: Directory to search.
        on_found: Callback receiving each file path as it's found.
        on_scanning: Optional callback receiving current directory being scanned.
        exts: Set of extensions to match.

    Returns:
        Full list of discovered paths.
    """
    if exts is None:
        exts = config.game_exts

    all_found: List[str] = []

    # Breadth-first: process directories level by level
    dirs_to_scan = [root]

    while dirs_to_scan:
        next_level: List[str] = []

        for dirpath in dirs_to_scan:
            # Report current directory
            if on_scanning:
                rel_path = os.path.relpath(dirpath, root)
                if rel_path == ".":
                    rel_path = os.path.basename(root)
                on_scanning(rel_path)

            # Scan this directory (non-recursive)
            try:
                entries = os.scandir(dirpath)
            except OSError:
                continue

            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        if os.path.splitext(entry.name)[1].lower() in exts:
                            all_found.append(entry.path)
                            on_found(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        next_level.append(entry.path)
                except OSError:
                    continue

        dirs_to_scan = next_level

    all_found.sort()
    return all_found


ProgressCallback = Callable[[int, int], None]


def copy_with_progress(
    src: str,
    dst: str,
    on_prog: Optional[ProgressCallback] = None,
) -> int:
    """Copy file with progress callback.

    Args:
        src: Source file path.
        dst: Destination file path.
        on_prog: Callback function receiving (done_bytes, total_bytes).

    Returns:
        Total bytes copied.
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
