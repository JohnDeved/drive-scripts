from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uuid
from server.services.extract_service import ExtractService
from server.services.sse_service import sse_service

router = APIRouter()


class ExtractRequest(BaseModel):
    archive_path: str


@router.post("/")
async def start_extraction(request: ExtractRequest, background_tasks: BackgroundTasks):
    """Start an extraction job."""
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        ExtractService.run_extraction, job_id, request.archive_path
    )
    return {"job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_extraction(job_id: str):
    """Stream extraction progress."""
    return sse_service.stream(job_id)
