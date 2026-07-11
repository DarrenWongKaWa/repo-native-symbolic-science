# human_gate — Human Gate Task Template

## task identity
- **task_id**: `{TASK_ID}`
- **task_type**: `human_gate`
- **role**: `human_scientist`
- **request_task**: `{INFORMATION_REQUEST_TASK_ID}` (references the `human_information_request` this responds to)
- **created**: `{ISO_TIMESTAMP}`
- **human_owner**: `{HUMAN_IDENTIFIER}`

## response mandate
- The human response MUST be **exact and materialized** (not chat-only, not ephemeral).
- The response is recorded in this artifact as the authoritative record of the human decision.
- Vague or ambiguous responses are rejected; the gate remains open until an exact response is materialized.

## gate identity
- **gate_id**: `{GATE_ID}`
- **gate_label**: Human-readable label for this decision point.
- **question_answered**: Restatement of the exact question from the `human_information_request`.

## decision
- **Decision**: `ACCEPT` | `REJECT` | `DEFER`
- If `ACCEPT`: the human provides the requested information, convention, or assumption.
- If `REJECT`: the human rejects the proposed interpretation; must provide an alternative or instruct a different approach.
- If `DEFER`: the human defers the decision; must specify conditions for re-evaluation or a future gate trigger.

### decision record
| request_id | decision | provided_value | format |
|------------|----------|---------------|--------|
|            |          |               |        |

## reasoning
- **Rationale**: The human's reasoning for the decision.
- **Evidence considered**: What sources, prior work, physical principles, or conventions informed the decision.
- **Alternatives considered and rejected**: Were there other plausible answers? Why were they rejected?

### evidence considered
| source | relevance | weight |
|--------|-----------|--------|
|        |           |        |

## new assumptions or restrictions
- **New assumptions**: Any new assumptions introduced by this decision.
- **New restrictions**: Any new restrictions or bounds introduced.
- **Scope of applicability**: Under what conditions does this decision hold? When would it need revisiting?

### assumptions registry
| assumption_id | statement | scope | revisitation_trigger |
|---------------|-----------|-------|----------------------|
|               |           |       |                      |

## forbidden operations
- The human may not provide a non-materialized response (e.g., verbal or chat-only without artifact recording).
- The human may not leave the gate open with an ambiguous response.
- No rewriting or editing of prior human_gate records.
- No historical overwrite of prior decisions.

## artifact contract
This task MUST produce all of the following output artifacts:

| artifact | path | description |
|----------|------|-------------|
| result.json | `{TASK_ID}/result.json` | Structured human decision record |
| report.md | `{TASK_ID}/report.md` | Human-readable summary of the decision and its rationale |
| artifact_contract.json | `{TASK_ID}/artifact_contract.json` | Declares which artifacts this task commits to produce |
| claim_boundary.json | `{TASK_ID}/claim_boundary.json` | Scope of the decision and new assumptions introduced |
| input_sha_manifest.json | `{TASK_ID}/input_sha_manifest.json` | SHA256 digest of all inputs considered (including the information request) |
| output_sha_manifest.json | `{TASK_ID}/output_sha_manifest.json` | SHA256 digest of output artifacts |
| runtime_log.json | `{TASK_ID}/runtime_log.json` | Timestamped record of the decision process |

## next task
- The blocked task that issued the `human_information_request` may now resume.
- A `generic_verify` task should verify that the human_gate response is consistent with the information request before resumption.
- If the human response introduces new assumptions, a `generic_plan` task should update the plan accordingly.
