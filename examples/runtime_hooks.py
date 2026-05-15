"""Runtime Hooks example.

Demonstrates: registering built-in Generic Hooks (permission, network error,
captcha, update dialog, ad dialog), creating a custom App-specific Hook,
and inspecting InterferenceResult when a terminal outcome occurs.
"""

from operatekit import (
    Actions,
    AdDialogHook,
    AutomationSDK,
    CaptchaHook,
    ErrorPolicy,
    ErrorRule,
    HookOutcome,
    HookResult,
    Locator,
    NetworkErrorHook,
    PermissionHook,
    PermissionPolicy,
    RuntimeObservation,
    StabilizationConfig,
    UpdateDialogHook,
    WorkflowStatus,
)

sdk = AutomationSDK.create_android(
    package="com.example.app",
    artifacts_dir="./artifacts/hooks",
    stabilization=StabilizationConfig(max_rounds=5, timeout_seconds=5.0),
)

# --- Built-in Generic Hooks ---

# Permission prompts: auto-allow camera, auto-deny contacts, pause on unknown
sdk.register_hook(PermissionHook(PermissionPolicy(
    prompt_patterns=("permission", "allow"),
    allow={"camera": Locator.text("Allow")},
    deny={"contacts": Locator.text("Deny")},
)))

# Network errors: retry on timeout, fail on unknown
sdk.register_hook(NetworkErrorHook(ErrorPolicy(
    rules=[
        ErrorRule("network unavailable", HookOutcome.RETRY_STEP, reason="retry after recovery"),
        ErrorRule("server maintenance", HookOutcome.MANUAL_REQUIRED, reason="needs manual check"),
    ],
    error_patterns=("network", "server"),
)))

# Captcha: always pause for human
sdk.register_hook(CaptchaHook(patterns=("captcha", "human verification")))

# Update dialog: auto-dismiss
sdk.register_hook(UpdateDialogHook(
    patterns=("new version", "update now"),
    dismiss=Locator.text("Later"),
))

# Ad dialog: auto-dismiss
sdk.register_hook(AdDialogHook(
    patterns=("advertisement", "promotion", "limited time"),
    dismiss=Locator.text("Close"),
))


# --- Custom App-specific Hook ---

class WechatEditExitHook:
    """Dismisses WeChat's "save changes?" prompt on edit exit."""

    name = "wechat_edit_exit"
    priority = 60

    def handle(self, ctx, observation: RuntimeObservation) -> HookResult:
        if "save changes" not in observation.ui_tree.lower():
            return HookResult(HookOutcome.NOOP)
        ctx.click(Locator.text("Don't Save"))
        return HookResult(HookOutcome.HANDLED, reason="edit exit prompt dismissed")


sdk.register_hook(WechatEditExitHook())


# --- Run and inspect results ---

run = sdk.run_steps("demo", [
    Actions.launch(),
    Actions.tap(Locator.text("Submit")),
])

if run.status == WorkflowStatus.MANUAL_REQUIRED:
    result = run.step_results[-1]

    # Typed access (recommended)
    print(f"Terminal: {result.interference.is_terminal}")
    print(f"Outcome:  {result.interference.outcome.value}")
    print(f"Reason:   {result.interference.reason}")
    print(f"Hook:     {result.interference.hook_name}")

    if result.interference.last_observation:
        print(f"UI tree:  {result.interference.last_observation.ui_tree[:100]}...")

    # Backward-compatible dict access
    print(f"Dict:     {run.metadata['runtime_hook']['outcome']}")

elif run.status == WorkflowStatus.PASSED:
    print("All steps passed, no interference detected.")

elif run.status == WorkflowStatus.FAILED:
    result = run.step_results[-1]
    if result.interference:
        print(f"Failed due to hook: {result.interference.reason}")
    else:
        print(f"Failed: {result.error}")
