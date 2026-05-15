"""ScreenObject (Page Object) example.

Demonstrates: defining page elements as a ScreenObject, then using
tap, type_text, and assert_visible through the page object instead
of scattering Locators throughout flow code.
"""

from operatekit import AutomationSDK, Actions

sdk = AutomationSDK.create_android(
    package="com.example.app",
    artifacts_dir="./artifacts/screen_object",
)

# --- Define page objects ---

login_screen = sdk.screen("login", {
    "username":     {"resource_id": "com.example:id/username"},
    "password":     {"resource_id": "com.example:id/password"},
    "submit":       {"text": "Login"},
    "error_msg":    {"resource_id": "com.example:id/error"},
    "forgot":       {"text": "Forgot Password?"},
})

home_screen = sdk.screen("home", {
    "search":       {"resource_id": "com.example:id/search"},
    "profile":      {"text": "Profile"},
    "settings":     {"content_desc": "Settings"},
    "notification": {"resource_id": "com.example:id/notification_badge"},
})

# --- Login flow using page objects ---

run = sdk.run_steps("login", [
    Actions.launch(),
    login_screen.tap("username"),
    login_screen.type_text("username", "user@example.com", clear=True),
    login_screen.type_text("password", "secure_password", clear=True),
    login_screen.tap("submit"),
])

print(f"Login: {run.status.value}")

# --- Home page navigation ---

run = sdk.run_steps("navigate_home", [
    home_screen.tap("search"),
    home_screen.assert_visible("profile", timeout=5),
    home_screen.tap("settings"),
])

print(f"Navigate: {run.status.value}")
