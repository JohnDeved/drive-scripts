"""Base class for all drive-scripts tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class BaseTool(ABC):
    """Abstract base class for all tools with standardized lifecycle.

    All tools must inherit from this class and implement the required methods.
    The loader will automatically discover and register tools that extend this class.

    Class Attributes:
        name: Module name used for imports (e.g., "extract").
        title: Display title shown in UI (e.g., "Extract Archives").
        description: Short description of what the tool does.
        icon: FontAwesome icon name (e.g., "file-archive-o").
        button_style: ipywidgets button style ("primary", "info", "success", "warning", "danger").
        order: Sort order for menu display (lower = first).

    Example:
        class ExtractTool(BaseTool):
            name = "extract"
            title = "Extract Archives"
            description = "Extract ZIP, 7z, and RAR archives"
            icon = "file-archive-o"
            button_style = "primary"
            order = 1

            def ensure_deps(self) -> None:
                ensure_bins({"7z": "p7zip-full"})
                ensure_python_modules(["py7zr"])

            def main(self) -> None:
                # Display UI and handle interaction
                ...
    """

    # Required class attributes (must be set by subclasses)
    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str] = ""
    icon: ClassVar[str] = ""
    button_style: ClassVar[str] = "primary"
    order: ClassVar[int] = 100  # Default to high number, explicit tools go first

    @abstractmethod
    def ensure_deps(self) -> None:
        """Install or import required dependencies.

        This method is called before main() and should handle:
        - Installing apt packages via ensure_bins()
        - Installing Python modules via ensure_python_modules()
        - Lazy-loading expensive imports

        Raises:
            RuntimeError: If dependencies cannot be satisfied.
        """
        ...

    @abstractmethod
    def main(self) -> None:
        """Display the tool UI and handle user interaction.

        This is the main entry point for the tool. It should:
        - Check that Drive is ready (ensure_drive_ready())
        - Build and display the UI
        - Handle user actions

        The method runs in the main thread with access to ipywidgets.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} title={self.title!r}>"
