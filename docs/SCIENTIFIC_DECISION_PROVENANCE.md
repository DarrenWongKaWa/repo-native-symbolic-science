# Scientific Decision Provenance Layer

## Overview

The Scientific Decision Provenance Layer provides a generic, fail-closed framework for managing the lifecycle of scientific claims, trusted checkpoints, rollback after invalidation, stale-artifact detection, and scope/projection authorization.

All transitions fail closed: any state transition not explicitly listed in the allowed transition table is rejected.

## Schematic Lifecycle

```
CANDIDATE ----[source evidence linked]----> SOURCE_BACKED
                                               |
                          [submitted for independent verification]
                                               |
                                               v
                   PENDING_INDEPENDENT_VERIFICATION
                          |                    |
     [indep. verifier]    |                    |  [model projection verified]
                          v                    v
                   ACTIVE_VERIFIED      MODEL_SPECIFIC_ONLY
                          |                    |
     [new claim supersedes / evidence invalidates / stale detected]
                          v                    v
              SUPERSEDED / INVALIDATED / STALE_NONAUTHORITATIVE
                                                    |
                          [fresh executable evidence + recovery reason]
                                                    |
                                                    v
                                               CANDIDATE
```

All active states can also transition to `BLOCKED`. `BLOCKED` can recover to `CANDIDATE` with a recovery decision.

## Claim States

| State | Description |
|-------|-------------|
| `CANDIDATE` | Claim is proposed but lacks source evidence linkage. |
| `SOURCE_BACKED` | Claim is linked to source evidence but not yet independently verified. |
| `PENDING_INDEPENDENT_VERIFICATION` | Claim has been submitted for independent verification. |
| `ACTIVE_VERIFIED` | Claim has been independently verified and is active. Requires independent_verifier role. |
| `MODEL_SPECIFIC_ONLY` | Claim holds only under a model-projected scope; cannot be promoted to general identity. |
| `SUPERSEDED` | A newer claim has replaced this one. Irrecoverable terminal. |
| `INVALIDATED` | Evidence has shown this claim to be invalid. Irrecoverable terminal. |
| `STALE_NONAUTHORITATIVE` | Claim is based on stale artifacts. Recoverable to `CANDIDATE` with fresh executable evidence. |
| `BLOCKED` | Claim is blocked by an explicit guard. Recoverable to `CANDIDATE` with recovery decision. |

## Allowed Transitions

Transitions fail closed. The following are the only permitted transitions:

| From | To |
|------|----|
| `CANDIDATE` | `SOURCE_BACKED`, `SUPERSEDED`, `INVALIDATED`, `BLOCKED` |
| `SOURCE_BACKED` | `PENDING_INDEPENDENT_VERIFICATION`, `SUPERSEDED`, `INVALIDATED`, `STALE_NONAUTHORITATIVE`, `BLOCKED` |
| `PENDING_INDEPENDENT_VERIFICATION` | `ACTIVE_VERIFIED`, `MODEL_SPECIFIC_ONLY`, `SUPERSEDED`, `INVALIDATED`, `BLOCKED`, `STALE_NONAUTHORITATIVE` |
| `ACTIVE_VERIFIED` | `SUPERSEDED`, `INVALIDATED`, `STALE_NONAUTHORITATIVE` |
| `MODEL_SPECIFIC_ONLY` | `SUPERSEDED`, `INVALIDATED`, `STALE_NONAUTHORITATIVE` |
| `STALE_NONAUTHORITATIVE` | `CANDIDATE` (re-lifecycle: requires fresh executable evidence, recovery reason, prior authoritative status) |
| `BLOCKED` | `CANDIDATE` (unblock and restart: requires new evidence reference, explicit recovery reason, prior authoritative status) |
| `SUPERSEDED`, `INVALIDATED` | *(irrecoverable terminal — no further transitions)* |

## Recovery Requirements

Transitions from recoverable dormant states (`BLOCKED`, `STALE_NONAUTHORITATIVE`) back to `CANDIDATE` require an explicit recovery decision containing all of:

