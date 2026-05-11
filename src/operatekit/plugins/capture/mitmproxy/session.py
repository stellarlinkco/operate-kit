from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from operatekit.plugins.android.proxy_controller import AndroidProxyController
from operatekit.plugins.capture.mitmproxy.proxy import MitmproxyCaptureProxy


@dataclass
class MitmCaptureSession:
    proxy: MitmproxyCaptureProxy
    device_proxy: AndroidProxyController | None = None

    def __enter__(self) -> "MitmCaptureSession":
        self.proxy.start()
        if self.device_proxy is not None:
            self.device_proxy.enable()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        if self.device_proxy is not None:
            self.device_proxy.disable()
        self.proxy.stop()
