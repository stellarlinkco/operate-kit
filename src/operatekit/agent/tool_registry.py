from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from operatekit.core.policy.risk import RiskPolicy


@dataclass(frozen=True)
class AutomationTool:
    name: str
    description: str
    func: Callable[..., Any]
    risk_policy: RiskPolicy = field(default_factory=RiskPolicy.low)

    def invoke(self, *args: Any, approved: bool = False, **kwargs: Any) -> Any:
        if self.risk_policy.requires_approval and not approved:
            raise PermissionError(f"tool {self.name!r} requires approval: {self.risk_policy.reason}")
        return self.func(*args, **kwargs)


class ToolRegistry:
    """Registry for future LLM/agent integration.

    Agent code should call registered tools instead of bypassing the RPA runtime.
    """

    def __init__(self):
        self._tools: dict[str, AutomationTool] = {}

    def register(self, tool: AutomationTool) -> None:
        if tool.name in self._tools:
            raise KeyError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AutomationTool:
        return self._tools[name]

    def list(self) -> list[AutomationTool]:
        return list(self._tools.values())
