from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from operatekit.core.shared.errors import ObservationTimeoutError

T = TypeVar("T")


@dataclass(frozen=True)
class WaitPolicy:
    timeout: float = 10
    poll_interval: float = 0.25


class AutoWaiter:
    def until(self, fn: Callable[[], T | None | bool], *, timeout: float = 10, poll_interval: float = 0.25, message: str = "condition") -> T:
        deadline = time.monotonic() + timeout
        last_value = None
        while time.monotonic() <= deadline:
            value = fn()
            if value:
                return value  # type: ignore[return-value]
            last_value = value
            time.sleep(poll_interval)
        raise ObservationTimeoutError(f"timed out waiting for {message}; last={last_value!r}")
