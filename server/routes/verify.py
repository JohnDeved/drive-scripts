from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
import uuid
from server.services.verify_service import VerifyService
from server.services.sse_service import sse_service

router = APIRouter()


class VerifyRequest(BaseModel):
    files: List[str]


@router.post("")
@router.post("/")
async def start_verification(request: VerifyRequest, background_tasks: BackgroundTasks):
    """Start a verification job."""
    job_id = str(uuid.uuid4())
    background_tasks.add_task(VerifyService.run_verification, job_id, request.files)
    return {"job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_verification(job_id: str):
    """Stream verification progress."""
    return sse_service.stream(job_id)
