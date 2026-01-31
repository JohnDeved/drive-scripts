"""Verify Tool: Verify game files using NSZ quick verify."""

from __future__ import annotations
from tools.base import BaseTool


class VerifyTool(BaseTool):
    """Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify."""

    name = "verify"
    title = "Verify NSZ"
    description = "Verify game files using NSZ quick verify"
    icon = "check-circle"
    button_style = "info"
    order = 2

    def ensure_deps(self) -> None:
        pass

    def main(self) -> None:
        """UI handled by Web GUI."""
        pass
