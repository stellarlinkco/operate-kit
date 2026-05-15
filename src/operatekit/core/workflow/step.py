from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import time

from operatekit.core.shared.errors import StepExecutionError
from operatekit.core.shared.ids import StepId
from operatekit.core.shared.time import utc_now_iso
from operatekit.core.workflow.value_objects import HookOutcome, InterferenceResult, RetryPolicy, StabilizationResult, StepStatus

StepFn = Callable[[Any], Any]


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
    interference: InterferenceResult | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
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
        if self.interference is not None:
            d["interference"] = self.interference.to_dict()
        return d


@dataclass
class Step:
    name: str
    action: StepFn
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    hookable: bool = False
    step_id: StepId = field(default_factory=StepId.new)

    def execute(self, ctx: Any) -> StepResult:
        started = utc_now_iso()
        delay = self.retry_policy.delay_seconds
        attempts = 0
        last_error: str | None = None
        last_metadata: dict[str, Any] | None = None
        last_interference: InterferenceResult | None = None

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            attempts = attempt
            if ctx.trace is not None:
                ctx.trace.before_step(ctx, self, attempt)
            try:
                if self.hookable and ctx.stabilizer is not None:
                    pre_result = ctx.stabilizer.stabilize(ctx, step_name=self.name, phase="pre")
                    if pre_result.outcome == HookOutcome.RETRY_STEP and attempt < self.retry_policy.max_attempts:
                        if delay:
                            time.sleep(delay)
                            delay *= self.retry_policy.backoff_multiplier
                        continue
                    if pre_result.outcome != HookOutcome.NOOP:
                        return _hook_step_result(self, started, attempts, pre_result)
                output = self.action(ctx)
                if self.hookable and ctx.stabilizer is not None:
                    post_result = ctx.stabilizer.stabilize(ctx, step_name=self.name, phase="post")
                    if post_result.outcome == HookOutcome.RETRY_STEP and attempt < self.retry_policy.max_attempts:
                        if delay:
                            time.sleep(delay)
                            delay *= self.retry_policy.backoff_multiplier
                        continue
                    if post_result.outcome != HookOutcome.NOOP:
                        return _hook_step_result(self, started, attempts, post_result)
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
                if isinstance(exc, StepExecutionError):
                    failed_result = getattr(exc, "step_result", None)
                    if failed_result is not None:
                        failed_metadata = getattr(failed_result, "metadata", None)
                        if isinstance(failed_metadata, dict):
                            last_metadata = failed_metadata
                        if getattr(failed_result, "interference", None) is not None:
                            last_interference = failed_result.interference
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
            metadata={**self.metadata, **(last_metadata or {})},
            interference=last_interference,
        )
        if ctx.trace is not None:
            ctx.trace.after_step(ctx, self, result)
        return result

    @staticmethod
    def from_callable(name: str, func: StepFn, *, retry_policy: RetryPolicy | None = None, hookable: bool = False, **metadata: Any) -> "Step":
        return Step(name=name, action=func, retry_policy=retry_policy or RetryPolicy(), metadata=metadata, hookable=hookable)


def _hook_step_result(step: Step, started: str, attempts: int, hook_result: StabilizationResult) -> StepResult:
    interference = InterferenceResult(
        outcome=hook_result.outcome,
        reason=hook_result.reason,
        hook_name=hook_result.hook_name,
        last_observation=hook_result.observation,
        metadata=hook_result.metadata,
    )
    metadata = {**step.metadata, "runtime_hook": interference.to_dict()}
    return StepResult(
        step_id=str(step.step_id),
        name=step.name,
        status=StepStatus.FAILED,
        attempts=attempts,
        started_at=started,
        ended_at=utc_now_iso(),
        error=hook_result.reason or f"runtime hook requested {hook_result.outcome.value}",
        metadata=metadata,
        interference=interference,
    )


def ensure_passed(result: StepResult) -> None:
    if result.status != StepStatus.PASSED:
        raise StepExecutionError(result.error or f"step failed: {result.name}", step_result=result)
