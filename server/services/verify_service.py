import os
import shutil
import subprocess
import asyncio
from typing import List, Tuple
from config import config
from tools.shared.utils import ensure_python_modules, short
from server.services.sse_service import sse_service


class VerifyService:
    @staticmethod
    async def run_verification(job_id: str, files: List[str]):
        """Verify files with SSE reporting."""
        try:
            await sse_service.create_job(job_id)
            ensure_python_modules(["nsz"])

            # Step 1: Stage keys
            await sse_service.send_event(
                job_id, "log", {"message": "Staging decryption keys..."}
            )
            ok, path = VerifyService._stage_keys()
            if not ok:
                raise RuntimeError(f"prod.keys missing - place in {config.keys_dir}/")
            await sse_service.send_event(
                job_id, "log", {"message": f"Keys staged: {path}"}
            )

            # Step 2: Verify
            passed = failed = 0
            total = len(files)

            for i, f in enumerate(files, 1):
                await sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": "[2/2] Verifying",
                        "current": i,
                        "total": total,
                        "percent": round(i / total * 100, 2),
                        "message": os.path.basename(f),
                        "stats": {"passed": passed, "failed": failed},
                    },
                )

                # Run verification in thread
                ok, err = await asyncio.to_thread(VerifyService._verify_file, f)

                if ok:
                    passed += 1
                    await sse_service.send_event(
                        job_id, "log", {"message": f"OK    {os.path.basename(f)}"}
                    )
                else:
                    failed += 1
                    await sse_service.send_event(
                        job_id,
                        "log",
                        {"message": f"FAIL  {os.path.basename(f)} - {err}"},
                    )

                # Update stats after each file
                await sse_service.send_event(
                    job_id, "progress", {"stats": {"passed": passed, "failed": failed}}
                )

            await sse_service.send_event(
                job_id,
                "complete",
                {
                    "message": f"Verification done: {passed} OK, {failed} failed",
                    "passed": passed,
                    "failed": failed,
                },
            )

        except Exception as e:
            await sse_service.send_event(job_id, "error", {"message": str(e)})

    @staticmethod
    def _stage_keys() -> Tuple[bool, str]:
        os.makedirs(config.local_keys_dir, exist_ok=True)
        key_files = ["prod.keys", "title.keys", "keys.txt"]
        for name in key_files:
            src = os.path.join(config.keys_dir, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(config.local_keys_dir, name))
        prod = os.path.join(config.local_keys_dir, "prod.keys")
        return os.path.isfile(prod) and os.path.getsize(prod) > 0, prod

    @staticmethod
    def _verify_file(path: str) -> Tuple[bool, str]:
        result = subprocess.run(
            ["nsz", "--quick-verify", path], capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, ""
        err = result.stderr.strip() or result.stdout.strip()
        if err:
            err = err.split("\n")[-1]
        return False, short(err, 100)
