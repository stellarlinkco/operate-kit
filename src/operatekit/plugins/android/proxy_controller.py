from __future__ import annotations

from dataclasses import dataclass

from operatekit.plugins.android.adbutils_host import AdbutilsHostDriver


@dataclass
class AndroidProxyController:
    host: AdbutilsHostDriver
    port: int = 8080
    route: str = "adb_reverse"  # adb_reverse | emulator_host | lan_host
    lan_host: str | None = None

    def enable(self) -> None:
        if self.route == "adb_reverse":
            self.host.reverse(f"tcp:{self.port}", f"tcp:{self.port}")
            self.host.set_http_proxy("127.0.0.1", self.port)
        elif self.route == "emulator_host":
            self.host.set_http_proxy("10.0.2.2", self.port)
        elif self.route == "lan_host":
            if not self.lan_host:
                raise ValueError("lan_host is required for route='lan_host'")
            self.host.set_http_proxy(self.lan_host, self.port)
        else:
            raise ValueError(f"unsupported Android proxy route: {self.route}")

    def disable(self) -> None:
        self.host.clear_http_proxy()
        if self.route == "adb_reverse":
            self.host.reverse_remove(f"tcp:{self.port}")
