from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from operatekit.core.workflow.run import WorkflowRun


class JsonlRunLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def record_run(self, run: WorkflowRun) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(run.to_dict(), ensure_ascii=False) + "\n")
