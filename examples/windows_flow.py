from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_windows(
    executable=r"C:\\Windows\\System32\\notepad.exe",
    backend="uia",
    artifacts_dir="./artifacts/windows",
)

sdk.run_steps("windows_notepad", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit"),
    Actions.press_key("ctrl+s"),
])
