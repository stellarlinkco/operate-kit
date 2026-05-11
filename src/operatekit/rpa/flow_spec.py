from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandSpec:
    command: str
    params: Any = None


@dataclass(frozen=True)
class FlowSpec:
    name: str
    commands: list[CommandSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FlowSpec":
        commands: list[CommandSpec] = []
        for item in data.get("commands", []):
            if not isinstance(item, dict) or len(item) != 1:
                raise ValueError(f"command must be single-key dict: {item}")
            key, value = next(iter(item.items()))
            commands.append(CommandSpec(key, value))
        return FlowSpec(name=data.get("name", "flow"), commands=commands, metadata=data.get("metadata", {}))
