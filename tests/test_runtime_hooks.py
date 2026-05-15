from pathlib import Path

from operatekit import (
    Actions,
    AutomationSDK,
    BlockerManager,
    BlockerRule,
    CaptchaHook as ProductionCaptchaHook,
    ErrorPolicy,
    ErrorRule,
    FlowCompiler,
    HookOutcome,
    HookResult,
    InterferenceResult,
    Locator,
    NetworkErrorHook,
    PermissionHook,
    PermissionPolicy,
    RetryPolicy,
    StabilizationConfig,
    TargetSpec,
)
from operatekit.rpa.blockers import LegacyBlockerHook


class FakeSurface:
    def __init__(self):
        self.events = []
        self.trees = ["<update/>", "<root/>", "<root/>"]

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
        self.events.append(("observe",))
        if self.trees:
            return self.trees.pop(0)
        return "<root/>"

    def screenshot(self, path):
        return path


class CloseUpdateHook:
    name = "close_update"
    priority = 10

    def handle(self, ctx, observation):
        if "update" not in observation.ui_tree:
            return HookResult(HookOutcome.NOOP)
        ctx.click(Locator.text("Later"))
        return HookResult(HookOutcome.HANDLED, reason="update dialog dismissed")


def test_registered_hook_stabilizes_around_tap(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CloseUpdateHook())

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert sdk.context.surface.events == [
        ("observe",),
        ("click", "Later"),
        ("observe",),
        ("click", "Submit"),
        ("observe",),
    ]
    assert len(run.step_results) == 1
    assert run.step_results[0].name == "tap"


def test_internal_steps_do_not_stabilize(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CloseUpdateHook())

    run = sdk.run_steps("demo", [Actions.sleep(0), Actions.call("custom", lambda ctx: None)])

    assert run.status.value == "passed"
    assert sdk.context.surface.events == []


