# generic_execute — Execution Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `generic_execute`
- **role**: `executor`
- **parent_task**: `{PARENT_TASK_ID}` (must reference a verified plan task)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## input contract
- All input artifacts MUST be listed with their SHA256 hashes.
- Input artifacts must have been verified by a `generic_verify` task before consumption.
- Inputs are read-only for reference; the executor transforms according to the plan.
- Unverified artifacts MUST NOT be consumed as inputs.

### input manifest
| artifact_path | sha256 | verified_by (task_id) | approved_for_execution |
|---------------|--------|------------------------|------------------------|
|               |        |                        |                        |

## allowed operations
- Only task-authorized transformation levels, as specified in the verified plan.
- Computing symbolic tables, reports, metrics, and validation files.
- Producing output artifacts specified in the artifact contract.
- Recording provenance and traceability for every transformation step.
- Reading verified inputs and following the plan's execution directives.

## forbidden operations
- No rewriting, editing, or overwriting historical reports or artifacts.
- No consuming partial or unverified parallel-artifact outputs.
- No silent claim promotion (all output claims must remain provisional until verified).
- No git write, commit, push, or tag.
- No hiding human-decision inheritance.
- No historical overwrite.
- No execution beyond the transformation levels authorized in the verified plan.
- No mixing pre-IBP and post-IBP tables without explicit authorization.

## claim boundary
- All output claims are **provisional** until verified by a `generic_verify` task.
- Output artifacts must reference their exact input dependencies by SHA.
- No claim of canonical status is permitted at this stage.
- The executor does not judge correctness of its own output — that role belongs to the verifier.

### output claims
| claim_id | statement | derived_from_input_sha | transformation_level | scope |
|----------|-----------|------------------------|----------------------|-------|
|          |           |                        |                      |       |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured execution results, computed data, transformation records |
| report.md | `{TASK_ID}/report.md` | Human-readable execution report with methodology, steps taken, and observations |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce, with expected schemas |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Explicit boundary: what is computed, what is assumed, what is out of scope |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of every input artifact consumed |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of every output artifact produced |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of operations performed, tools invoked, and decisions taken |
| provenance.json | `{TASK_ID}/provenance.json` | Traceable record mapping every output claim to its input chain and transformation steps |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "generic_execute",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "provenance.json", "path": "{TASK_ID}/provenance.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["generic_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `EXECUTE_COMPLETED` | All transformations completed successfully; outputs ready for verification |
| `EXECUTE_COMPLETED_WITH_WARNINGS` | Execution completed but with non-blocking warnings or caveats |
| `BLOCKED_INPUT_UNAVAILABLE` | Required verified input not found or SHA mismatch |
| `BLOCKED_TRANSFORMATION_LIMIT` | Execution would exceed authorized transformation level |
| `BLOCKED_PERMISSION` | Operation exceeds executor role scope |
| `ERROR` | Unrecoverable error during execution |

## next task
- If `EXECUTE_COMPLETED` or `EXECUTE_COMPLETED_WITH_WARNINGS`: next task is `generic_verify` (performed by a separate verifier role).
- The executor must NOT self-verify. Role separation between executor and verifier is mandatory.
- If `BLOCKED_*`: emit appropriate escalation (human_information_request or plan amendment).
