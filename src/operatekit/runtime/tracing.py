from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from operatekit.core.workflow.step import Step, StepResult
from operatekit.core.shared.time import utc_now_iso


@dataclass
class TraceConfig:
    capture_ui_tree: bool = False
    capture_screenshot: bool = False
    screenshot_on_error: bool = True


class TraceRecorder:
    def __init__(self, artifacts_dir: str | Path, config: TraceConfig | None = None):
        self.artifacts_dir = Path(artifacts_dir)
        self.trace_dir = self.artifacts_dir / "trace"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or TraceConfig()
        self.path = self.trace_dir / "trace.jsonl"

    def _write(self, event: str, data: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event, "at": utc_now_iso(), **data}, ensure_ascii=False) + "\n")

    def before_step(self, ctx: Any, step: Step, attempt: int) -> None:
        record: dict[str, Any] = {"run_id": str(ctx.run_id), "step": step.name, "attempt": attempt, "metadata": step.metadata}
        if self.config.capture_ui_tree:
            try:
                tree = ctx.surface.get_tree()
                p = self.trace_dir / f"{step.name.replace(' ', '_')}_{attempt}.xml"
                p.write_text(tree, encoding="utf-8")
                record["ui_tree"] = str(p)
            except Exception as exc:  # noqa: BLE001
                record["ui_tree_error"] = str(exc)
        self._write("before_step", record)

    def after_step(self, ctx: Any, step: Step, result: StepResult) -> None:
        self._write("after_step", {"run_id": str(ctx.run_id), "step": step.name, "result": result.to_dict()})

    def step_error(self, ctx: Any, step: Step, attempt: int, exc: Exception) -> None:
        record: dict[str, Any] = {"run_id": str(ctx.run_id), "step": step.name, "attempt": attempt, "error": f"{type(exc).__name__}: {exc}"}
        if self.config.screenshot_on_error:
            try:
                p = self.trace_dir / f"{step.name.replace(' ', '_')}_{attempt}_error.png"
                ctx.surface.screenshot(p)
                record["screenshot"] = str(p)
            except Exception as screenshot_exc:  # noqa: BLE001
                record["screenshot_error"] = str(screenshot_exc)
        self._write("step_error", record)
