from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from operatekit.core.ui.locator import Locator
from operatekit.core.workflow.value_objects import HookOutcome, HookResult, RuntimeObservation, StabilizationResult


class HookContext(Protocol):
    def click(self, locator: Locator, *, timeout: float = 0.5) -> None: ...
    def press_key(self, key: str) -> None: ...
    def wait(self, seconds: float) -> None: ...
    def notify(self, event: str, payload: dict[str, Any]) -> None: ...


class RuntimeHook(Protocol):
    name: str
    priority: int

    def handle(self, ctx: HookContext, observation: RuntimeObservation) -> HookResult: ...


@dataclass(frozen=True)
class StabilizationConfig:
    max_rounds: int = 5
    timeout_seconds: float = 5.0


class RuntimeObserver:
    def observe(self, ctx: Any) -> RuntimeObservation:
        ui_tree = ctx.surface.get_tree()
        return RuntimeObservation(
            ui_tree=ui_tree,
            package=_read_optional_string(ctx.surface, ctx.host, names=("get_current_package", "current_package", "package")),
            activity=_read_optional_string(ctx.surface, ctx.host, names=("get_current_activity", "current_activity", "activity")),
        )


class RuntimeHookContext:
    def __init__(self, ctx: Any):
        self._ctx = ctx

    def click(self, locator: Locator, *, timeout: float = 0.5) -> None:
        self._ctx.surface.click(locator, timeout=timeout)

    def press_key(self, key: str) -> None:
        self._ctx.surface.press_key(key)

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        self._ctx.notify(event, payload)


class Stabilizer:
    def __init__(self, hooks: list[RuntimeHook] | None = None, *, config: StabilizationConfig | None = None, observer: RuntimeObserver | None = None):
        self.hooks = sorted(hooks or [], key=lambda hook: getattr(hook, "priority", 0), reverse=True)
        self.config = config or StabilizationConfig()
        self.observer = observer or RuntimeObserver()

    def add_hook(self, hook: RuntimeHook) -> None:
        self.hooks.append(hook)
        self.hooks.sort(key=lambda item: getattr(item, "priority", 0), reverse=True)

    def stabilize(self, ctx: Any, *, step_name: str, phase: str) -> StabilizationResult:
        if not self.hooks:
            return StabilizationResult(HookOutcome.NOOP)
        _emit_runtime_event(ctx, "stabilization.started", {"step": step_name, "phase": phase})
        started = time.monotonic()
        hook_ctx = RuntimeHookContext(ctx)
        last_observation: RuntimeObservation | None = None
        for round_number in range(1, self.config.max_rounds + 1):
            if time.monotonic() - started > self.config.timeout_seconds:
                return self._finish(ctx, step_name, phase, round_number, StabilizationResult(HookOutcome.FAIL_WORKFLOW, reason="stabilization timeout", observation=last_observation))
            last_observation = self.observer.observe(ctx)
            handled = False
            for hook in self.hooks:
                result = hook.handle(hook_ctx, last_observation)
                outcome = HookOutcome(result.outcome)
                _emit_runtime_event(
                    ctx,
                    "runtime_hook.outcome",
                    {"step": step_name, "phase": phase, "round": round_number, "hook": hook.name, "outcome": outcome.value, "reason": result.reason},
                )
                if outcome == HookOutcome.NOOP:
                    continue
                handled = True
                if outcome == HookOutcome.HANDLED:
                    break
                return self._finish(
                    ctx,
                    step_name,
                    phase,
                    round_number,
                    StabilizationResult(outcome, reason=result.reason, observation=last_observation, hook_name=hook.name, metadata=result.metadata),
                )
            if handled:
                continue
            return self._finish(ctx, step_name, phase, round_number, StabilizationResult(HookOutcome.NOOP, observation=last_observation))
        return self._finish(ctx, step_name, phase, self.config.max_rounds, StabilizationResult(HookOutcome.FAIL_WORKFLOW, reason="stabilization max rounds exceeded", observation=last_observation))

    def _finish(self, ctx: Any, step_name: str, phase: str, round_number: int, result: StabilizationResult) -> StabilizationResult:
        _emit_runtime_event(ctx, "stabilization.finished", {"step": step_name, "phase": phase, "round": round_number, "outcome": result.outcome.value, "reason": result.reason})
        return result


def _emit_runtime_event(ctx: Any, event: str, payload: dict[str, Any]) -> None:
    ctx.notify(event, payload)
    trace = getattr(ctx, "trace", None)
    if trace is not None and hasattr(trace, "event"):
        trace.event(event, ctx, payload)


def _read_optional_string(surface: Any, host: Any, *, names: tuple[str, ...]) -> str | None:
    for provider in (surface, host):
        if provider is None:
            continue
        for name in names:
            if not hasattr(provider, name):
                continue
            value = getattr(provider, name)
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
            if isinstance(value, str):
                return value
    return None
