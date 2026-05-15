# OperateKit SDK 使用指南

[English Version](usage-guide.md)

OperateKit 是一个 RPA 优先的跨平台自动化运行时 SDK。当前支持 Android 和 Windows 两个平台，架构上为 Agent（LLM 决策）预留了扩展层，但核心执行层保持确定性。

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
  - [Android](#android)
  - [Windows](#windows)
  - [自定义 Driver](#自定义-driver)
- [Locator 定位器](#locator-定位器)
- [Actions API](#actions-api)
- [FlowSpec 声明式流程](#flowspec-声明式流程)
- [ScreenObject 页面对象](#screenobject-页面对象)
- [Runtime Hooks 运行时干扰处理](#runtime-hooks-运行时干扰处理)
  - [注册 Hook](#注册-hook)
  - [内置 Generic Hooks](#内置-generic-hooks)
  - [自定义 App-specific Hook](#自定义-app-specific-hook)
  - [InterferenceResult 类型化结果](#interferenceresult-类型化结果)
  - [StabilizationConfig 预算配置](#stabilizationconfig-预算配置)
- [观测与网络抓包](#观测与网络抓包)
- [Trace 执行追踪](#trace-执行追踪)
- [Agent ToolRegistry](#agent-toolregistry)
- [架构概览](#架构概览)

---

## 安装

```bash
# Android 自动化（依赖 uiautomator2 + adbutils）
pip install -e .[android]

# Windows 自动化（依赖 pywinauto）
pip install -e .[windows]

# 网络抓包（依赖 mitmproxy）
pip install -e .[capture]

# 全部安装
pip install -e .[android,windows,capture]
```

---

## 快速开始

### Android

```python
from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_android(
    package="com.example.app",
    serial=None,              # 自动检测设备；多设备时指定序列号
    artifacts_dir="./artifacts",
)

run = sdk.run_steps("搜索流程", [
    Actions.launch(),
    Actions.tap(Locator.text("搜索")),
    Actions.type_text("关键词", clear=True),
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
    backend="uia",            # "uia" 或 "win32"
    artifacts_dir="./artifacts",
)

run = sdk.run_steps("记事本测试", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit"),
    Actions.press_key("ctrl+s"),
])
```

### 自定义 Driver

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

## Locator 定位器

`Locator` 是平台无关的 UI 元素定位描述。Android 平台自动转换为 XPath，Windows 平台自动转换为 pywinauto `child_window` 参数。

```python
from operatekit import Locator

# 通用
Locator.text("提交")
Locator.xpath('//*[@resource-id="com.example:id/btn"]')

# Android 专用
Locator.resource_id("com.example:id/search_input")
Locator.content_desc("返回按钮")

# Windows 专用
Locator.automation_id("submitButton")
Locator.title("文件")
Locator.name("保存")
Locator.control_type("Button")
Locator.class_name("Edit")

# 坐标（慎用）
Locator.coordinates(500, 300)
```

---

## Actions API

`Actions` 是平台无关的 RPA 步骤工厂。每个方法返回一个 `Step` 对象，交给 `sdk.run_steps()` 执行。

### 交互类（Business Step，会触发 Stabilization）

| 方法 | 说明 |
|------|------|
| `Actions.launch(stop=False)` | 启动目标应用 |
| `Actions.close()` | 关闭目标应用 |
| `Actions.tap(locator, timeout=10)` | 点击元素 |
| `Actions.type_text(text, locator=None, clear=False, timeout=10)` | 输入文本 |
| `Actions.press_key(key)` | 按键（如 `"enter"`, `"back"`, `"ctrl+s"`） |
| `Actions.scroll(direction="down", amount=0.8)` | 滚动 |
| `Actions.deeplink(url)` | 打开 deeplink |

### 辅助类（Internal Step，不触发 Stabilization）

| 方法 | 说明 |
|------|------|
| `Actions.wait_visible(locator, timeout=10)` | 等待元素可见 |
| `Actions.sleep(seconds)` | 等待固定时间 |
| `Actions.shell(command, timeout=None, store_key=None)` | 执行 shell 命令 |
| `Actions.capture_cursor(key)` | 捕获观测游标 |
| `Actions.wait_observation(kind=None, pattern=..., cursor_key=None, timeout=30, store_key=None)` | 等待匹配的观测 |
| `Actions.wait_payload(pattern, cursor_key=None, timeout=30, store_key=None)` | 等待网络观测（`wait_observation` 的 `kind=network` 快捷方式） |

### 重试块

```python
Actions.retry_block(
    "提交并等待",
    [
        Actions.tap(Locator.text("提交")),
        Actions.wait_payload("contains:/api/result", timeout=30, store_key="result"),
    ],
    max_retries=3,
    delay_seconds=2.0,
    backoff_multiplier=1.5,
)
```

`retry_block` 内的子 Business Step 仍然会触发 Stabilization。如果子步骤因 Runtime Hook 产生终端结果（如 `manual_required`），retry_block 会立即传播，不会重试。

### 自定义步骤

```python
# 默认 Internal Step（不触发 Stabilization）
Actions.call("自定义操作", lambda ctx: do_something(ctx))

# 显式声明为 Business Step（会触发 Stabilization）
Actions.call("自定义业务操作", lambda ctx: do_something(ctx), hookable=True)
```

### 重试策略

```python
from operatekit import RetryPolicy

step = Actions.tap(Locator.text("提交"))
step.retry_policy = RetryPolicy(
    max_attempts=3,
    delay_seconds=1.0,
    backoff_multiplier=2.0,
)
```

---

## FlowSpec 声明式流程

FlowSpec 用字典/JSON 描述自动化流程，适合配置驱动的场景。

```python
flow = {
    "name": "提交并等待结果",
    "commands": [
        {"launch": {}},
        {"tap": {"text": "提交", "timeout": 10}},
        {"inputText": {"text": "搜索内容", "clear": True}},
        {"pressKey": "enter"},
        {"scroll": "down"},
        {"waitVisible": {"text": "结果", "timeout": 15}},
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
            "name": "重试提交",
            "maxRetries": 3,
            "delay": 2,
            "commands": [
                {"tap": {"text": "提交"}},
                {"waitPayload": {"pattern": "contains:/api/submit", "timeout": 10}},
            ],
        }},
        {"checkBlockers": {}},
    ],
}

run = sdk.run_flow_spec(flow, raise_on_failure=False)
```

---

## ScreenObject 页面对象

ScreenObject 把页面元素集中管理，减少 Locator 散落在流程代码里。

```python
login_screen = sdk.screen("登录页", {
    "username": {"resource_id": "com.example:id/username"},
    "password": {"resource_id": "com.example:id/password"},
    "submit":   {"text": "登录"},
})

run = sdk.run_steps("登录", [
    Actions.launch(),
    login_screen.tap("username"),
    login_screen.type_text("username", "user@example.com", clear=True),
    login_screen.type_text("password", "secret", clear=True),
    login_screen.tap("submit"),
    login_screen.assert_visible("submit", timeout=5),
])
```

---

## Runtime Hooks 运行时干扰处理

Runtime Hooks 自动处理自动化过程中出现的横切干扰（Interference），如更新弹窗、广告、权限提示、验证码、网络错误等。

每个 Business Step 执行前后都会经历 **Stabilization**（稳定化）：观察当前 UI 状态 -> 按优先级运行 Hook -> 若 handled 则重新观察 -> 直到稳定或产生终端结果。

### 注册 Hook

```python
from operatekit import (
    PermissionHook, PermissionPolicy,
    NetworkErrorHook, ErrorPolicy, ErrorRule,
    CaptchaHook, UpdateDialogHook, AdDialogHook,
    HookOutcome, Locator,
)

sdk = AutomationSDK.create_android(package="com.example.app")

# 权限弹窗处理
sdk.register_hook(PermissionHook(PermissionPolicy(
    prompt_patterns=("permission", "允许"),
    allow={"camera": Locator.text("允许"), "位置": Locator.text("始终允许")},
    deny={"通讯录": Locator.text("拒绝")},
)))

# 网络/服务器错误处理
sdk.register_hook(NetworkErrorHook(ErrorPolicy(
    rules=[
        ErrorRule("网络不可用", HookOutcome.RETRY_STEP, reason="网络恢复后重试"),
        ErrorRule("服务器维护", HookOutcome.MANUAL_REQUIRED, reason="需要人工确认"),
    ],
    error_patterns=("network", "server", "网络", "服务器"),
)))

# 验证码 -> 人工介入
sdk.register_hook(CaptchaHook(patterns=("验证码", "captcha", "人机验证")))

# 更新弹窗 -> 自动关闭
sdk.register_hook(UpdateDialogHook(
    patterns=("新版本", "立即更新", "update"),
    dismiss=Locator.text("以后再说"),
))

# 广告弹窗 -> 自动关闭
sdk.register_hook(AdDialogHook(
    patterns=("广告", "推荐", "限时"),
    dismiss=Locator.text("关闭"),
))
```

### 内置 Generic Hooks

| Hook | 默认优先级 | 行为 |
|------|-----------|------|
| `CaptchaHook` | 100 | 检测验证码 -> `manual_required` |
| `PermissionHook` | 90 | 已知权限 allow/deny -> `handled`；未知权限 -> `manual_required` |
| `NetworkErrorHook` | 80 | 按 ErrorPolicy 规则 -> `retry_step` / `fail_workflow` / `manual_required` |
| `UpdateDialogHook` | 70 | 匹配更新弹窗 -> 点击 dismiss -> `handled` |
| `AdDialogHook` | 70 | 匹配广告弹窗 -> 点击 dismiss -> `handled` |
| `LegacyBlockerHook` | 0 | 兼容旧 BlockerRule -> `handled` |

优先级数值越高，越先执行。同一轮 Stabilization 中只有第一个非 noop 的 Hook 生效。

### 自定义 App-specific Hook

```python
from operatekit import HookResult, HookOutcome, RuntimeObservation, Locator

class WechatEditExitHook:
    name = "wechat_edit_exit"
    priority = 60

    def handle(self, ctx, observation: RuntimeObservation) -> HookResult:
        if "是否保存" not in observation.ui_tree:
            return HookResult(HookOutcome.NOOP)
        ctx.click(Locator.text("不保存"))
        return HookResult(HookOutcome.HANDLED, reason="微信编辑退出弹窗已关闭")

sdk.register_hook(WechatEditExitHook())
```

**Hook Outcome 语义：**

| Outcome | 含义 |
|---------|------|
| `NOOP` | 本 Hook 不处理当前状态 |
| `HANDLED` | 已处理，Stabilization 重新观察 |
| `RETRY_STEP` | 消费当前 Business Step 的 retry policy 重试 |
| `MANUAL_REQUIRED` | 需要人工介入，工作流暂停 |
| `FAIL_WORKFLOW` | 工作流失败 |

**Hook 只能使用 Dismissal Primitives：**
- `ctx.click(locator, timeout=0.5)` -- 点击
- `ctx.press_key(key)` -- 按键
- `ctx.wait(seconds)` -- 短暂等待
- `ctx.notify(event, payload)` -- 发送通知事件

### InterferenceResult 类型化结果

当 Hook 产生终端结果时，`StepResult.interference` 提供类型化访问：

```python
from operatekit import WorkflowStatus

run = sdk.run_steps("demo", [Actions.tap(Locator.text("提交"))])

if run.status == WorkflowStatus.MANUAL_REQUIRED:
    result = run.step_results[-1]

    # 类型化访问（推荐）
    assert result.interference.is_manual_required
    assert result.interference.is_terminal
    print(result.interference.outcome)           # HookOutcome.MANUAL_REQUIRED
    print(result.interference.reason)            # "unknown permission prompt"
    print(result.interference.hook_name)         # "permission"
    print(result.interference.last_observation)  # RuntimeObservation(ui_tree=..., package=..., activity=...)

    # 向后兼容的 dict 访问（仍可用）
    print(run.metadata["runtime_hook"]["outcome"])  # "manual_required"
```

正常通过的步骤 `interference` 为 `None`。

### StabilizationConfig 预算配置

```python
from operatekit import StabilizationConfig, TargetSpec

sdk = AutomationSDK.create_with_drivers(
    target=TargetSpec.android("com.example.app"),
    surface=surface,
    artifacts_dir="./artifacts",
    stabilization=StabilizationConfig(
        max_rounds=5,          # 每个 phase 最多观察轮数
        timeout_seconds=5.0,   # 每个 phase 最长耗时
    ),
)
```

超出预算会产生 `fail_workflow` 结果。

---

## 观测与网络抓包

OperateKit 将网络抓包建模为观测（Observation），业务流程通过 `wait_observation` / `wait_payload` 等待特定网络响应。

### 启动 mitmproxy 抓包

```python
# 基础抓包
proxy = sdk.mitm_proxy(port=8080, endpoint_patterns=["/api/submit", "/api/result"])

# Android 一键抓包（ADB 反向代理 + mitmproxy）
session = sdk.android_mitm_session(
    port=8080,
    route="adb_reverse",      # "adb_reverse" 或 "wifi"
    endpoint_patterns=["/api/*"],
)
```

### 等待网络观测

```python
run = sdk.run_steps("抓包流程", [
    Actions.launch(),
    Actions.capture_cursor("before"),
    Actions.tap(Locator.text("提交")),
    Actions.wait_payload(
        "contains:/api/result",
        cursor_key="before",
        timeout=30,
        store_key="api_result",
    ),
])

# 获取观测快照
snapshot = sdk.snapshot_observation("api_result", fields=["data", "code"])
print(snapshot.hash)
```

### 观测类型

```python
from operatekit import ObservationKind

ObservationKind.NETWORK     # 网络请求/响应
ObservationKind.UI_TREE     # UI 层次结构
ObservationKind.SCREENSHOT  # 截图
ObservationKind.HOST        # 主机操作
ObservationKind.FILE        # 文件
ObservationKind.LOG         # 日志
ObservationKind.DECISION    # 决策记录
```

---

## Trace 执行追踪

Trace 记录每个步骤的执行细节，用于调试和审计。

```python
from operatekit import TraceConfig

recorder = sdk.enable_trace(TraceConfig(
    capture_ui_tree=False,       # 是否在每步前保存 UI XML
    capture_screenshot=False,    # 是否在每步前截图
    screenshot_on_error=True,    # 步骤失败时截图
))

sdk.run_steps("traced_flow", [
    Actions.launch(),
    Actions.tap(Locator.text("提交")),
])

# 追踪数据写入 artifacts/trace/trace.jsonl
```

---

## Agent ToolRegistry

ToolRegistry 为未来的 LLM/Agent 集成提供薄接入层。Agent 代码通过注册的工具调用 RPA 运行时，而不直接接触底层驱动。

```python
from operatekit import AutomationTool, ToolRegistry, RiskPolicy

registry = ToolRegistry()

registry.register(AutomationTool(
    name="search",
    description="在应用中搜索关键词",
    func=lambda keyword: sdk.run_steps("search", [
        Actions.tap(Locator.text("搜索")),
        Actions.type_text(keyword, clear=True),
        Actions.press_key("enter"),
    ]),
    risk_policy=RiskPolicy.low(),
))

# 高风险工具需要审批
registry.register(AutomationTool(
    name="delete_account",
    description="删除用户账号",
    func=lambda: sdk.run_steps("delete", [
        Actions.tap(Locator.text("删除账号")),
        Actions.tap(Locator.text("确认")),
    ]),
    risk_policy=RiskPolicy.high("不可逆操作", requires_approval=True),
))

# 调用
tool = registry.get("search")
tool.invoke("OperateKit")

# 高风险工具未审批会抛 PermissionError
tool = registry.get("delete_account")
tool.invoke(approved=True)  # 必须显式审批
```

---

## 架构概览

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

**关键约束：**
- `core` 和 `runtime` 不导入 `adbutils`、`uiautomator2`、`pywinauto` 或 `mitmproxy`
- Runtime Hooks 只通过 Dismissal Primitives 操作 UI，不直接调用平台驱动
- Hook Registry 在 SDK/Runner 层配置，不写进 FlowSpec
- Agent 层在确定性 RPA 运行时之上，不绕过 `Actions` / `WorkflowRunner`
