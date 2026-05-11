from __future__ import annotations

import subprocess


class LocalWindowsHostDriver:
    """Host operations for a local Windows PC.

    The class is safe to import on non-Windows hosts; methods that execute
    Windows-specific commands should be used only on Windows.
    """

    def shell(self, command: str, *, timeout: float | None = None) -> str:
        completed = subprocess.run(command, shell=True, check=False, capture_output=True, text=True, timeout=timeout)
        output = (completed.stdout or "") + (completed.stderr or "")
        if completed.returncode != 0:
            raise RuntimeError(f"command failed with code {completed.returncode}: {output}")
        return output

    def open_url(self, url: str) -> None:
        self.shell(f'start "" "{url}"')
