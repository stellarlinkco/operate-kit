from __future__ import annotations

from typing import Protocol, runtime_checkable
from operatekit.core.workflow.run import WorkflowRun


@runtime_checkable
class RunLedger(Protocol):
    def record_run(self, run: WorkflowRun) -> None: ...
