from __future__ import annotations

from collections.abc import Sequence

from operatekit.core.shared.errors import StepExecutionError
from operatekit.core.workflow.run import WorkflowRun
from operatekit.core.workflow.step import Step
from operatekit.core.workflow.value_objects import StepStatus, WorkflowStatus
from operatekit.ports.run_ledger import RunLedger
from operatekit.runtime.context import RunContext


class WorkflowRunner:
    def __init__(self, ledger: RunLedger | None = None):
        self.ledger = ledger

    def run_steps(
        self,
        name: str,
        steps: Sequence[Step],
        ctx: RunContext,
        *,
        raise_on_failure: bool = True,
    ) -> WorkflowRun:
        run = WorkflowRun(name=name)
        run.run_id = ctx.run_id
        run.start()
        failed = False

        for step in steps:
            result = step.execute(ctx)
            run.add_step_result(result)
            if result.status != StepStatus.PASSED:
                failed = True
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
