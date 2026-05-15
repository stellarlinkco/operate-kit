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

## Documentation

| Document | Description |
|----------|-------------|
| **[Usage Guide (English)](docs/usage-guide.md)** | Full API reference — Actions, FlowSpec, ScreenObject, Runtime Hooks, Observation, Trace, Agent ToolRegistry |
| **[使用指南 (中文)](docs/usage-guide-zh.md)** | 全量 API 文档 — Actions、FlowSpec、ScreenObject、Runtime Hooks、观测抓包、Trace、Agent ToolRegistry |
| [Architecture](docs/architecture.md) | Layering design and module responsibilities |
| [Runtime Hooks Spec](docs/feature-spec/runtime-hooks-feature-spec.md) | Feature specification for the interference handling mechanism |

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
