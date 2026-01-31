import os
import json
import re
import shutil
import time
import asyncio
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config import config
from tools.shared.utils import ensure_python_modules
from server.services.sse_service import sse_service

TITLEDB_URL = "https://raw.githubusercontent.com/blawar/titledb/master/US.en.json"


class OrganizeService:
    @staticmethod
    async def run_analysis(job_id: str, files: List[str]):
        """Analyze files and propose a rename plan."""
        loop = asyncio.get_running_loop()
        try:
            await sse_service.create_job(job_id)
            ensure_python_modules(["nsz", "requests"])

            # Step 1: Stage keys
            await sse_service.send_event(job_id, "log", {"message": "Staging keys..."})
            ok, key_path = OrganizeService._stage_keys()

            # Load keys
            from nsz.nut import Keys

            if ok:
                try:
                    Keys.load(key_path)
                except:
                    pass

            # Step 2: Download TitleDB
            await sse_service.send_event(
                job_id, "log", {"message": "Loading TitleDB..."}
            )
            titledb = await asyncio.to_thread(OrganizeService._download_titledb, job_id)

            # Step 3: Analyze
            plan = []
            total = len(files)

            for i, path in enumerate(files, 1):
                await sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": f"Analyzing ({i}/{total})",
                        "current": i,
                        "total": total,
                        "percent": round(i / total * 100, 2),
                        "message": os.path.basename(path),
                    },
                )

                tid, ver = await asyncio.to_thread(OrganizeService._get_file_info, path)

                if tid:
                    name = titledb.get(tid)
                    if name:
                        safe_name = OrganizeService._sanitize_filename(name)
                        ext = os.path.splitext(path)[1].lower()
                        ver_str = f" [v{ver}]" if ver is not None else ""
                        new_name = f"{safe_name} [{tid}]{ver_str}{ext}"
                        new_path = os.path.join(os.path.dirname(path), new_name)

                        if new_path != path:
                            plan.append(
                                {
                                    "old": path,
                                    "new": new_path,
                                    "old_name": os.path.basename(path),
                                    "new_name": new_name,
                                }
                            )
                    else:
                        await sse_service.send_event(
                            job_id,
                            "log",
                            {
                                "message": f"Skipping {os.path.basename(path)}: TitleID {tid} not in DB"
                            },
                        )
                else:
                    await sse_service.send_event(
                        job_id,
                        "log",
                        {
                            "message": f"Skipping {os.path.basename(path)}: Could not identify"
                        },
                    )

            if not plan:
                await sse_service.send_event(
                    job_id, "complete", {"message": "No files need renaming."}
                )
                return

            # Wait for confirmation to apply plan
            apply = await sse_service.wait_for_confirmation(job_id, {"plan": plan})

            if apply:
                OrganizeService._execute_rename(job_id, plan, loop)
            else:
                await sse_service.send_event(
                    job_id, "complete", {"message": "Rename cancelled by user."}
                )

        except Exception as e:
            await sse_service.send_event(job_id, "error", {"message": str(e)})

    @staticmethod
    def _execute_rename(job_id: str, plan: List[Dict], loop: asyncio.AbstractEventLoop):
        total = len(plan)
        success = 0
        fail = 0
        for i, item in enumerate(plan, 1):
            asyncio.run_coroutine_threadsafe(
                sse_service.send_event(
                    job_id,
                    "progress",
                    {
                        "step": f"Renaming ({i}/{total})",
                        "current": i,
                        "total": total,
                        "percent": round(i / total * 100, 2),
                        "message": item["new_name"],
                    },
                ),
                loop,
            )

            try:
                os.rename(item["old"], item["new"])
                asyncio.run_coroutine_threadsafe(
                    sse_service.send_event(
                        job_id,
                        "log",
                        {"message": f"OK   {item['old_name']} -> {item['new_name']}"},
                    ),
                    loop,
                )
                success += 1
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    sse_service.send_event(
                        job_id, "log", {"message": f"FAIL {item['old_name']}: {str(e)}"}
                    ),
                    loop,
                )
                fail += 1

        asyncio.run_coroutine_threadsafe(
            sse_service.send_event(
                job_id,
                "complete",
                {"message": f"Done: {success} renamed, {fail} failed."},
            ),
            loop,
        )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "-", name)
        return name.strip()

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
    def _download_titledb(job_id: str) -> Dict[str, str]:
        cache_path = Path(config.temp_dir) / "titledb.json"
        os.makedirs(config.temp_dir, exist_ok=True)

        if not cache_path.exists() or (
            time.time() - cache_path.stat().st_mtime > 86400
        ):
            try:
                response = requests.get(TITLEDB_URL, stream=True, timeout=30)
                response.raise_for_status()
                with open(cache_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception:
                if not cache_path.exists():
                    return {}

        db: Dict[str, str] = {}
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.values():
                    if isinstance(item, dict) and "id" in item and "name" in item:
                        db[item["id"].upper()] = item["name"]
        except:
            pass
        return db

    @staticmethod
    def _get_file_info(path: str) -> Tuple[Optional[str], Optional[int]]:
        from nsz.FileExistingChecks import ExtractTitleIDAndVersion

        class Args:
            parseCnmt = True
            alwaysParseCnmt = False

        try:
            res = ExtractTitleIDAndVersion(path, Args())
            if res:
                return res[0], res[1]
        except:
            pass
        return None, None
