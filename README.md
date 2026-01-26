# Drive Scripts

Colab tools for managing Nintendo Switch files on Google Drive.

## Features

- **Extract Archives** - Extract ZIP, 7z, and RAR archives with nested archive support
- **Verify NSZ** - Verify NSP/NSZ/XCI/XCZ files using NSZ quick verify

## Quick Start

1. Open [Google Colab](https://colab.research.google.com/)
2. Create a new notebook
3. Paste this code in a cell and run it:

```python
exec(__import__('urllib.request').request.urlopen('https://raw.githubusercontent.com/JohnDeved/drive-scripts/main/loader.py').read().decode())
```

## Expected Directory Structure

The tools expect your Switch files to be in:
```
Google Drive/Shareddrives/Gaming/Switch/
```

For NSZ verification, place your keys in:
```
Google Drive/Shareddrives/Gaming/Switch/.switch/prod.keys
```

## Tools

### Extract Archives

- Extracts ZIP files directly from Drive (no copy step needed)
- Copies 7z/RAR to local storage before extraction for better performance
- Handles nested archives (up to 5 levels deep)
- Uploads extracted files back to Drive
- Deletes source archive after successful extraction

### Verify NSZ

- Verifies NSP/NSZ/XCI/XCZ files using `nsz --quick-verify`
- Supports range selection for batch verification
- Shows pass/fail status and error messages
- Requires `prod.keys` file for verification

## Development

```bash
git clone https://github.com/JohnDeved/drive-scripts.git
cd drive-scripts
```

The repository structure:
```
drive-scripts/
├── loader.py           # Entry point with menu UI
├── requirements.txt    # Python dependencies
└── tools/
    ├── shared.py       # Common utilities
    ├── extract.py      # Archive extraction tool
    └── verify.py       # NSZ verification tool
```
