# Feature Spec: Runtime Hooks

## Convergence Summary

- **Confirmed goal**: Add Runtime-managed hooks that automatically stabilize RPA workflows around Business Steps and remove cross-cutting interference from business flow definitions.
- **Confirmed requirements**: Hooks run before/after hookable Business Steps, use lightweight observations, return explicit outcomes, respect bounded stabilization, and are registered at SDK/Runner level.
- **Known scope boundaries**: Hooks handle Interference only; business Actions, FlowSpec, deeplink, arbitrary shell, and App-specific hooks are out of core SDK scope.
- **Relevant existing context**: `WorkflowRunner` executes `Step`; `Step.execute()` owns retry/trace; `FlowCompiler` has legacy `checkBlockers`; `BlockerManager` is the existing blocker abstraction.
- **Working assumptions**: Existing tests use fake drivers; validation should rely on `pytest` and not require real Android/Windows devices.
- **Blocking questions**: None. This spec is mission-ready for TDD implementation.

## Goal

Introduce a Runtime Hook system so OperateKit executes `observe -> stabilize -> execute business action -> observe -> stabilize` automatically for Business Steps, while keeping workflow definitions focused on business intent.

## Non-goals

- Do not put WechatExitEditHook, Car300AdHook, or other App-specific hooks into core SDK.
- Do not auto-enable all hooks in `create_android()` or `create_windows()`.
- Do not let hooks execute business Actions, FlowSpecs, deeplinks, or arbitrary shell commands.
- Do not model hook execution as `StepResult` or append hook handling as business steps.
- Do not require screenshots for every stabilization round.

## Terms

- **Business Step**: Hookable step that performs workflow intent such as launch, tap, input, key press, scroll, or deeplink.
- **Internal Step**: Non-hookable step for observation bookkeeping, sleep, wait, retry orchestration, tracing, or runtime control.
- **Runtime Hook**: Runtime-managed handler for cross-cutting Interference before/after a Business Step.
- **Runtime Observation**: Lightweight state: UI XML plus package/activity when supported.
- **Stabilization**: Bounded loop that observes and runs hooks until no handled Interference remains or a terminal outcome occurs.
- **Dismissal Primitive**: Limited hook action: click locator, press key, or brief wait.
- **Manual Required**: Distinct workflow outcome for human intervention, not failure.

## PRD Requirements

- **REQ-001**: Runtime automatically surrounds each Business Step with pre- and post-Stabilization.
- **REQ-002**: Internal Steps must not trigger automatic Stabilization.
- **REQ-003**: Runtime Observation must default to UI XML plus current package/activity when available.
- **REQ-004**: Hook outcomes must be explicit: `noop`, `handled`, `manual_required`, `retry_step`, `fail_workflow`.
- **REQ-005**: Stabilization must be globally bounded by max rounds and elapsed timeout per phase.
- **REQ-006**: HookRegistry must be SDK/Runner-level, ordered by priority, and explicitly enabled.
- **REQ-007**: Permission and error handling must use explicit policies; unknown permission prompts become `manual_required`.
- **REQ-008**: Existing `BlockerManager`/`checkBlockers` must be unified with Runtime Hooks, not remain a second mechanism.

## Public Interface

```python
class HookOutcome(str, Enum):
    NOOP = "noop"
    HANDLED = "handled"
    MANUAL_REQUIRED = "manual_required"
    RETRY_STEP = "retry_step"
    FAIL_WORKFLOW = "fail_workflow"

@dataclass(frozen=True)
class RuntimeObservation:
    ui_tree: str
    package: str | None = None
    activity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class HookResult:
    outcome: HookOutcome
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class HookContext(Protocol):
    def click(self, locator: Locator, *, timeout: float = 0.5) -> None: ...
    def press_key(self, key: str) -> None: ...
    def wait(self, seconds: float) -> None: ...
    def notify(self, event: str, payload: dict[str, Any]) -> None: ...

class RuntimeHook(Protocol):
    name: str
    priority: int
    def handle(self, ctx: HookContext, observation: RuntimeObservation) -> HookResult: ...
```

- `Step` should expose hookability, e.g. `hookable: bool` or equivalent metadata; Actions that produce Business Steps set it true, Internal Steps set it false.
- `AutomationSDK` should expose hook registration, e.g. `sdk.register_hook(hook)` / constructor hook list / `WorkflowRunner(..., hooks=...)`.
- `default_android_hooks(...)` may return common Generic Hooks but must not be auto-enabled.
- `WorkflowStatus` must add `MANUAL_REQUIRED = "manual_required"`.

## Lifecycle Semantics

- **FR-001**: For each Business Step attempt: run pre-Stabilization, execute the Step action, then run post-Stabilization.
- **FR-002**: Each Stabilization round observes state, evaluates hooks by priority, and applies only the first non-noop outcome.
- **FR-003**: `handled` causes a fresh observation and another round within the same Stabilization phase.
- **FR-004**: `noop` from all hooks ends the current Stabilization phase successfully.
- **FR-005**: `manual_required` finishes the workflow with `WorkflowStatus.MANUAL_REQUIRED` and records reason + last Runtime Observation.
- **FR-006**: `fail_workflow` finishes the workflow with failed status and records reason + last Runtime Observation.
- **FR-007**: `retry_step` consumes the current Business Step retry policy and re-executes the same Step attempt when retries remain.
- **FR-008**: Stabilization budget exhaustion is treated as `fail_workflow` with last Runtime Observation preserved.