def test_unknown_permission_prompt_requires_manual_intervention_without_click(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog>permission required</dialog>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(PermissionHook(PermissionPolicy(prompt_patterns=("permission",))))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "manual_required"
    assert run.step_results[0].interference.is_manual_required is True
    assert run.metadata["runtime_hook"]["outcome"] == "manual_required"
    assert run.metadata["runtime_hook"]["reason"] == "unknown permission prompt"
    assert [event for event in surface.events if event[0] == "click"] == []


def test_known_permission_policy_clicks_allow_and_continues_workflow(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog>camera permission</dialog>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(
        PermissionHook(
            PermissionPolicy(
                prompt_patterns=("permission",),
                allow={"camera permission": Locator.text("Allow")},
            )
        )
    )

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert ("click", "Allow") in surface.events
    assert ("click", "Submit") in surface.events


def test_known_permission_policy_clicks_deny_and_continues_workflow(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog>contacts permission</dialog>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(
        PermissionHook(
            PermissionPolicy(
                prompt_patterns=("permission",),
                deny={"contacts permission": Locator.text("Deny")},
            )
        )
    )

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert ("click", "Deny") in surface.events
    assert ("click", "Submit") in surface.events


def test_known_network_error_policy_retries_current_business_step(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<root/>", "<error>network unavailable</error>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(NetworkErrorHook(ErrorPolicy([ErrorRule("network unavailable", HookOutcome.RETRY_STEP)])))
    step = Actions.tap(Locator.text("Submit"), timeout=1)
    step.retry_policy = RetryPolicy(max_attempts=2)

    run = sdk.run_steps("demo", [step])

    assert run.status.value == "passed"
    assert [event for event in surface.events if event == ("click", "Submit")] == [
        ("click", "Submit"),
        ("click", "Submit"),
    ]
    assert run.step_results[0].attempts == 2


def test_unknown_network_or_server_error_fails_workflow_with_hook_metadata(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<error>server temporarily unavailable</error>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(NetworkErrorHook(ErrorPolicy(error_patterns=("network", "server"))))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))], raise_on_failure=False)

    assert run.status.value == "failed"
    assert run.step_results[0].interference.outcome == HookOutcome.FAIL_WORKFLOW
    assert run.metadata["runtime_hook"]["outcome"] == "fail_workflow"
    assert run.metadata["runtime_hook"]["reason"] == "unknown network/server error"


def test_production_captcha_hook_returns_manual_required(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<challenge>human verification required</challenge>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(ProductionCaptchaHook(patterns=("human verification",)))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "manual_required"
    assert run.step_results[0].interference.is_manual_required is True
    assert run.step_results[0].interference.reason == "captcha/human verification detected"
    assert run.metadata["runtime_hook"]["outcome"] == "manual_required"
    assert run.metadata["runtime_hook"]["reason"] == "captcha/human verification detected"


def test_actions_call_can_opt_in_to_stabilization(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CloseUpdateHook())

    run = sdk.run_steps("demo", [Actions.call("custom", lambda ctx: ctx.surface.click(Locator.text("Submit")), hookable=True)])

    assert run.status.value == "passed"
    assert sdk.context.surface.events[:4] == [("observe",), ("click", "Later"), ("observe",), ("click", "Submit")]


class CaptchaHook:
    name = "captcha"
    priority = 100

    def handle(self, ctx, observation):
        return HookResult(HookOutcome.MANUAL_REQUIRED, reason="captcha detected")


def test_manual_required_hook_stops_workflow_with_observation_metadata(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<captcha/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CaptchaHook())

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "manual_required"
    assert run.step_results[0].interference.is_manual_required is True
    assert run.step_results[0].interference.last_observation.ui_tree == "<captcha/>"
    assert run.metadata["runtime_hook"]["reason"] == "captcha detected"
    assert run.metadata["runtime_hook"]["last_observation"]["ui_tree"] == "<captcha/>"
    assert sdk.context.surface.events == [("observe",)]


class RetryOnceHook:
    name = "retry_once"
    priority = 50

    def __init__(self):
        self.retry_requested = False

    def handle(self, ctx, observation):
        if "retry" in observation.ui_tree and not self.retry_requested:
            self.retry_requested = True
            return HookResult(HookOutcome.RETRY_STEP, reason="network recovered")
        return HookResult(HookOutcome.NOOP)


def test_retry_step_reexecutes_business_step_and_consumes_retry_policy(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<root/>", "<retry/>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(RetryOnceHook())
    step = Actions.tap(Locator.text("Submit"), timeout=1)
    step.retry_policy = RetryPolicy(max_attempts=2)

    run = sdk.run_steps("demo", [step])

    assert run.status.value == "passed"
    assert [event for event in sdk.context.surface.events if event == ("click", "Submit")] == [
        ("click", "Submit"),
        ("click", "Submit"),
    ]
    assert run.step_results[0].attempts == 2


class RecordingHook:
    def __init__(self, name, priority, events, outcome):
        self.name = name
        self.priority = priority
        self.events = events
        self.outcome = outcome

    def handle(self, ctx, observation):
        self.events.append((self.name, observation.ui_tree))
        if self.outcome == HookOutcome.HANDLED:
            ctx.click(Locator.text(self.name))
            self.outcome = HookOutcome.NOOP
            return HookResult(HookOutcome.HANDLED, reason=self.name)
        return HookResult(self.outcome)


def test_only_highest_priority_non_noop_hook_handles_each_round(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog/>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    calls = []
    sdk.register_hook(RecordingHook("low", 1, calls, HookOutcome.HANDLED))
    sdk.register_hook(RecordingHook("high", 100, calls, HookOutcome.HANDLED))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert calls[:2] == [("high", "<dialog/>"), ("high", "<root/>")]
    assert ("low", "<dialog/>") not in calls
    assert sdk.context.surface.events[:3] == [("observe",), ("click", "high"), ("observe",)]


class AlwaysHandleHook:
    name = "always"
    priority = 1

    def handle(self, ctx, observation):
        return HookResult(HookOutcome.HANDLED, reason="still blocked")


def test_stabilization_budget_exhaustion_fails_workflow_with_last_observation(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<blocked/>", "<blocked/>" ]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
        stabilization=StabilizationConfig(max_rounds=2, timeout_seconds=10),
    )
    sdk.register_hook(AlwaysHandleHook())

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))], raise_on_failure=False)

    assert run.status.value == "failed"
    assert run.step_results[0].interference.outcome == HookOutcome.FAIL_WORKFLOW
    assert run.step_results[0].interference.last_observation.ui_tree == "<blocked/>"
    assert run.metadata["runtime_hook"]["outcome"] == "fail_workflow"
    assert run.metadata["runtime_hook"]["last_observation"]["ui_tree"] == "<blocked/>"


class ForegroundSurface(FakeSurface):
    current_package = "com.example"

    def get_current_activity(self):
        return ".MainActivity"


