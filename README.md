# Drive Scripts Web GUI

A modern web-based toolkit for managing Nintendo Switch game files on Google Drive, designed specifically for Google Colab.

## 🚀 Quick Start (Colab)

Run this one-liner in a Colab cell to launch the Web GUI:

```python
exec(__import__('urllib.request').request.urlopen('https://raw.githubusercontent.com/JohnDeved/drive-scripts/main/loader.py').read().decode())
```

This will:
1. Clone/update the repository
2. Mount your Google Drive
3. Install necessary dependencies
4. Launch the FastAPI server
5. Provide a "Launch Web GUI" button to open the modern interface

## ✨ Features

- **Modern Web Interface**: Built with Preact and Tailwind CSS. **Zero build step required** — works immediately in Colab.
- **Extract Archives**: Support for ZIP, 7z, and RAR with automatic nested archive extraction.
- **Verify Integrity**: Batch verify NSP/NSZ/XCI/XCZ files using `nsz`.
- **Compress NSZ**: Convert NSP/XCI to solid-compressed NSZ/XCZ format with real-time size comparison.
- **Organize & Rename**: Automatically rename files based on Nintendo TitleDB (Format: `Name [TitleID] [vVersion].ext`).
- **Real-time Progress**: Live progress bars, step tracking, and console logs via Server-Sent Events (SSE).
- **Drive Optimized**: Optimized for Google Drive's filesystem and throughput limitations.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: Preact + HTM (Build-free, ESM based)
- **Styling**: Tailwind CSS (CDN)
- **Communication**: REST API + Server-Sent Events (SSE)
- **Core Logic**: nsz, py7zr, rarfile

## 📁 Configuration

Configuration is centralized in `config.py`. Key settings include:
- `drive_root`: Root path for Drive mount (`/content/drive`)
- `switch_dir`: Default directory for game files
- `temp_dir`: Local storage for processing large files
- `max_nested_depth`: Depth limit for recursive extraction

## 📝 License

MIT
