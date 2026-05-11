from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

try:
    from mitmproxy import ctx, http  # type: ignore
except Exception:  # pragma: no cover - imported by mitmdump at runtime
    ctx = None
    http = None


def load(loader: Any) -> None:  # pragma: no cover - mitmproxy runtime hook
    loader.add_option("operatekit_repo", str, "", "OperateKit observation JSONL path")
    loader.add_option("operatekit_patterns", str, "", "Comma separated URL contains patterns")


class CaptureAddon:
    def response(self, flow: Any) -> None:  # pragma: no cover - mitmproxy runtime hook
        repo = getattr(ctx.options, "operatekit_repo", "") if ctx else ""
        if not repo:
            return
        patterns_raw = getattr(ctx.options, "operatekit_patterns", "") if ctx else ""
        patterns = [p for p in patterns_raw.split(",") if p]
        url = flow.request.pretty_url
        if patterns and not any(_pattern_matches(p, url) for p in patterns):
            return
        body = flow.response.raw_content or flow.response.content or b""
        record = {
            "kind": "network",
            "source": "mitmproxy",
            "content": base64.b64encode(body).decode("ascii"),
            "content_encoding": "base64",
            "metadata": {
                "url": url,
                "method": flow.request.method,
                "status_code": flow.response.status_code,
                "headers": dict(flow.response.headers.items()),
                "request_headers": dict(flow.request.headers.items()),
                "host": flow.request.host,
                "path": flow.request.path,
            },
            "captured_at": None,
            "run_id": None,
        }
        path = Path(repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _pattern_matches(pattern: str, url: str) -> bool:
    if pattern.startswith("contains:"):
        return pattern[len("contains:") :] in url
    return pattern in url


addons = [CaptureAddon()]
