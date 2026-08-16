# Physics Stress A — Massive Dirac Berry curvature

## Scientific identity

For the two-band Hamiltonian

    H(k) = k_x σ_x + k_y σ_y + m σ_z,   R² = k_x² + k_y² + m²,   n = (k_x, k_y, m)/√(R²),

the lower-band Berry curvature is

    Ω_xy = −½ n · (∂_{k_x} n × ∂_{k_y} n) = −m / [2 (k_x² + k_y² + m²)^{3/2}].

Two independent mechanical routes are submitted to the judge:

- **A0 (projector trace):** build the lower-band projector
  `P_− = (I − n·σ)/2` and `Ω_xy = −i Tr(P_− [∂_{k_x}P_−, ∂_{k_y}P_−])`;
- **A1/A2 (unit vector):** `n·(∂_x n × ∂_y n)` (A1) and
  `−½ n·(∂_x n × ∂_y n)` (A2).

## Variables and domain (part of the claim)

- `k_x, k_y ∈ ℝ`
- `m ∈ ℝ, m ≠ 0` (gapped; together with real `k` this makes `R² > 0`, so
  `R = √(R²)` is the positive real square root — the branch is declared, never
  implicit)

## Allowed transformations

Exact differentiation of the declared unit vector and projector; exact matrix
trace and cross products **in the trusted derivation layer**; exact algebra in
the judge. No IBP, no limit reordering, no weak-`m` expansion.

## Claim type

`identity_under_assumptions` (exact symbolic equality under the declared real
gapped domain), scope `real_scalars`.

## Verification route

`derive_claims.py` emits the mechanical (unsimplified) claim strings;
`run_all.py` submits them through
`python3 scripts/orch_controller.py symbolic-identity-verify` with the pinned
second engine.

## Expected results

- A1, A2: certified at evidence level 3 with recorded side conditions
  (observed 2026-08-16 at `main` 52e1045: `VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS`).
- A0: the primary canonicalizers prove the residual, but the pinned Wolfram
  second engine declines to confirm within its bounds on this long mechanical
  string, so the verdict is the fail-closed
  `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` — a capability-boundary result, not a
  pass.
- `Au_cross`: `UNSUPPORTED_BY_CURRENT_CONTRACT` (whitelist rejects
  `cross(...)`).

## Mutation

`Am_signflip` flips the sign of `Ω_xy` (`−m/(2R³) → +m/(2R³)`). Expected:
`DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` (reproducible nonzero
evidence at a deterministic probe point). Without Wolfram, the positive claims
degrade to `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` (never a fake PASS); the
mutation is still refuted.
