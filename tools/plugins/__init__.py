"""Plugin package for drive-scripts tools.

Each tool is a Python module in this directory that contains a class
extending BaseTool. Plugins are auto-discovered by the registry.

Example plugin structure:
    # plugins/my_tool.py
    from tools.base import BaseTool
    from tools.shared import ensure_drive_ready

    class MyTool(BaseTool):
        name = "my_tool"
        title = "My Tool"
        description = "Does something useful"
        icon = "wrench"
        button_style = "info"
        order = 10

        def ensure_deps(self) -> None:
            pass

        def main(self) -> None:
            ensure_drive_ready()
            # ... display UI
"""
