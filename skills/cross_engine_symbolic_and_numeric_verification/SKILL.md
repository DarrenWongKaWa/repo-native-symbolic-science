# Cross-Engine Symbolic and Numerical Verification

Role: Verification skill that performs independent replay and cross-engine checks while preserving claim scope.

## Parent skill
`scientific_symbolic_repo_entry`

## Must distinguish

- `exact symbolic equality` → literal symbolic identity across engines
- `exact reconstruction` → independent recalculation from same input
- `structural replay` → same structural form after normalization
- `high-precision numerical support` → mpmath/N[] agreement to declared precision
- `numerical-only agreement` → numeric evaluation agreement (NOT proof of equality)
- `counterexample` → numerical sample that contradicts a claim
- `inconclusive` → insufficient evidence for any claim

## Must track

- Translation loss between expression languages (e.g., SymPy → Mathematica syntax)
- Reduced verification diversity when only one compatible exact backend exists
- Expression-language translation records with lossy/lossless classification

## Must not do

- Require two independent exact engines when only one compatible exact backend exists
- Treat numerical agreement as symbolic equality
- Promote structural replay to exact reconstruction when translation was lossy
- Claim cross-engine verification when only one engine executed

## Comparison methods

| Method | Evidence Type | Symbolic Equality Claim |
|---|---|---|
| `EXACT_SYMBOLIC_IDENTITY` | Two independent exact engines produce identical normal form | Authorized if no translation loss |
| `STRUCTURAL_REPLAY` | Secondary engine independently reconstructs expression structure | Authorized for structure claims only |
| `NUMERICAL_REGRESSION` | Independent numerical evaluation agrees within tolerance | Explicitly NOT symbolic equality |
| `HIGH_PRECISION_SUPPORT` | mpmath converged to high precision | Supporting evidence only |
| `MIXED` | Combination of above with appropriate caveats | Only strongest evidence type applies |

## Translation-loss policy

When expression translation between backends is lossy:
- Set `translation_loss = true`
- Set `exact_cross_engine_verification_eligible = false`
- Record unsupported constructs explicitly
- Do not claim exact cross-engine agreement

## Output artifact

`cross_engine_verification` conforming to `schemas/cross_engine_verification.schema.json`, recording:
- Primary and secondary engine results
- Comparison method and status for each evidence type
- Expression translation records for each engine pair
- Translation loss flag and details
- Claim scope with explicit authorization boundaries
- Maximum authorized claim (never exceeding evidence)
- All caveats

## Integration

Uses `schemas/cross_engine_verification.schema.json` for artifact structure.
Uses `scripts/engine_validators.py cross_engine` for validation.
Extends claim-relation taxonomy from REUSE_003.
