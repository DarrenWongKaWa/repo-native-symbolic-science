# Theoretical-Physics Stress Examples

Hard theoretical-physics identities exercised through the real
`symbolic_identity_verify` judge (the LLM-SR × Viper fusion capability) with
adversarial wrong-physics mutations. Correct science must certify or stay
fail-closed pending evidence; every specific wrong science must produce NONZERO
evidence.

## Capability boundary (read this first)

The judge's whitelist grammar covers scalar expressions over declared real
symbols with: +, -, *, /, integer and rational powers, `sqrt`, `exp`,
`log`, trig/hyperbolic/inverse-trig functions, `Abs`, `conjugate`,
`re`, `im`, and the constants `pi`, `E`, `I`. It does **not** accept
matrices, vector cross products, or derivative operators as input syntax. In
these examples, vector/matrix mechanics (Pauli traces, cross products,
gradients, curls) are computed in the **trusted derivation layer** (SymPy,
exact arithmetic) and the resulting **scalar pointwise identities** are
submitted to the judge. Submitting `cross(kx,ky)` directly fails closed with
`UNDECLARED_OR_DISALLOWED_NAME` — see the `unsupported_grammar` control in
each run. That is `UNSUPPORTED_BY_CURRENT_CONTRACT`, reported, never faked.

## Examples

| Example | Scientific identity | Claim type | Mutation caught |
|---|---|---|---|
| [a_dirac_berry_curvature](a_dirac_berry_curvature/README.md) | Berry curvature `Ω_xy = -m/(2(kx²+ky²+m²)^{3/2})` of the massive Dirac two-band model | `identity_under_assumptions` | wrong sign of `Ω_xy` |
| [b_quantum_metric](b_quantum_metric/README.md) | Quantum metric `g_ij` and `det(g) = Ω_xy²/4` | `identity_under_assumptions` | wrong `g_xy` sign; `Ω²/2` instead of `Ω²/4` |
| [c_finite_gamma_resolvent](c_finite_gamma_resolvent/README.md) | Retarded/advanced finite-`Γ` resolvent structure | `identity_under_assumptions` | `x-iΓ → x+iΓ` in the advanced term |
| [d_gauge_equivalence](d_gauge_equivalence/README.md) | Symmetric vs Landau gauge: `A_L - A_sym = ∇χ`, same curl | `identity_under_assumptions` | `χ → Bxy` (missing 1/2); illegal pointwise equality |

## Run

```bash
python3 examples/physics_stress/run_all.py
```

Each example directory also contains its own `derive_claims.py`, which
emits one JSONL claim per line (mechanical, unsimplified left-hand sides where
a derivation exists) and its own `README.md` with the scientific statement,
variables, domains, allowed transformations, claim type, expected result, and
mutation table.

## Verdict semantics honored here

- Positive claims accept only the honest ladder:
  `VERIFIED_SYMBOLIC_IDENTITY`,
  `VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS`,
  `VERIFIED_ON_EXPLICIT_SUBDOMAIN`,
  `VERIFIED_BY_DERIVATIVE_AND_BASE_POINT`, or the fail-closed
  `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE`. A verdict containing `DISPROVED`
  or `INCONCLUSIVE` fails the positive claim.
- Wrong-physics mutations must return
  `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` (or a
  second-engine `NONZERO`/`CONFLICT` verdict) — reproducible nonzero
  evidence, never a silent pass.
- Without the pinned Wolfram runtime, positives degrade to
  `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` (never a fake PASS); mutations are
  unaffected (disproof needs no second engine).