1. **New evidence reference** (`evidence_artifact_ids` must be non-empty)
2. **Explicit recovery reason** (`reason` must be a non-empty string)
3. **Prior authoritative status** (the claim's `authority_level` must be recorded)

Additional requirements by source state:

- **`STALE_NONAUTHORITATIVE`**: If `fresher_executable_available` is true in the staleness check, the claim must contain `executable_replay` or `frozen_machine_readable_operand` evidence — a timestamp alone is not sufficient.

Recovery is not permitted merely because a timestamp is newer. The decision event, evidence, and reason are mandatory.

## Authority Ordering

Artifacts are ranked by evidential authority:

```
fresh executable replay          (tier 0, highest authority)
  >
frozen machine-readable operand  (tier 1)
  >
structured result summary        (tier 2)
  >
human-readable report            (tier 3)
  >
historical PASS field            (tier 4, lowest authority)
```

The framework rejects claims backed only by `PASS`, `all_zero`, or `nonzero_count` fields without linked executable evidence. `historical_pass_field` and `human_readable_report` are forbidden as standalone evidence types.

## Stale Artifact Detection

When a fresh executable replay is available and a claim is backed only by frozen/historical evidence, the claim is flagged as `STALE_NONAUTHORITATIVE`. Fresh replay always takes precedence over frozen artifacts.

## Checkpoint Rollback

1. Checkpoints chain via `parent_checkpoint_id`.
2. Only `trusted: true` checkpoints serve as rollback targets.
3. When a checkpoint is invalidated, all descendants are enumerated.
4. `build_rollback_recommendation()` finds the last trusted checkpoint before the invalidated one.
5. All descendants of the last trusted checkpoint after the invalidation point are listed for re-validation.

## Projection vs General Identity

- A **model-projected** match may authorize `MODEL_SPECIFIC_EQUIVALENCE`.
- It must NOT authorize `GENERAL_SYMBOLIC_IDENTITY` unless injectivity is explicitly established.
- The `cannot_promote_to_general` field explicitly blocks promotion.

## Local Identity vs Boundary Applicability

Two independent gates:

| Gate | Description |
|------|-------------|
| `LOCAL_EXACT_IDENTITY_GATE` | Exact identity established within a local domain. |
| `BOUNDARY_APPLICABILITY_GATE` | Generalization to boundary/integrated domain. |

Local identity may pass (`passed: true`) while boundary applicability remains pending (`passed: false`). Both must pass for general-scope promotion.

## Generator-Verifier Separation

- The generator engine produces evidence (e.g., `sympy`).
- The verifier engine independently checks it (e.g., `python_numeric`).
- Same-engine verification emits a warning.
- The `executor` role cannot promote a claim to `ACTIVE_VERIFIED` — this requires `independent_verifier`.

## Linear System Evidence

The `linear_system_evidence` schema captures:

- Matrix shape `[rows, cols]`
- `rank` and `augmented_rank` (inconsistency when augmented_rank > rank)
- `nullity` (must equal cols - rank)
- `left_nullspace_dimension` (must equal rows - rank)
- `consistent` (rank == augmented_rank)
- `unique_solution` (consistent and nullity == 0)
- `basis_ordering` — ordered variable basis
- `solution` — method, vector, nullspace basis
- `equation_residuals` — per-equation residual with tolerance check

Numerical baselines (`numerical_baseline`) are retained after downstream analytical invalidation for comparison.

## Domain-Specific Adapters

Benchmarks provide domain-specific adapters that map:
- Symbol dictionaries
- Index role conventions
- Assumption sets
- Symmetry rules
- Limit-order rules
- Canonicalization policy
- Required human gates

These adapters conform to `scientific_adapter.schema.json` and do **not** encode scientific rules in the core framework.

## CLI

```bash
# List all valid states
python3 scripts/claim_decision_engine.py states

# Show allowed transitions from a state
python3 scripts/claim_decision_engine.py transitions-for CANDIDATE

# Apply a transition
python3 scripts/claim_decision_engine.py transition claim.json ACTIVE_VERIFIED independent_verifier "verified"

# Validate linear system evidence
python3 scripts/claim_decision_engine.py validate-evidence evidence.json

# Build rollback recommendation
python3 scripts/claim_decision_engine.py rollback checkpoints.json CP_BROKEN

# Check projection gate
python3 scripts/claim_decision_engine.py projection-gate projection.json

# Check stale rejection
python3 scripts/claim_decision_engine.py reject-stale claim.json true

# Validate claim lifecycle artifact
python3 scripts/validate_claim_lifecycle.py claim.json

# Validate decision provenance artifact
python3 scripts/validate_decision_provenance.py decision_event decision.json
```

## Tests

```bash
python3 tests/decision_provenance/test_scientific_decision_provenance.py
```

13 test suites, 61 assertions. All tests use synthetic fixtures.

## Schemas

| Schema | File |
|--------|------|
| Claim Lifecycle | `schemas/claim_lifecycle.schema.json` |
| Checkpoint | `schemas/checkpoint.schema.json` |
| Decision Provenance | `schemas/decision_provenance.schema.json` |
| Linear System Evidence | `schemas/linear_system_evidence.schema.json` |
