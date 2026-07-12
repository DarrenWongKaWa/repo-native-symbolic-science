# Agent-First Controller Usage

How to run the orchestration controller from a human-facing Codex/Claude Code session while
keeping isolated subagent roles separate.

---

## 1. Overview

The orchestration controller (`scripts/orch_controller.py`) coordinates a multi-agent scientific
workflow where each role (planner, executor, verifier) runs in a **separate, isolated context**.
This prevents one agent from silently editing another's output, verifying its own work, or
upgrading its claim authority without independent corroboration.

You (the human scientist) operate from a single coordinating session. The controller enforces
role isolation, fail-closed validation, and claim-boundary checks at every stage.

**Controller architecture:**

```
Human-facing session
       │
       ▼
┌──────────────────────────────────────────────┐
│  orch_controller.py (CLI)                     │
│  ┌────────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Dispatcher  │──│ Registry  │──│ Validator │ │
│  │ (routing)   │  │ (roles)   │  │ (scripts) │ │
│  └────────────┘  └──────────┘  └───────────┘ │
└──────────────────────────────────────────────┘
       │                │                │
       ▼                ▼                ▼
  ┌─────────┐    ┌──────────┐    ┌─────────────┐
  │ Planner │    │ Executor │    │  Verifier   │
  │ Context │    │ Context  │    │  Context    │
  │  (A)    │    │   (B)    │    │    (C)      │
  └─────────┘    └──────────┘    └─────────────┘
```

---

## 2. Quick Start

All commands are run from the repository root.

### Check registered roles

```bash
python3 scripts/orch_controller.py list-roles
# {"roles": ["executor", "global_planner", ...]}
```

### Validate a task contract

```bash
python3 scripts/orch_controller.py validate-task path/to/task_contract.json
# {"passed": true, "blocking_findings": [], "errors": []}
```

Use `--verbose` to see all internal checks:

```bash
python3 scripts/orch_controller.py --verbose validate-task path/to/task_contract.json
```

### Check a state transition

```bash
python3 scripts/orch_controller.py check-transition --from EXECUTING --to EXECUTION_COMPLETE
# {"allowed": true, "reason": "Transition from 'EXECUTING' to 'EXECUTION_COMPLETE' is allowed", ...}
```

### Run a workflow fixture

```bash
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
# {"passed": true, "blocking_findings": [], "errors": []}
```

---

## 3. Controller as Coordinator

The controller **routes** but does NOT **replace** verification. It enforces three invariants:

1. **No self-verification.** An executor cannot verify its own output. The `forbidden_actions`
   list includes `self_verify` for every role that produces artifacts.
2. **Claim authority is bounded.** A planner can claim at most `planning`-level authority. It
   cannot promote its output to `canonical`. The `claim_boundary.max_claim_level` field enforces
   this.
3. **Every transition requires positive evidence.** The default verdict is FAIL. A PASS requires
   `checks_executed > 0`, `checks_passed == checks_executed`, and zero blocking findings.

### What the controller does NOT do

- The controller does **not** verify scientific correctness. That is the verifier's job.
- The controller does **not** edit symbolic output. It only validates structure and compliance.
- The controller does **not** make scientific decisions. It defers to human gates.

### Using the controller in a real session

```bash
# 1. Synthesize a plan
python3 scripts/init_stage.py --role planner --output plan.json

# 2. Validate the plan's structure
python3 scripts/orch_controller.py validate-task plan.json

# 3. If valid, freeze and dispatch
python3 scripts/orch_controller.py check-transition --from PLAN_READY --to EXECUTION_ELIGIBLE
```

---

## 4. Role Isolation

### The core principle

```
executor_context != verifier_context
```

Every role runs in its own context. Contexts are identified by:
- **Adapter class** (`SyntheticExecutor` vs `SyntheticVerifier`)
- **Forbidden actions** (e.g. an executor cannot `issue_verdict`)
- **Claim boundary** (an executor cannot claim `verification`)
- **Input scope** (a verifier only sees frozen executor artifacts, not scratch)

### How to ensure isolation

