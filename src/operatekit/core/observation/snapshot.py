from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable
import json

from operatekit.core.observation.observation import Observation


@dataclass(frozen=True)
class ObservationSnapshot:
    hash: str
    observation_id: str
    kind: str
    summary: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_observation(observation: Observation, *, fields: Iterable[str] | None = None) -> "ObservationSnapshot":
        if fields is None:
            material: Any = observation.to_dict(include_id=False)
        else:
            source = observation.json() if isinstance(observation.content, (dict, list, str, bytes)) else {}
            material = _pick_fields(source, list(fields))
        encoded = json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return ObservationSnapshot(
            hash=sha256(encoded).hexdigest(),
            observation_id=str(observation.observation_id),
            kind=observation.kind.value,
            summary={"source": observation.source, "metadata": observation.metadata},
        )


def _pick_fields(source: Any, fields: list[str]) -> Any:
    if isinstance(source, list):
        return [_pick_fields(item, fields) for item in source]
    if not isinstance(source, dict):
        return source
    return {name: source.get(name) for name in fields}
