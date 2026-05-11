from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from operatekit.core.shared.ids import RunId
from operatekit.core.target.target import TargetSpec
from operatekit.ports.host_driver import HostDriver
from operatekit.ports.notifier import Notifier
from operatekit.ports.observation_port import ObservationRepository
from operatekit.ports.surface_driver import SurfaceDriver


@dataclass
class RunContext:
    target: TargetSpec
    host: HostDriver | None
    surface: SurfaceDriver
    observations: ObservationRepository
    artifacts_dir: Path
    run_id: RunId = field(default_factory=RunId.new)
    variables: dict[str, Any] = field(default_factory=dict)
    notifier: Notifier | None = None
    trace: Any | None = None

    def __post_init__(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        if self.notifier is not None:
            self.notifier.notify(event, {"run_id": str(self.run_id), **payload})
