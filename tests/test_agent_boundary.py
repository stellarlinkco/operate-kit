import pytest

from operatekit import AutomationTool, RiskPolicy, ToolRegistry


def test_tool_registry_blocks_unapproved_high_risk_tool():
    registry = ToolRegistry()
    registry.register(AutomationTool("submit", "submit bid", lambda: "ok", RiskPolicy.high("money action")))

    with pytest.raises(PermissionError):
        registry.get("submit").invoke()

    assert registry.get("submit").invoke(approved=True) == "ok"
