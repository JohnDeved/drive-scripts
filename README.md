# Drive Scripts

Colab toolkit for managing Nintendo Switch files on Google Drive.

## Quick Start

```python
exec(__import__('urllib.request').request.urlopen('https://raw.githubusercontent.com/JohnDeved/drive-scripts/main/loader.py').read().decode())
```

## Tools

| Tool | Description |
|------|-------------|
| **Extract Archives** | Extract ZIP/7z/RAR with nested archive support, upload back to Drive |
| **Verify NSZ** | Batch verify NSP/NSZ/XCI/XCZ files using `nsz --quick-verify` |

## Setup

Files should be in: `Google Drive/Shareddrives/Gaming/Switch/`

For verification, place keys in: `.switch/prod.keys`

## Creating Plugins

Drop a file in `tools/plugins/`:

```python
from tools.base import BaseTool
from tools.shared import ensure_drive_ready

class MyTool(BaseTool):
    name = "my_tool"
    title = "My Tool"
    icon = "wrench"
    button_style = "info"
    order = 10

    def ensure_deps(self) -> None:
        pass

    def main(self) -> None:
        ensure_drive_ready()
        # Your logic here
```

Auto-discovered and added to the menu.

## Project Structure

```
drive-scripts/
├── loader.py           # Bootstrap + menu
├── config.py           # Paths and settings
└── tools/
    ├── base.py         # BaseTool abstract class
    ├── registry.py     # Plugin discovery
    ├── shared/         # Utilities (fmt_bytes, ProgressUI, etc.)
    └── plugins/        # Tool plugins (auto-discovered)
```
