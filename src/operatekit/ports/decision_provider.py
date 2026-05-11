from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DecisionProvider(Protocol):
    def decide(self, task: str, *, evidence: list[Any], schema: Any | None = None) -> Any: ...
