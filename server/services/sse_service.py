import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional
from sse_starlette.sse import EventSourceResponse


class SSEService:
    def __init__(self):
        self.jobs: Dict[str, asyncio.Queue] = {}
        self.confirmations: Dict[str, asyncio.Future] = {}

    async def create_job(self, job_id: str):
        """Create a new job and its message queue."""
        self.jobs[job_id] = asyncio.Queue()

    async def send_event(self, job_id: str, event_type: str, data: Any):
        """Send an event to a specific job's queue."""
        if job_id in self.jobs:
            await self.jobs[job_id].put({"event": event_type, "data": json.dumps(data)})

    async def wait_for_confirmation(self, job_id: str, data: Any) -> bool:
        """Send a confirmation request and wait for the response."""
        if job_id not in self.jobs:
            return False

        # Create a future to wait for the response
        future = asyncio.get_event_loop().create_future()
        self.confirmations[job_id] = future

        # Send confirmation request to frontend
        await self.send_event(job_id, "confirm_request", data)

        try:
            # Wait for confirm() to be called
            return await future
        finally:
            if job_id in self.confirmations:
                del self.confirmations[job_id]

    def confirm(self, job_id: str, result: bool):
        """Resume a job with a confirmation result."""
        if job_id in self.confirmations:
            self.confirmations[job_id].set_result(result)

    async def event_generator(
        self, job_id: str
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Generator that yields events from a job's queue."""
        if job_id not in self.jobs:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Job {job_id} not found"}),
            }
            return

        try:
            while True:
                event = await self.jobs[job_id].get()
                yield event
                if event["event"] in ["complete", "error", "cancelled"]:
                    break
        finally:
            # Clean up job when the stream is closed
            if job_id in self.jobs:
                del self.jobs[job_id]
            if job_id in self.confirmations:
                # Cancel any pending confirmation if stream closes
                if not self.confirmations[job_id].done():
                    self.confirmations[job_id].set_result(False)
                del self.confirmations[job_id]

    def stream(self, job_id: str) -> EventSourceResponse:
        """Return an EventSourceResponse for a job."""
        return EventSourceResponse(self.event_generator(job_id))


sse_service = SSEService()
