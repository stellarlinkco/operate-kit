from operatekit import Locator


def test_android_locator_translation():
    assert Locator.text("搜索").to_android_xpath() == '//*[@text="搜索"]'
    assert Locator.resource_id("com.example:id/input").to_android_xpath() == '//*[@resource-id="com.example:id/input"]'


def test_windows_locator_translation():
    assert Locator.automation_id("SubmitButton").to_windows_kwargs() == {"auto_id": "SubmitButton"}
    assert Locator.title("提交").to_windows_kwargs() == {"title": "提交"}
    assert Locator.control_type("Button").to_windows_kwargs() == {"control_type": "Button"}
