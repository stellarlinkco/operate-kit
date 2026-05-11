from operatekit import Actions, AutomationSDK, TargetSpec


class FakeSurface:
    def launch(self, target=None, *, stop=False): pass
    def close(self): pass
    def click(self, locator, *, timeout=10): pass
    def type_text(self, text, *, locator=None, clear=False, timeout=10): pass
    def press_key(self, key): pass
    def exists(self, locator, *, timeout=0): return True
    def wait_visible(self, locator, *, timeout=10): pass
    def scroll(self, direction="down", *, amount=0.8): pass
    def get_tree(self): return ""
    def screenshot(self, path): return path


def test_retry_block_retries_whole_block(tmp_path):
    sdk = AutomationSDK.create_with_drivers(target=TargetSpec.android("com.example"), surface=FakeSurface(), artifacts_dir=tmp_path)
    state = {"attempts": 0}

    def flaky(ctx):
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise RuntimeError("not yet")

    step = Actions.retry_block("flaky_block", [Actions.call("flaky", flaky)], max_retries=3)
    run = sdk.run_steps("retry", [step])
    assert run.status.value == "passed"
    assert state["attempts"] == 3
