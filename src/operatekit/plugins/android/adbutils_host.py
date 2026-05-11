from __future__ import annotations

import shlex
from typing import Any

from operatekit.core.shared.errors import DriverUnavailableError


class AdbutilsHostDriver:
    def __init__(self, *, serial: str | None = None, adb_host: str = "127.0.0.1", adb_port: int = 5037):
        self.serial = serial
        self.adb_host = adb_host
        self.adb_port = adb_port
        self._device: Any | None = None

    def _get_device(self) -> Any:
        if self._device is not None:
            return self._device
        try:
            import adbutils  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise DriverUnavailableError("adbutils is required: pip install operatekit[android]") from exc
        client = adbutils.AdbClient(host=self.adb_host, port=self.adb_port)
        self._device = client.device(serial=self.serial) if self.serial else client.device()
        return self._device

    def shell(self, command: str, *, timeout: float | None = None) -> str:
        device = self._get_device()
        return str(device.shell(command, timeout=timeout))

    def open_url(self, url: str) -> None:
        quoted = shlex.quote(url)
        self.shell(f"am start -a android.intent.action.VIEW -d {quoted}")

    def push(self, local: str, remote: str) -> None:
        self._get_device().sync.push(local, remote)

    def pull(self, remote: str, local: str) -> None:
        self._get_device().sync.pull(remote, local)

    def install(self, apk: str, *, uninstall: bool = False) -> None:
        self._get_device().install(apk, uninstall=uninstall)

    def reverse(self, remote: str, local: str) -> None:
        self._get_device().reverse(remote, local)

    def reverse_remove(self, remote: str) -> None:
        self._get_device().reverse_remove(remote)

    def set_http_proxy(self, host: str, port: int) -> None:
        self.shell(f"settings put global http_proxy {host}:{port}")

    def clear_http_proxy(self) -> None:
        self.shell("settings put global http_proxy :0")
        try:
            self.shell("settings delete global http_proxy", timeout=5)
        except Exception:  # noqa: BLE001 - Android versions differ; :0 cleanup above is enough
            pass
