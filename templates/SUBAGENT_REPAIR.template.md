# Subagent Repair Task

## Task Identity
- **Task ID**: `{{TASK_ID}}` (NEW task ID — not the original)
- **Role**: `repair_executor`
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`
- **Original Task ID**: `{{ORIGINAL_TASK_ID}}` (the REJECTED task)
- **Verifier Task ID**: `{{VERIFIER_TASK_ID}}` (the verifier that rejected)

## Repair Lineage

```
{{ORIGINAL_TASK_ID}} → REJECTED → {{TASK_ID}} (this repair)
```

Historical rejected artifacts from `{{ORIGINAL_TASK_ID}}` are preserved and immutable.

## Objective

Repair the rejected artifacts from task `{{ORIGINAL_TASK_ID}}` based on verifier evidence from `{{VERIFIER_TASK_ID}}`.

## Authorized Inputs (Read-Only)

| Path | SHA-256 | Purpose |
|------|---------|---------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` | {{description}} |
{{/each}}

- **Original executor artifacts**: `{{ORIGINAL_OUTPUT_DIRECTORY}}/` (read-only, preserved)
- **Verifier rejection evidence**: `{{VERIFIER_OUTPUT_DIRECTORY}}/verifier_result_envelope.json`

## Required Outputs

| Path | Description |
|------|-------------|
{{#each REQUIRED_OUTPUTS}}
| `{{this}}` | |
{{/each}}

All outputs must be written to: `{{OUTPUT_DIRECTORY}}/` (a NEW directory, separate from the original)

## Rejection Summary

The verifier rejected the original execution for these reasons:

{{#each REJECTION_REASONS}}
- {{this}}
{{/each}}

## Repair Instructions

{{REPAIR_INSTRUCTIONS}}

## Allowed Actions

{{#each ALLOWED_ACTIONS}}
- {{this}}
{{/each}}

## Forbidden Actions

{{#each FORBIDDEN_ACTIONS}}
- {{this}}
{{/each}}

- Do NOT modify the original rejected artifacts
- Do NOT reuse the original executor's subagent identifier
- Do NOT claim the original rejection was invalid

## Write Protocol

Same as executor: write to temporary paths, validate, atomically promote, generate SHA manifest.

## Validation

```
{{#each VALIDATION_COMMANDS}}
{{this}}
{{/each}}
```

## Result Envelope

Produce `{{OUTPUT_DIRECTORY}}/result_envelope.json` conforming to `schemas/subagent_result_envelope.schema.json`.

## Timeout

Maximum time: `{{TIMEOUT_SECONDS}}` seconds.

## Completion

After your repair completes, a NEW independent verifier will be commissioned to verify your outputs.
