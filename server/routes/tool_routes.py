from fastapi import APIRouter
from typing import List, Dict
from tools.registry import discover_tools

router = APIRouter()


@router.get("", response_model=List[Dict])
@router.get("/", response_model=List[Dict])
async def list_tools() -> List[Dict]:
    """List all available tools and their metadata."""
    tools = discover_tools()
    return [
        {
            "id": tool.name,
            "title": tool.title,
            "description": tool.description,
            "icon": tool.icon,
            "order": tool.order,
        }
        for tool in tools
    ]
