"""Android automation example.

Demonstrates: launch, tap, type, press key, scroll, wait visible,
deeplink, retry block, and result inspection.
"""

from operatekit import AutomationSDK, Actions, Locator, RetryPolicy

sdk = AutomationSDK.create_android(
    package="com.example.app",
    serial=None,
    artifacts_dir="./artifacts/android",
)

# --- Basic flow ---

run = sdk.run_steps("android_search", [
    Actions.launch(stop=True),
    Actions.tap(Locator.text("Search"), timeout=10),
    Actions.type_text("keyword", clear=True),
    Actions.press_key("enter"),
    Actions.scroll("down"),
    Actions.wait_visible(Locator.text("Result"), timeout=15),
])

print(f"Status: {run.status.value}, steps: {len(run.step_results)}")

# --- Retry block ---

run = sdk.run_steps("submit_with_retry", [
    Actions.retry_block(
        "submit",
        [
            Actions.tap(Locator.text("Submit")),
            Actions.wait_visible(Locator.text("Success"), timeout=5),
        ],
        max_retries=3,
        delay_seconds=1.0,
    ),
])

# --- Custom step with retry policy ---

step = Actions.tap(Locator.text("Confirm"))
step.retry_policy = RetryPolicy(max_attempts=3, delay_seconds=0.5, backoff_multiplier=2.0)

run = sdk.run_steps("confirm", [step])

# --- Deeplink ---

run = sdk.run_steps("deeplink_nav", [
    Actions.deeplink("myapp://page/detail?id=123"),
    Actions.wait_visible(Locator.resource_id("com.example:id/detail_title"), timeout=10),
])
