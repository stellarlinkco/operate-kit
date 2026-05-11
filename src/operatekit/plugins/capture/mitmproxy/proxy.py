from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from operatekit.core.shared.errors import DriverUnavailableError


@dataclass
class MitmproxyCaptureProxy:
    repo_path: Path
    port: int = 8080
    host: str = "127.0.0.1"
    endpoint_patterns: list[str] = field(default_factory=list)
    mitmdump_bin: str = "mitmdump"
    process: subprocess.Popen | None = None
    stderr_path: Path | None = None

    def start(self) -> "MitmproxyCaptureProxy":
        if self.process and self.process.poll() is None:
            return self
        if shutil.which(self.mitmdump_bin) is None:
            raise DriverUnavailableError("mitmdump not found. Install mitmproxy or use pip install operatekit[capture].")
        addon = Path(__file__).with_name("addon.py")
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        self.stderr_path = self.repo_path.parent / "mitmproxy.stderr.log"
        stderr = self.stderr_path.open("a", encoding="utf-8")
        cmd = [
            self.mitmdump_bin,
            "--listen-host", self.host,
            "--listen-port", str(self.port),
            "-s", str(addon),
            "--set", f"operatekit_repo={self.repo_path}",
            "--set", f"operatekit_patterns={','.join(self.endpoint_patterns)}",
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=stderr)
        self.wait_ready(timeout=10)
        return self

    def wait_ready(self, *, timeout: float = 10) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"mitmdump exited with code {self.process.returncode}; see {self.stderr_path}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                try:
                    s.connect((self.host, self.port))
                    return
                except OSError:
                    time.sleep(0.1)
        raise TimeoutError(f"mitmproxy did not listen on {self.host}:{self.port}")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def __enter__(self) -> "MitmproxyCaptureProxy":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.stop()
