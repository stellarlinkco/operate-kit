from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

from operatekit.core.observation.observation import Observation, ObservationCursor, ObservationKind
from operatekit.core.observation.patterns import match_observation
from operatekit.core.shared.errors import ObservationTimeoutError


class JsonlObservationRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _load(self) -> list[Observation]:
        if not self.path.exists():
            return []
        observations: list[Observation] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                observations.append(Observation.from_dict(json.loads(line)))
        return observations

    def add(self, observation: Observation) -> Observation:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(observation.to_dict(), ensure_ascii=False) + "\n")
        return observation

    def cursor(self) -> ObservationCursor:
        return ObservationCursor(position=len(self._load()))

    def list_after(self, cursor: ObservationCursor | None = None, *, kind: ObservationKind | str | None = None) -> list[Observation]:
        start = cursor.position if cursor else 0
        kind_value = ObservationKind(kind).value if kind else None
        rows = self._load()[start:]
        if kind_value is None:
            return rows
        return [obs for obs in rows if obs.kind.value == kind_value]

    def wait_for(
        self,
        pattern: str,
        *,
        kind: ObservationKind | str | None = None,
        cursor: ObservationCursor | None = None,
        timeout: float = 30,
        poll_interval: float = 0.25,
    ) -> Observation:
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            for obs in self.list_after(cursor, kind=kind):
                if match_observation(pattern, obs):
                    return obs
            time.sleep(poll_interval)
        raise ObservationTimeoutError(f"timed out waiting for observation pattern={pattern!r} kind={kind!r}")
