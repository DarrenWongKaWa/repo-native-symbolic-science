# Expected Backend Selection

This file shows the expected backend selection result.

---

## Backend Selection Result

### Capability Requirements

| Operation | Capability | Required For |
|-----------|-----------|--------------|
| Expand (x+1)^n | `expand` | Sector F1 binomial expansion |
| Factor polynomial | `factor` | Post-expansion factorization |
| Substitute gamma identity | `subs` | Replace gamma with finite sum |
| Substitute Hermite values | `subs` | Evaluate H_0, H_1 for regression |
| Evaluate sin(pi*z) at sample points | `mpmath_evalf` | Numerical regression |
| Evaluate exp(-x) at sample points | `mpmath_evalf` | Numerical regression |
| Evaluate gamma at sample points | `mpmath_gamma` | Numerical regression |

### Backend Matching

| Backend | Type | Matches |
|---------|------|---------|
| SymPy | EXACT_SYMBOLIC | expand, factor, subs ✓ |
| Python Numeric | NUMERICAL | mpmath_evalf, mpmath_gamma ✓ |
| Mathematica | EXACT_SYMBOLIC | All ✓ (not needed) |

### Selection

```json
{
  "selected_primary_backend": "sympy",
  "selected_supporting_backends": ["python_numeric"],
  "selected_verification_backends": [],
  "selection_reason": "Open-source exact symbolic baseline sufficient for all required algebraic operations. Numerical backend provides regression testing support.",
  "human_decision_required": false,
  "fallback_path": "Use sympy for exact algebra, python_numeric for numerical sampling"
}
```

### Capability Gaps

None. All required capabilities are available in the open-source backends.

### License Constraints

None. SymPy (BSD) and NumPy/SciPy/mpmath (BSD) are freely redistributable.

### Note on Mathematica

Mathematica is not required for this synthetic walkthrough. The operations (expand, substitute, evaluate numerically) are fully supported by open-source backends. Mathematica would be selected only if a Mathematica-specific capability were essential and no open-source alternative existed.
