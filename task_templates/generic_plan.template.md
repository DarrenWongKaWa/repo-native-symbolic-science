# generic_plan — Planning Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `generic_plan`
- **role**: `planner`
- **parent_task**: `{PARENT_TASK_ID}` (may be null for root tasks)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## input contract
- All input artifacts MUST be listed with their SHA256 hashes.
- Input artifacts may include:
  - verified checkpoints from prior tasks
  - materialized human decisions (from `human_gate`)
  - raw provenance tables
  - convention maps
- Inputs are read-only. No transformation of inputs is permitted.

### input manifest
| artifact_path | sha256 | verified_by | ingested_at |
|---------------|--------|-------------|-------------|
|               |        |             |             |

## allowed operations
- Reading and inspecting input artifacts.
- Searching the workspace for relevant prior artifacts.
- Producing a structured plan (result.json, report.md).
- Declaring claim boundaries scoped to this planning task.
- Requesting human information via `human_information_request` if upstream semantics are missing.
- Proposing next task directives.

## forbidden operations
- No execution of transformations, simplifications, or computations beyond planning.
- No git write, commit, push, or tag.
- No rewriting, editing, or overwriting historical reports or artifacts.
- No consuming partial or unverified parallel-artifact outputs.
- No silent claim promotion (provisional claims must be explicitly marked).
- No hiding human-decision inheritance (all human inputs must be traceable).
- No historical overwrite.

## claim boundary
- This task produces **role-scoped provisional records only**.
- All claims are provisional until verified by a `generic_verify` task.
- Claims must reference the exact input artifacts (by SHA) they derive from.
- No claim may assert canonical status.

### provisional claims
| claim_id | statement | derived_from_sha | scope |
|----------|-----------|------------------|-------|
|          |           |                  |       |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured plan with task decomposition, dependency graph, next-task directives |
| report.md | `{TASK_ID}/report.md` | Human-readable planning report with rationale and decisions |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce, with expected schemas |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Explicit boundary: what is claimed, what is assumed, what is out of scope |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of every input artifact consumed |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of every output artifact produced |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of operations performed, tools invoked, and decisions taken |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "generic_plan",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["generic_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `PLAN_COMPLETED` | Plan successfully produced; ready for verification |
| `PLAN_COMPLETED_WITH_GAPS` | Plan produced but with known missing dependencies or unresolved semantics |
| `BLOCKED_INPUT_MISSING` | Required input artifact not found or unverifiable |
| `BLOCKED_AMBIGUOUS_UPSTREAM` | Upstream artifacts contain contradictions or ambiguous semantics requiring human resolution |
| `BLOCKED_PERMISSION` | Operation exceeds planner role scope |
| `ERROR` | Unrecoverable error during planning |

## next task
- If `PLAN_COMPLETED` or `PLAN_COMPLETED_WITH_GAPS`: structure the plan's result.json to reference the next task type (typically `generic_verify` to verify the plan, then `generic_execute` for execution).
- If `BLOCKED_*`: emit a `human_information_request` task template identifying the blocker.
- The next task directive must be explicit in result.json under `next_task`.
