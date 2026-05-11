from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from operatekit.core.shared.errors import LocatorError


class LocatorKind(str, Enum):
    TEXT = "text"
    XPATH = "xpath"
    RESOURCE_ID = "resource_id"
    CONTENT_DESC = "content_desc"
    AUTOMATION_ID = "automation_id"
    TITLE = "title"
    NAME = "name"
    CONTROL_TYPE = "control_type"
    CLASS_NAME = "class_name"
    COORDINATES = "coordinates"
    CSS = "css"
    IMAGE = "image"
    OCR_TEXT = "ocr_text"


@dataclass(frozen=True)
class Locator:
    kind: LocatorKind
    value: Any
    filters: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def text(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.TEXT, value, filters)

    @staticmethod
    def xpath(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.XPATH, value, filters)

    @staticmethod
    def resource_id(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.RESOURCE_ID, value, filters)

    @staticmethod
    def content_desc(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.CONTENT_DESC, value, filters)

    @staticmethod
    def automation_id(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.AUTOMATION_ID, value, filters)

    @staticmethod
    def title(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.TITLE, value, filters)

    @staticmethod
    def name(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.NAME, value, filters)

    @staticmethod
    def control_type(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.CONTROL_TYPE, value, filters)

    @staticmethod
    def class_name(value: str, **filters: Any) -> "Locator":
        return Locator(LocatorKind.CLASS_NAME, value, filters)

    @staticmethod
    def coordinates(x: int, y: int, **filters: Any) -> "Locator":
        return Locator(LocatorKind.COORDINATES, (x, y), filters)

    def to_android_xpath(self) -> str:
        if self.kind == LocatorKind.XPATH:
            return str(self.value)
        if self.kind == LocatorKind.TEXT:
            return f'//*[@text="{_escape_xpath(str(self.value))}"]'
        if self.kind == LocatorKind.RESOURCE_ID:
            return f'//*[@resource-id="{_escape_xpath(str(self.value))}"]'
        if self.kind == LocatorKind.CONTENT_DESC:
            return f'//*[@content-desc="{_escape_xpath(str(self.value))}"]'
        raise LocatorError(f"locator {self.kind.value!r} cannot be translated to Android XPath")

    def to_windows_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(self.filters)
        if self.kind == LocatorKind.AUTOMATION_ID:
            kwargs["auto_id"] = self.value
        elif self.kind in {LocatorKind.TITLE, LocatorKind.TEXT, LocatorKind.NAME}:
            kwargs["title"] = self.value
        elif self.kind == LocatorKind.CONTROL_TYPE:
            kwargs["control_type"] = self.value
        elif self.kind == LocatorKind.CLASS_NAME:
            kwargs["class_name"] = self.value
        elif self.kind == LocatorKind.COORDINATES:
            return {"coordinates": self.value}
        else:
            raise LocatorError(f"locator {self.kind.value!r} cannot be translated to pywinauto child_window kwargs")
        return kwargs

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "value": self.value, "filters": dict(self.filters)}


def _escape_xpath(value: str) -> str:
    return value.replace('"', '&quot;')
