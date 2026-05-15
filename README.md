# OperateKit Automation SDK

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

OperateKit is an RPA-first, cross-surface automation runtime SDK. Currently supports **Android** and **Windows** platforms. The architecture is agent-ready, but the agent layer stays above the deterministic RPA runtime.

> The old `mobile-agent-sdk` name over-constrained the project — it sounded mobile-only and agent-first. OperateKit fits Android apps, Windows desktop applications, network observations, workflow retry, traces, and future LLM/agent decisions under the same execution model.

## Install

```bash
pip install -e .[android]          # Android (uiautomator2 + adbutils)
pip install -e .[windows]          # Windows (pywinauto)
pip install -e .[capture]          # Network capture (mitmproxy)
pip install -e .[android,windows,capture]  # All
```

## Quick Start

### Android

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_android(
    package="com.example.app",
    serial=None,
    artifacts_dir="./artifacts",
)

sdk.run_steps("search", [
    Actions.launch(),
    Actions.tap(Locator.text("Search")),
    Actions.type_text("keyword", clear=True),
    Actions.press_key("enter"),
])
```

### Windows

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_windows(
    executable=r"C:\Windows\System32\notepad.exe",
    backend="uia",
    artifacts_dir="./artifacts",
)

sdk.run_steps("notepad", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit"),
    Actions.press_key("ctrl+s"),
])
```

### FlowSpec (Declarative)

```python
flow = {
    "name": "submit_with_retry",
    "commands": [
        {"launch": {}},
        {"retry": {
            "name": "submit_and_wait",
            "maxRetries": 3,
            "commands": [
                {"tap": {"text": "Submit"}},
                {"waitPayload": {
                    "pattern": "contains:/api/result",
                    "timeout": 30,
                    "storeKey": "result_payload",
                }},
            ],
        }},
    ],
}

sdk.run_flow_spec(flow, raise_on_failure=False)
```

## Examples

| Example | Description |
|---------|-------------|
| [android_flow.py](examples/android_flow.py) | Android: launch, tap, type, scroll, retry block, deeplink |
| [windows_flow.py](examples/windows_flow.py) | Windows: notepad automation, locator types |
| [cross_surface_flow_spec.py](examples/cross_surface_flow_spec.py) | FlowSpec: all declarative commands |
| [runtime_hooks.py](examples/runtime_hooks.py) | Runtime Hooks: permission, captcha, network error, custom hook, InterferenceResult |
| [screen_object.py](examples/screen_object.py) | ScreenObject: page object pattern |
| [trace_and_observation.py](examples/trace_and_observation.py) | Trace & mitmproxy network capture |
| [agent_tool_registry.py](examples/agent_tool_registry.py) | Agent ToolRegistry: risk policies, approval |

## Documentation

| Document | Description |
|----------|-------------|
| **[Usage Guide (English)](docs/usage-guide.md)** | Full API reference |
| **[使用指南 (中文)](docs/usage-guide-zh.md)** | 全量 API 文档 |
| [Architecture](docs/architecture.md) | Layering design and module responsibilities |
| [Runtime Hooks Spec](docs/feature-spec/runtime-hooks-feature-spec.md) | Interference handling feature spec |

## Architecture

```
solutions/*
  -> operatekit.rpa        # Actions, FlowSpec, ScreenObject, Generic Hooks
  -> operatekit.runtime    # SDK, Runner, Stabilizer, Hooks, Context, Trace
  -> operatekit.core       # Step, StepResult, Locator, Observation, ValueObjects

plugins/android|windows|capture
  -> operatekit.ports      # SurfaceDriver, HostDriver, Notifier, RunLedger
  -> operatekit.core
```

Core and runtime never import platform libraries (`adbutils`, `uiautomator2`, `pywinauto`, `mitmproxy`).

## License

MIT
