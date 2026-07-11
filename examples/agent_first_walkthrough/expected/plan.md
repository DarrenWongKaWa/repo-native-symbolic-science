# Expected Plan

This file shows the expected plan after the human scientist resolves the missing definitions.

---

## Response from Human Scientist

> H_n(y) uses the **physicist's convention**: H_n^phys(y) = (-1)^n exp(y^2) d^n/dy^n exp(-y^2), with H_0(y)=1, H_1(y)=2y.
>
> gamma(n+1, x) is the **lower incomplete gamma function**: gamma(a, x) = ∫_0^x t^{a-1} exp(-t) dt. The identity gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k / k! holds for integer n.
>
> z is a **continuous real variable**. No integer restriction applies. sin(pi*z) is periodic with period 2.

---

## Plan

### Plan ID: PLAN-SYNTHETIC-WALKTHROUGH-001

### Task Class: Transformation

### Sub-Class: transformation.candidate_B

### Scientific Adapter

```json
{
  "adapter_id": "synthetic_hermite_gamma",
  "declared_symbols": {
    "x": {"domain": "positive real", "role": "free_scalar"},
    "y": {"domain": "real", "role": "free_scalar"},
    "z": {"domain": "real", "role": "free_scalar"},
    "n": {"domain": "nonnegative_integer", "role": "free_parameter"},
    "pi": {"domain": "mathematical_constant", "role": "constant"},
    "H": {"convention": "physicist", "role": "hermite_polynomial"},
    "gamma": {"convention": "lower_incomplete", "role": "lower_incomplete_gamma"}
  },
  "authorized_identities": [
    "H_0(y) = 1",
    "H_1(y) = 2y",
    "H_{n+1}(y) = 2*y*H_n(y) - 2*n*H_{n-1}(y)",
    "gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k / k!  (for integer n >= 0)"
  ],
  "symmetries": [
    "sin(pi*z) periodic with period 2",
    "H_n(-y) = (-1)^n H_n(y)"
  ],
  "assumptions": {
    "x > 0": true,
    "y in R": true,
    "z in R": true,
    "n >= 0 integer": true,
    "commutative_scalars": true
  }
}
```

### Allowed Transformation Levels

**Level A** (syntax-preserving): rename terms, reorder commuting terms
**Level B** (exact algebraic): expand, factor, collect terms
**Level C** (scientific-definition identities): substitute declared Hermite and gamma identities

### Forbidden Transformation Levels

**Level D** (differential): not needed for scalar expression
**Level E** (integration/IBP): explicitly forbidden
**Level F** (integrated cancellation): explicitly forbidden
**Level G** (closure/canonicalization): requires human gate

### Expected Output Artifacts

1. `candidate_transformation.json` — simplified form
2. `rule_application_trace.json` — each transformation and its justification
3. `level_boundary_audit.json` — confirmation no forbidden levels were crossed
4. `transformation_report.md` — human-readable summary

### Backend Selection

Prefer SymPy for exact algebraic manipulation. Use Python numeric for regression testing against known special values.

### Verification Strategy

1. Exact symbolic verification: `original - candidate = 0` under declared assumptions
2. Numerical regression: evaluate at n=0,1,2 with random (x,y,z) and compare
3. Cross-engine: not required for scalar algebraic identity

### Human Gates Required

- None at this stage (all operations are levels A–C with declared identities)
- Canonical promotion is separately gated
