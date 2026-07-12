# Subagent Execute Task

## Task Identity
- **Task ID**: `{{TASK_ID}}`
- **Role**: `executor`
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`

## Objective

{{OBJECTIVE}}

## Authorized Inputs

The following frozen artifacts are authorized for reading. Do NOT read any other files. All SHAs have been verified.

| Path | SHA-256 |
|------|---------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` |
{{/each}}

## Required Outputs

You must materialize the following artifacts:

{{#each REQUIRED_OUTPUTS}}
- `{{this}}`
{{/each}}

All outputs must be written to: `{{OUTPUT_DIRECTORY}}/`

## Dependency Gates

The following gates are ELIGIBLE:

{{#each DEPENDENCY_GATE_IDS}}
- `{{this}}`
{{/each}}

## Allowed Actions

{{#each ALLOWED_ACTIONS}}
- {{this}}
{{/each}}

## Forbidden Actions

{{#each FORBIDDEN_ACTIONS}}
- {{this}}
{{/each}}

**Important**: You may NOT verify your own output as an independent verifier would. Do NOT claim verification-level certainty.

## Claim Boundary

### You MAY claim:
{{#each AUTHORIZED_CLAIMS}}
- {{this}}
{{/each}}

### You MUST NOT claim:
{{#each PROHIBITED_CLAIMS}}
- {{this}}
{{/each}}

Maximum claim level: `execution`

## Write Protocol

1. Write outputs to temporary paths first (e.g., `{{OUTPUT_DIRECTORY}}/.tmp/`)
2. Validate each output: parse JSON, validate against schemas, compute SHA-256
3. After all outputs are valid, atomically rename to final paths
4. Generate output SHA manifest: `{{OUTPUT_DIRECTORY}}/output_sha_manifest.json`
5. Produce result envelope: `{{OUTPUT_DIRECTORY}}/result_envelope.json`

## Validation

Before declaring completion, run:
```
{{#each VALIDATION_COMMANDS}}
{{this}}
{{/each}}
```

## Result Envelope

Produce your result in `{{OUTPUT_DIRECTORY}}/result_envelope.json` conforming to `schemas/subagent_result_envelope.schema.json`.

The envelope must include:
- All produced artifacts with SHA-256 hashes
- Self-reported validation results
- All claims (must stay within claim boundary)
- Any caveats or blockers encountered
- Resource usage statistics
- Completion status (COMPLETED, PARTIAL, FAILED, TIMED_OUT)

## Timeout

Maximum time: `{{TIMEOUT_SECONDS}}` seconds.

## Completion States

Valid: `{{#each COMPLETION_STATES}}{{this}} {{/each}}`

Silence, timeout, or process exit alone never implies COMPLETED. All required outputs must exist and be SHA-valid.
