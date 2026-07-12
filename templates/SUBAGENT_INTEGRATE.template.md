# Subagent Integrate Task

## Task Identity
- **Task ID**: `{{TASK_ID}}`
- **Role**: `{{ROLE}}` (integration_executor or integration_verifier)
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`

## Objective

{{#if IS_VERIFIER}}
Verify the integration outputs produced by integration executor `{{INTEGRATION_EXECUTOR_TASK_ID}}`.
{{else}}
Integrate verified results from the following completed lanes into a unified output.
{{/if}}

## Authorized Inputs (Read-Only)

| Path | SHA-256 | Source |
|------|---------|--------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` | {{source}} |
{{/each}}

### Input Lanes

{{#each INPUT_LANES}}
- **Lane `{{lane_id}}`**: `{{output_directory}}/` (VERIFIED, SHA: `{{manifest_sha}}`)
{{/each}}

## Required Outputs

| Path | Description |
|------|-------------|
{{#each REQUIRED_OUTPUTS}}
| `{{this}}` | |
{{/each}}

All outputs must be written to: `{{OUTPUT_DIRECTORY}}/`

{{#if IS_VERIFIER}}
## Verification Protocol

1. Load the integration executor's frozen artifacts (read-only)
2. Independently verify:
   - All lane results are correctly incorporated
   - No lane result is misrepresented
   - No partial cross-consumption occurred
   - SHAs match
3. Issue verdict: VERIFIED / VERIFIED_WITH_CAVEAT / REJECTED

You may NOT edit or repair the integration outputs.
{{/if}}

{{#unless IS_VERIFIER}}
## Integration Protocol

1. Load all input lane results (read-only, verified)
2. Combine results according to the integration specification
3. Resolve any naming or indexing conflicts
4. Ensure no partial cross-consumption
5. Write integrated outputs

## Claim Boundary for Integration Executor

### You MAY claim:
- Lane results were combined according to specification
- Integration was performed without data loss

### You MUST NOT claim:
- The integration is independently verified
- Lane results were re-verified
- Integration implies any new scientific result
{{/unless}}

## Forbidden Actions

- {{#each FORBIDDEN_ACTIONS}}
- {{this}}
{{/each}}
- Do NOT read from mutable or in-progress lanes
- Do NOT modify input lane artifacts

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