1. **Never reuse context identifiers between roles.** If you dispatch an executor to
   `subagent:codex/exec-1`, the verifier must go to `subagent:codex/verify-1`, not the same slot.

2. **Freeze inputs before dispatch.** The `input_sha_manifest` field in the task contract
   records the SHA-256 of every authorized input. The verifier checks this against actual
   artifacts to detect tampering.

3. **Separate output directories.** Each role writes to its own output directory. The
   controller validates that no two concurrent writers share a directory.

```bash
# Each role writes to a separate directory
EXEC_DIR=.loop/output/exec-1
VERIFY_DIR=.loop/output/verify-1
```

### Isolation validation commands

```bash
# Check that verifier and executor contexts are distinct
python3 scripts/orch_controller.py validate-task --role independent_verifier verify_contract.json
# Fails if the verifier's forbidden_actions don't include "edit_executor_outputs"
```

---

## 5. Working with Task Contracts

A task contract is a JSON object that freezes everything a subagent needs to know at dispatch
time. It is **immutable after freezing**.

### Required fields

| Field | Description |
|-------|-------------|
| `task_id` | Unique immutable identifier |
| `role` | Assigned role (`executor`, `independent_verifier`, etc.) |
| `objective` | Human-readable task description |
| `authorized_inputs` | List of `{path, sha256}` objects; empty for planner |
| `required_outputs` | List of output filenames that must be materialized |
| `allowed_actions` | Actions the role is authorized to perform |
| `forbidden_actions` | Actions the role is explicitly forbidden from performing |
| `claim_boundary` | `{max_claim_level: string}` defining the authority ceiling |

### Constructing a task contract

```python
# In Python (from within a script or adapter)
contract = {
    "task_id": "exec-001",
    "role": "executor",
    "objective": "Decompose a symbolic expression into index sectors",
    "authorized_inputs": [
        {"path": "plan_output.json", "sha256": "abc123..."}
    ],
    "required_outputs": [
        "execution_output.json",
        "output_sha_manifest.json"
    ],
    "allowed_actions": [
        "read_frozen_inputs",
        "execute_transformations",
        "write_outputs",
        "generate_sha_manifest"
    ],
    "forbidden_actions": [
        "verify_own_output",
        "repair_own_output",
        "promote_canonical",
        "self_verify"
    ],
    "claim_boundary": {"max_claim_level": "execution"}
}
```

### Validating a task contract from the CLI

```bash
# Write the contract to a file
python3 -c "import json; json.dump(contract, open('contract.json','w'))"

# Validate it
python3 scripts/orch_controller.py --verbose validate-task contract.json
```

### Claim boundary levels (ascending)

| Level | Rank | Who can claim it |
|-------|------|------------------|
| `planning` | 0 | `global_planner`, `lane_planner` |
| `execution` | 1 | `executor`, `repair_executor` |
| `verification` | 2 | `independent_verifier`, `integration_verifier` |
| `human_gate` | 3 | `human_gate_materializer` (controller) |
| `integration` | 4 | `integration_executor` |
| `reporting` | 5 | `report_generator`, `supplement_writer` |
| `canonical` | 6 | None (requires human sign-off) |
| `publication` | 7 | None (requires journal acceptance) |

---

## 6. Running Workflows

### Synthetic workflows (for testing)

Synthetic workflows use the built-in `SyntheticPlanner`, `SyntheticExecutor`, and
`SyntheticVerifier` adapters. They exist solely to validate controller logic without
touching real symbolic engines.

```bash
# Run the 3-stage demo
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json

# Expected output (pass):
# {"passed": true, "blocking_findings": [], "errors": []}
```

### Configuring synthetic failure modes

The `SyntheticExecutor` adapter accepts configuration flags via the registry. To test
fail-closed behavior, set `should_fail: true` in the adapter config:

