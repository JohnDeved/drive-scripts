import os
from typing import List, Dict, Optional, Set
from tools.shared.utils import fmt_bytes, find_archives, find_games


class FileService:
    @staticmethod
    def list_directory(path: str) -> List[Dict]:
        """List files and directories in the given path."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")

        if not os.path.isdir(path):
            raise NotADirectoryError(f"Path is not a directory: {path}")

        items = []
        try:
            for entry in os.scandir(path):
                stats = entry.stat()
                is_dir = entry.is_dir()
                items.append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "size": stats.st_size if not is_dir else None,
                        "size_str": fmt_bytes(stats.st_size) if not is_dir else None,
                        "modified": stats.st_mtime,
                    }
                )
        except PermissionError:
            # Handle cases where we don't have permission to list the directory
            pass

        # Sort: directories first, then files, both alphabetically
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    @staticmethod
    def search_files(root: str, file_type: str) -> List[str]:
        """Search for files of a specific type (archives, games)."""
        if file_type == "archives":
            return find_archives(root)
        elif file_type == "games":
            return find_games(root)
        else:
            raise ValueError(f"Invalid file type: {file_type}")
