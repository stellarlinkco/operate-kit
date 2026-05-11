from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from operatekit.core.ui.locator import Locator


@dataclass(frozen=True)
class BlockerRule:
    name: str
    locator: Locator
    dismiss: Locator | None = None
    timeout: float = 0.5


class BlockerManager:
    def __init__(self, rules: Iterable[BlockerRule] = ()): 
        self.rules = list(rules)

    def check_and_dismiss(self, surface: object) -> list[str]:
        dismissed: list[str] = []
        for rule in self.rules:
            exists = surface.exists(rule.locator, timeout=rule.timeout)  # type: ignore[attr-defined]
            if exists:
                surface.click(rule.dismiss or rule.locator, timeout=rule.timeout)  # type: ignore[attr-defined]
                dismissed.append(rule.name)
        return dismissed
