from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CacheStore(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def has(self, key: str) -> bool: ...
