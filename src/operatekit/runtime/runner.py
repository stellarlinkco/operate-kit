from __future__ import annotations

from collections.abc import Sequence
from typing import Iterable

from operatekit.core.shared.errors import StepExecutionError
from operatekit.core.workflow.run import WorkflowRun
from operatekit.core.workflow.step import Step
from operatekit.core.workflow.value_objects import StepStatus, WorkflowStatus
from operatekit.ports.run_ledger import RunLedger
from operatekit.runtime.context import RunContext
from operatekit.runtime.hooks import RuntimeHook, Stabilizer, StabilizationConfig


class WorkflowRunner:
    def __init__(self, ledger: RunLedger | None = None, *, hooks: Iterable[RuntimeHook] = (), stabilization: StabilizationConfig | None = None):
        self.ledger = ledger
        self.stabilizer = Stabilizer(list(hooks), config=stabilization)

    def register_hook(self, hook: RuntimeHook) -> None:
        self.stabilizer.add_hook(hook)

    def run_steps(
        self,
        name: str,
        steps: Sequence[Step],
        ctx: RunContext,
        *,
        raise_on_failure: bool = True,
    ) -> WorkflowRun:
        if ctx.stabilizer is None and self.stabilizer.hooks:
            ctx.stabilizer = self.stabilizer
        run = WorkflowRun(name=name)
        run.run_id = ctx.run_id
        run.start()
        failed = False

        for step in steps:
            result = step.execute(ctx)
            run.add_step_result(result)
            if result.status != StepStatus.PASSED:
                failed = True
                if result.interference is not None and result.interference.is_manual_required:
                    run.metadata["runtime_hook"] = result.interference.to_dict()
                    run.finish(WorkflowStatus.MANUAL_REQUIRED)
                    if self.ledger is not None:
                        self.ledger.record_run(run)
                    ctx.notify("workflow.manual_required", {"name": name, "step": step.name, "reason": result.error})
                    return run
                if result.interference is not None:
                    run.metadata["runtime_hook"] = result.interference.to_dict()
                run.finish(WorkflowStatus.FAILED)
                if self.ledger is not None:
                    self.ledger.record_run(run)
                ctx.notify("workflow.failed", {"name": name, "step": step.name, "error": result.error})
                if raise_on_failure:
                    raise StepExecutionError(result.error or f"step failed: {step.name}")
                return run

        run.finish(WorkflowStatus.FAILED if failed else WorkflowStatus.PASSED)
        if self.ledger is not None:
            self.ledger.record_run(run)
        ctx.notify("workflow.finished", {"name": name, "status": run.status.value})
        return run

    def run_subflow(self, name: str, steps: Sequence[Step], ctx: RunContext) -> WorkflowRun:
        return self.run_steps(name, steps, ctx, raise_on_failure=False)