## Generic Hook Scope

- **UpdateDialogHook**: closes recognized update prompts using configured cancel/close locators.
- **AdDialogHook**: closes recognized cross-app ad overlays using configured close locators.
- **PermissionHook**: uses `PermissionPolicy`; unknown permission prompts return `manual_required`.
- **CaptchaHook**: detects captcha/human verification patterns and returns `manual_required`.
- **NetworkErrorHook**: uses `ErrorPolicy`; known rules return `retry_step`, `fail_workflow`, or `manual_required`; unknown matching error screens default to `fail_workflow`.
- **LegacyBlockerHook**: adapts existing `BlockerRule` behavior into Runtime Hook semantics for compatibility.

## Trace and Notification Semantics

- **NFR-001**: Hook execution is recorded as independent runtime events, not StepResults.
- **NFR-002**: Emit events such as `stabilization.started`, `runtime_hook.outcome`, and `stabilization.finished` with phase, step name, round, hook name, outcome, and reason.
- **NFR-003**: Screenshots are captured only on errors, `manual_required`, or explicit trace configuration.
- **NFR-004**: Hook events must be sufficient to reconstruct which interference was handled before a Business Step.

## Technical Plan

- Add hook domain models under `operatekit.runtime` or `operatekit.rpa` without importing platform-specific dependencies into core/runtime.
- Add `RuntimeObserver` that reads `ctx.surface.get_tree()` and optional foreground package/activity when available.
- Add bounded `Stabilizer` that owns loop control, priority ordering, HookContext, and outcome handling.
- Integrate stabilization at the Step/Runner boundary so nested execution paths, including retry blocks, do not bypass hooks.
- Extend `WorkflowStatus` and `WorkflowRun.metadata` to preserve `manual_required` reason and last Runtime Observation.
- Convert `BlockerManager` semantics into `LegacyBlockerHook`; keep `checkBlockers` only as a compatibility shim to the same HookRegistry if retained.
- Export stable public types from `operatekit.__init__` only after tests lock the interface.

## Acceptance Criteria

- **AC-001**: A registered hook that returns `handled` before a tap is called automatically without a `checkBlockers` FlowSpec command.
- **AC-002**: A non-hookable internal `waitObservation` or `captureCursor` Step does not invoke stabilization.
- **AC-003**: When two hooks match, only the higher-priority hook handles the current round, and runtime observes again before any later hook can act.
- **AC-004**: A captcha hook produces `WorkflowStatus.MANUAL_REQUIRED` with reason and last observation in run metadata.
- **AC-005**: A network error hook returning `retry_step` re-runs the same Business Step and consumes its retry policy.
- **AC-006**: Stabilization budget exhaustion fails the workflow with trace/notifier evidence.
- **AC-007**: Existing `BlockerRule` behavior can be expressed through Runtime Hook compatibility without a separate blocker execution path.

## Validation Plan

- **VAL-001**: `pytest tests/test_runtime_hooks.py` covers hook lifecycle, priority, outcomes, and budget behavior.
- **VAL-002**: `pytest tests/test_workflow_runner.py tests/test_retry_block.py` confirms existing runner and retry behavior remains compatible.
- **VAL-003**: `pytest` full suite passes without Android/Windows optional dependencies.
- **VAL-004**: Tests assert notifier/trace events for hook outcomes without adding hook StepResults.
- **VAL-005**: Tests use fake surfaces/hosts to validate Runtime Observation and foreground metadata fallback.

## Test Case Checklist

- Runtime calls pre/post stabilization around `Actions.tap`.
- Runtime does not stabilize around `Actions.wait_observation`, `Actions.capture_cursor`, or `Actions.sleep`.
- `handled` hook loops until all hooks return `noop` or budget is exhausted.
- Priority ordering executes only one handled hook per observation round.
- `manual_required` stops workflow with distinct status and metadata.
- `fail_workflow` stops workflow as failed with reason and last observation.
- `retry_step` retries current Business Step, including post-stabilization retry.
- Retry exhaustion after `retry_step` fails workflow deterministically.
- PermissionPolicy unknown prompt returns `manual_required`.
- ErrorPolicy unknown network/server error defaults to `fail_workflow`.
- Legacy `BlockerRule` closes a blocker through hook compatibility.
- `checkBlockers` compatibility path, if kept, delegates to HookRegistry/Stabilizer.

## Agent Execution Contract

- Implement vertical slices with TDD: one failing behavior test, minimal implementation, then refactor.
- Preserve existing public behavior when no hooks are registered.
- Do not add platform-specific imports to core/runtime.
- Do not weaken tests by mocking away runtime loop behavior; use fake drivers with observable calls.
- Do not introduce parallel v2 hook/blocker implementations.

## Mission Handoff

1. **Slice 1**: Add hook models, hookable Step classification, Runtime Observation, and no-op Stabilizer tests.
2. **Slice 2**: Integrate pre/post stabilization for Business Steps and prove Internal Steps are skipped.
3. **Slice 3**: Implement bounded loop, priority handling, trace/notifier events, and terminal outcomes.
4. **Slice 4**: Add `manual_required` workflow status and `retry_step` retry-policy semantics.
5. **Slice 5**: Adapt `BlockerManager`/`checkBlockers` and add Generic Hook policy tests.

## Readiness Score

- **Score**: 91/100 mission-ready.
- **Residual risk**: Exact foreground package/activity provider shape may need small adjustment during implementation to avoid breaking fake or Windows drivers.
