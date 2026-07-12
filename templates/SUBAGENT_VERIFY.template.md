# Subagent Verify Task

## Task Identity
- **Task ID**: `{{TASK_ID}}`
- **Role**: `independent_verifier`
- **Parent Orchestration ID**: `{{ORCHESTRATION_ID}}`
- **Target Task ID**: `{{TARGET_TASK_ID}}` (the executor task to verify)

## Objective

Independently verify the frozen artifacts produced by executor task `{{TARGET_TASK_ID}}`.

## Authorized Inputs (Read-Only)

You may read ONLY the following frozen artifacts. Do NOT read executor scratch files, hidden reasoning, mutable workspace, or any undeclared files.

| Path | SHA-256 |
|------|---------|
{{#each AUTHORIZED_INPUTS}}
| `{{path}}` | `{{sha256}}` |
{{/each}}

## Required Outputs

| Path | Description |
|------|-------------|
| `{{OUTPUT_DIRECTORY}}/verifier_result_envelope.json` | Your verdict and evidence |
| `{{OUTPUT_DIRECTORY}}/verification_evidence.md` | Detailed verification evidence |

## Forbidden Actions

- Do NOT read any executor scratch files, `.tmp/` directories, or mutable workspaces
- Do NOT read undeclared files or assumptions
- Do NOT edit, repair, or modify executor outputs
- Do NOT reuse the executor's context or subagent identifier
- Do NOT claim to have verified anything you did not independently reproduce

## Verification Protocol

1. Load the executor's frozen artifacts (read-only)
2. Load the executor's task contract and claim boundary
3. Independently reproduce the executor's claims:
   - Recompute any derivations
   - Revalidate SHAs of all artifacts
   - Verify the output SHA manifest matches actual files
   - Check claims stay within the executor's claim boundary
4. Check for partial artifacts, temporary files, or incomplete outputs
5. Verify the result envelope satisfies the schema
6. Issue one of three verdicts:

### VERIFIED

Issued when:
- All executor claims are independently confirmed
- All artifacts are valid and complete
- All SHAs match
- No undeclared assumptions were found
- Output contract is fully satisfied

### VERIFIED_WITH_CAVEAT

Issued when:
- Core claims are confirmed
- But specific caveats exist (document them):
  - Assumption not independently verified (requires external knowledge)
  - Computational precision limitation
  - Minor format deviation
  - Backend-specific result that cannot be cross-verified

### REJECTED

Issued when:
- Any claim does not independently reproduce
- Any SHA does not match
- Any required artifact is missing or partial
- Executor exceeded claim boundary
- Undeclared assumptions affected results
- Verification cannot be completed with available resources

## Verdict Evidence

For each claim made by the executor, your verification evidence must include:

1. The claim text
2. Your independent reproduction method
3. Whether the claim was confirmed, contradicted, or could not be verified
4. Specific evidence (SHA comparisons, recomputation results, schema validation output)

## Claim Boundary

### You MAY claim:
- The executor's artifacts are VERIFIED / VERIFIED_WITH_CAVEAT / REJECTED
- Specific evidence supporting your verdict

### You MUST NOT claim:
- That you have repaired or fixed the executor's work
- That you endorse the scientific correctness of unverified claims
- That verification may be skipped

## Result Envelope

Produce `{{OUTPUT_DIRECTORY}}/verifier_result_envelope.json` conforming to `schemas/subagent_result_envelope.schema.json`.

## Timeout

Maximum time: `{{TIMEOUT_SECONDS}}` seconds.

## Completion States

Valid: COMPLETED (with verdict), FAILED (unable to verify), TIMED_OUT

Your verdict determines the downstream eligibility of task `{{TARGET_TASK_ID}}`.
