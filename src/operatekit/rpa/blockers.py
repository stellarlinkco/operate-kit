from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from operatekit.core.ui.locator import Locator
from operatekit.core.workflow.value_objects import HookOutcome, HookResult, RuntimeObservation


@dataclass(frozen=True)
class BlockerRule:
    name: str
    locator: Locator
    dismiss: Locator | None = None
    timeout: float = 0.5


class BlockerManager:
    def __init__(self, rules: Iterable[BlockerRule] = ()):
        self.rules = list(rules)

    def check_and_dismiss(self, surface: object) -> list[str]:
        dismissed: list[str] = []
        hook = LegacyBlockerHook(self.rules)
        ctx = _SurfaceHookContext(surface, dismissed)
        for _ in range(max(1, len(self.rules))):
            observation = RuntimeObservation(ui_tree=surface.get_tree())  # type: ignore[attr-defined]
            result = hook.handle(ctx, observation)
            if result.outcome != HookOutcome.HANDLED:
                break
        return dismissed


class _SurfaceHookContext:
    def __init__(self, surface: object, dismissed: list[str]):
        self.surface = surface
        self.dismissed = dismissed

    def click(self, locator: Locator, *, timeout: float = 0.5) -> None:
        self.surface.click(locator, timeout=timeout)  # type: ignore[attr-defined]

    def notify(self, event: str, payload: dict[str, object]) -> None:
        if event == "legacy_blocker.dismissed":
            rule = payload.get("rule")
            if isinstance(rule, str):
                self.dismissed.append(rule)


@dataclass(frozen=True)
class PermissionPolicy:
    """Substring-based permission policy for generic runtime hooks."""

    allow: dict[str, Locator] = field(default_factory=dict)
    deny: dict[str, Locator] = field(default_factory=dict)
    prompt_patterns: tuple[str, ...] = ("permission",)
    timeout: float = 0.5


class PermissionHook:
    name = "permission"
    priority = 90

    def __init__(self, policy: PermissionPolicy | None = None, *, priority: int = 90):
        self.policy = policy or PermissionPolicy()
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        for pattern, locator in self.policy.allow.items():
            if _text_matches_observation(pattern, observation):
                ctx.click(locator, timeout=self.policy.timeout)  # type: ignore[attr-defined]
                return HookResult(HookOutcome.HANDLED, reason="permission allowed", metadata={"pattern": pattern, "decision": "allow"})
        for pattern, locator in self.policy.deny.items():
            if _text_matches_observation(pattern, observation):
                ctx.click(locator, timeout=self.policy.timeout)  # type: ignore[attr-defined]
                return HookResult(HookOutcome.HANDLED, reason="permission denied", metadata={"pattern": pattern, "decision": "deny"})
        if _any_pattern_matches(self.policy.prompt_patterns, observation):
            return HookResult(HookOutcome.MANUAL_REQUIRED, reason="unknown permission prompt")
        return HookResult(HookOutcome.NOOP)


@dataclass(frozen=True)
class ErrorRule:
    pattern: str
    outcome: HookOutcome | str
    reason: str | None = None


@dataclass(frozen=True)
class ErrorPolicy:
    rules: Iterable[ErrorRule] = ()
    error_patterns: tuple[str, ...] = ("network", "server")


class NetworkErrorHook:
    name = "network_error"
    priority = 80

    def __init__(self, policy: ErrorPolicy | None = None, *, priority: int = 80):
        self.policy = policy or ErrorPolicy()
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        for rule in self.policy.rules:
            if _text_matches_observation(rule.pattern, observation):
                outcome = HookOutcome(rule.outcome)
                return HookResult(outcome, reason=rule.reason or rule.pattern, metadata={"pattern": rule.pattern})
        if _any_pattern_matches(self.policy.error_patterns, observation):
            return HookResult(HookOutcome.FAIL_WORKFLOW, reason="unknown network/server error")
        return HookResult(HookOutcome.NOOP)


class CaptchaHook:
    name = "captcha"
    priority = 100

    def __init__(self, patterns: Iterable[str] = ("captcha", "human verification"), *, priority: int = 100):
        self.patterns = tuple(patterns)
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        if _any_pattern_matches(self.patterns, observation):
            return HookResult(HookOutcome.MANUAL_REQUIRED, reason="captcha/human verification detected")
        return HookResult(HookOutcome.NOOP)


class UpdateDialogHook:
    name = "update_dialog"
    priority = 70

    def __init__(self, patterns: Iterable[str], dismiss: Locator, *, timeout: float = 0.5, priority: int = 70):
        self.patterns = tuple(patterns)
        self.dismiss = dismiss
        self.timeout = timeout
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        if _any_pattern_matches(self.patterns, observation):
            ctx.click(self.dismiss, timeout=self.timeout)  # type: ignore[attr-defined]
            return HookResult(HookOutcome.HANDLED, reason="update dialog dismissed")
        return HookResult(HookOutcome.NOOP)


class AdDialogHook:
    name = "ad_dialog"
    priority = 70

    def __init__(self, patterns: Iterable[str], dismiss: Locator, *, timeout: float = 0.5, priority: int = 70):
        self.patterns = tuple(patterns)
        self.dismiss = dismiss
        self.timeout = timeout
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        if _any_pattern_matches(self.patterns, observation):
            ctx.click(self.dismiss, timeout=self.timeout)  # type: ignore[attr-defined]
            return HookResult(HookOutcome.HANDLED, reason="ad dialog dismissed")
        return HookResult(HookOutcome.NOOP)


class LegacyBlockerHook:
    name = "legacy_blocker"
    priority = 0

    def __init__(self, rules: Iterable[BlockerRule] = (), *, priority: int = 0):
        self.rules = list(rules)
        self.priority = priority

    def handle(self, ctx: object, observation: RuntimeObservation) -> HookResult:
        for rule in self.rules:
            if _locator_matches_observation(rule.locator, observation):
                ctx.click(rule.dismiss or rule.locator, timeout=rule.timeout)  # type: ignore[attr-defined]
                ctx.notify("legacy_blocker.dismissed", {"rule": rule.name})  # type: ignore[attr-defined]
                return HookResult(HookOutcome.HANDLED, reason=rule.name)
        return HookResult(HookOutcome.NOOP)


def _locator_matches_observation(locator: Locator, observation: RuntimeObservation) -> bool:
    return str(locator.value) in observation.ui_tree


def _text_matches_observation(pattern: str, observation: RuntimeObservation) -> bool:
    return pattern.lower() in observation.ui_tree.lower()


def _any_pattern_matches(patterns: Iterable[str], observation: RuntimeObservation) -> bool:
    return any(_text_matches_observation(pattern, observation) for pattern in patterns)
