"""Centralized configuration for drive-scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Set


@dataclass
class Config:
    """Configuration settings with sensible defaults.

    All paths and settings can be customized by creating a new Config instance
    or modifying the global `config` singleton.

    Attributes:
        drive_root: Root path where Google Drive is mounted.
        switch_dir: Directory containing Switch game files and archives.
        temp_dir: Local temporary directory for extraction operations.
        archive_exts: Set of supported archive file extensions.
        game_exts: Set of supported game file extensions.
        max_nested_depth: Maximum depth for nested archive extraction.
    """

    drive_root: str = "/content/drive"
    switch_dir: str = ""
    temp_dir: str = "/content/extract_temp"
    archive_exts: Set[str] = field(default_factory=lambda: {".zip", ".7z", ".rar"})
    game_exts: Set[str] = field(
        default_factory=lambda: {".nsp", ".nsz", ".xci", ".xcz"}
    )
    max_nested_depth: int = 5

    def __post_init__(self) -> None:
        """Set default switch_dir based on drive_root if not provided."""
        if not self.switch_dir:
            self.switch_dir = os.path.join(
                self.drive_root, "Shareddrives", "Gaming", "Switch"
            )

    @property
    def shared_drives(self) -> str:
        """Path to shared drives directory."""
        return os.path.join(self.drive_root, "Shareddrives")

    @property
    def keys_dir(self) -> str:
        """Path to .switch keys directory."""
        return os.path.join(self.switch_dir, ".switch")

    @property
    def local_keys_dir(self) -> str:
        """Local keys directory for NSZ verification."""
        return os.path.expanduser("~/.switch")


# Global singleton - can be replaced for testing or user customization
config = Config()
