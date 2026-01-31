"""Centralized configuration for drive-scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Set

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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

    drive_root: str = field(
        default_factory=lambda: os.getenv("DRIVE_ROOT", "/content/drive")
    )
    switch_dir: str = field(default_factory=lambda: os.getenv("SWITCH_DIR", ""))
    temp_dir: str = field(
        default_factory=lambda: os.getenv(
            "TEMP_DIR",
            "/content/extract_temp"
            if os.path.exists("/content")
            else os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp"),
        )
    )
    archive_exts: Set[str] = field(default_factory=lambda: {".zip", ".7z", ".rar"})
    game_exts: Set[str] = field(
        default_factory=lambda: {".nsp", ".nsz", ".xci", ".xcz"}
    )
    max_nested_depth: int = 5

    def __post_init__(self) -> None:
        """Set default switch_dir based on drive_root if not provided."""
        if not self.switch_dir:
            # On macOS Google Drive Desktop uses "Shared drives", Colab uses "Shareddrives"
            # Try both common names
            shared_name = "Shareddrives"
            for candidate in ["Shared drives", "Shareddrives"]:
                if os.path.exists(os.path.join(self.drive_root, candidate)):
                    shared_name = candidate
                    break

            # Construct standard Switch path
            self.switch_dir = os.path.join(
                self.drive_root, shared_name, "Gaming", "Switch"
            )

            # If the constructed path doesn't exist, fall back to shared drives root
            if not os.path.exists(self.switch_dir):
                self.switch_dir = os.path.join(self.drive_root, shared_name)

            self.switch_dir = os.path.join(
                self.drive_root, shared_name, "Gaming", "Switch"
            )

    @property
    def shared_drives(self) -> str:
        """Path to shared drives directory."""
        shared_name = (
            "Shared drives"
            if os.path.exists(os.path.join(self.drive_root, "Shared drives"))
            else "Shareddrives"
        )
        return os.path.join(self.drive_root, shared_name)

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
