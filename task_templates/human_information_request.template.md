# human_information_request — Human Information Request Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `human_information_request`
- **role**: `planner` or `executor` (the role requesting information)
- **blocking_task**: `{BLOCKING_TASK_ID}` (the task that cannot proceed without this information)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## what is missing
- **Missing semantic**: Describe precisely what information, convention, parameter, assumption, or decision is missing.
- **Location of gap**: In which artifact, equation, or claim does the gap appear? Reference by path and SHA.
- **Symptom**: How does the gap manifest? (e.g., ambiguous notation, undefined symbol, conflicting conventions, missing boundary condition).

### missing items
| item_id | description | location (artifact_path:sha) | symptom |
|---------|-------------|------------------------------|---------|
|         |             |                              |         |

## why required
- **Blocked claims**: Enumerate the specific scientific claims, computations, or simplifications that cannot proceed without this information.
- **Downstream impact**: Which downstream tasks, verifications, or integrations are blocked?
- **Criticality**: `BLOCKING` | `NON_BLOCKING_CLARIFICATION`

### blocked claims registry
| claim_id | statement | blocked_task | consequence if unresolved |
|----------|-----------|--------------|---------------------------|
|          |           |              |                           |

## search universe
- **Where looked**: Enumerate the artifacts, documents, conventions, and sources that were searched.
- **Search query/logic**: What search strategy was used?
- **Why not inferable**: Explain why the missing information cannot be derived or inferred from available data.

### search record
| source (artifact:sha) | what was searched for | result |
|-----------------------|-----------------------|--------|
|                       |                       |        |

## absent vs not-found classification
- `ABSENT`: The information genuinely does not exist in any accessible artifact within the workspace.
- `NOT_FOUND`: The information may exist but was not locatable with available search capabilities.
- **Classification**: `{ABSENT | NOT_FOUND}`
- **Confidence in classification**: `HIGH | MEDIUM | LOW`

## exact evidence requested
- **What the human should provide**: Precise specification of the information needed.
- **Acceptable formats**: (e.g., equation in LaTeX, numeric value, boolean decision, convention declaration).
- **Example valid response**: Provide a template or example of a response that would unblock the task.

### evidence specification
| request_id | what is needed | acceptable formats | example response |
|------------|---------------|--------------------|--------------------|
|            |               |                    |                    |

## safe continuation
- **What can proceed**: Are there any sub-tasks, branches, or partial computations that can safely proceed while awaiting the human response?
- **What must wait**: Which specific operations must be paused?
- **Estimated rework risk**: If human answer changes downstream artifacts, what is the blast radius?

## forbidden operations
- No guessing or fabricating the missing information.
- No proceeding past the blocked claim without materialized human input.
- No hiding the gap or downgrading its criticality to bypass the block.
- No rewriting historical artifacts to remove the gap.
- No git write, commit, push, or tag.

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured information request record |
| report.md | `{TASK_ID}/report.md` | Human-readable request with full context for human decision-maker |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of the request: what is in question, what is established |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of searched artifacts |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped log of search and gap-analysis operations |

## next task
- The human scientist must materialize their response via a `human_gate` task.
- The `human_gate` task must reference this `human_information_request` task_id.
- The blocked task may resume only after the `human_gate` is completed and verified.
