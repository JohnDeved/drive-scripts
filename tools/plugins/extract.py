"""Extract Tool: Extract archives from Drive, upload extracted files back."""

from __future__ import annotations
from typing import ClassVar
from tools.base import BaseTool


class ExtractTool(BaseTool):
    """Extract archives from Drive and upload extracted files back."""

    name = "extract"
    title = "Extract Archives"
    description = "Extract ZIP, 7z, and RAR archives with nested archive support"
    icon = "file-archive-o"
    button_style = "primary"
    order = 1

    def ensure_deps(self) -> None:
        pass

    def main(self) -> None:
        """UI handled by Web GUI."""
        pass
