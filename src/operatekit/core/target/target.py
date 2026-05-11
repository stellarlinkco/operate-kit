from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TargetKind(str, Enum):
    ANDROID = "android"
    WINDOWS = "windows"
    WEB = "web"
    API = "api"


@dataclass(frozen=True)
class TargetSpec:
    kind: TargetKind
    id: str
    name: str | None = None
    package: str | None = None
    executable: str | None = None
    title: str | None = None
    backend: str | None = None
    launch_args: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def android(package: str, *, serial: str | None = None, name: str | None = None, **metadata: Any) -> "TargetSpec":
        return TargetSpec(
            kind=TargetKind.ANDROID,
            id=package,
            name=name or package,
            package=package,
            metadata={"serial": serial, **metadata},
        )

    @staticmethod
    def windows(
        executable: str | None = None,
        *,
        title: str | None = None,
        backend: str = "uia",
        name: str | None = None,
        launch_args: list[str] | None = None,
        **metadata: Any,
    ) -> "TargetSpec":
        identifier = executable or title or name or "windows-target"
        return TargetSpec(
            kind=TargetKind.WINDOWS,
            id=identifier,
            name=name or identifier,
            executable=executable,
            title=title,
            backend=backend,
            launch_args=launch_args or [],
            metadata=metadata,
        )
