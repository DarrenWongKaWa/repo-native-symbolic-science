# End-to-End Workflow

This document provides a complete synthetic walkthrough of the Repo-Native Symbolic Science workflow from raw input to traceable report. The example uses only synthetic, redistributable expressions. No private `sigma_xxx` or `sigma_abc` scientific content is included.

> **Note**: The framework was stress-tested on a private nonlinear-transport scientific reference case. The synthetic walkthrough below demonstrates the same workflow pattern using generic public expressions.

---

## Workflow Overview

```
raw input
→ immutable ingestion
→ semantic audit
→ human information request
→ human response
→ plan
→ decomposition
→ backend selection
→ bounded execution
→ independent verification
→ claim registry
→ report
```

---

## Step 1: Raw Input

The human scientist provides a raw expression:

```
F(a, b, c) = a^2 + 2*a*b + b^2 - c^2 + ln(x)*exp(x) + sin(y)^2 + cos(y)^2
```

Accompanied by the initial declaration:

> The variables a, b, c, x, y are commuting real scalars. I want to simplify this expression and verify any identities found.

---

## Step 2: Immutable Ingestion

The agent activates `scientific_symbolic_repo_entry`, which routes to `generic_raw_expression_ingestion`.

The raw expression is hashed and frozen:

```json
{
  "object_id": "raw-abc123",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "raw_bytes_frozen": true,
  "expression_language": "sympy",
  "symbols_found": ["a", "b", "c", "x", "y"],
  "functions_found": ["ln", "exp", "sin", "cos"],
  "structure": {
    "term_count": 5,
    "is_polynomial_subset": false,
    "has_transcendental": true,
    "has_trigonometric": true
  }
}
```

A semantic audit is triggered automatically.

---

## Step 3: Semantic Audit

The agent audits all symbols against declared definitions:

| Symbol | Status | Issue |
|--------|--------|-------|
| a | Declared | commuting real scalar |
| b | Declared | commuting real scalar |
| c | Declared | commuting real scalar |
| x | Declared | commuting real scalar |
| y | Declared | commuting real scalar |
| ln | Library | standard natural logarithm |
| exp | Library | standard exponential |
| sin | Library | standard sine |
| cos | Library | standard cosine |

No missing definitions are detected at this stage. However, the agent identifies two potential semantic gaps:

1. **Branch cut assumptions**: `ln(x)` and `sqrt`-like functions may require sign conventions for `x`.
2. **Trigonometric domain**: `sin(y)^2 + cos(y)^2 = 1` holds pointwise but must be declared as an authorized identity.

---

## Step 4: Human Information Request

The agent produces a structured human information request:

```markdown
# Human Information Request

## Missing Scientific Information

### 1. Domain of x for ln(x)
The expression contains `ln(x)`. Please declare:
- The domain of x (e.g., x > 0, x ∈ ℝ\{0}, complex with branch cut specification)
- Any branch cut conventions

### 2. Trigonometric Identity Authorization
The expression contains `sin(y)^2 + cos(y)^2`. The identity
sin²(y) + cos²(y) = 1 is a standard trigonometric identity.
Please declare:
- Whether this identity may be applied
- Any restrictions on y (real, complex, etc.)
```

---

## Step 5: Human Response

The human scientist responds:

> x is a positive real scalar (x > 0). The identity sin²(y) + cos²(y) = 1 is authorized as an exact algebraic replacement for any real y. No branch cut issues for ln(x) under x > 0.

The agent records this as a human gate decision and proceeds.

---

## Step 6: Plan

The agent materializes a plan:

```json
{
  "plan_id": "plan-001",
  "task_class": "transformation",
  "sub_class": "transformation.candidate_B",
  "target": "Simplify F(a,b,c,x,y)",
  "allowed_levels": ["B"],
  "authorized_identities": ["sin^2 + cos^2 = 1"],
  "forbidden_operations": [
    "integration_by_parts",
    "boundary_term_discard",
    "limit_reordering",
    "series_expansion",
    "assumption_invention"
  ],
  "expected_output": "CANDIDATE_TRANSFORMED"
}
```

---

## Step 7: Decomposition

The agent normalizes and decomposes the expression into independent child sectors:

**Sector 1 — Polynomial in a, b, c**:
```
F1(a, b, c) = a^2 + 2*a*b + b^2 - c^2
```
Note: `a^2 + 2*a*b + b^2 = (a + b)^2`, so `F1 = (a + b)^2 - c^2 = (a + b + c)*(a + b - c)`.

**Sector 2 — Transcendental**:
```
F2(x) = ln(x)*exp(x)
```

**Sector 3 — Trigonometric**:
```
F3(y) = sin(y)^2 + cos(y)^2
```
Using the authorized identity: `F3(y) = 1`.

Parent reconstruction test: `F = F1 + F2 + F3 = (a+b+c)*(a+b-c) + ln(x)*exp(x) + 1`. Exact reconstruction confirmed via subtraction.

