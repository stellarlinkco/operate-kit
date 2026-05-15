"""Windows automation example.

Demonstrates: launch, type text, press key, tap by automation_id,
wait visible, and different locator types for pywinauto.
"""

from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_windows(
    executable=r"C:\Windows\System32\notepad.exe",
    backend="uia",
    artifacts_dir="./artifacts/windows",
)

# --- Basic notepad flow ---

run = sdk.run_steps("notepad_edit", [
    Actions.launch(),
    Actions.type_text("hello from OperateKit\n"),
    Actions.type_text("second line"),
    Actions.press_key("ctrl+a"),
    Actions.press_key("ctrl+c"),
])

print(f"Status: {run.status.value}")

# --- Windows locator types ---
# Locator.automation_id("submitButton")
# Locator.title("File")
# Locator.name("Save")
# Locator.control_type("Button")
# Locator.class_name("Edit")

# --- Connect to an already-running window ---

# sdk = AutomationSDK.create_windows(
#     title="My Application",
#     backend="uia",
#     connect=True,
#     artifacts_dir="./artifacts/windows",
# )
