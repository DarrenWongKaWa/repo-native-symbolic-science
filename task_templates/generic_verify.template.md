# generic_verify — Verification Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `generic_verify`
- **role**: `verifier`
- **parent_task**: `{PARENT_TASK_ID}` (must reference a completed execute or plan task)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

### role separation mandate
- The verifier MUST be a role **separate from the executor** of the task being verified.
- If the same agent performed the execution, a different agent instance MUST perform verification.
- Executor/verifier role collapse invalidates the verification result.

## input contract
- The task under verification (parent_task) must have completed with verdict `EXECUTE_COMPLETED`, `EXECUTE_COMPLETED_WITH_WARNINGS`, `PLAN_COMPLETED`, or `PLAN_COMPLETED_WITH_GAPS`.
- All output artifacts from the parent task MUST be present and SHA-consistent.
- The verifier MUST have access to all upstream artifacts in the parent's dependency chain.
- Inputs are read-only.

### input manifest
| artifact_path | sha256 | produced_by (task_id) | role of producer |
|---------------|--------|------------------------|------------------|
|               |        |                        |                  |

## allowed operations
- Reading and inspecting the parent task's output artifacts and their dependency chain.
- Checking exact identities (e.g., `old - new` or `old - new - dF` validation).
- Checking for regressions against prior verified checkpoints.
- Checking row counts, table consistency, and data integrity.
- Running benchmark gates (including protected projection benchmarks).
- Checking SHA conformity between input_sha_manifest.json and output_sha_manifest.json.
- Checking that claim boundaries are respected.
- Checking that forbidden operations were not performed.
- Emitting one of the allowed verdicts.

## forbidden operations
- No rewriting, editing, or overwriting historical reports or artifacts (including the task under verification).
- No performing transformations or computations that belong to the executor role.
- No silent claim promotion.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.
- The verifier MUST NOT modify the artifacts under verification.

## claim boundary
- The verifier does not create new scientific claims.
- The verifier may confirm that claims made in the parent task are supported by evidence.
- The verifier may identify unsupported claims, boundary violations, or missing evidence.
- The verifier may recommend canonical status promotion but cannot authorize it.
- The verifier's own output (verdict) is scoped to the verification task itself.

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured verification results, verdict, and evidence for each gate checked |
| report.md | `{TASK_ID}/report.md` | Human-readable verification report detailing each check and its outcome |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of verification: what was checked, what was not checked, assumptions |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of every artifact inspected during verification |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of every output artifact produced |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of verification steps and checks performed |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "generic_verify",
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
  "verification_required_by": []
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `VERIFIED_PASS` | All checks passed; parent task's outputs and claims are fully verified |
| `VERIFIED_WITH_CAVEAT` | Checks passed with identified caveats that do not invalidate the core claims |
| `VERIFIED_FAIL` | One or more checks failed; parent task's outputs or claims are not verified |
| `BLOCKED_INPUT_UNVERIFIABLE` | Required input artifacts missing, corrupted, or SHA-inconsistent |
| `BLOCKED_ROLE_COLLAPSE` | Verifier is same role/agent as executor; verification invalid |
| `BLOCKED_PERMISSION` | Operation exceeds verifier role scope |
| `ERROR` | Unrecoverable error during verification |

## next task
- If `VERIFIED_PASS`: the verified artifacts may be consumed by downstream tasks. Next task is typically `integration_execute` or `report_plan`, depending on pipeline stage.
- If `VERIFIED_WITH_CAVEAT`: downstream consumption permitted with caveat documentation; next task directive must reference the caveats.
- If `VERIFIED_FAIL`: the parent task must be re-planned or re-executed; emit an appropriate blocker or issue directive.
- If `BLOCKED_*`: emit appropriate escalation.
