from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Optional
from server.services.file_service import FileService
from config import config

router = APIRouter()


@router.get("/list")
async def list_files(path: str = Query(..., description="Absolute path to list")):
    """List files and directories in a path."""
    try:
        return FileService.list_directory(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search")
async def search_files(
    root: str = Query(..., description="Root directory to search"),
    type: str = Query(..., description="Type of files to search for (archives, games)"),
):
    """Search for files of a specific type."""
    try:
        return FileService.search_files(root, type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config")
async def get_file_config():
    """Get file-related configuration (default paths, extensions)."""
    return {
        "shared_drives": config.shared_drives,
        "drive_root": config.drive_root,
        "archive_exts": list(config.archive_exts),
        "game_exts": list(config.game_exts),
    }
