from operatekit import Actions, AutomationSDK, Locator, TargetSpec
from operatekit.core.observation.observation import Observation


class FakeSurface:
    def __init__(self):
        self.events = []
        self.visible = {"提交": False}

    def launch(self, target=None, *, stop=False):
        self.events.append(("launch", stop))

    def close(self):
        self.events.append(("close",))

    def click(self, locator, *, timeout=10):
        self.events.append(("click", locator.value))

    def type_text(self, text, *, locator=None, clear=False, timeout=10):
        self.events.append(("type", text, clear))

    def press_key(self, key):
        self.events.append(("key", key))

    def exists(self, locator, *, timeout=0):
        return True

    def wait_visible(self, locator, *, timeout=10):
        return None

    def scroll(self, direction="down", *, amount=0.8):
        self.events.append(("scroll", direction, amount))

    def get_tree(self):
        return "<root/>"

    def screenshot(self, path):
        return path


class FakeHost:
    def shell(self, command, *, timeout=None):
        return "ok"

    def open_url(self, url):
        pass


def test_run_steps_with_fake_surface(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        host=FakeHost(),
        artifacts_dir=tmp_path,
    )
    run = sdk.run_steps("demo", [Actions.launch(), Actions.tap(Locator.text("提交")), Actions.type_text("abc")])
    assert run.status.value == "passed"
    assert sdk.context.surface.events[:3] == [("launch", False), ("click", "提交"), ("type", "abc", False)]


def test_flow_spec_wait_observation(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        host=FakeHost(),
        artifacts_dir=tmp_path,
    )
    cursor = sdk.observations.cursor()
    sdk.context.set("before", cursor)
    sdk.observations.add(Observation.network(url="https://x.test/api/result", body={"ok": True}))
    run = sdk.run_flow_spec({
        "name": "wait_api",
        "commands": [
            {"waitPayload": {"pattern": "contains:/api/result", "cursorKey": "before", "timeout": 0.5, "storeKey": "payload"}}
        ]
    })
    assert run.status.value == "passed"
    assert sdk.context.get("payload").json()["ok"] is True
