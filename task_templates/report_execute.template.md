# report_execute — Report Execution Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `report_execute`
- **role**: `executor`
- **parent_task**: `{PARENT_TASK_ID}` (must reference a verified `report_plan` task)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## input contract
- The report plan (from `report_plan`) MUST be verified before execution.
- All source artifacts referenced in the plan must be present and SHA-consistent.
- The executor must have access to all source artifacts listed in the traceability plan.
- No unverified or ineligible sources may be included.

### input manifest
| artifact_path | sha256 | type | verified_by (task_id) | report_section |
|---------------|--------|------|------------------------|----------------|
|               |        |      |                        |                |

### pre-execution gate checklist
- [ ] Report plan is verified (`VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT`).
- [ ] All planned source artifacts are present and SHA-consistent.
- [ ] All planned source artifacts have valid verification status.
- [ ] Traceability plan mappings are complete and unambiguous.

## allowed operations
- Writing TeX/LaTeX source files according to the verified report plan.
- Generating PDF output from the TeX source.
- Producing the evidence mapping document (mapping each report element to its source artifact by SHA).
- Producing the claim boundary section of the report.
- Including traceability markers in the TeX source (e.g., comments referencing source SHA).
- Producing output artifacts specified in the artifact contract.

## forbidden operations
- **NO promoting scientific status through reporting.** Presenting a claim in a report does NOT make it verified or canonical. The report must faithfully reflect the verification status of each claim.
- No modifying source artifacts or their claims during report generation.
- No including unverified or ineligible sources.
- No rewriting historical reports or artifacts.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.
- No altering claim wording to imply higher confidence or verification status than the source artifact supports.

### presentation integrity rules
1. Verified claims must be labeled as verified with reference to the verifying task.
2. Provisional claims must be labeled as provisional.
3. Assumptions from human_gate decisions must be explicitly stated.
4. Known caveats (`VERIFIED_WITH_CAVEAT`) must be documented in the report.
5. Forbidden presentation: no assertion of correctness without citation of verification evidence.

## claim boundary
- The report presents claims from source artifacts; it does not create new claims.
- Any synthesis, interpretation, or narrative framing that goes beyond literal source claims must be explicitly marked as such and flagged for verification.
- The report's claim boundary section must enumerate the verification status of every presented claim.

### report claim inventory
| claim_id | source_artifact:sha | source_verification_status | report_presentation_status |
|----------|---------------------|---------------------------|----------------------------|
|          |                     |                           |                            |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured report generation results, list of produced files |
| report.md | `{TASK_ID}/report.md` | Human-readable summary of report generation and caveats |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Status of every claim presented in the report |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of all source artifacts used |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of all produced files (TeX, PDF, evidence map, etc.) |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of report generation operations |
| report.tex | `{TASK_ID}/report.tex` | Traceable LaTeX source with SHA references in comments |
| report.pdf | `{TASK_ID}/report.pdf` | Generated PDF report |
| evidence_map.json | `{TASK_ID}/evidence_map.json` | Mapping from every report section/claim to its verified source artifact (by SHA) |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "report_execute",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "report.tex", "path": "{TASK_ID}/report.tex", "required": true},
    {"name": "report.pdf", "path": "{TASK_ID}/report.pdf", "required": true},
    {"name": "evidence_map.json", "path": "{TASK_ID}/evidence_map.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["report_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `REPORT_COMPLETED` | Report successfully generated; TeX and PDF produced; evidence map complete |
| `REPORT_COMPLETED_WITH_MISSING_EVIDENCE` | Report generated but some source-to-claim evidence mappings are incomplete |
| `BLOCKED_UNVERIFIED_PLAN` | The report plan has not been verified |
| `BLOCKED_SOURCE_UNAVAILABLE` | A required source artifact from the plan is missing or SHA-mismatched |
| `BLOCKED_PERMISSION` | Operation exceeds executor role scope |
| `ERROR` | Unrecoverable error during report generation |

## next task
- If `REPORT_COMPLETED` or `REPORT_COMPLETED_WITH_MISSING_EVIDENCE`: next task is `report_verify` (separate verifier role).
- The report executor MUST NOT self-verify.
- If `BLOCKED_*`: emit appropriate escalation.
