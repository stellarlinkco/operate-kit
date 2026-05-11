from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING
import time

from operatekit.core.shared.errors import StepExecutionError
from operatekit.core.shared.ids import StepId
from operatekit.core.shared.time import utc_now_iso
from operatekit.core.workflow.value_objects import RetryPolicy, StepStatus

if TYPE_CHECKING:
    from operatekit.runtime.context import RunContext

StepFn = Callable[["RunContext"], Any]


@dataclass
class StepResult:
    step_id: str
    name: str
    status: StepStatus
    attempts: int
    started_at: str
    ended_at: str
    error: str | None = None
    output: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "status": self.status.value,
            "attempts": self.attempts,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "error": self.error,
            "output": self.output,
            "metadata": self.metadata,
        }


@dataclass
class Step:
    name: str
    action: StepFn
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    step_id: StepId = field(default_factory=StepId.new)

    def execute(self, ctx: "RunContext") -> StepResult:
        started = utc_now_iso()
        delay = self.retry_policy.delay_seconds
        attempts = 0
        last_error: str | None = None

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            attempts = attempt
            if ctx.trace is not None:
                ctx.trace.before_step(ctx, self, attempt)
            try:
                output = self.action(ctx)
                ended = utc_now_iso()
                result = StepResult(
                    step_id=str(self.step_id),
                    name=self.name,
                    status=StepStatus.PASSED,
                    attempts=attempts,
                    started_at=started,
                    ended_at=ended,
                    output=output,
                    metadata=dict(self.metadata),
                )
                if ctx.trace is not None:
                    ctx.trace.after_step(ctx, self, result)
                return result
            except Exception as exc:  # noqa: BLE001 - wrap any step failure with ledger info
                last_error = f"{type(exc).__name__}: {exc}"
                if ctx.trace is not None:
                    ctx.trace.step_error(ctx, self, attempt, exc)
                if attempt >= self.retry_policy.max_attempts:
                    break
                if delay:
                    time.sleep(delay)
                    delay *= self.retry_policy.backoff_multiplier

        ended = utc_now_iso()
        result = StepResult(
            step_id=str(self.step_id),
            name=self.name,
            status=StepStatus.FAILED,
            attempts=attempts,
            started_at=started,
            ended_at=ended,
            error=last_error,
            metadata=dict(self.metadata),
        )
        if ctx.trace is not None:
            ctx.trace.after_step(ctx, self, result)
        return result

    @staticmethod
    def from_callable(name: str, func: StepFn, *, retry_policy: RetryPolicy | None = None, **metadata: Any) -> "Step":
        return Step(name=name, action=func, retry_policy=retry_policy or RetryPolicy(), metadata=metadata)


def ensure_passed(result: StepResult) -> None:
    if result.status != StepStatus.PASSED:
        raise StepExecutionError(result.error or f"step failed: {result.name}")
