"""Trace and Observation example.

Demonstrates: enabling execution trace, capturing network observations
via mitmproxy, waiting for specific API responses, and taking snapshots.
"""

from operatekit import AutomationSDK, Actions, Locator, TraceConfig

sdk = AutomationSDK.create_android(
    package="com.example.app",
    artifacts_dir="./artifacts/trace",
)

# --- Enable trace ---

sdk.enable_trace(TraceConfig(
    capture_ui_tree=False,
    capture_screenshot=False,
    screenshot_on_error=True,
))

# --- Network capture with mitmproxy ---
# Requires: pip install -e .[capture]

# Option 1: Android ADB reverse proxy (recommended for USB-connected devices)
# session = sdk.android_mitm_session(
#     port=8080,
#     route="adb_reverse",
#     endpoint_patterns=["/api/submit", "/api/result"],
# )

# Option 2: Basic proxy
# proxy = sdk.mitm_proxy(port=8080, endpoint_patterns=["/api/*"])

# --- Flow with observation capture ---

run = sdk.run_steps("capture_api", [
    Actions.launch(),
    Actions.capture_cursor("before_submit"),
    Actions.tap(Locator.text("Submit")),
    Actions.wait_payload(
        "contains:/api/result",
        cursor_key="before_submit",
        timeout=30,
        store_key="api_result",
    ),
])

print(f"Status: {run.status.value}")

# --- Snapshot observation for comparison ---

# snapshot = sdk.snapshot_observation("api_result", fields=["data", "code"])
# print(f"Response hash: {snapshot.hash}")
# print(f"Observation ID: {snapshot.observation_id}")

# --- Trace output ---
# Trace data is written to: artifacts/trace/trace/trace.jsonl
# Each step records: before_step, after_step, step_error events
# Error screenshots saved to: artifacts/trace/trace/<step>_<attempt>_error.png
