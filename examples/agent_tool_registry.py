"""Agent ToolRegistry example.

Demonstrates: registering RPA workflows as agent-callable tools with
risk policies, invoking tools, and handling approval for high-risk operations.
"""

from operatekit import (
    Actions,
    AutomationSDK,
    AutomationTool,
    Locator,
    RiskPolicy,
    ToolRegistry,
)

sdk = AutomationSDK.create_android(
    package="com.example.app",
    artifacts_dir="./artifacts/agent",
)

registry = ToolRegistry()

# --- Low-risk tool: no approval needed ---

registry.register(AutomationTool(
    name="search",
    description="Search for a keyword in the app",
    func=lambda keyword: sdk.run_steps("search", [
        Actions.tap(Locator.text("Search")),
        Actions.type_text(keyword, clear=True),
        Actions.press_key("enter"),
    ]),
    risk_policy=RiskPolicy.low(),
))

# --- High-risk tool: requires explicit approval ---

registry.register(AutomationTool(
    name="delete_account",
    description="Permanently delete the user account",
    func=lambda: sdk.run_steps("delete_account", [
        Actions.tap(Locator.text("Settings")),
        Actions.tap(Locator.text("Delete Account")),
        Actions.tap(Locator.text("Confirm")),
    ]),
    risk_policy=RiskPolicy.high("irreversible operation", requires_approval=True),
))

# --- Medium-risk tool with custom limits ---

registry.register(AutomationTool(
    name="batch_send",
    description="Send messages to multiple recipients",
    func=lambda recipients, msg: sdk.run_steps("batch_send", [
        Actions.tap(Locator.text("Compose")),
        Actions.type_text(msg),
        Actions.tap(Locator.text("Send")),
    ]),
    risk_policy=RiskPolicy.high(
        "sends messages to external users",
        requires_approval=True,
        max_recipients=50,
    ),
))

# --- Invoke tools ---

# Low-risk: direct invocation
tool = registry.get("search")
run = tool.invoke("OperateKit")
print(f"Search: {run.status.value}")

# High-risk: must pass approved=True
tool = registry.get("delete_account")
try:
    tool.invoke()  # raises PermissionError
except PermissionError as e:
    print(f"Blocked: {e}")

run = tool.invoke(approved=True)  # explicit approval
print(f"Delete: {run.status.value}")

# --- List all registered tools ---

for t in registry.list():
    print(f"  {t.name}: risk={t.risk_policy.level.value}, approval={t.risk_policy.requires_approval}")
