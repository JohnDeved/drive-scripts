"""Compress Tool: Compress NSP/XCI to NSZ/XCZ format."""

from __future__ import annotations
from tools.base import BaseTool


class CompressTool(BaseTool):
    """Compress NSP/XCI files to NSZ/XCZ format."""

    name = "compress"
    title = "Compress NSZ"
    description = "Compress NSP/XCI to NSZ/XCZ format"
    icon = "compress"
    button_style = "warning"
    order = 3

    def ensure_deps(self) -> None:
        pass

    def main(self) -> None:
        """UI handled by Web GUI."""
        pass
