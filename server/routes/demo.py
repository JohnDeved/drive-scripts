import asyncio
import uuid
import random
from fastapi import APIRouter, BackgroundTasks, WebSocket
from server.services.sse_service import sse_service

router = APIRouter()


class DemoService:
    @staticmethod
    async def run_simulation(job_id: str):
        """Simulate a complex multi-stage job."""
        try:
            await sse_service.create_job(job_id)

            # Stage 1: Fast Streaming
            await sse_service.send_event(
                job_id, "log", {"message": "Initializing high-speed data stream..."}
            )
            total = 100 * 1024 * 1024  # 100MB
            current = 0
            while current < total:
                chunk = random.randint(1024 * 1024, 5 * 1024 * 1024)
                current = min(total, current + chunk)
                await sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": "Phase 1: Turbo Download",
                        "current": current,
                        "total": total,
                        "percent": round(current / total * 100, 2),
                        "message": f"Downloading asset_{random.randint(1, 100)}.bin",
                    },
                )
                await asyncio.sleep(0.05)  # 20 updates per second

            await sse_service.send_event(
                job_id,
                "log",
                {"message": "Download complete. Waiting for user confirmation..."},
            )

            # Stage 2: Interaction
            keep = await sse_service.wait_for_confirmation(
                job_id,
                {
                    "filename": "demo_package.zip",
                    "original_size_str": "100 MB",
                    "compressed_size_str": "42 MB",
                    "savings": "58 MB",
                    "percent": 42,
                },
            )

            if not keep:
                await sse_service.send_event(
                    job_id, "error", {"message": "Simulation aborted by user."}
                )
                return

            # Stage 3: Heavy Processing (Fluctuating speeds)
            await sse_service.send_event(
                job_id,
                "log",
                {"message": "User confirmed. Starting heavy computation..."},
            )
            total = 500
            for i in range(total):
                await sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": "Phase 2: Neural Processing",
                        "current": i + 1,
                        "total": total,
                        "percent": round((i + 1) / total * 100, 2),
                        "message": f"Processing shard {i + 1}...",
                    },
                )
                # Simulate fluctuating CPU load
                await asyncio.sleep(random.uniform(0.01, 0.1))

            await sse_service.send_event(
                job_id, "log", {"message": "Simulation successful!"}
            )
            await sse_service.send_event(
                job_id, "complete", {"message": "Demo finished successfully"}
            )

        except Exception as e:
            await sse_service.send_event(job_id, "error", {"message": str(e)})


@router.post("/start")
async def start_demo(background_tasks: BackgroundTasks):
    job_id = f"demo-{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(DemoService.run_simulation, job_id)
    return {"job_id": job_id}


@router.websocket("/{job_id}/ws")
async def websocket_demo(websocket: WebSocket, job_id: str):
    await sse_service.handle_ws(job_id, websocket)
