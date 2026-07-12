# Subagent Plan Task

## Task Identity
- **Task ID**: `{{TASK_ID}}`
- **Role**: `{{ROLE}}` (global_planner or lane_planner)
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`

## Objective

{{OBJECTIVE}}

## Authorized Inputs

The following frozen artifacts are authorized for reading. Do NOT read any other files.

| Path | SHA-256 |
|------|---------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` |
{{/each}}

## Required Outputs

You must materialize the following artifacts. Failure to produce any of them means the task is incomplete.

{{#each REQUIRED_OUTPUTS}}
- `{{this}}`
{{/each}}

All outputs must be written to: `{{OUTPUT_DIRECTORY}}/`

## Dependency Gates

The following gates have been evaluated and passed before your launch:

{{#each DEPENDENCY_GATE_IDS}}
- `{{this}}`: ELIGIBLE
{{/each}}

## Allowed Actions

{{#each ALLOWED_ACTIONS}}
- {{this}}
{{/each}}

## Forbidden Actions

{{#each FORBIDDEN_ACTIONS}}
- {{this}}
{{/each}}

## Claim Boundary

### You MAY claim:
{{#each AUTHORIZED_CLAIMS}}
- {{this}}
{{/each}}

### You MUST NOT claim:
{{#each PROHIBITED_CLAIMS}}
- {{this}}
{{/each}}

Maximum claim level: `{{MAX_CLAIM_LEVEL}}`

## Plan Output Requirements

Your plan must include:

1. **Task decomposition**: List all subtasks with their purposes.
2. **Dependency graph**: Which tasks depend on which.
3. **Parallelism analysis**: Which tasks can run concurrently and why.
4. **Input requirements**: What each task needs as frozen input.
5. **Output requirements**: What each task must produce.
6. **Risk assessment**: What could go wrong and how to handle it.
7. **Execution order**: The recommended sequence.

## Validation

Before declaring completion, run:
```
{{#each VALIDATION_COMMANDS}}
{{this}}
{{/each}}
```

## Result Envelope

Produce your result in `{{OUTPUT_DIRECTORY}}/result_envelope.json` conforming to `schemas/subagent_result_envelope.schema.json`.

## Timeout

Maximum time: `{{TIMEOUT_SECONDS}}` seconds. If you exceed this, the task will be marked TIMED_OUT.

## Completion Status

Valid completion states: `{{#each COMPLETION_STATES}}{{this}} {{/each}}`
