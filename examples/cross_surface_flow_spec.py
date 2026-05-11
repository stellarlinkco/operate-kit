from operatekit import AutomationSDK

flow = {
    "name": "submit_with_retry",
    "commands": [
        {"launch": {}},
        {"retry": {
            "name": "submit_and_wait",
            "maxRetries": 3,
            "commands": [
                {"tap": {"text": "提交", "timeout": 10}},
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

sdk = AutomationSDK.create_android(package="com.example.app")
sdk.run_flow_spec(flow, raise_on_failure=False)
