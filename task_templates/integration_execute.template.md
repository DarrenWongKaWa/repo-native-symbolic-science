# integration_execute — Integration Execution Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `integration_execute`
- **role**: `integrator`
- **parent_tasks**: `[{PARENT_TASK_ID_1}, {PARENT_TASK_ID_2}, ...]` (list of verified tasks whose outputs are being integrated)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## input contract
- **ALL inputs MUST be verified before consumption.**
- Each input must have a valid `VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT` verdict from a `generic_verify` task.
- Inputs with `VERIFIED_FAIL` MUST NOT be consumed.
- Inputs with `VERIFIED_WITH_CAVEAT` may be consumed only if the caveats are explicitly documented and do not interact destructively with other inputs.
- The integrator MUST check SHA consistency of all inputs against their verification manifests.
- Unverified or partially-verified artifacts are blocked.

### input manifest
| artifact_path | sha256 | verified_by (task_id) | verification_verdict | caveats |
|---------------|--------|------------------------|----------------------|---------|
|               |        |                        |                      |         |

### verification gate checklist
- [ ] Each input has been verified by a `generic_verify` task (separate from its executor).
- [ ] Each input's SHA matches the manifest from its verification task.
- [ ] No input has verdict `VERIFIED_FAIL`.
- [ ] Caveats from `VERIFIED_WITH_CAVEAT` inputs are recorded and their interaction assessed.

## allowed operations
- Combining verified artifacts into a unified result.
- Resolving cross-artifact references and conventions.
- Producing integrated output artifacts (result.json, report.md, etc.).
- Recording provenance for combined outputs (mapping integrated claims to their source artifacts).
- Freezing integration checkpoints (without promoting to canonical status).

## forbidden operations
- No consuming unverified or partially-verified inputs.
- No silent claim promotion — integrated outputs remain provisional until verified by `integration_verify`.
- No rewriting historical reports or source artifacts.
- No consuming partial parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.
- No substituting missing inputs with assumptions.

## claim boundary
- Integrated claims combine claims from source artifacts but do not assert correctness beyond the union.
- No new scientific claims beyond those verified in the source artifacts (unless explicitly noted as new and flagged for verification).
- All integrated claims remain provisional until verified by `integration_verify`.

### integrated claims
| claim_id | statement | source_claims (claim_ids) | source_artifacts (sha) | integration_operation |
|----------|-----------|---------------------------|------------------------|-----------------------|
|          |           |                           |                        |                       |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured integration results with merged data, cross-references, and unified tables |
| report.md | `{TASK_ID}/report.md` | Human-readable integration report documenting how artifacts were combined |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Boundary for integrated claims: what is unified, what remains separate |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of every input artifact consumed, with verification references |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of every output artifact produced |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of integration operations |
| integration_provenance.json | `{TASK_ID}/integration_provenance.json` | Traceable mapping of each integrated output to its verified source inputs |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "integration_execute",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "integration_provenance.json", "path": "{TASK_ID}/integration_provenance.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["integration_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `INTEGRATE_COMPLETED` | All verified inputs successfully integrated; outputs ready for integration verification |
| `INTEGRATE_COMPLETED_WITH_WARNINGS` | Integration completed with documented warnings or unresolved cross-artifact issues |
| `BLOCKED_UNVERIFIED_INPUT` | One or more inputs lack a `VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT` verdict |
| `BLOCKED_SHA_MISMATCH` | Input SHA does not match the manifest from its verification task |
| `BLOCKED_CONFLICTING_INPUTS` | Verified inputs contain irreconcilable conflicts |
| `BLOCKED_PERMISSION` | Operation exceeds integrator role scope |
| `ERROR` | Unrecoverable error during integration |

## next task
- If `INTEGRATE_COMPLETED` or `INTEGRATE_COMPLETED_WITH_WARNINGS`: next task is `integration_verify` (separate verifier role).
- The integrator MUST NOT self-verify. Role separation from `integration_verify` is mandatory.
- If `BLOCKED_*`: emit appropriate escalation.
