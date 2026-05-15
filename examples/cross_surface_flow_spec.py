"""FlowSpec declarative workflow example.

Demonstrates: all FlowSpec commands including launch, tap, inputText,
pressKey, scroll, waitVisible, sleep, shell, deeplink, captureCursor,
waitPayload, retry, and checkBlockers.
"""

from operatekit import AutomationSDK

sdk = AutomationSDK.create_android(
    package="com.example.app",
    artifacts_dir="./artifacts/flowspec",
)

# --- Full FlowSpec with all command types ---

flow = {
    "name": "complete_flow",
    "commands": [
        {"launch": {}},
        {"tap": {"text": "Search", "timeout": 10}},
        {"inputText": {"text": "keyword", "clear": True}},
        {"pressKey": "enter"},
        {"scroll": "down"},
        {"waitVisible": {"text": "Result", "timeout": 15}},
        {"sleep": 1},
        {"tap": {"text": "Result"}},
        {"captureCursor": {"key": "before_submit"}},
        {"tap": {"text": "Submit"}},
        {"waitPayload": {
            "pattern": "contains:/api/result",
            "cursorKey": "before_submit",
            "timeout": 30,
            "storeKey": "result_payload",
        }},
    ],
}

run = sdk.run_flow_spec(flow, raise_on_failure=False)
print(f"Status: {run.status.value}")

# --- FlowSpec with retry ---

retry_flow = {
    "name": "submit_with_retry",
    "commands": [
        {"launch": {}},
        {"retry": {
            "name": "submit_and_wait",
            "maxRetries": 3,
            "delay": 2,
            "commands": [
                {"tap": {"text": "Submit", "timeout": 10}},
                {"waitPayload": {
                    "pattern": "contains:/api/submit",
                    "timeout": 10,
                    "storeKey": "submit_result",
                }},
            ],
        }},
    ],
}

run = sdk.run_flow_spec(retry_flow, raise_on_failure=False)

# --- FlowSpec with shell and deeplink ---

utility_flow = {
    "name": "utility_commands",
    "commands": [
        {"shell": "echo hello"},
        {"deeplink": "myapp://page/detail?id=123"},
        {"waitVisible": {"text": "Detail", "timeout": 10}},
        {"checkBlockers": {}},
    ],
}

run = sdk.run_flow_spec(utility_flow, raise_on_failure=False)
