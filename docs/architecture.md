# OperateKit v4 architecture

## Positioning

OperateKit is an RPA-first automation runtime SDK. Android and Windows are the first two supported surfaces. Agent capabilities are intentionally placed above the deterministic runtime.

## Layering

```text
solutions/*
  -> operatekit.rpa
  -> operatekit.runtime
  -> operatekit.core

operatekit.plugins.android  -> operatekit.ports -> operatekit.core
operatekit.plugins.windows  -> operatekit.ports -> operatekit.core
operatekit.plugins.capture  -> operatekit.ports -> operatekit.core
```

## Core concepts

- `TargetSpec`: the thing to automate, such as an Android package or Windows executable.
- `SurfaceDriver`: UI interaction port. Android uses uiautomator2; Windows uses pywinauto.
- `HostDriver`: host/system operations. Android uses adbutils; Windows uses local shell.
- `Observation`: unified evidence stream. Network payloads, UI trees, screenshots, files, logs, and future decisions can all become observations.
- `Actions`: platform-neutral RPA steps.
- `WorkflowRunner`: deterministic run engine with retry, ledger, trace, and notifications.
- `FlowSpec`: declaration-oriented command model inspired by popular RPA/testing flow tools.

## Why not mobile-agent-sdk

The old name pushed the architecture toward mobile-only and agent-first thinking. The current foundation needs to run Android apps and Windows desktop applications first; LLM/agent decisioning should be an optional upper layer.

## Android plugin

```text
operatekit.plugins.android.adbutils_host       # ADB shell, deeplink, push/pull, proxy
operatekit.plugins.android.uiautomator2_surface # UI actions and hierarchy
operatekit.plugins.android.proxy_controller     # Android proxy routing for mitmproxy
```

## Windows plugin

```text
operatekit.plugins.windows.pywinauto_surface    # pywinauto UI automation
operatekit.plugins.windows.pywinauto_host       # local shell / URL opening
```

The Windows plugin supports `backend="uia"` and `backend="win32"`. Code imports pywinauto lazily so the package can be imported and tested on non-Windows environments.

## Capture plugin

`mitmproxy` is modeled as an observation source. Business workflows wait for `ObservationKind.NETWORK`, not for a mitmproxy-specific object.

## Agent-ready, not agent-first

The SDK includes a small `operatekit.agent.ToolRegistry` and `RiskPolicy` model. These are intentionally thin. They make it possible to expose deterministic RPA flows as future agent tools while keeping platform calls behind `Actions`, `WorkflowRunner`, and drivers.

Agent code should never call raw coordinates, raw pywinauto objects, raw uiautomator2 sessions, or raw ADB commands unless they are wrapped as audited SDK tools.
