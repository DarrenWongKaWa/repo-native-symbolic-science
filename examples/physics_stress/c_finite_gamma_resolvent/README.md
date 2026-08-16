# Physics Stress C — finite-Γ retarded/advanced resolvent structure

## Scientific identity

For real energy `x` and `Γ > 0`:

    1/(x + iΓ) − 1/(x − iΓ) = −2 i Γ / (x² + Γ²),

and the product (modulus) structure representative of finite-lifetime Kubo
response:

    1/((x + iΓ)(x − iΓ)) = 1/(x² + Γ²).

The retarded resolvent carries `+iΓ`, the advanced carries `−iΓ`; complex
conjugation maps one onto the other, and the `Γ` sign is part of the claim.

## Variables and domain (part of the claim)

- `x ∈ ℝ` (real energy)
- `Γ ∈ ℝ, Γ > 0` (finite lifetime; nonzero to keep the resolvents regular)

## Allowed transformations

Exact complex arithmetic in the whitelist judge (`I` is a permitted
constant). No real-algebra flattening: the identities are complex-valued and
are adjudicated as such.

## Claim type

`identity_under_assumptions`, scope `real_scalars` (real symbols; complex
values arise only through `I`).

## Verification route

`derive_claims.py` → `run_all.py` → real
`symbolic-identity-verify` CLI with pinned second engine.

## Expected results

- C1, C2: certified (observed 2026-08-16 at 52e1045; see run_all output for
  the exact verdict, `VERIFIED_SYMBOLIC_IDENTITY[_WITH_SIDE_CONDITIONS]`).
- `Cu_cross`: `UNSUPPORTED_BY_CURRENT_CONTRACT` (undeclared function).

## Mutations

- `Cm_adv_to_ret`: replace the advanced `x − iΓ` by the retarded
  `x + iΓ` (so the left side vanishes identically) — expected
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.
- `Cm_double_ret`: use two retarded resolvents in the product — expected
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE`.

The point is that finite-Γ complex semantics are not silently flattened into
real algebra: a wrong Γ sign must be caught.
