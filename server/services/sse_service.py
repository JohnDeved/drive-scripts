import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse


class StreamService:
    def __init__(self):
        self.jobs: Dict[str, asyncio.Queue] = {}
        self.confirmations: Dict[str, asyncio.Future] = {}
        self.ws_connections: Dict[str, List[WebSocket]] = {}

    async def create_job(self, job_id: str):
        """Create a new job and its message queue."""
        self.jobs[job_id] = asyncio.Queue()

    async def send_event(self, job_id: str, event_type: str, data: Any):
        """Send an event to a specific job's queue and any connected WebSockets."""
        payload = {"event": event_type, "data": json.dumps(data)}

        # Send to SSE queue
        if job_id in self.jobs:
            await self.jobs[job_id].put(payload)

        # Send to WebSockets
        if job_id in self.ws_connections:
            ws_payload = {"type": event_type, "data": data}
            for ws in self.ws_connections[job_id]:
                try:
                    await ws.send_json(ws_payload)
                except:
                    pass

    async def wait_for_confirmation(self, job_id: str, data: Any) -> bool:
        """Send a confirmation request and wait for the response."""
        if job_id not in self.jobs and job_id not in self.ws_connections:
            return False

        # Create a future to wait for the response
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.confirmations[job_id] = future

        # Send confirmation request
        await self.send_event(job_id, "confirm_request", data)

        try:
            return await future
        finally:
            if job_id in self.confirmations:
                del self.confirmations[job_id]

    def confirm(self, job_id: str, result: bool):
        """Resume a job with a confirmation result."""
        if job_id in self.confirmations:
            if not self.confirmations[job_id].done():
                self.confirmations[job_id].set_result(result)

    async def handle_ws(self, job_id: str, websocket: WebSocket):
        """Handle a WebSocket connection for a job."""
        await websocket.accept()
        if job_id not in self.ws_connections:
            self.ws_connections[job_id] = []
        self.ws_connections[job_id].append(websocket)

        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "confirm":
                    self.confirm(job_id, data.get("result", False))
        except WebSocketDisconnect:
            pass
        finally:
            if job_id in self.ws_connections:
                self.ws_connections[job_id].remove(websocket)
                if not self.ws_connections[job_id]:
                    del self.ws_connections[job_id]

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
            # Clean up job when the stream is closed (if no WS connections)
            if job_id in self.jobs and job_id not in self.ws_connections:
                del self.jobs[job_id]

    def stream(self, job_id: str) -> EventSourceResponse:
        """Return an EventSourceResponse for a job."""
        return EventSourceResponse(self.event_generator(job_id))


sse_service = StreamService()
