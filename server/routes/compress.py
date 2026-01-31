from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
import uuid
from server.services.compress_service import CompressService
from server.services.sse_service import sse_service

router = APIRouter()


class CompressRequest(BaseModel):
    files: List[str]
    verify_after: bool = True
    ask_confirm: bool = True


class ConfirmRequest(BaseModel):
    keep: bool


@router.post("/")
async def start_compression(
    request: CompressRequest, background_tasks: BackgroundTasks
):
    """Start a compression job."""
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        CompressService.run_compression,
        job_id,
        request.files,
        request.verify_after,
        request.ask_confirm,
    )
    return {"job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_compression(job_id: str):
    """Stream compression progress."""
    return sse_service.stream(job_id)


@router.post("/{job_id}/confirm")
async def confirm_compression(job_id: str, request: ConfirmRequest):
    """Resume a compression job with a confirmation."""
    sse_service.confirm(job_id, request.keep)
    return {"status": "ok"}
