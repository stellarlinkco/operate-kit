from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from operatekit.core.shared.errors import DriverUnavailableError, LocatorError, ObservationTimeoutError
from operatekit.core.target.target import TargetSpec
from operatekit.core.ui.locator import Locator, LocatorKind


class Uiautomator2SurfaceDriver:
    def __init__(self, *, serial: str | None = None, package: str | None = None):
        self.serial = serial
        self.package = package
        self._device: Any | None = None

    def _d(self) -> Any:
        if self._device is not None:
            return self._device
        try:
            import uiautomator2 as u2  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise DriverUnavailableError("uiautomator2 is required: pip install operatekit[android]") from exc
        self._device = u2.connect(self.serial)
        return self._device

    def launch(self, target: TargetSpec | None = None, *, stop: bool = False) -> None:
        package = (target.package if target else None) or self.package
        if not package:
            raise ValueError("Android package is required to launch target")
        self._d().app_start(package, stop=stop)

    def close(self) -> None:
        if self.package:
            self._d().app_stop(self.package)

    def _xpath(self, locator: Locator) -> Any:
        return self._d().xpath(locator.to_android_xpath())

    def click(self, locator: Locator, *, timeout: float = 10) -> None:
        if locator.kind == LocatorKind.COORDINATES:
            x, y = locator.value
            self._d().click(x, y)
            return
        node = self._xpath(locator)
        if not node.wait(timeout=timeout):
            raise ObservationTimeoutError(f"locator not visible: {locator}")
        node.click()

    def type_text(self, text: str, *, locator: Locator | None = None, clear: bool = False, timeout: float = 10) -> None:
        if locator is not None:
            self.click(locator, timeout=timeout)
        self._d().send_keys(text, clear=clear)

    def press_key(self, key: str) -> None:
        self._d().press(key)

    def exists(self, locator: Locator, *, timeout: float = 0) -> bool:
        if locator.kind == LocatorKind.COORDINATES:
            return True
        try:
            return bool(self._xpath(locator).wait(timeout=timeout))
        except LocatorError:
            return False

    def wait_visible(self, locator: Locator, *, timeout: float = 10) -> None:
        if not self.exists(locator, timeout=timeout):
            raise ObservationTimeoutError(f"locator not visible: {locator}")

    def scroll(self, direction: str = "down", *, amount: float = 0.8) -> None:
        d = self._d()
        if hasattr(d, "swipe_ext"):
            d.swipe_ext(direction, scale=amount)
            return
        width, height = d.window_size()
        if direction in {"down", "up"}:
            start_y = int(height * (0.8 if direction == "down" else 0.2))
            end_y = int(height * (0.2 if direction == "down" else 0.8))
            d.swipe(width // 2, start_y, width // 2, end_y)
        else:
            start_x = int(width * (0.8 if direction == "right" else 0.2))
            end_x = int(width * (0.2 if direction == "right" else 0.8))
            d.swipe(start_x, height // 2, end_x, height // 2)

    def get_tree(self) -> str:
        return str(self._d().dump_hierarchy())

    def screenshot(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._d().screenshot(str(p))
        return p
