# OperateKit RPA Runtime

OperateKit provides a deterministic RPA runtime for executing business automation across Android and Windows surfaces while keeping agent decisioning above the runtime boundary.

## Language

**Business Step**:
A hookable workflow step that performs domain-specific automation intent, such as launching an app, tapping a business control, entering text, or navigating through the target surface.
_Avoid_: Hook step, blocker step

**Internal Step**:
A non-hookable workflow step used for observation bookkeeping, waiting, sleeping, tracing, or runtime control rather than business interaction.
_Avoid_: Business Step

**Runtime Hook**:
A runtime-managed handler that detects and resolves cross-cutting interference before or after a Business Step.
_Avoid_: Flow command, business action

**Generic Hook**:
A Runtime Hook for common cross-app Interference such as update prompts, ads, permissions, captchas, or network errors.
_Avoid_: App-specific Hook

**App-specific Hook**:
A Runtime Hook owned by business-side code for Interference unique to a particular app or workflow.
_Avoid_: Generic Hook, SDK built-in

**Interference**:
Unexpected UI or environment state that blocks automation progress but is not part of the business workflow.
_Avoid_: Business state, expected screen

**Stabilization**:
The repeated runtime phase that observes current state and runs Runtime Hooks until no handled Interference remains or a terminal outcome is reached.
_Avoid_: Verification, assertion

**Runtime Observation**:
The lightweight evidence captured during Stabilization, consisting of UI XML plus current package and activity when the surface supports them.
_Avoid_: Screenshot trace, full diagnostic bundle

**Stabilization Budget**:
The global per-phase limit for Stabilization rounds and elapsed time.
_Avoid_: Per-hook retry policy

**Hook Outcome**:
The explicit result of a Runtime Hook: noop, handled, manual_required, retry_step, or fail_workflow.
_Avoid_: Boolean handled flag, StepResult

**Hook Priority**:
The runtime order used to decide which matching Runtime Hook handles the current Runtime Observation first.
_Avoid_: Unordered hook set

**Hook Registry**:
The SDK or runner-level ordered collection of Runtime Hooks enabled for a workflow run.
_Avoid_: Flow-defined hook list, global auto-enabled hooks

**Dismissal Primitive**:
A constrained action Runtime Hooks may use to remove Interference, such as clicking a locator, pressing a key, or briefly waiting.
_Avoid_: Business Action, FlowSpec, arbitrary shell

**Permission Policy**:
The explicit allow-or-deny decision table used by PermissionHook for system permission prompts.
_Avoid_: Always allow, always deny

**Error Policy**:
The explicit decision table that maps user-visible network or server error states to retry_step, fail_workflow, or manual_required.
_Avoid_: Always retry, always fail

**Manual Required**:
A distinct workflow outcome indicating automation cannot safely continue without human input.
_Avoid_: Failure, retry

## Relationships

- A **Business Step** is surrounded by **Stabilization** before and after execution.
- An **Internal Step** is not surrounded by **Stabilization**.
- **Stabilization** creates a **Runtime Observation** before asking **Runtime Hooks** to act.
- **Stabilization** is bounded by a **Stabilization Budget**.
- A **Hook Registry** is configured at the SDK or runner boundary, not inside business FlowSpecs.
- **Stabilization** runs **Runtime Hooks** from the **Hook Registry** by **Hook Priority**.
- In one Stabilization round, only the first handled or terminal **Hook Outcome** is applied before observing again.
- A **Runtime Hook** handles **Interference** only; it does not perform **Business Step** logic.
- A **Runtime Hook** may be a **Generic Hook** provided by the SDK or an **App-specific Hook** provided by business-side code.
- A **Runtime Hook** may act only through **Dismissal Primitives**.
- A **Runtime Hook** reports a **Hook Outcome** instead of a StepResult.
- A handled **Hook Outcome** causes **Stabilization** to observe again.
- A retry_step **Hook Outcome** consumes the current **Business Step** retry policy.
- Permission prompts are handled through a **Permission Policy**; unknown permission prompts produce **Manual Required**.
- Network and server error screens are handled through an **Error Policy**.
- **Manual Required** is distinct from failure because the workflow is paused for human action rather than declared incorrect.
- A workflow that reaches **Manual Required** reports a distinct run status with the reason and last **Runtime Observation**.

## Example dialogue

> **Dev:** "Should the flow include a step to close update dialogs before every tap?"
> **Domain expert:** "No — that is Interference. A Runtime Hook should handle it during Stabilization so the Business Step stays focused on the workflow intent."

## Flagged ambiguities

- "hook" means **Runtime Hook** in this project, not a FlowSpec command inserted by business workflows.
- "blocker" is treated as legacy wording for **Interference** handled by a **Runtime Hook**, not a separate runtime concept.
