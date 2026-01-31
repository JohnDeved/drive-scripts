from fastapi import APIRouter, BackgroundTasks, WebSocket
from pydantic import BaseModel
from typing import List
import uuid
from server.services.organize_service import OrganizeService
from server.services.sse_service import sse_service

router = APIRouter()


class OrganizeRequest(BaseModel):
    files: List[str]


class ConfirmRequest(BaseModel):
    apply: bool


@router.post("")
@router.post("/")
async def start_organization(
    request: OrganizeRequest, background_tasks: BackgroundTasks
):
    """Start an organization job (analysis phase)."""
    job_id = str(uuid.uuid4())
    background_tasks.add_task(OrganizeService.run_analysis, job_id, request.files)
    return {"job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_organization(job_id: str):
    """Stream organization progress."""
    return sse_service.stream(job_id)


@router.websocket("/{job_id}/ws")
async def websocket_organization(websocket: WebSocket, job_id: str):
    """WebSocket for organization progress and interaction."""
    await sse_service.handle_ws(job_id, websocket)


@router.post("/{job_id}/confirm")
async def confirm_organization(job_id: str, request: ConfirmRequest):
    """Resume an organization job with a confirmation."""
    sse_service.confirm(job_id, request.apply)
    return {"status": "ok"}
