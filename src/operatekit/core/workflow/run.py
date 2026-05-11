from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from operatekit.core.shared.ids import RunId
from operatekit.core.shared.time import utc_now_iso
from operatekit.core.workflow.step import StepResult
from operatekit.core.workflow.value_objects import WorkflowStatus


@dataclass
class WorkflowRun:
    name: str
    run_id: RunId = field(default_factory=RunId.new)
    status: WorkflowStatus = WorkflowStatus.CREATED
    started_at: str | None = None
    ended_at: str | None = None
    step_results: list[StepResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.status = WorkflowStatus.RUNNING
        self.started_at = utc_now_iso()

    def add_step_result(self, result: StepResult) -> None:
        self.step_results.append(result)

    def finish(self, status: WorkflowStatus) -> None:
        self.status = status
        self.ended_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "steps": [r.to_dict() for r in self.step_results],
            "metadata": self.metadata,
        }
