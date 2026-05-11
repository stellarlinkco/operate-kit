from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RiskPolicy:
    """Policy object for high-impact RPA actions.

    This stays in core so deterministic RPA and future agent workflows can share
    the same approval and audit semantics.
    """

    level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    reason: str | None = None
    limits: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def low() -> "RiskPolicy":
        return RiskPolicy(RiskLevel.LOW)

    @staticmethod
    def high(reason: str, *, requires_approval: bool = True, **limits: Any) -> "RiskPolicy":
        return RiskPolicy(RiskLevel.HIGH, requires_approval=requires_approval, reason=reason, limits=limits)
