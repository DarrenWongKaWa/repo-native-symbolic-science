# Reporting Contract

## Required Artifacts

Every task execution produces:
- `result.json` — structured verdict
- `report.md` — human-readable summary
- `runtime_log.json` — execution log
- `input_sha_manifest.json` — input file hashes
- `output_sha_manifest.json` — output file hashes

## Claim Boundary

- Maximum relation type per task: defined in task contract
- Forbidden relation types: scientific_equivalence, canonical_scientific_promotion (unless explicitly authorized)
- No automatic promotion from lower to higher claim types

## Verdict Registry

All verdicts reference:
- task_id
- task_type
- verdict (PASS, FAIL, CAVEATED_PASS)
- evidence artifacts