class CaptureObservationHook:
    name = "capture_observation"
    priority = 1

    def __init__(self):
        self.observation = None

    def handle(self, ctx, observation):
        self.observation = observation
        return HookResult(HookOutcome.NOOP)


def test_runtime_observation_includes_foreground_metadata_when_available(tmp_path):
    hook = CaptureObservationHook()
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=ForegroundSurface(),
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(hook)

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert hook.observation.package == "com.example"
    assert hook.observation.activity == ".MainActivity"


def test_legacy_blocker_rule_can_run_as_runtime_hook(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<root><button text='Update later'/></root>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(LegacyBlockerHook([BlockerRule("update", Locator.text("Update later"), dismiss=Locator.text("Later"))]))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert sdk.context.surface.events[:2] == [("observe",), ("click", "Later")]


def test_nested_retry_block_child_business_steps_are_stabilized(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<update/>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CloseUpdateHook())

    run = sdk.run_steps("demo", [Actions.retry_block("nested", [Actions.tap(Locator.text("Submit"))])])

    assert run.status.value == "passed"
    assert sdk.context.surface.events[:4] == [("observe",), ("click", "Later"), ("observe",), ("click", "Submit")]


def test_core_workflow_step_does_not_import_runtime_layer():
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "src" / "operatekit" / "core" / "workflow" / "step.py").read_text()

    assert "operatekit.runtime" not in source


class AlwaysRetryHook:
    name = "always_retry"
    priority = 100

    def handle(self, ctx, observation):
        return HookResult(HookOutcome.RETRY_STEP, reason="retry requested")


def test_nested_retry_block_child_manual_required_stops_outer_workflow(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<captcha/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CaptchaHook())

    run = sdk.run_steps("demo", [Actions.retry_block("nested", [Actions.tap(Locator.text("Submit"))], max_retries=3)])

    assert run.status.value == "manual_required"
    assert run.step_results[0].interference.is_manual_required is True
    assert run.metadata["runtime_hook"]["outcome"] == "manual_required"
    assert run.metadata["runtime_hook"]["reason"] == "captcha detected"
    assert [event for event in surface.events if event == ("click", "Submit")] == []


