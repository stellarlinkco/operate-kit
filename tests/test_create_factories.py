from operatekit import AutomationSDK
from operatekit.plugins.android.uiautomator2_surface import Uiautomator2SurfaceDriver
from operatekit.plugins.windows.pywinauto_surface import PywinautoSurfaceDriver


def test_create_android_does_not_import_optional_driver_until_used(tmp_path):
    sdk = AutomationSDK.create_android(package="com.example", artifacts_dir=tmp_path)
    assert isinstance(sdk.context.surface, Uiautomator2SurfaceDriver)
    assert sdk.target.kind.value == "android"


def test_create_windows_does_not_import_pywinauto_until_used(tmp_path):
    sdk = AutomationSDK.create_windows(executable="notepad.exe", artifacts_dir=tmp_path)
    assert isinstance(sdk.context.surface, PywinautoSurfaceDriver)
    assert sdk.target.kind.value == "windows"