```bash
# This simulates an executor that always fails
python3 -c "
from loop_engine.orch_dispatcher import ControllerDispatcher
from loop_engine.orch_registry import OrchRegistry
r = OrchRegistry()
r.register_adapter('executor', {
    'module_path': 'loop_engine.orch_adapters.synthetic_executor',
    'class_name': 'SyntheticExecutor',
    'validator_scripts': [],
    'required_inputs': ['/dev/null'],
    'allowed_actions': [],
    'forbidden_actions': [],
    'claim_authority': 'execution',
    'config': {'should_fail': True},
})
"
```

### Real workflows (with symbolic engines)

Real workflows use actual symbolic computation engines (SymPy, Mathematica, etc.) via
registered adapters. The workflow fixture format is the same; only the adapter
implementations differ.

```bash
# Example: run a real simplification workflow
python3 scripts/orch_controller.py run-workflow tasks/synthetic_decompose.workflow.json
```

### Workflow fixture format

Workflows are defined as JSON with a `stages` array. Each stage specifies:

```json
{
  "workflow_id": "unique-id",
  "workflow_name": "Human-readable name",
  "description": "What this workflow does",
  "stages": [
    {
      "stage_id": "unique-stage-id",
      "role": "role_name",
      "depends_on": ["other-stage-id"],
      "task_contract": { /* task contract fields */ }
    }
  ]
}
```

The `depends_on` field enforces ordering: a stage only becomes eligible when all its
dependencies have completed with a PASS verdict.

---

## 7. Validation Stages

The controller runs validators at specific points in the workflow lifecycle. These are
configured in the adapter registry (`loop_engine/orch_adapters/registry.json`).

### Pre-execution validators (run before executor dispatch)

```
scripts/validate_input_sha_freezing.py      -- verify all inputs are frozen (SHA exists)
scripts/validate_dependency_eligibility.py  -- verify all dependency gates passed
```

### Post-execution validators (run after executor completes)

```
scripts/validate_output_contract_completion.py    -- verify all required outputs exist
scripts/validate_partial_artifact_consumption.py  -- verify no input was skipped
```

### Pre-verification validators (run before verifier dispatch)

```
scripts/validate_verifier_independence.py  -- verify verifier context != executor context
scripts/validate_role_separation.py        -- verify verifier is not also the executor
```

### Post-verification validators (run after verifier completes)

```
scripts/validate_handoff_completeness.py   -- verify all artifacts are accounted for
```

### Running validators manually

```bash
python3 scripts/validate_output_contract_completion.py .loop/output/exec-1/
# exit 0 = pass, exit 1 = fail
```

### Adding a custom validator

1. Write a script that exits 0 on success and nonzero on failure.
2. Register it in the adapter's `validator_scripts` list in `registry.json`.
3. The controller picks it up automatically at the relevant stage.

---

## 8. Fail-Closed Behavior

### The default verdict is FAIL

In `ControllerValidationResult`, `passed` starts as `False` and `final_exit_status` as `1`.
A PASS is only awarded when **all** of the following are true:

1. `checks_executed > 0` — at least one positive check was performed
2. `checks_passed == checks_executed` — every check passed
3. `blocking_findings` is empty — no blockers were recorded

### What triggers a block

| Condition | Block reason |
|-----------|-------------|
| Unknown role | "Unknown role 'X'" |
| Role attempts action in `forbidden_actions` | "Role unauthorized" |
| Missing required input | "Required input artifacts missing" |
| Adapter not importable | "Declared validator unavailable" |
| Validator script exits nonzero | "Validator script 'X' failed with exit code Y" |
| Validator script times out | "Validator script 'X' timed out" |
| Zero checks executed | "Validator stage 'X' executed zero checks" |
| Invalid state transition | "Transition from X to Y is not allowed" |

### How to test fail-closed

```bash
# Configure executor to fail, then run the workflow.
# Expected: blocking_findings contains "Synthetic executor: configured to fail"
#           passed = false, final_exit_status = 1
```

---

## 9. Human Gates

Human gates are decision points where the controller pauses and waits for explicit
human input before continuing.

### When gates are triggered

- `VERIFIED_WITH_CAVEAT` — verification passed but with caveats that need human judgment
- `REJECTED` — verification failed and automatic repair is not allowed
- `HUMAN_GATE_REQUIRED` — the workflow explicitly requested human review
- `FAILED` — pipeline failed and human intervention is required

