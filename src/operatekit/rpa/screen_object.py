from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from operatekit.core.ui.locator import Locator
from operatekit.rpa.actions import Actions


@dataclass(frozen=True)
class ScreenElement:
    name: str
    locator: Locator


class ScreenObject:
    def __init__(self, name: str, elements: dict[str, Locator]):
        self.name = name
        self.elements = {k: ScreenElement(k, v) for k, v in elements.items()}

    def locator(self, name: str) -> Locator:
        return self.elements[name].locator

    def tap(self, name: str, *, timeout: float = 10):
        return Actions.tap(self.locator(name), timeout=timeout)

    def type_text(self, name: str, text: str, *, clear: bool = False, timeout: float = 10):
        return Actions.type_text(text, locator=self.locator(name), clear=clear, timeout=timeout)

    def assert_visible(self, name: str, *, timeout: float = 10):
        return Actions.assert_visible(self.locator(name), timeout=timeout)


def screen_from_spec(name: str, spec: dict[str, dict[str, Any]]) -> ScreenObject:
    elements: dict[str, Locator] = {}
    for key, loc in spec.items():
        elements[key] = locator_from_spec(loc)
    return ScreenObject(name, elements)


def locator_from_spec(spec: dict[str, Any]) -> Locator:
    if "text" in spec:
        return Locator.text(spec["text"])
    if "xpath" in spec:
        return Locator.xpath(spec["xpath"])
    if "resource_id" in spec:
        return Locator.resource_id(spec["resource_id"])
    if "content_desc" in spec:
        return Locator.content_desc(spec["content_desc"])
    if "automation_id" in spec:
        return Locator.automation_id(spec["automation_id"])
    if "title" in spec:
        return Locator.title(spec["title"])
    if "name" in spec:
        return Locator.name(spec["name"])
    if "control_type" in spec:
        return Locator.control_type(spec["control_type"])
    if "class_name" in spec:
        return Locator.class_name(spec["class_name"])
    if "coordinates" in spec:
        x, y = spec["coordinates"]
        return Locator.coordinates(int(x), int(y))
    raise ValueError(f"unsupported locator spec: {spec}")
