# integration_verify — Integration Verification Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `integration_verify`
- **role**: `verifier` (separate from integrator)
- **parent_task**: `{PARENT_TASK_ID}` (the `integration_execute` task being verified)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

### role separation mandate
- The integration verifier MUST be a role **separate from the integration executor**.
- The person or agent who performed `integration_execute` MUST NOT perform `integration_verify`.
- Executor/verifier role collapse invalidates the integration verification result.

## input contract
- The `integration_execute` task under verification must have completed with verdict `INTEGRATE_COMPLETED` or `INTEGRATE_COMPLETED_WITH_WARNINGS`.
- All output artifacts from the integration task must be present and SHA-consistent.
- The verifier MUST trace each integrated claim back to a verified source artifact (recursive verification chain).
- All source artifacts in the integration's input manifest must themselves be verified.

### input manifest
| artifact_path | sha256 | produced_by (task_id) | role of producer | upstream_verified |
|---------------|--------|------------------------|------------------|-------------------|
|               |        |                        |                  |                   |

### recursive verification checklist
- [ ] Each integrated claim traces to a source claim in a verified artifact.
- [ ] No source artifact in the chain has an unresolved `VERIFIED_FAIL` status.
- [ ] Integration operations (merge, union, cross-reference) are logically valid given the source claims.
- [ ] No claims have been silently promoted during integration.

## allowed operations
- Reading and inspecting integration output artifacts.
- Tracing claim provenance back through the verification chain.
- Checking SHA consistency across all manifests.
- Checking integration operations for logical validity.
- Running cross-artifact consistency checks.
- Emitting one of the allowed verdicts.
- Recommending canonical status promotion (but not authorizing it).

## forbidden operations
- No rewriting, editing, or overwriting integration artifacts or source artifacts.
- No performing new integrations or transformations (verifier is not integrator).
- No silent claim promotion.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.

## claim boundary
- The verifier confirms or refutes that integrated claims are supported by their verified source chain.
- The verifier may recommend promotion of verified integrated artifacts to canonical status, but **cannot authorize it** — canonical promotion requires a separate human_gate or authorized process.
- The verifier does not create new scientific claims.

### recommendation
| recommendation | target_artifact | rationale |
|----------------|-----------------|-----------|
|                |                 |           |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured integration verification results |
| report.md | `{TASK_ID}/report.md` | Human-readable verification report with traceability audit |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of verification: what was checked, what was not checked |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of all artifacts inspected |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of verification operations |
| traceability_audit.json | `{TASK_ID}/traceability_audit.json` | Full trace from each integrated claim back to its original verified source |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "integration_verify",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "traceability_audit.json", "path": "{TASK_ID}/traceability_audit.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": []
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `VERIFIED_PASS` | Integration fully verified; all claims trace to verified sources; cross-artifact consistency confirmed |
| `VERIFIED_WITH_CAVEAT` | Integration verified with documented caveats (e.g., one source had `VERIFIED_WITH_CAVEAT`) |
| `VERIFIED_FAIL` | Integration verification failed; broken provenance, inconsistent claims, or unverified source |
| `BLOCKED_ROLE_COLLAPSE` | Verifier is same role/agent as integration executor |
| `BLOCKED_SOURCE_UNVERIFIED` | One or more source artifacts in the integration chain are unverified |
| `BLOCKED_PERMISSION` | Operation exceeds verifier role scope |
| `ERROR` | Unrecoverable error during verification |

## next task
- If `VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT`: the integrated artifacts may be recommended for canonical promotion. Next task may be `report_plan` (for report generation) or a human_gate for canonical approval.
- If `VERIFIED_FAIL`: the integration must be re-executed; emit a blocking directive.
- Canonical promotion requires a separate authorization step (human_gate or pipeline-defined process).
