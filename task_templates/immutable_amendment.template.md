# immutable_amendment — Immutable Amendment Task Template

## task identity
- **task_id**: `{TASK_ID}` (MUST be a NEW task ID — never reuse an existing one)
- **task_type**: `immutable_amendment`
- **role**: `planner` or `executor` (the role initiating the amendment)
- **original_task**: `{ORIGINAL_TASK_ID}` (the historical task being amended)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

### immutability mandate
- **The original task and its artifacts MUST NOT be modified, overwritten, or deleted.**
- The amendment is a NEW task that references the original.
- The original task's artifacts remain in place as the rejected historical record.
- Downstream consumers must be able to trace the amendment chain to understand what changed and why.

## amendment reason
- **Why is the amendment necessary?** Provide a detailed explanation of what was wrong, incomplete, or superseded in the original task.
- **What triggered the amendment?** (e.g., verification failure, human decision reversal, new evidence, discovered error).
- **Impact assessment**: What downstream artifacts or claims are affected by this amendment?

### reason record
| aspect | original | amended | justification |
|--------|----------|---------|---------------|
|        |          |         |               |

## original task reference
- **original_task_id**: `{ORIGINAL_TASK_ID}`
- **original_task_type**: `{ORIGINAL_TASK_TYPE}`
- **original_verdict**: `{ORIGINAL_VERDICT}`
- **original_output_sha**: SHA256 of the original task's output directory (to verify it has not been tampered with)
- **original_artifacts_path**: Path to the preserved original artifacts

### preserved original artifacts
| artifact_path | sha256 | preserved_as |
|---------------|--------|--------------|
|               |        |              |

## what is being amended
- **Scope of amendment**: Which specific claims, computations, or artifacts are being amended?
- **What is preserved**: Which parts of the original task remain valid and are carried forward?
- **What is replaced**: Which parts are superseded by this amendment?

### amendment scope
| original_element | amendment_action | reason |
|------------------|------------------|--------|
|                  |                  |        |

### preserved elements
| original_element | carried_forward_to | unchanged |
|------------------|--------------------|------------|
|                  |                    |            |

## new output
The amendment produces NEW artifacts (never overwriting the original). 
These artifacts may incorporate preserved elements from the original alongside amended elements.

### new artifact mapping
| original_artifact | new_artifact | relationship |
|--------------------|--------------|--------------|
|                    |              |              |

## rejected history
- The original task's output is **rejected** for the purposes specified in the amendment reason.
- The original output remains **preserved** in the workspace as immutable history.
- The rejection is recorded in this amendment so that downstream consumers know to use the amended version.
- A `rejection_record.json` is produced documenting what was rejected and why.

### rejection record
| rejected_task_id | rejection_reason | effective_date | superseded_by |
|------------------|------------------|----------------|---------------|
|                  |                  |                |               |

## forbidden operations
- **NO overwriting, modifying, or deleting the original task's artifacts.**
- **NO reusing the original task_id.** A new task_id is mandatory.
- **NO silent replacement** — the amendment must explicitly reference the original task.
- **NO hiding the rejection** — the rejection_record.json must be discoverable.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag (unless explicitly authorized for amendment archiving).

## claim boundary
- The amendment's claims supersede the original claims within the scope of the amendment.
- Preserved elements from the original are explicitly re-certified (not silently inherited).
- New claims introduced by the amendment must be verified through the standard pipeline (`generic_verify`).

### amended claims
| claim_id | statement | relationship_to_original | verification_status |
|----------|-----------|--------------------------|---------------------|
|          |           |                          |                     |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured amendment record with amended results |
| report.md | `{TASK_ID}/report.md` | Human-readable amendment report explaining changes and rationale |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Boundary of amended claims, preserved elements, and new claims |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of original artifacts and any other inputs consulted |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of amendment operations |
| rejection_record.json | `{TASK_ID}/rejection_record.json` | Formal record of what was rejected from the original and why |
| amendment_provenance.json | `{TASK_ID}/amendment_provenance.json` | Full provenance chain: original → amendment mapping |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "immutable_amendment",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "rejection_record.json", "path": "{TASK_ID}/rejection_record.json", "required": true},
    {"name": "amendment_provenance.json", "path": "{TASK_ID}/amendment_provenance.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["generic_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `AMENDMENT_COMPLETED` | Amendment successfully produced; original preserved; new artifacts ready for verification |
| `AMENDMENT_COMPLETED_WITH_WARNINGS` | Amendment produced with documented caveats or partial preservation |
| `BLOCKED_ORIGINAL_UNVERIFIABLE` | Original task artifacts missing, corrupted, or SHA-inconsistent |
| `BLOCKED_IMMUTABILITY_VIOLATION` | Amendment attempted to overwrite original artifacts |
| `BLOCKED_PERMISSION` | Operation exceeds role scope |
| `ERROR` | Unrecoverable error during amendment |

## next task
- If `AMENDMENT_COMPLETED` or `AMENDMENT_COMPLETED_WITH_WARNINGS`: the amended artifacts must pass through the standard verification pipeline (`generic_verify`). A `generic_plan` may be needed to update the overall pipeline plan.
- The amendment is not valid until verified.
- Downstream tasks that consumed the original may need re-execution with the amended version — this is determined during verification.
