from __future__ import annotations

import time
from typing import Any, Callable, Iterable

from operatekit.core.observation.observation import ObservationKind
from operatekit.core.shared.errors import StepExecutionError
from operatekit.core.ui.locator import Locator
from operatekit.core.workflow.step import Step, ensure_passed
from operatekit.core.workflow.value_objects import RetryPolicy


class Actions:
    """Factory for reusable RPA steps.

    The methods here are platform-neutral. Android and Windows behavior is
    supplied by the active SurfaceDriver / HostDriver in RunContext.
    """

    @staticmethod
    def call(name: str, fn: Callable[[Any], Any], *, retry: RetryPolicy | None = None, hookable: bool = False, **metadata: Any) -> Step:
        return Step.from_callable(name, fn, retry_policy=retry, hookable=hookable, **metadata)

    @staticmethod
    def launch(*, stop: bool = False) -> Step:
        def _run(ctx: Any) -> None:
            ctx.surface.launch(ctx.target, stop=stop)
        return Step.from_callable("launch", _run, hookable=True, stop=stop)

    @staticmethod
    def close() -> Step:
        return Step.from_callable("close", lambda ctx: ctx.surface.close(), hookable=True)

    @staticmethod
    def tap(locator: Locator, *, timeout: float = 10) -> Step:
        def _run(ctx: Any) -> None:
            ctx.surface.click(locator, timeout=timeout)
        return Step.from_callable("tap", _run, hookable=True, locator=locator.to_dict(), timeout=timeout)

    click = tap

    @staticmethod
    def type_text(text: str, *, locator: Locator | None = None, clear: bool = False, timeout: float = 10) -> Step:
        def _run(ctx: Any) -> None:
            ctx.surface.type_text(text, locator=locator, clear=clear, timeout=timeout)
        metadata = {"text": "***" if len(text) > 64 else text, "clear": clear, "timeout": timeout}
        if locator is not None:
            metadata["locator"] = locator.to_dict()
        return Step.from_callable("type_text", _run, hookable=True, **metadata)

    @staticmethod
    def press_key(key: str) -> Step:
        return Step.from_callable("press_key", lambda ctx: ctx.surface.press_key(key), hookable=True, key=key)

    @staticmethod
    def scroll(direction: str = "down", *, amount: float = 0.8) -> Step:
        return Step.from_callable("scroll", lambda ctx: ctx.surface.scroll(direction, amount=amount), hookable=True, direction=direction, amount=amount)

    @staticmethod
    def wait_visible(locator: Locator, *, timeout: float = 10) -> Step:
        def _run(ctx: Any) -> None:
            ctx.surface.wait_visible(locator, timeout=timeout)
        return Step.from_callable("wait_visible", _run, locator=locator.to_dict(), timeout=timeout)

    @staticmethod
    def assert_visible(locator: Locator, *, timeout: float = 10) -> Step:
        return Actions.wait_visible(locator, timeout=timeout)

    @staticmethod
    def shell(command: str, *, timeout: float | None = None, store_key: str | None = None) -> Step:
        def _run(ctx: Any) -> str:
            if ctx.host is None:
                raise StepExecutionError("no host driver is configured")
            output = ctx.host.shell(command, timeout=timeout)
            if store_key:
                ctx.set(store_key, output)
            return output
        return Step.from_callable("shell", _run, command=command, timeout=timeout, store_key=store_key)

    @staticmethod
    def deeplink(url: str) -> Step:
        def _run(ctx: Any) -> None:
            if ctx.host is None:
                raise StepExecutionError("no host driver is configured")
            ctx.host.open_url(url)
        return Step.from_callable("deeplink", _run, hookable=True, url=url)

    @staticmethod
    def sleep(seconds: float) -> Step:
        return Step.from_callable("sleep", lambda ctx: time.sleep(seconds), seconds=seconds)

    @staticmethod
    def capture_cursor(key: str) -> Step:
        def _run(ctx: Any) -> Any:
            cursor = ctx.observations.cursor()
            ctx.set(key, cursor)
            return {"position": cursor.position}
        return Step.from_callable("capture_cursor", _run, key=key)

    @staticmethod
    def wait_observation(
        *,
        kind: ObservationKind | str | None = None,
        pattern: str,
        cursor_key: str | None = None,
        timeout: float = 30,
        store_key: str | None = None,
    ) -> Step:
        def _run(ctx: Any) -> Any:
            cursor = ctx.get(cursor_key) if cursor_key else None
            obs = ctx.observations.wait_for(pattern, kind=kind, cursor=cursor, timeout=timeout)
            if store_key:
                ctx.set(store_key, obs)
            return {"observation_id": str(obs.observation_id), "hash": obs.hash}
        return Step.from_callable("wait_observation", _run, kind=str(kind), pattern=pattern, cursor_key=cursor_key, timeout=timeout, store_key=store_key)

    @staticmethod
    def wait_payload(pattern: str, *, cursor_key: str | None = None, timeout: float = 30, store_key: str | None = None) -> Step:
        return Actions.wait_observation(kind=ObservationKind.NETWORK, pattern=pattern, cursor_key=cursor_key, timeout=timeout, store_key=store_key)

    @staticmethod
    def retry_block(
        name: str,
        steps: Iterable[Step],
        *,
        max_retries: int = 3,
        delay_seconds: float = 0.0,
        backoff_multiplier: float = 1.0,
    ) -> Step:
        block_steps = list(steps)

        def _run(ctx: Any) -> None:
            delay = delay_seconds
            last_error: str | None = None
            total_attempts = max_retries + 1
            for attempt in range(1, total_attempts + 1):
                try:
                    for child in block_steps:
                        result = child.execute(ctx)
                        ensure_passed(result)
                    return
                except StepExecutionError as exc:
                    failed_result = getattr(exc, "step_result", None)
                    failed_metadata = getattr(failed_result, "metadata", None)
                    hook_metadata = failed_metadata.get("runtime_hook") if isinstance(failed_metadata, dict) else None
                    if hook_metadata is not None:
                        raise exc
                    last_error = f"{type(exc).__name__}: {exc}"
                    ctx.notify("retry_block.failed_attempt", {"name": name, "attempt": attempt, "error": last_error})
                    if attempt >= total_attempts:
                        break
                    if delay:
                        time.sleep(delay)
                        delay *= backoff_multiplier
                except Exception as exc:  # noqa: BLE001
                    last_error = f"{type(exc).__name__}: {exc}"
                    ctx.notify("retry_block.failed_attempt", {"name": name, "attempt": attempt, "error": last_error})
                    if attempt >= total_attempts:
                        break
                    if delay:
                        time.sleep(delay)
                        delay *= backoff_multiplier
            raise StepExecutionError(f"retry block {name!r} failed after {total_attempts} attempts: {last_error}")

        return Step.from_callable("retry_block:" + name, _run, max_retries=max_retries, child_steps=[s.name for s in block_steps])
