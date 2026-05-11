from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HostDriver(Protocol):
    def shell(self, command: str, *, timeout: float | None = None) -> str: ...
    def open_url(self, url: str) -> None: ...
