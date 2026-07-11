# Expected Verification

This file shows the expected verification results, including an exact symbolic transformation and an invalid claim promotion rejection.

---

## Verification Report

### Claim 1: Exact Symbolic Transformation (VERIFIED)

**Relation**: The original expression `G(x,y,z,n)` is exactly equal to the normalized candidate under the declared assumptions.

**Type**: `identity_under_assumptions`

**Method**: `exact_difference_subtraction`

**Result**: `G_original - G_candidate = 0` (SymPy confirms exact zero)

**Scope**: Pointwise, for all x > 0, y ∈ ℝ, z ∈ ℝ, n ∈ ℕ₀.

**Assumptions**:
- x > 0 (positive real)
- y ∈ ℝ (real)
- z ∈ ℝ (real)
- n ∈ ℕ₀ (non-negative integer)
- H_n uses physicist's convention
- gamma(n+1, x) is the lower incomplete gamma function
- sin² + cos² = 1 (standard, not needed here)

**Status**: VERIFIED

**Caveats**: None. Exact symbolic subtraction confirms identity.

---

### Claim 2: Numerical Regression Support (VERIFIED_WITH_CAVEAT)

**Relation**: Numerical evaluation of original and candidate expressions agrees at 100 random sample points.

**Type**: `numerical_regression`

**Method**: `numerical_sampling`

**Result**: Maximum residual < 1e-12 at all 100 points.

**Status**: VERIFIED_WITH_CAVEAT

**Caveat**: **Numerical agreement does not establish symbolic equality.** This is supporting evidence only. The exact symbolic claim (Claim 1) is the primary verification. The numerical regression confirms that no implementation error or assumption violation produces a discrepancy at random test points.

---

### Claim 3: Attempted Canonical Promotion (REJECTED)

**Request**: Human asks "Promote G to canonical result."

**Agent Response**:

> **REJECTED: Canonical promotion requires human gate.**
>
> The expression `G(x, y, z, n) = exp(-x)*(n! * sum_{k=0}^n x^k/k! + (x+1)^n) + sin(pi*z)*H_n(y)` is VERIFIED but is NOT canonical.
>
> Canonical promotion requires:
> 1. Explicit human authorization statement
> 2. All parent verifications accepted
> 3. All assumptions and caveats documented and accepted
> 4. **Blocker 5 (global guard) lifted** by explicit human acknowledgement
>
> Current status: Blocker 5 is ACTIVE (default). The global guard against premature closure has not been lifted.
>
> The verified result may be used for inspection and further work, but it is not the authoritative reference form until explicitly canonized.
>
> To proceed: provide an explicit canonical promotion authorization and acknowledge readiness to lift Blocker 5.

**Status**: REJECTED (pending human gate for canonical promotion)

**Type**: `forbidden_promotion` — `VERIFIED → CANONICAL` requires human gate.

---

### Claim 4: Human Authorization Gate (ACCEPTED after human response)

**Human Request**: "I authorize the use of the physicist's Hermite convention and the lower incomplete gamma identity. I confirm x > 0, y ∈ ℝ, z ∈ ℝ, n ∈ ℕ₀. These authorizations are for levels A–C only and do not include integration by parts, boundary term discard, or canonical promotion."

**Agent Action**: Materialized as a repo-native human decision record.

```json
{
  "decision_id": "HUMAN-GATE-SYNTHETIC-001",
  "decision_type": "gate_approve",
  "scope": "levels A through C",
  "authorized_identities": [
    "H_n(y) physicist convention",
    "gamma(n+1, x) lower incomplete gamma",
    "H_0=1, H_1=2y, recurrence relation",
    "gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k/k!"
  ],
  "forbidden_operations": [
    "integration_by_parts",
    "boundary_term_discard",
    "canonical_promotion"
  ],
  "status": "ACCEPTED",
  "recorded_at": "<timestamp>"
}
```

**Status**: HUMAN_GATE_PASSED. Dependent operations may now proceed at levels A–C.

---

### Verification Summary

| Claim | Type | Status | Notes |
|-------|------|--------|-------|
| Exact symbolic transformation | identity_under_assumptions | VERIFIED | Exact difference = 0 |
| Numerical regression | numerical_regression | VERIFIED_WITH_CAVEAT | Supporting evidence only |
| Canonical promotion | canonical_result | REJECTED | Requires human gate + Blocker 5 |
| Human authorization gate | gate_approve | ACCEPTED | Levels A–C authorized |

**Verdict**: The expression transformation is verified. Canonical promotion is blocked pending human authorization. Numerical evidence is available as supporting documentation but does not independently establish symbolic equality.
