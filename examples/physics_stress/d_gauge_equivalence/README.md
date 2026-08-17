# Physics Stress D — gauge-equivalent vector potentials

## Scientific identity

For a constant magnetic field `B`, compare the symmetric and Landau gauges:

    A_sym = (−B y/2, B x/2),    A_L = (0, B x),    χ = B x y / 2.

Componentwise:

    A_L − A_sym = ∇χ   (i.e. (B y/2, B x/2)),

and independently both potentials give the same field:

    ∂_x A_y − ∂_y A_x = B.

## The distinction the framework must keep

- `A_L` and `A_sym` are **not pointwise equal** (claim D5 is a negative
  control that must be refuted).
- They are related by a **gauge transformation** (claims D1/D2: the
  difference equals `∇χ` componentwise), and the curvature (curl) is
  gauge-invariant (claims D3/D4).

## Variables and domain (part of the claim)

- `B, x, y ∈ ℝ`; `B` constant (no position dependence).

## Allowed transformations

Exact differentiation and vector-component bookkeeping in the trusted
derivation layer; exact algebra in the judge. No IBP, no boundary assumptions
(all statements here are pointwise, not integrated).

## Claim type

`identity_under_assumptions`, scope `real_scalars`.

## Verification route

`derive_claims.py` (which also re-verifies the gauge relation internally
with exact SymPy) → `run_all.py` → real `symbolic-identity-verify` CLI.

## Expected results

- D1–D4: certified (observed 2026-08-16 at 52e1045; see run_all output).
- D5 (illegal pointwise equality): refuted —
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.
- `Du_cross`: `UNSUPPORTED_BY_CURRENT_CONTRACT` (whitelist rejects
  `curl(...)`).

## Mutation

- `Dm_chi_no_half`: `χ → B x y` (the 1/2 is dropped, so
  `A_L − A_sym ≠ ∇χ`) — expected
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.
