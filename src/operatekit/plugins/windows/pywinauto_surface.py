from __future__ import annotations

from pathlib import Path
import io
from contextlib import redirect_stdout
from typing import Any

from operatekit.core.shared.errors import DriverUnavailableError, ObservationTimeoutError
from operatekit.core.target.target import TargetSpec
from operatekit.core.ui.locator import Locator, LocatorKind


_KEY_MAP = {
    "enter": "{ENTER}",
    "back": "{BACKSPACE}",
    "backspace": "{BACKSPACE}",
    "tab": "{TAB}",
    "esc": "{ESC}",
    "escape": "{ESC}",
    "ctrl+s": "^s",
    "ctrl+a": "^a",
}


class PywinautoSurfaceDriver:
    """Windows SurfaceDriver implemented with pywinauto.

    It supports both `backend="uia"` and `backend="win32"`. Imports are lazy
    so the SDK can be imported on Linux/macOS and in CI without pywinauto.
    """

    def __init__(
        self,
        *,
        executable: str | None = None,
        title: str | None = None,
        backend: str = "uia",
        launch_args: list[str] | None = None,
        connect: bool = False,
    ):
        self.executable = executable
        self.title = title
        self.backend = backend
        self.launch_args = launch_args or []
        self.connect_existing = connect
        self._app: Any | None = None

    def _imports(self) -> tuple[Any, Any, Any]:
        try:
            from pywinauto import Application, Desktop, keyboard  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise DriverUnavailableError("pywinauto is required: pip install operatekit[windows]") from exc
        return Application, Desktop, keyboard

    def launch(self, target: TargetSpec | None = None, *, stop: bool = False) -> None:  # noqa: ARG002
        Application, _Desktop, _keyboard = self._imports()
        executable = (target.executable if target else None) or self.executable
        title = (target.title if target else None) or self.title
        backend = (target.backend if target and target.backend else None) or self.backend
        args = (target.launch_args if target else None) or self.launch_args

        self.backend = backend
        if executable and not self.connect_existing:
            command = " ".join([f'"{executable}"', *args]).strip()
            self._app = Application(backend=backend).start(command)
        elif executable:
            self._app = Application(backend=backend).connect(path=executable)
        elif title:
            self._app = Application(backend=backend).connect(title=title)
        else:
            raise ValueError("Windows target requires executable or title")

    def close(self) -> None:
        if self._app is not None:
            try:
                self._app.kill()
            except Exception:  # noqa: BLE001
                pass

    def _ensure_app(self) -> Any:
        if self._app is None:
            self.launch()
        return self._app

    def _window(self) -> Any:
        app = self._ensure_app()
        title = self.title
        if title:
            return app.window(title=title)
        return app.top_window()

    def _resolve(self, locator: Locator, *, timeout: float = 10) -> Any:
        if locator.kind == LocatorKind.COORDINATES:
            return None
        window = self._window()
        kwargs = locator.to_windows_kwargs()
        control = window.child_window(**kwargs)
        try:
            control.wait("exists enabled visible ready", timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            raise ObservationTimeoutError(f"locator not ready: {locator}") from exc
        return control

    def click(self, locator: Locator, *, timeout: float = 10) -> None:
        if locator.kind == LocatorKind.COORDINATES:
            _Application, _Desktop, _keyboard = self._imports()
            from pywinauto import mouse  # type: ignore
            x, y = locator.value
            mouse.click(coords=(int(x), int(y)))
            return
        self._resolve(locator, timeout=timeout).click_input()

    def type_text(self, text: str, *, locator: Locator | None = None, clear: bool = False, timeout: float = 10) -> None:
        _Application, _Desktop, keyboard = self._imports()
        if locator is not None:
            control = self._resolve(locator, timeout=timeout)
            control.set_focus()
            if clear:
                control.type_keys("^a{BACKSPACE}", set_foreground=True)
            control.type_keys(text, with_spaces=True, set_foreground=True)
        else:
            if clear:
                keyboard.send_keys("^a{BACKSPACE}")
            keyboard.send_keys(text, with_spaces=True)

    def press_key(self, key: str) -> None:
        _Application, _Desktop, keyboard = self._imports()
        keyboard.send_keys(_KEY_MAP.get(key.lower(), key))

    def exists(self, locator: Locator, *, timeout: float = 0) -> bool:
        if locator.kind == LocatorKind.COORDINATES:
            return True
        try:
            kwargs = locator.to_windows_kwargs()
            return bool(self._window().child_window(**kwargs).exists(timeout=timeout))
        except Exception:  # noqa: BLE001
            return False

    def wait_visible(self, locator: Locator, *, timeout: float = 10) -> None:
        self._resolve(locator, timeout=timeout)

    def scroll(self, direction: str = "down", *, amount: float = 0.8) -> None:  # noqa: ARG002
        _Application, _Desktop, keyboard = self._imports()
        key = "{PGDN}" if direction in {"down", "right"} else "{PGUP}"
        keyboard.send_keys(key)

    def get_tree(self) -> str:
        window = self._window()
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                window.print_control_identifiers()
            return buffer.getvalue()
        except Exception:  # noqa: BLE001
            return repr(window)

    def screenshot(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        image = self._window().capture_as_image()
        image.save(str(p))
        return p
