from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    def notify(self, event: str, payload: dict[str, Any]) -> None: ...
