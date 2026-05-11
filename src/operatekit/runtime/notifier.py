from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from operatekit.core.shared.time import utc_now_iso


class JsonlNotifier:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        record = {"event": event, "payload": payload, "created_at": utc_now_iso()}
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
