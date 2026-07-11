# report_verify — Report Verification Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `report_verify`
- **role**: `verifier` (separate from report executor)
- **parent_task**: `{PARENT_TASK_ID}` (the `report_execute` task being verified)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

### role separation mandate
- The report verifier MUST be a role **separate from the report executor**.
- The person or agent who performed `report_execute` MUST NOT perform `report_verify`.
- Executor/verifier role collapse invalidates the report verification result.

## input contract
- The `report_execute` task under verification must have completed with verdict `REPORT_COMPLETED` or `REPORT_COMPLETED_WITH_MISSING_EVIDENCE`.
- All output artifacts from the report execution must be present and SHA-consistent.
- All source artifacts referenced in the evidence map must be accessible for verification.
- The report plan and its verification must be available.

### input manifest
| artifact_path | sha256 | produced_by (task_id) | role of producer |
|---------------|--------|------------------------|------------------|
|               |        |                        |                  |

## verification gates

### gate 1: LaTeX evidence map completeness
- [ ] Every scientific claim in report.tex is traceable to a source artifact via the evidence_map.json.
- [ ] Every source reference in evidence_map.json resolves to an existing artifact with matching SHA.
- [ ] No claim in the report lacks a source reference.

### gate 2: forbidden presentation absence
- [ ] No unverified claim is presented as verified.
- [ ] No provisional claim is presented without appropriate qualification.
- [ ] No caveated claim is presented as a clean pass.
- [ ] No claim has been silently promoted in presentation status relative to its source verification.
- [ ] Human assumptions from human_gate decisions are explicitly disclosed.

### gate 3: SHA consistency
- [ ] Every SHA reference in the TeX source or evidence map resolves to an actual artifact with matching SHA.
- [ ] The output_sha_manifest.json of the report_execute task correctly lists all produced files with correct SHAs.
- [ ] The input_sha_manifest.json of the report_execute task correctly lists all consumed source artifacts.

### gate 4: canonical/candidate status correctness
- [ ] The report does not label any provisional or unverified artifact as canonical.
- [ ] If canonical artifacts are referenced, their canonical status is verified (traced back to an authorized promotion step).
- [ ] Integration-verified artifacts are presented with their correct status (canonical or verified-candidate).

### gate 5: claim boundary compliance
- [ ] The report's claim boundary section accurately reflects the claim boundaries of all source artifacts.
- [ ] No claim appears in the report that exceeds the scope of its source artifact.
- [ ] Out-of-scope or speculative content is clearly demarcated.

## allowed operations
- Reading and inspecting report artifacts (TeX, PDF, evidence_map.json, manifests).
- Tracing claim-to-source mappings.
- Checking SHA consistency.
- Checking presentation status against source verification status.
- Running the five verification gates defined above.
- Emitting one of the allowed verdicts.

## forbidden operations
- No rewriting or editing report artifacts.
- No modifying TeX source, PDF, or evidence map.
- No performing new report generation.
- No silent claim promotion or status alteration.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.

## claim boundary
- The verifier confirms or refutes that the report faithfully and completely represents its verified sources.
- The verifier does not judge the scientific correctness of the underlying claims (that belongs to `generic_verify`).
- The verifier judges only: fidelity of presentation, evidence map completeness, and status labeling accuracy.

### verification gate results
| gate | result | details |
|------|--------|---------|
| 1: evidence_map_completeness | `PASS` / `FAIL` / `CAVEAT` | |
| 2: forbidden_presentation_absence | `PASS` / `FAIL` / `CAVEAT` | |
| 3: sha_consistency | `PASS` / `FAIL` / `CAVEAT` | |
| 4: canonical_status_correctness | `PASS` / `FAIL` / `CAVEAT` | |
| 5: claim_boundary_compliance | `PASS` / `FAIL` / `CAVEAT` | |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured report verification results with gate-by-gate outcomes |
| report.md | `{TASK_ID}/report.md` | Human-readable verification report detailing each gate check |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of verification: what was checked, what was not checked |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of all inspected artifacts |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of verification operations |
| evidence_audit.json | `{TASK_ID}/evidence_audit.json` | Detailed audit of each evidence_map entry against source artifacts |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "report_verify",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "evidence_audit.json", "path": "{TASK_ID}/evidence_audit.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": []
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `VERIFIED_PASS` | All five gates pass; report faithfully represents verified sources |
| `VERIFIED_WITH_CAVEAT` | All gates pass or pass-with-caveat; identified caveats documented |
| `VERIFIED_FAIL` | One or more gates failed; report does not faithfully represent sources or contains forbidden presentation |
| `BLOCKED_ROLE_COLLAPSE` | Verifier is same role/agent as report executor |
| `BLOCKED_SOURCE_UNVERIFIABLE` | Source artifacts referenced in evidence map cannot be located or verified |
| `BLOCKED_PERMISSION` | Operation exceeds verifier role scope |
| `ERROR` | Unrecoverable error during verification |

## next task
- If `VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT`: the report is ready for publication or downstream consumption. This may be a terminal state for the pipeline, or may feed into a final human approval gate.
- If `VERIFIED_FAIL`: the report execution must be corrected and re-executed; emit specific failure directives referencing the failed gates.
- If `BLOCKED_*`: emit appropriate escalation.
