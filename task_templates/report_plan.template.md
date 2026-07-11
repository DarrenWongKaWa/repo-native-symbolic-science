# report_plan — Report Planning Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `report_plan`
- **role**: `planner`
- **parent_tasks**: `[{PARENT_TASK_ID_1}, ...]` (tasks whose outputs will be included in the report)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## input contract

### eligible sources
Only artifacts meeting ALL of the following criteria may be considered for inclusion in the report:

1. **Verified artifacts**: Outputs of `generic_execute` or `integration_execute` tasks that have received `VERIFIED_PASS` or `VERIFIED_WITH_CAVEAT` from a corresponding `generic_verify` or `integration_verify` task.
2. **Materialized human decisions**: Completed `human_gate` artifacts that have been verified as consistent with their corresponding `human_information_request`.
3. **Integration-verified canonical state**: Artifacts that have been verified by `integration_verify` and (if applicable) approved for canonical status via a `human_gate`.

Artifacts that are NOT eligible:
- Unverified execution outputs.
- Rejected or deferred human decisions.
- Provisional claims that have not passed verification.
- Partial parallel-artifact outputs.

### source manifest
| artifact_path | sha256 | type | verified_by | canonical_status |
|---------------|--------|------|-------------|------------------|
|               |        |      |             |                  |

### traceability audit plan
The report plan MUST include a traceability audit plan specifying:
- How each scientific claim in the report will be mapped to its source artifact (by SHA).
- How evidence tables will reference verified provenance chains.
- How the report will distinguish between verified and provisional claims.
- How claim boundaries from source tasks will be reflected in the report.

## allowed operations
- Reading and inspecting eligible source artifacts.
- Designing the report structure, section outline, and evidence map.
- Planning TeX/LaTeX template and macro definitions.
- Planning figure and table placement strategy.
- Defining the claim boundary section for the report.
- Planning the traceability audit structure.
- Proposing next task directives (typically `report_execute`).

## forbidden operations
- No writing or executing TeX/LaTeX (that belongs to `report_execute`).
- No including unverified or ineligible sources in the report plan.
- No silent claim promotion through reporting.
- No rewriting historical reports or artifacts.
- No consuming partial or unverified parallel-artifact outputs.
- No hiding human-decision inheritance.
- No historical overwrite.
- No git write, commit, push, or tag.

## claim boundary
- The report plan specifies HOW claims will be presented, not WHAT the claims are (the source artifacts define the claims).
- The plan must declare which claims will appear as verified vs. provisional vs. assumed.
- The plan must declare any narrative framing or synthesis that goes beyond literal source claims — such framing must be flagged for verification.

### report claim classification plan
| claim_id | source_artifact:sha | presentation_status | narrative_framing |
|----------|---------------------|---------------------|-------------------|
|          |                     |                     |                   |

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured report plan with section outline, evidence map, and figure/table schedule |
| report.md | `{TASK_ID}/report.md` | Human-readable report plan describing structure, audience, and design decisions |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of the report: what is covered, what is excluded, status of each claim |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of all source artifacts considered |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of planning operations |
| traceability_plan.json | `{TASK_ID}/traceability_plan.json` | Plan for mapping every report element back to verified source artifacts |

### artifact_contract.json schema
```json
{
  "task_id": "{TASK_ID}",
  "task_type": "report_plan",
  "committed_artifacts": [
    {"name": "result.json", "path": "{TASK_ID}/result.json", "required": true},
    {"name": "report.md", "path": "{TASK_ID}/report.md", "required": true},
    {"name": "artifact_contract.json", "path": "{TASK_ID}/artifact_contract.json", "required": true},
    {"name": "claim_boundary.json", "path": "{TASK_ID}/claim_boundary.json", "required": true},
    {"name": "input_sha_manifest.json", "path": "{TASK_ID}/input_sha_manifest.json", "required": true},
    {"name": "output_sha_manifest.json", "path": "{TASK_ID}/output_sha_manifest.json", "required": true},
    {"name": "runtime_log.json", "path": "{TASK_ID}/runtime_log.json", "required": true},
    {"name": "traceability_plan.json", "path": "{TASK_ID}/traceability_plan.json", "required": true}
  ],
  "input_dependencies": [],
  "verification_required_by": ["generic_verify", "report_verify"]
}
```

## verdict family

| verdict | description |
|---------|-------------|
| `PLAN_COMPLETED` | Report plan successfully produced; ready for verification and execution |
| `PLAN_COMPLETED_WITH_GAPS` | Report plan produced but with incomplete source coverage or pending human decisions |
| `BLOCKED_INSUFFICIENT_SOURCES` | Too few verified sources to produce a meaningful report plan |
| `BLOCKED_UNVERIFIED_SOURCES` | Required sources are not yet verified |
| `BLOCKED_PERMISSION` | Operation exceeds planner role scope |
| `ERROR` | Unrecoverable error during report planning |

## next task
- If `PLAN_COMPLETED` or `PLAN_COMPLETED_WITH_GAPS`: next task is `report_execute` to materialize the plan into TeX/LaTeX and PDF.
- The plan should be verified by `generic_verify` before execution.
- If `BLOCKED_*`: emit appropriate escalation.
