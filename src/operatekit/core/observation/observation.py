from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any
import base64
import json

from operatekit.core.shared.ids import ObservationId
from operatekit.core.shared.time import utc_now_iso


class ObservationKind(str, Enum):
    NETWORK = "network"
    UI_TREE = "ui_tree"
    SCREENSHOT = "screenshot"
    HOST = "host"
    FILE = "file"
    LOG = "log"
    DECISION = "decision"


@dataclass(frozen=True)
class ObservationCursor:
    position: int


@dataclass
class Observation:
    kind: ObservationKind
    source: str
    content: bytes | str | dict[str, Any] | list[Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=utc_now_iso)
    observation_id: ObservationId = field(default_factory=ObservationId.new)
    run_id: str | None = None

    @staticmethod
    def network(
        *,
        url: str,
        method: str = "GET",
        status_code: int | None = None,
        headers: dict[str, Any] | None = None,
        body: bytes | str | dict[str, Any] | list[Any] | None = None,
        source: str = "mitmproxy",
        **metadata: Any,
    ) -> "Observation":
        return Observation(
            kind=ObservationKind.NETWORK,
            source=source,
            content=body,
            metadata={
                "url": url,
                "method": method,
                "status_code": status_code,
                "headers": headers or {},
                **metadata,
            },
        )

    @property
    def hash(self) -> str:
        payload = json.dumps(self.to_dict(include_id=False), sort_keys=True, ensure_ascii=False).encode("utf-8")
        return sha256(payload).hexdigest()

    def text(self) -> str:
        if self.content is None:
            return ""
        if isinstance(self.content, bytes):
            return self.content.decode("utf-8", errors="replace")
        if isinstance(self.content, str):
            return self.content
        return json.dumps(self.content, ensure_ascii=False)

    def json(self) -> Any:
        if isinstance(self.content, (dict, list)):
            return self.content
        return json.loads(self.text())

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        content: Any
        encoding: str
        if isinstance(self.content, bytes):
            content = base64.b64encode(self.content).decode("ascii")
            encoding = "base64"
        else:
            content = self.content
            encoding = "plain"
        data = {
            "kind": self.kind.value,
            "source": self.source,
            "content": content,
            "content_encoding": encoding,
            "metadata": self.metadata,
            "captured_at": self.captured_at,
            "run_id": self.run_id,
        }
        if include_id:
            data["observation_id"] = str(self.observation_id)
            data["hash"] = self.hash
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Observation":
        content = data.get("content")
        if data.get("content_encoding") == "base64" and content is not None:
            content = base64.b64decode(content)
        obs = Observation(
            kind=ObservationKind(data["kind"]),
            source=data["source"],
            content=content,
            metadata=dict(data.get("metadata") or {}),
            captured_at=data.get("captured_at") or utc_now_iso(),
            run_id=data.get("run_id"),
        )
        if data.get("observation_id"):
            obs.observation_id = ObservationId(data["observation_id"])
        return obs
