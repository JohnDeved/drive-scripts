"""Organize Tool: Rename and organize files using TitleDB."""

from __future__ import annotations
from tools.base import BaseTool


class OrganizeTool(BaseTool):
    """Organize and rename files using TitleDB."""

    name = "organize"
    title = "Organize & Rename"
    description = "Rename files based on TitleDB (Name [TitleID] [vVersion])"
    icon = "tags"
    button_style = "success"
    order = 5

    def ensure_deps(self) -> None:
        pass

    def main(self) -> None:
        """UI handled by Web GUI."""
        pass
