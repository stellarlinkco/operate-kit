from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@dataclass(frozen=True)
class RunId:
    value: str

    @staticmethod
    def new() -> "RunId":
        return RunId(new_id("run"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StepId:
    value: str

    @staticmethod
    def new() -> "StepId":
        return StepId(new_id("step"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ObservationId:
    value: str

    @staticmethod
    def new() -> "ObservationId":
        return ObservationId(new_id("obs"))

    def __str__(self) -> str:
        return self.value
