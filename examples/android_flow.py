from operatekit import AutomationSDK, Actions, Locator

sdk = AutomationSDK.create_android(package="com.example.app", artifacts_dir="./artifacts/android")

sdk.run_steps("android_search", [
    Actions.launch(stop=True),
    Actions.tap(Locator.text("搜索"), timeout=10),
    Actions.type_text("keyword", clear=True),
    Actions.press_key("enter"),
])
