from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"
    CANCELLED = "cancelled"


class HookOutcome(str, Enum):
    NOOP = "noop"
    HANDLED = "handled"
    MANUAL_REQUIRED = "manual_required"
    RETRY_STEP = "retry_step"
    FAIL_WORKFLOW = "fail_workflow"


@dataclass(frozen=True)
class RuntimeObservation:
    ui_tree: str
    package: str | None = None
    activity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HookResult:
    outcome: HookOutcome
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StabilizationResult:
    outcome: HookOutcome
    reason: str | None = None
    observation: RuntimeObservation | None = None
    hook_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for one step.

    `max_attempts` includes the first try. For a Maestro-like retry block with
    three retries after the first attempt, pass `max_retries=3` to
    `Actions.retry_block`; it will map to four attempts internally.
    """

    max_attempts: int = 1
    delay_seconds: float = 0.0
    backoff_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be >= 1")
