# Android and Windows plugin guide

## Android

```python
sdk = AutomationSDK.create_android(package="com.example.app", serial=None)
```

Android uses:

- `AdbutilsHostDriver` for shell, deeplink, reverse, proxy, install, push and pull.
- `Uiautomator2SurfaceDriver` for launch, click, type, press, scroll, screenshot, UI tree.

## Windows

```python
sdk = AutomationSDK.create_windows(
    executable=r"C:\\Windows\\System32\\notepad.exe",
    backend="uia",
)
```

Windows uses:

- `LocalWindowsHostDriver` for shell commands and URL opening.
- `PywinautoSurfaceDriver` for launch/connect, click, type, keypress, screenshot and control tree.

Recommended locator mappings:

| OperateKit locator | Android | Windows / pywinauto |
|---|---|---|
| `Locator.text("OK")` | XPath by text | `title="OK"` |
| `Locator.resource_id("id")` | XPath resource-id | not used |
| `Locator.automation_id("id")` | not used | `auto_id="id"` |
| `Locator.control_type("Button")` | not used | `control_type="Button"` |
| `Locator.class_name("Edit")` | not used | `class_name="Edit"` |
| `Locator.coordinates(x, y)` | raw click | raw mouse click |
