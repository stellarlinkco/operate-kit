# Agent-ready boundary

OperateKit is not agent-first. The runtime stays deterministic and auditable.

Future LLM/agent modules must use `ToolRegistry` and registered `AutomationTool` objects. They should not call raw pywinauto, uiautomator2, adb shell, or mitmproxy APIs directly.

```text
Agent planner
  -> ToolRegistry
  -> Actions / FlowSpec / WorkflowRunner
  -> SurfaceDriver / HostDriver / ObservationRepository
```

High-impact tools can carry a `RiskPolicy`:

```python
from operatekit import AutomationTool, RiskPolicy

tool = AutomationTool(
    name="submit_bid",
    description="Submit a bid in the target app",
    func=submit_bid_flow,
    risk_policy=RiskPolicy.high("submits external price", max_amount=280000),
)
```

This lets the future agent layer request approval without weakening the current RPA workflow model.
