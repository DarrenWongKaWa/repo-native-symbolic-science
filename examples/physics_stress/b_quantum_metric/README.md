# Physics Stress B — Quantum metric / Berry-curvature relation

## Scientific identity

For the same massive Dirac model (n as in example A) define

    g_ij = ¼ ∂_i n · ∂_j n.

Then, with `R² = k_x² + k_y² + m²`:

    g_xx = (k_y² + m²) / (4 R⁴)
    g_yy = (k_x² + m²) / (4 R⁴)
    g_xy = −k_x k_y / (4 R⁴)

and the genuine quantum-geometric relation

    det(g) = g_xx g_yy − g_xy² = Ω_xy² / 4 = m² / [16 (k_x² + k_y² + m²)³].

## Variables and domain (part of the claim)

- `k_x, k_y ∈ ℝ`, `m ∈ ℝ, m ≠ 0` (gapped; `R² > 0` so the square root is
  the positive real branch, declared explicitly).

## Allowed transformations

Exact differentiation and dot products in the trusted derivation layer; exact
algebra in the judge. No IBP, no limit reordering.

## Claim type

`identity_under_assumptions`, scope `real_scalars`.

## Verification route

`derive_claims.py` → `run_all.py` → real
`symbolic-identity-verify` CLI with pinned second engine.

## Expected results

- B1–B5: certified at evidence level 3 with recorded side conditions
  (observed 2026-08-16 at 52e1045: `VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS`).
- `Bu_cross`: `UNSUPPORTED_BY_CURRENT_CONTRACT` (whitelist rejects matrix syntax).

## Mutations

- `Bm_gxy_signflip`: `g_xy → +k_x k_y/(4R⁴)` — expected
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.
- `Bm_omega2_half`: `det(g) = Ω²/2` instead of `Ω²/4` — expected
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.

Without the pinned Wolfram runtime, positives degrade to
`SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` (never a fake PASS); mutations are
still refuted.
