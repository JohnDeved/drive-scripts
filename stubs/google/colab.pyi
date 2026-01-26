from typing import Any, Optional

class drive:
    @staticmethod
    def mount(
        mountpoint: str,
        force_remount: bool = False,
        timeout_ms: int = 120000,
        readonly: bool = False,
    ) -> None: ...
    @staticmethod
    def flush_and_unmount(timeout_ms: int = 120000) -> None: ...

class userdata:
    @staticmethod
    def get(key: str) -> str: ...
