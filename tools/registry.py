"""Plugin registry for auto-discovering and managing tools."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List, Optional

from .base import BaseTool

# Cache of discovered tools
_registry: List[BaseTool] = []
_discovered: bool = False


def discover_tools(force_reload: bool = False) -> List[BaseTool]:
    """Auto-discover and instantiate tools from plugins/ directory.

    Scans the plugins/ directory for Python modules containing classes
    that inherit from BaseTool. Each valid tool class is instantiated
    and added to the registry.

    Args:
        force_reload: If True, re-scan and reload all plugins even if
                      already discovered. Useful for hot-reloading.

    Returns:
        List of instantiated tool objects, sorted by their order attribute.

    Example:
        tools = discover_tools()
        for tool in tools:
            print(f"{tool.title}: {tool.description}")
    """
    global _registry, _discovered

    if _discovered and not force_reload:
        return _registry

    _registry = []

    # Find plugins directory
    plugins_dir = Path(__file__).parent / "plugins"
    if not plugins_dir.exists():
        _discovered = True
        return _registry

    # Scan for plugin modules
    for module_path in plugins_dir.glob("*.py"):
        if module_path.stem.startswith("_"):
            continue

        module_name = f"tools.plugins.{module_path.stem}"

        try:
            # Force reload if requested
            if force_reload and module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)

            # Find BaseTool subclasses in the module
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseTool)
                    and obj is not BaseTool
                    and hasattr(obj, "name")
                    and hasattr(obj, "title")
                ):
                    _registry.append(obj())

        except Exception as e:
            # Log but don't fail on bad plugins
            print(f"Warning: Failed to load plugin {module_path.stem}: {e}")

    # Sort by order, then by title
    _registry.sort(key=lambda t: (t.order, t.title))
    _discovered = True

    return _registry


def get_tool(name: str) -> Optional[BaseTool]:
    """Get a tool by its name.

    Args:
        name: The tool's name attribute (e.g., "extract").

    Returns:
        The tool instance if found, None otherwise.
    """
    for tool in discover_tools():
        if tool.name == name:
            return tool
    return None


def reload_tools() -> List[BaseTool]:
    """Force reload all plugins and return updated tool list.

    This is useful when developing plugins or when tools have been
    updated on disk (e.g., via git pull).

    Returns:
        List of freshly instantiated tool objects.
    """
    global _discovered
    _discovered = False

    # Clear any cached plugin modules
    for name in list(sys.modules.keys()):
        if name.startswith("tools.plugins."):
            del sys.modules[name]

    return discover_tools(force_reload=True)


def list_tools() -> List[str]:
    """Get list of available tool names.

    Returns:
        List of tool name strings.
    """
    return [tool.name for tool in discover_tools()]
