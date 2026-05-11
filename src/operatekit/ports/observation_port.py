from __future__ import annotations

from typing import Protocol, runtime_checkable

from operatekit.core.observation.observation import Observation, ObservationCursor, ObservationKind


@runtime_checkable
class ObservationRepository(Protocol):
    def add(self, observation: Observation) -> Observation: ...
    def cursor(self) -> ObservationCursor: ...
    def list_after(self, cursor: ObservationCursor | None = None, *, kind: ObservationKind | str | None = None) -> list[Observation]: ...
    def wait_for(
        self,
        pattern: str,
        *,
        kind: ObservationKind | str | None = None,
        cursor: ObservationCursor | None = None,
        timeout: float = 30,
        poll_interval: float = 0.25,
    ) -> Observation: ...
