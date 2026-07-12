# Human Gate Resume

## Gate Identity
- **Gate ID**: `{{GATE_ID}}`
- **Orchestration ID**: `{{ORCHESTRATION_ID}}`
- **Triggered by Task**: `{{TRIGGERING_TASK_ID}}`
- **Decision Type**: `{{DECISION_TYPE}}`

## Question for the Human Scientist

{{QUESTION}}

## Context

The following frozen artifacts provide context for this decision:

| Path | SHA-256 |
|------|---------|
{{#each KNOWN_CONTEXT}}
| `{{path}}` | `{{sha256}}` |
{{/each}}

## Allowed Responses

{{#each ALLOWED_RESPONSES}}
- `{{this}}`
{{/each}}

Default response (if no decision within timeout): `{{DEFAULT_RESPONSE}}`

## Blocked Tasks

The following tasks are blocked until this gate is resolved:

{{#each BLOCKED_TASK_IDS}}
- `{{this}}`
{{/each}}

## Decision Types Reference

| Type | Meaning |
|------|---------|
| `missing_definition` | A scientific definition is missing and must be provided |
| `index_role` | The role of an index is ambiguous |
| `assumption` | A new assumption is needed |
| `symmetry` | A symmetry assumption must be explicitly authorized |
| `boundary_condition` | Boundary conditions need specification |
| `integration_by_parts` | Integration by parts must be authorized |
| `boundary_term_removal` | Removal of boundary terms must be authorized |
| `limit_ordering` | Ordering of limits must be specified |
| `transformation_level_promotion` | Promotion of a transformation result needs authorization |
| `canonical_promotion` | Promotion to canonical state requires human gate |
| `publication_claim` | Any publication-level claim requires human gate |
| `software_or_environment_mutation` | Environment changes require permission |

## Decision Recording

Your decision will be recorded in:
- **Decision artifact**: `{{DECISION_ARTIFACT_PATH}}`
- **Human decision registry**: `{{HUMAN_DECISION_REGISTRY_PATH}}`

## Instructions for the Human

1. Review the context artifacts listed above
2. Consider the question carefully
3. Provide your decision as one of the allowed responses
4. Optionally provide a rationale

## Resumption

After your decision is recorded and frozen:

1. The controller will validate the decision artifact
2. The human gate will be marked FROZEN
3. Blocked dependency gates will be re-evaluated
4. Eligible tasks will be resumed

No blocked task resumes until a valid repository-native human decision artifact is frozen.