def test_nested_retry_block_does_not_retry_after_child_retry_step_exhausted(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<retry/>", "<retry/>", "<retry/>", "<retry/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(AlwaysRetryHook())
    child = Actions.tap(Locator.text("Submit"))
    child.retry_policy = RetryPolicy(max_attempts=2)

    run = sdk.run_steps("demo", [Actions.retry_block("nested", [child], max_retries=3)], raise_on_failure=False)

    assert run.status.value == "failed"
    assert run.step_results[0].interference.outcome == HookOutcome.RETRY_STEP
    assert run.metadata["runtime_hook"]["outcome"] == "retry_step"
    assert [event for event in surface.events if event == ("observe",)] == [("observe",), ("observe",)]
    assert [event for event in surface.events if event == ("click", "Submit")] == []


class CheckBlockersHook:
    name = "check_blockers_hook"
    priority = 10

    def __init__(self):
        self.calls = []

    def handle(self, ctx, observation):
        self.calls.append(observation.ui_tree)
        if "modal" in observation.ui_tree:
            ctx.click(Locator.text("Dismiss"))
            return HookResult(HookOutcome.HANDLED, reason="modal dismissed")
        return HookResult(HookOutcome.NOOP)


def test_flow_spec_check_blockers_uses_active_registered_runtime_hooks(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<modal/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    hook = CheckBlockersHook()
    sdk.register_hook(hook)

    run = sdk.run_flow_spec({"name": "check", "commands": [{"checkBlockers": {}}]})

    assert run.status.value == "passed"
    assert hook.calls == ["<modal/>", "<root/>"]
    assert ("click", "Dismiss") in surface.events


def test_flow_spec_check_blockers_includes_legacy_blocker_manager_when_sdk_stabilizer_exists(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<root><button text='Update later'/></root>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    manager = BlockerManager([BlockerRule("update", Locator.text("Update later"), dismiss=Locator.text("Later"))])
    sdk.flow_compiler = FlowCompiler(blocker_manager=manager)

    assert sdk.context.stabilizer is not None
    run = sdk.run_flow_spec({"name": "check", "commands": [{"checkBlockers": {}}]})

    assert run.status.value == "passed"
    assert sdk.context.surface.events == [("observe",), ("click", "Later"), ("observe",)]


def test_blocker_manager_compat_uses_legacy_blocker_hook_matching():
    surface = FakeSurface()
    surface.trees = ["<root/>"]
    manager = BlockerManager([BlockerRule("update", Locator.text("Update later"), dismiss=Locator.text("Later"))])

    dismissed = manager.check_and_dismiss(surface)

    assert dismissed == []
    assert ("click", "Later") not in surface.events


class RecordingNotifier:
    def __init__(self):
        self.events = []

    def notify(self, event, payload):
        self.events.append((event, payload))


class RecordingTrace:
    def __init__(self):
        self.events = []

    def before_step(self, ctx, step, attempt):
        pass

    def after_step(self, ctx, step, result):
        pass

    def step_error(self, ctx, step, attempt, exc):
        pass

    def event(self, event, ctx, payload):
        self.events.append((event, payload))


def test_runtime_hook_events_are_emitted_independently_of_step_results(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<update/>", "<root/>", "<root/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    notifier = RecordingNotifier()
    trace = RecordingTrace()
    sdk.context.notifier = notifier
    sdk.context.trace = trace
    sdk.register_hook(CloseUpdateHook())

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    notified_events = [event for event, _payload in notifier.events]
    assert "stabilization.started" in notified_events
    assert "runtime_hook.outcome" in notified_events
    assert "stabilization.finished" in notified_events
    assert [event for event, _payload in trace.events] == [
        event for event in notified_events if event in {"stabilization.started", "runtime_hook.outcome", "stabilization.finished"}
    ]
    assert run.status.value == "passed"
    assert [result.name for result in run.step_results] == ["tap"]
    assert "runtime_hook" not in run.step_results[0].metadata


def test_manual_required_produces_typed_interference_result(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog>permission required</dialog>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(PermissionHook(PermissionPolicy(prompt_patterns=("permission",))))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    step_result = run.step_results[0]
    assert isinstance(step_result.interference, InterferenceResult)
    assert step_result.interference.outcome == HookOutcome.MANUAL_REQUIRED
    assert step_result.interference.reason == "unknown permission prompt"
    assert step_result.interference.hook_name == "permission"
    assert step_result.interference.is_manual_required is True
    assert step_result.interference.is_terminal is True
    assert step_result.interference.last_observation is not None
    assert "permission" in step_result.interference.last_observation.ui_tree
    # backward compat: run.metadata still has runtime_hook dict
    assert run.metadata["runtime_hook"]["outcome"] == "manual_required"


def test_fail_workflow_produces_typed_interference_result(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<error>server temporarily unavailable</error>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(NetworkErrorHook(ErrorPolicy(error_patterns=("network", "server"))))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))], raise_on_failure=False)

    step_result = run.step_results[0]
    assert isinstance(step_result.interference, InterferenceResult)
    assert step_result.interference.outcome == HookOutcome.FAIL_WORKFLOW
    assert step_result.interference.is_terminal is True
    assert step_result.interference.is_manual_required is False
    # backward compat
    assert run.metadata["runtime_hook"]["outcome"] == "fail_workflow"


def test_passed_step_has_no_interference(tmp_path):
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=FakeSurface(),
        artifacts_dir=tmp_path,
    )
    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    assert run.status.value == "passed"
    assert run.step_results[0].interference is None


def test_nested_retry_propagates_typed_interference_to_outer_step(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<captcha/>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(CaptchaHook())

    run = sdk.run_steps("demo", [Actions.retry_block("nested", [Actions.tap(Locator.text("Submit"))], max_retries=3)])

    assert run.status.value == "manual_required"
    outer_result = run.step_results[0]
    assert isinstance(outer_result.interference, InterferenceResult)
    assert outer_result.interference.outcome == HookOutcome.MANUAL_REQUIRED
    assert outer_result.interference.reason == "captcha detected"


def test_step_result_to_dict_includes_interference(tmp_path):
    surface = FakeSurface()
    surface.trees = ["<dialog>permission required</dialog>"]
    sdk = AutomationSDK.create_with_drivers(
        target=TargetSpec.android("com.example"),
        surface=surface,
        artifacts_dir=tmp_path,
    )
    sdk.register_hook(PermissionHook(PermissionPolicy(prompt_patterns=("permission",))))

    run = sdk.run_steps("demo", [Actions.tap(Locator.text("Submit"))])

    d = run.step_results[0].to_dict()
    assert d["interference"]["outcome"] == "manual_required"
    assert d["interference"]["hook"] == "permission"
    assert d["interference"]["last_observation"]["ui_tree"] == "<dialog>permission required</dialog>"
