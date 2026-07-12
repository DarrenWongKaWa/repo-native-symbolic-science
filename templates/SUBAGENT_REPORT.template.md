# Subagent Report Task

## Task Identity
- **Task ID**: `{{TASK_ID}}`
- **Role**: `{{ROLE}}` (report_generator or report_verifier)
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`

## Objective

{{#if IS_VERIFIER}}
Independently verify the report produced by report generator `{{REPORT_GENERATOR_TASK_ID}}`.
{{else}}
Generate a human-readable report from verified results.
{{/if}}

## Authorized Inputs (Read-Only)

| Path | SHA-256 | Source |
|------|---------|--------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` | {{source}} |
{{/each}}

### Verified Results

{{#each VERIFIED_RESULTS}}
- **Task `{{task_id}}`**: `{{output_directory}}/result_envelope.json` (verdict: `{{verdict}}`)
{{/each}}

## Required Outputs

| Path | Description |
|------|-------------|
{{#each REQUIRED_OUTPUTS}}
| `{{this}}` | |
{{/each}}

All outputs must be written to: `{{OUTPUT_DIRECTORY}}/`

## Report Format

{{REPORT_FORMAT_SPECIFICATION}}

{{#if IS_VERIFIER}}
## Verification Protocol

1. Load the report generator's artifacts (read-only)
2. Verify:
   - All claims in the report are backed by verified results
   - No claim exceeds the source verification verdict
   - Caveats are accurately reported
   - Numerical values are correctly transcribed
   - No new scientific claims are introduced
3. Issue verdict: VERIFIED / VERIFIED_WITH_CAVEAT / REJECTED

You may NOT edit or rewrite the report.
{{/if}}

{{#unless IS_VERIFIER}}
## Report Content Requirements

1. **Summary**: Concise overview of results
2. **Methodology**: How results were obtained (reference task IDs)
3. **Results**: Present verified findings
4. **Caveats**: Document all caveats from verification
5. **Claims**: Only claims backed by VERIFIED or VERIFIED_WITH_CAVEAT verdicts
6. **References**: Task IDs, artifact paths, SHAs

### You MUST NOT:
- Introduce new scientific claims not in the verified results
- Misrepresent VERIFIED_WITH_CAVEAT as VERIFIED
- Omit caveats
- Claim the report itself has been independently verified
{{/unless}}

## Forbidden Actions

{{#each FORBIDDEN_ACTIONS}}
- {{this}}
{{/each}}

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