### Materializing a human gate

```bash
# The controller records a human gate decision
python3 tools/sloop_handoff.py materialize-gate \
    --gate-id "gate-001" \
    --decision "APPROVE_WITH_CAVEAT" \
    --rationale "Caveat is acceptable because it only affects subleading terms"
```

### Decision options

| Decision | Effect |
|----------|--------|
| `APPROVE` | Promote artifacts to verified, continue pipeline |
| `APPROVE_WITH_CAVEAT` | Promote with recorded caveat, continue |
| `REJECT` | Block promotion, require repair |
| `ESCALATE` | Pause pipeline, notify human reviewer |

### Recording decisions

All human decisions are recorded to `.loop/human_decisions/` with timestamps, rationale,
and the identity of the human who made the decision.

```bash
ls .loop/human_decisions/
# gate-001_2026-07-12T14-30-00Z.json
```

---

## 10. State Recovery

The controller persists its state to `.loop/orch_state/`. If a session crashes or is
interrupted, you can resume from the last known state.

### Where state is stored

```
.loop/orch_state/
├── current_state.json     -- active workflow state
├── transitions.log        -- ordered list of state transitions
├── task_results/          -- per-task validation results
└── artifacts/             -- frozen input snapshots
```

### Resuming after restart

```bash
# 1. Check current state
python3 tools/sloop_status.py

# 2. List eligible next actions
python3 scripts/decide_next_action.py

# 3. Resume from the last checkpoint
python3 scripts/open_next_stage.py
```

### State invariants preserved across restarts

- All frozen inputs retain their SHA-256 hashes (verified on resume)
- Completed tasks are not re-executed unless their inputs changed
- Blockers persist until explicitly resolved
- The event log cursor tracks the last persisted event

### Manual recovery

If state is corrupted or the workflow was manually interrupted:

```bash
# Reset to a known state
python3 scripts/orch_controller.py check-transition --from FAILED --to RECEIVED
# Restart the workflow from the fixture
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
```

---

## 11. Adapters

Adapters are the bridge between the controller's role-based dispatch and the actual
computational work. Each role maps to an adapter class.

### Adapter registry

The default registry is at `loop_engine/orch_adapters/registry.json`. It maps role names
to adapter implementations.

### Registering a new adapter (without modifying controller core)

1. Create a new Python module in `loop_engine/orch_adapters/`:

```python
# loop_engine/orch_adapters/my_custom_executor.py
class MyCustomExecutor:
    def __init__(self, config=None):
        self.config = config or {}

    def execute(self, task_contract, inputs_dir):
        # Your custom logic here
        from loop_engine.orch_dispatcher import ControllerValidationResult
        result = ControllerValidationResult()
        result.task_id = task_contract.get("task_id")
        result.checks_expected = 1
        result.checks_executed = 1
        result.checks_passed = 1
        result.award_pass()
        return result
```

2. Add an entry to `loop_engine/orch_adapters/registry.json`:

```json
{
  "my_custom_executor": {
    "module_path": "loop_engine.orch_adapters.my_custom_executor",
    "class_name": "MyCustomExecutor",
    "description": "Custom executor for my workflow",
    "validator_scripts": [],
    "config": {}
  }
}
```

3. Register the role in `loop_engine/orch_registry.py` (add to `ROLE_REGISTRY`):

```python
"my_custom_executor": {
    "max_claim": "execution",
    "allowed_actions": ["read_inputs", "execute_transformations", "write_outputs"],
    "forbidden_actions": ["self_verify", "promote_canonical"],
    "can_verify_self": False,
    "can_repair": False,
    "requires_independent_verifier": True,
}
```

4. Use it in a workflow fixture:

```json
{
  "stage_id": "my-stage",
  "role": "my_custom_executor",
  "task_contract": { /* ... */ }
}
```

### Adapter interface contract

Every adapter must implement the method expected by its role:

