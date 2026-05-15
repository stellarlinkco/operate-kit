# OperateKit SDK Usage Guide

[中文版](usage-guide-zh.md)

OperateKit is an RPA-first, cross-surface automation runtime SDK. Currently supports Android and Windows. The architecture reserves an extension layer for Agent (LLM decisioning) while keeping the core execution layer deterministic.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Android](#android)
  - [Windows](#windows)
  - [Custom Drivers](#custom-drivers)
- [Locator](#locator)
- [Actions API](#actions-api)
- [FlowSpec (Declarative Workflows)](#flowspec-declarative-workflows)
- [ScreenObject (Page Object)](#screenobject-page-object)
- [Runtime Hooks (Interference Handling)](#runtime-hooks-interference-handling)
  - [Registering Hooks](#registering-hooks)
  - [Built-in Generic Hooks](#built-in-generic-hooks)
  - [Custom App-specific Hooks](#custom-app-specific-hooks)
  - [InterferenceResult (Typed Result)](#interferenceresult-typed-result)
  - [StabilizationConfig (Budget)](#stabilizationconfig-budget)
- [Observation & Network Capture](#observation--network-capture)
- [Trace (Execution Recording)](#trace-execution-recording)
- [Agent ToolRegistry](#agent-toolregistry)
- [Architecture Overview](#architecture-overview)

---

## Installation

```bash
# Android automation (requires uiautomator2 + adbutils)
pip install -e .[android]

# Windows automation (requires pywinauto)
pip install -e .[windows]

# Network capture (requires mitmproxy)
pip install -e .[capture]

# All extras
pip install -e .[android,windows,capture]
```

---

## Quick Start

### Android

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_android(
    package="com.example.app",
    serial=None,              # auto-detect; specify serial for multi-device
    artifacts_dir="./artifacts",
)

run = sdk.run_steps("search_flow", [
    Actions.launch(),
    Actions.tap(Locator.text("Search")),
    Actions.type_text("keyword", clear=True),
    Actions.press_key("enter"),
    Actions.scroll("down"),
])

print(run.status)  # WorkflowStatus.PASSED
```

### Windows

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_windows(
    executable=r"C:\Windows\System32\notepad.exe",
    backend="uia",            # "uia" or "win32"
    artifacts_dir="./artifacts",
)

run = sdk.run_steps("notepad_test", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit"),
    Actions.press_key("ctrl+s"),
])
```

### Custom Drivers

```python
from operatekit import AutomationSDK, TargetSpec

sdk = AutomationSDK.create_with_drivers(
    target=TargetSpec.android("com.example.app"),
    surface=my_surface_driver,
    host=my_host_driver,
    artifacts_dir="./artifacts",
)
```

---

## Locator

`Locator` is a platform-agnostic UI element descriptor. Automatically translates to Android XPath or pywinauto `child_window` kwargs depending on the active surface.

```python
from operatekit import Locator

# Cross-platform
Locator.text("Submit")
Locator.xpath('//*[@resource-id="com.example:id/btn"]')

# Android-specific
Locator.resource_id("com.example:id/search_input")
Locator.content_desc("Back button")

# Windows-specific
Locator.automation_id("submitButton")
Locator.title("File")
Locator.name("Save")
Locator.control_type("Button")
Locator.class_name("Edit")

# Coordinates (use sparingly)
Locator.coordinates(500, 300)
```

---

## Actions API

`Actions` is a platform-agnostic RPA step factory. Each method returns a `Step` object to be executed by `sdk.run_steps()`.

### Business Steps (trigger Stabilization)

| Method | Description |
|--------|-------------|
| `Actions.launch(stop=False)` | Launch the target application |
| `Actions.close()` | Close the target application |
| `Actions.tap(locator, timeout=10)` | Tap an element |
| `Actions.type_text(text, locator=None, clear=False, timeout=10)` | Type text |
| `Actions.press_key(key)` | Press a key (e.g. `"enter"`, `"back"`, `"ctrl+s"`) |
| `Actions.scroll(direction="down", amount=0.8)` | Scroll |
| `Actions.deeplink(url)` | Open a deeplink |

### Internal Steps (no Stabilization)

| Method | Description |
|--------|-------------|
| `Actions.wait_visible(locator, timeout=10)` | Wait for an element to become visible |
| `Actions.sleep(seconds)` | Wait a fixed duration |
| `Actions.shell(command, timeout=None, store_key=None)` | Execute a shell command |
| `Actions.capture_cursor(key)` | Capture an observation cursor |
| `Actions.wait_observation(kind=None, pattern=..., cursor_key=None, timeout=30, store_key=None)` | Wait for a matching observation |
| `Actions.wait_payload(pattern, cursor_key=None, timeout=30, store_key=None)` | Wait for a network observation (shortcut for `wait_observation` with `kind=network`) |

### Retry Block

```python
Actions.retry_block(
    "submit_and_wait",
    [
        Actions.tap(Locator.text("Submit")),
        Actions.wait_payload("contains:/api/result", timeout=30, store_key="result"),
    ],
    max_retries=3,
    delay_seconds=2.0,
    backoff_multiplier=1.5,
)
```

Child Business Steps inside a retry block still trigger Stabilization. If a child step produces a terminal hook outcome (e.g. `manual_required`), the retry block propagates it immediately without retrying.

### Custom Steps

```python
# Default: Internal Step (no Stabilization)
Actions.call("custom_op", lambda ctx: do_something(ctx))

# Explicitly opt in to Stabilization
Actions.call("custom_business_op", lambda ctx: do_something(ctx), hookable=True)
```

### Retry Policy

```python
from operatekit import RetryPolicy

step = Actions.tap(Locator.text("Submit"))
step.retry_policy = RetryPolicy(
    max_attempts=3,
    delay_seconds=1.0,
    backoff_multiplier=2.0,
)
```

---

## FlowSpec (Declarative Workflows)

FlowSpec describes automation workflows using dictionaries / JSON, suited for config-driven scenarios.

```python
flow = {
    "name": "submit_and_wait",
    "commands": [
        {"launch": {}},
        {"tap": {"text": "Submit", "timeout": 10}},
        {"inputText": {"text": "search term", "clear": True}},
        {"pressKey": "enter"},
        {"scroll": "down"},
        {"waitVisible": {"text": "Result", "timeout": 15}},
        {"sleep": 2},
        {"shell": "echo hello"},
        {"deeplink": "myapp://page/detail"},
        {"captureCursor": {"key": "before_submit"}},
        {"waitPayload": {
            "pattern": "contains:/api/result",
            "cursorKey": "before_submit",
            "timeout": 30,
            "storeKey": "result_payload",
        }},
        {"retry": {
            "name": "retry_submit",
            "maxRetries": 3,
            "delay": 2,
            "commands": [
                {"tap": {"text": "Submit"}},
                {"waitPayload": {"pattern": "contains:/api/submit", "timeout": 10}},
            ],
        }},
        {"checkBlockers": {}},
    ],
}

run = sdk.run_flow_spec(flow, raise_on_failure=False)
```

---

## ScreenObject (Page Object)

ScreenObject centralizes page element definitions, keeping Locators out of flow code.

```python
login_screen = sdk.screen("login", {
    "username": {"resource_id": "com.example:id/username"},
    "password": {"resource_id": "com.example:id/password"},
    "submit":   {"text": "Login"},
})

run = sdk.run_steps("login", [
    Actions.launch(),
    login_screen.tap("username"),
    login_screen.type_text("username", "user@example.com", clear=True),
    login_screen.type_text("password", "secret", clear=True),
    login_screen.tap("submit"),
    login_screen.assert_visible("submit", timeout=5),
])
```

---

## Runtime Hooks (Interference Handling)

Runtime Hooks automatically handle cross-cutting interference during automation — update dialogs, ads, permission prompts, captchas, network errors, etc.

Every Business Step is wrapped in **Stabilization** before and after execution: observe the current UI state -> run hooks by priority -> if handled, re-observe -> repeat until stable or a terminal outcome is reached.

### Registering Hooks

```python
from operatekit import (
    PermissionHook, PermissionPolicy,
    NetworkErrorHook, ErrorPolicy, ErrorRule,
    CaptchaHook, UpdateDialogHook, AdDialogHook,
    HookOutcome, Locator,
)

sdk = AutomationSDK.create_android(package="com.example.app")

# Permission prompts
sdk.register_hook(PermissionHook(PermissionPolicy(
    prompt_patterns=("permission",),
    allow={"camera": Locator.text("Allow"), "location": Locator.text("Allow Always")},
    deny={"contacts": Locator.text("Deny")},
)))

# Network / server errors
sdk.register_hook(NetworkErrorHook(ErrorPolicy(
    rules=[
        ErrorRule("network unavailable", HookOutcome.RETRY_STEP, reason="retry after recovery"),
        ErrorRule("server maintenance", HookOutcome.MANUAL_REQUIRED, reason="needs manual check"),
    ],
    error_patterns=("network", "server"),
)))

# Captcha -> manual intervention
sdk.register_hook(CaptchaHook(patterns=("captcha", "human verification")))

# Update dialog -> auto-dismiss
sdk.register_hook(UpdateDialogHook(
    patterns=("new version", "update now"),
    dismiss=Locator.text("Later"),
))

# Ad dialog -> auto-dismiss
sdk.register_hook(AdDialogHook(
    patterns=("advertisement", "promotion"),
    dismiss=Locator.text("Close"),
))
```

### Built-in Generic Hooks

| Hook | Default Priority | Behavior |
|------|-----------------|----------|
| `CaptchaHook` | 100 | Detects captcha -> `manual_required` |
| `PermissionHook` | 90 | Known permission allow/deny -> `handled`; unknown -> `manual_required` |
| `NetworkErrorHook` | 80 | Per ErrorPolicy rules -> `retry_step` / `fail_workflow` / `manual_required` |
| `UpdateDialogHook` | 70 | Matches update dialog -> clicks dismiss -> `handled` |
| `AdDialogHook` | 70 | Matches ad dialog -> clicks dismiss -> `handled` |
| `LegacyBlockerHook` | 0 | Compatibility with old BlockerRule -> `handled` |

Higher priority values execute first. Only the first non-noop hook takes effect per Stabilization round.

### Custom App-specific Hooks

```python
from operatekit import HookResult, HookOutcome, RuntimeObservation, Locator

class SavePromptHook:
    name = "save_prompt"
    priority = 60

    def handle(self, ctx, observation: RuntimeObservation) -> HookResult:
        if "save changes" not in observation.ui_tree.lower():
            return HookResult(HookOutcome.NOOP)
        ctx.click(Locator.text("Don't Save"))
        return HookResult(HookOutcome.HANDLED, reason="save prompt dismissed")

sdk.register_hook(SavePromptHook())
```

**Hook Outcome semantics:**

| Outcome | Meaning |
|---------|---------|
| `NOOP` | This hook does not handle the current state |
| `HANDLED` | Handled; Stabilization re-observes |
| `RETRY_STEP` | Consumes the current Business Step's retry policy |
| `MANUAL_REQUIRED` | Workflow paused — human intervention needed |
| `FAIL_WORKFLOW` | Workflow failed |

**Hooks may only use Dismissal Primitives:**
- `ctx.click(locator, timeout=0.5)` — click
- `ctx.press_key(key)` — press key
- `ctx.wait(seconds)` — brief wait
- `ctx.notify(event, payload)` — emit a notification event

### InterferenceResult (Typed Result)

When a hook produces a terminal outcome, `StepResult.interference` provides typed access:

```python
from operatekit import WorkflowStatus

run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

if run.status == WorkflowStatus.MANUAL_REQUIRED:
    result = run.step_results[-1]

    # Typed access (recommended)
    assert result.interference.is_manual_required
    assert result.interference.is_terminal
    print(result.interference.outcome)           # HookOutcome.MANUAL_REQUIRED
    print(result.interference.reason)            # "unknown permission prompt"
    print(result.interference.hook_name)         # "permission"
    print(result.interference.last_observation)  # RuntimeObservation(...)

    # Backward-compatible dict access (still available)
    print(run.metadata["runtime_hook"]["outcome"])  # "manual_required"
```

`interference` is `None` for steps that pass normally.

### StabilizationConfig (Budget)

```python
from operatekit import StabilizationConfig, TargetSpec

sdk = AutomationSDK.create_with_drivers(
    target=TargetSpec.android("com.example.app"),
    surface=surface,
    artifacts_dir="./artifacts",
    stabilization=StabilizationConfig(
        max_rounds=5,          # max observation rounds per phase
        timeout_seconds=5.0,   # max elapsed time per phase
    ),
)
```

Exceeding the budget produces a `fail_workflow` outcome.

---

## Observation & Network Capture

OperateKit models network capture as Observations. Business workflows use `wait_observation` / `wait_payload` to wait for specific network responses.

### Starting mitmproxy Capture

```python
# Basic capture
proxy = sdk.mitm_proxy(port=8080, endpoint_patterns=["/api/submit", "/api/result"])

# Android one-step capture (ADB reverse proxy + mitmproxy)
session = sdk.android_mitm_session(
    port=8080,
    route="adb_reverse",      # "adb_reverse" or "wifi"
    endpoint_patterns=["/api/*"],
)
```

### Waiting for Network Observations

```python
run = sdk.run_steps("capture_flow", [
    Actions.launch(),
    Actions.capture_cursor("before"),
    Actions.tap(Locator.text("Submit")),
    Actions.wait_payload(
        "contains:/api/result",
        cursor_key="before",
        timeout=30,
        store_key="api_result",
    ),
])

# Get observation snapshot
snapshot = sdk.snapshot_observation("api_result", fields=["data", "code"])
print(snapshot.hash)
```

### Observation Kinds

```python
from operatekit import ObservationKind

ObservationKind.NETWORK     # Network request/response
ObservationKind.UI_TREE     # UI hierarchy
ObservationKind.SCREENSHOT  # Screenshot
ObservationKind.HOST        # Host operations
ObservationKind.FILE        # File
ObservationKind.LOG         # Log
ObservationKind.DECISION    # Decision record
```

---

## Trace (Execution Recording)

Trace records execution details for each step, useful for debugging and auditing.

```python
from operatekit import TraceConfig

recorder = sdk.enable_trace(TraceConfig(
    capture_ui_tree=False,       # save UI XML before each step
    capture_screenshot=False,    # screenshot before each step
    screenshot_on_error=True,    # screenshot on step failure
))

sdk.run_steps("traced_flow", [
    Actions.launch(),
    Actions.tap(Locator.text("Submit")),
])

# Trace data written to artifacts/trace/trace.jsonl
```

---

## Agent ToolRegistry

ToolRegistry provides a thin integration layer for future LLM/Agent use. Agent code invokes registered tools instead of touching underlying drivers directly.

```python
from operatekit import AutomationTool, ToolRegistry, RiskPolicy

registry = ToolRegistry()

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

# High-risk tools require approval
registry.register(AutomationTool(
    name="delete_account",
    description="Delete the user account",
    func=lambda: sdk.run_steps("delete", [
        Actions.tap(Locator.text("Delete Account")),
        Actions.tap(Locator.text("Confirm")),
    ]),
    risk_policy=RiskPolicy.high("irreversible operation", requires_approval=True),
))

# Invoke
tool = registry.get("search")
tool.invoke("OperateKit")

# High-risk tool raises PermissionError without approval
tool = registry.get("delete_account")
tool.invoke(approved=True)  # explicit approval required
```

---

## Architecture Overview

```
solutions/*
  -> operatekit.rpa          # Actions, FlowSpec, ScreenObject, Generic Hooks
  -> operatekit.runtime      # SDK, Runner, Stabilizer, Hooks, Context, Trace
  -> operatekit.core         # Step, StepResult, Locator, Observation, ValueObjects

operatekit.plugins.android   # uiautomator2 + adbutils
operatekit.plugins.windows   # pywinauto
operatekit.plugins.capture   # mitmproxy
  -> operatekit.ports        # SurfaceDriver, HostDriver, Notifier, RunLedger
  -> operatekit.core
```

**Key constraints:**
- `core` and `runtime` never import `adbutils`, `uiautomator2`, `pywinauto`, or `mitmproxy`
- Runtime Hooks operate through Dismissal Primitives only — no direct platform driver calls
- Hook Registry is configured at the SDK/Runner level, not inside FlowSpec
- Agent layer sits above the deterministic RPA runtime — never bypasses `Actions` / `WorkflowRunner`
