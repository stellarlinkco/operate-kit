from operatekit import AutomationSDK, TargetSpec


class FakeSurface:
    def __init__(self): self.events=[]
    def launch(self, target=None, *, stop=False): pass
    def close(self): pass
    def click(self, locator, *, timeout=10): self.events.append(locator.value)
    def type_text(self, text, *, locator=None, clear=False, timeout=10): pass
    def press_key(self, key): pass
    def exists(self, locator, *, timeout=0): return True
    def wait_visible(self, locator, *, timeout=10): pass
    def scroll(self, direction="down", *, amount=0.8): pass
    def get_tree(self): return ""
    def screenshot(self, path): return path


def test_screen_object(tmp_path):
    surface = FakeSurface()
    sdk = AutomationSDK.create_with_drivers(target=TargetSpec.windows(title="Demo"), surface=surface, artifacts_dir=tmp_path)
    screen = sdk.screen("Login", {"submit": {"automation_id": "SubmitButton"}})
    sdk.run_steps("screen", [screen.tap("submit")])
    assert surface.events == ["SubmitButton"]
