from __future__ import annotations

from typing import Any

from operatekit.core.ui.locator import Locator
from operatekit.core.workflow.step import Step
from operatekit.rpa.actions import Actions
from operatekit.rpa.blockers import BlockerManager, LegacyBlockerHook
from operatekit.runtime.hooks import Stabilizer
from operatekit.rpa.flow_spec import CommandSpec, FlowSpec
from operatekit.rpa.screen_object import locator_from_spec


class FlowCompiler:
    def __init__(self, *, blocker_manager: BlockerManager | None = None):
        self.blocker_manager = blocker_manager

    def compile(self, flow: FlowSpec | dict[str, Any]) -> list[Step]:
        spec = FlowSpec.from_dict(flow) if isinstance(flow, dict) else flow
        return [self._compile_command(cmd) for cmd in spec.commands]

    def _compile_command(self, cmd: CommandSpec) -> Step:
        name = cmd.command
        params = cmd.params if cmd.params is not None else {}
        if name == "launch":
            return Actions.launch(stop=bool(params.get("stop", False)) if isinstance(params, dict) else False)
        if name in {"tap", "click"}:
            loc, timeout = _locator_and_timeout(params)
            return Actions.tap(loc, timeout=timeout)
        if name in {"inputText", "typeText"}:
            if isinstance(params, str):
                return Actions.type_text(params)
            locator = _maybe_locator(params)
            return Actions.type_text(params["text"], locator=locator, clear=bool(params.get("clear", False)), timeout=float(params.get("timeout", 10)))
        if name == "pressKey":
            return Actions.press_key(params if isinstance(params, str) else params["key"])
        if name == "scroll":
            if isinstance(params, str):
                return Actions.scroll(params)
            return Actions.scroll(params.get("direction", "down"), amount=float(params.get("amount", 0.8)))
        if name == "waitVisible":
            loc, timeout = _locator_and_timeout(params)
            return Actions.wait_visible(loc, timeout=timeout)
        if name == "captureCursor":
            return Actions.capture_cursor(params["key"])
        if name in {"waitObservation", "waitPayload"}:
            if name == "waitPayload":
                params = {"kind": "network", **params}
            return Actions.wait_observation(
                kind=params.get("kind"),
                pattern=params["pattern"],
                cursor_key=params.get("cursorKey") or params.get("cursor_key"),
                timeout=float(params.get("timeout", 30)),
                store_key=params.get("storeKey") or params.get("store_key"),
            )
        if name == "shell":
            if isinstance(params, str):
                return Actions.shell(params)
            return Actions.shell(params["command"], timeout=params.get("timeout"), store_key=params.get("storeKey"))
        if name == "deeplink":
            url = params if isinstance(params, str) else params["url"]
            return Actions.deeplink(url)
        if name == "sleep":
            return Actions.sleep(float(params))
        if name == "checkBlockers":
            manager = self.blocker_manager

            def _check_blockers(ctx: Any) -> dict[str, Any]:
                stabilizer = _check_blockers_stabilizer(getattr(ctx, "stabilizer", None), manager)
                return stabilizer.stabilize(ctx, step_name="check_blockers", phase="compat").metadata

            return Actions.call("check_blockers", _check_blockers)
        if name == "retry":
            inner = params.get("commands", [])
            steps = FlowCompiler(blocker_manager=self.blocker_manager).compile({"name": params.get("name", "retry"), "commands": inner})
            return Actions.retry_block(
                params.get("name", "retry"),
                steps,
                max_retries=int(params.get("maxRetries", params.get("max_retries", 3))),
                delay_seconds=float(params.get("delay", params.get("delaySeconds", 0))),
            )
        raise ValueError(f"unsupported command: {name}")


def _check_blockers_stabilizer(active: Stabilizer | None, manager: BlockerManager | None) -> Stabilizer:
    rules = list(manager.rules) if manager is not None else []
    if active is None:
        return Stabilizer([LegacyBlockerHook(rules)] if rules else [])
    if not rules or _has_legacy_blocker_hook(active, rules):
        return active
    return Stabilizer([*active.hooks, LegacyBlockerHook(rules)], config=active.config, observer=active.observer)


def _has_legacy_blocker_hook(stabilizer: Stabilizer, rules: list[Any]) -> bool:
    return any(isinstance(hook, LegacyBlockerHook) and hook.rules == rules for hook in stabilizer.hooks)


def _locator_and_timeout(params: dict[str, Any]) -> tuple[Locator, float]:
    return locator_from_spec(params), float(params.get("timeout", 10))


def _maybe_locator(params: dict[str, Any]) -> Locator | None:
    locator_keys = {"text", "xpath", "resource_id", "content_desc", "automation_id", "title", "name", "control_type", "class_name", "coordinates"}
    if any(k in params for k in locator_keys):
        return locator_from_spec(params)
    return None
