"""Shared utilities for drive-scripts tools.

This package re-exports commonly used utilities so plugins can import from
a single location:

    from tools.shared import fmt_bytes, ensure_drive_ready
"""

from .utils import (
    ProgressCallback,
    copy_with_progress,
    ensure_bins,
    ensure_drive_ready,
    ensure_python_modules,
    find_archives,
    find_games,
    find_games_progressive,
    fmt_bytes,
    fmt_time,
    short,
)

__all__ = [
    # Utils
    "fmt_bytes",
    "fmt_time",
    "short",
    "find_archives",
    "find_games",
    "find_games_progressive",
    "copy_with_progress",
    "ensure_drive_ready",
    "ensure_bins",
    "ensure_python_modules",
    "ProgressCallback",
]
