# OperateKit Automation SDK

OperateKit is an RPA-first, cross-surface automation runtime SDK. The current priority is Android + Windows PC automation. The architecture is agent-ready, but the agent layer stays above the deterministic RPA runtime.

## Why this name

The old `mobile-agent-sdk` name over-constrained the project: it sounded mobile-only and agent-first. OperateKit is an automation runtime: Android apps, Windows desktop applications, network observations, workflow retry, traces, cache, and future LLM/agent decisions all fit under the same execution model.

## Install

```bash
pip install -e .[android]
pip install -e .[windows]
pip install -e .[capture]
```

## Android

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_android(
    package="com.example.app",
    serial=None,
    artifacts_dir="./artifacts",
)

sdk.run_steps("android_search", [
    Actions.launch(),
    Actions.tap(Locator.text("搜索")),
    Actions.type_text("keyword", clear=True),
    Actions.press_key("enter"),
])
```

## Windows / pywinauto

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_windows(
    executable=r"C:\\Windows\\System32\\notepad.exe",
    backend="uia",
    artifacts_dir="./artifacts",
)

sdk.run_steps("windows_notepad", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit"),
    Actions.press_key("ctrl+s"),
])
```

## FlowSpec

```python
flow = {
    "name": "submit_with_retry",
    "commands": [
        {"launch": {}},
        {"retry": {
            "name": "submit_and_wait",
            "maxRetries": 3,
            "commands": [
                {"tap": {"text": "提交"}},
                {"waitObservation": {
                    "kind": "network",
                    "pattern": "contains:/api/result",
                    "timeout": 30,
                    "storeKey": "result_payload"
                }}
            ]
        }}
    ]
}

sdk.run_flow_spec(flow, raise_on_failure=False)
```

## Documentation

- **[SDK 使用指南](docs/usage-guide.md)** — 全量 API 文档，涵盖安装、Android/Windows 快速开始、Actions、FlowSpec、ScreenObject、Runtime Hooks、观测抓包、Trace、Agent ToolRegistry
- [架构文档](docs/architecture.md) — 分层设计和模块职责
- [Runtime Hooks 特性规格](docs/feature-spec/runtime-hooks-feature-spec.md) — 干扰处理机制的设计规格

## Architecture in one line

`solutions -> rpa -> runtime -> core`, while `plugins/android`, `plugins/windows`, and `plugins/capture` implement ports. Core and runtime never import `adbutils`, `uiautomator2`, `pywinauto`, or `mitmproxy`.

## License

MIT