| Role | Required method | Signature |
|------|----------------|-----------|
| `global_planner` | `plan` | `(request: dict) -> dict` |
| `executor` | `execute` | `(task_contract: dict, inputs_dir: str) -> ControllerValidationResult` |
| `independent_verifier` | `verify` | `(executor_artifacts_dir: str, task_contract: dict) -> ControllerValidationResult` |
| `repair_executor` | `execute` | `(task_contract: dict, inputs_dir: str) -> ControllerValidationResult` |

All methods must return a `ControllerValidationResult` (or a dict that can be
deserialized into one). Fail-closed: any exception raised by an adapter becomes a
blocking finding.

---

## 12. Integration with Codex / Claude Code

The controller is designed to be invoked from within a Codex (OpenAI Codex CLI) or
Claude Code session. The adapters use thin wrappers that translate between the
controller's interface and the LLM agent's capabilities.

### How the thin adapters work

```
Controller (Python)
    │
    ▼
Adapter (synthetic_executor.py)
    │  create subagent context
    ▼
Codex/Claude subagent (isolated session)
    │  execute task
    │  return artifact paths
    ▼
Adapter validates output → ControllerValidationResult
```

### Invoking from Codex

```bash
# In a Codex session, the orchestrator acts as a coordinator:
codex exec "python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json"
```

### Invoking from Claude Code

```bash
# The controller is invoked as a subprocess. The human-facing Claude session
# coordinates but does NOT execute the subagent logic itself.
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
```

### Subagent dispatch pattern

When a real (non-synthetic) adapter needs to do actual symbolic work, it creates a
subagent handoff:

```bash
# The handoff creates an isolated context with a frozen task contract
python3 tools/sloop_handoff.py dispatch \
    --role executor \
    --contract path/to/contract.json \
    --output-dir .loop/output/exec-1/
```

The subagent handoff schema is defined in `schemas/subagent_handoff.schema.json` and
enforces that:
- The subagent session is ephemeral (no state persists beyond the task)
- The subagent cannot read files outside its authorized input scope
- The subagent's output is validated by the controller before being promoted

### Building review packets

After a workflow completes, you can build a structured reviewer packet for human
or automated review:

```bash
python3 scripts/build_review_packet.py \
    --workflow-id synthetic-demo-001 \
    --output review_packet.json
```

This produces a packet that the `AlgebraReviewer`, `PhysicsReviewer`, and
`SoftwareReviewer` subagents can consume without access to execution internals.

---

## Reference: Full CLI Surface

```
python3 scripts/orch_controller.py --help

usage: orch_controller.py [-h] [--verbose]
  {validate-task,check-transition,list-roles,run-workflow} ...

Orchestration Controller CLI

positional arguments:
  {validate-task,check-transition,list-roles,run-workflow}
    validate-task       Validate a task contract JSON file
    check-transition    Check if a state transition is valid
    list-roles          List all registered roles
    run-workflow        Run a workflow fixture

optional arguments:
  -h, --help            show this help message and exit
  --verbose             Print extra info to stderr
```

## Reference: Key Files

| File | Purpose |
|------|---------|
| `scripts/orch_controller.py` | CLI entry point |
| `loop_engine/orch_dispatcher.py` | Dispatcher with role routing and validation |
| `loop_engine/orch_registry.py` | Role and adapter registry |
| `loop_engine/orch_adapters/registry.json` | Adapter configuration |
| `loop_engine/orch_adapters/synthetic_planner.py` | Synthetic planner adapter |
| `loop_engine/orch_adapters/synthetic_executor.py` | Synthetic executor adapter |
| `loop_engine/orch_adapters/synthetic_verifier.py` | Synthetic verifier adapter |
| `fixtures/synthetic_workflow_demo.json` | Demo workflow fixture |
| `schemas/subagent_task_contract.schema.json` | Task contract JSON schema |
| `schemas/orchestration_state.schema.json` | Orchestration state JSON schema |
| `tools/sloop_handoff.py` | Subagent handoff tool |
| `scripts/build_review_packet.py` | Review packet builder |
| `scripts/decide_next_action.py` | Next action decision engine |
| `tools/sloop_status.py` | Workflow status reporter |
