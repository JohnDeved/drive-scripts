"""Drive Scripts Tools Package.

This package provides tools for managing Nintendo Switch files on Google Drive.

Public API:
    - discover_tools(): Get list of available tools
    - get_tool(name): Get a specific tool by name
    - reload_tools(): Force reload all plugins

Subpackages:
    - tools.shared: Shared utilities and UI components
    - tools.plugins: Tool plugins (auto-discovered)

Example:
    from tools import discover_tools, get_tool

    # List all tools
    for tool in discover_tools():
        print(f"{tool.title}: {tool.description}")

    # Run a specific tool
    extract = get_tool("extract")
    if extract:
        extract.main()
"""

__version__ = "2.0.0"

# Re-export public API from registry
from .registry import discover_tools, get_tool, list_tools, reload_tools

# Re-export base class for plugin authors
from .base import BaseTool

__all__ = [
    "BaseTool",
    "discover_tools",
    "get_tool",
    "list_tools",
    "reload_tools",
    "__version__",
]