---

## Step 8: Backend Selection

The agent probes available capabilities:

```json
{
  "selected_primary_backend": "sympy",
  "selected_supporting_backends": ["python_numeric"],
  "selection_reason": "Open-source exact symbolic baseline sufficient for polynomial factorization and trigonometric substitution",
  "human_decision_required": false
}
```

Mathematica is not required for these operations.

---

## Step 9: Bounded Execution

The agent runs the factorization and identity substitution on SymPy:

```json
{
  "request_id": "exec-001",
  "engine_id": "sympy",
  "operations_requested": ["factor", "subs"],
  "operations_observed": ["factor", "subs"],
  "normalized_output": "(a + b + c)*(a + b - c) + log(x)*exp(x) + 1",
  "exit_code": 0,
  "timeout_state": false,
  "memory_state": "ok",
  "errors": [],
  "warnings": []
}
```

Complete execution truth is recorded with all 22 required fields.

---

## Step 10: Independent Verification

The agent verifies the candidate against the frozen raw input:

### Exact Difference Check
```
original_expression - candidate_expression = 0
```
SymPy confirms exact subtraction yields zero under the declared assumptions.

### Structural Replay
The candidate expression structure is compared:
- Term count: 3 (vs original 5)
- Operations: factor, trigonometric identity substitution
- No new symbols introduced
- No symbols removed

### Pointwise Numerical Sampling
Numerical evaluation at 100 random points confirms agreement to machine precision. This is recorded as supporting evidence only — it does not establish symbolic equality.

### Verification Result
```json
{
  "relation_type": "exact_reconstruction",
  "status": "VERIFIED",
  "verification_method": "exact_difference_subtraction",
  "scope": "pointwise",
  "assumptions": ["x > 0", "y in R", "a,b,c in R", "sin^2+cos^2=1 authorized"],
  "supporting_evidence": "NUMERICAL_REGRESSION_PASS",
  "caveats": ["Numerical sampling is supporting evidence only; exact symbolic equality is established via subtraction"]
}
```

---

## Step 11: Claim Registry

The verified result is registered in provenance:

```
Expression F(a,b,c,x,y) = (a+b+c)*(a+b-c) + ln(x)*exp(x) + 1
Status: VERIFIED
Verification: exact difference subtraction yields zero
Assumptions: x > 0, y ∈ ℝ, a,b,c ∈ ℝ, Pythagorean identity authorized
Provenance: raw-abc123 → norm-001 → cand-001 → exec-001 → verif-001
```

The result is **not** promoted to canonical at this stage. Canonical promotion requires a separate human gate.

---

## Step 12: Report

A traceable LaTeX report is generated with:
- The original and simplified expressions
- SHA-256 provenance for every equation
- Verifier verdict and assumptions
- Human gate decisions
- Known caveats

---

## Invalid Claim Rejection Example

Consider what happens if the human scientist requests:

> Promote the simplified result to canonical.

The agent checks:
1. **Verified?** Yes — exact reconstruction passed.
2. **Human gate for canonical promotion?** No — no explicit canonical promotion gate has been authorized.
3. **Blocker 5 lifted?** No — the global guard against premature closure is active.

The agent responds:

```markdown
# Blocked: Canonical Promotion Requires Human Gate

The result F(a,b,c,x,y) = (a+b+c)*(a+b-c) + ln(x)*exp(x) + 1 is VERIFIED but
not CANONICAL.

Required:
- Explicit human authorization for canonical promotion
- Lifting of the global guard (Blocker 5) by explicit human acknowledgement
- Declaration that the verified result is intended as the final reference form

To proceed: explicitly authorize canonical promotion and acknowledge readiness.
```

---

## Numerical Support Example

If the expression had no closed-form simplification but required numerical evidence:

> Show numerical agreement between F(a,b,c) and an alternative representation G(a,b,c) at 1000 random points.

The agent would:
1. Select the numerical backend (python_numeric)
2. Execute bounded numerical sampling
3. Return `NUMERICAL_REGRESSION_PASS` with explicit caveat:
   > Numerical agreement does not establish symbolic equality.
4. NOT claim `exact_reconstruction` or `symbolic_equality`

---

## Summary

This synthetic walkthrough demonstrates the complete lifecycle:

| Step | Action | Gate |
|------|--------|------|
| 1 | Raw input provided | — |
| 2 | Immutable ingestion | — |
| 3 | Semantic audit | Missing definition → escalation |
| 4 | Human information request | Human response required |
| 5 | Human response recorded | Human gate passed |
| 6 | Plan materialized | — |
| 7 | Decomposition and normalization | Exact reconstruction gate |
| 8 | Backend selection | Capability match gate |
| 9 | Bounded execution | Timeout/memory gate |
| 10 | Independent verification | Exact difference gate |
| 11 | Claim registry | Canonical promotion gate (blocked) |
| 12 | Traceable report | Compilation authorization gate |
