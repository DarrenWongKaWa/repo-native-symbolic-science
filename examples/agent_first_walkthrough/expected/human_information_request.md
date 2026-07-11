# Expected Human Information Request

This file shows what a correct `human_information_request.md` should look like when the agent processes `input/raw_expression.md`.

---

## Human Information Request

### Request ID: HIR-SYNTHETIC-WALKTHROUGH-001

### Status: PENDING

---

## Missing Definitions

The following entities appear in the raw expression but lack authoritative scientific definitions.

### 1. H_n(y) — Hermite Polynomial Normalization Convention

**Found in expression**: `H_n(y)` in the term `sin(pi*z) * H_n(y)`

**What is missing**: The normalization convention for the Hermite polynomial has not been declared. Two common conventions exist:

- **Physicist's convention**: `H_n^phys(y) = (-1)^n exp(y^2) d^n/dy^n exp(-y^2)`
- **Probabilist's convention**: `He_n(y) = (-1)^n exp(y^2/2) d^n/dy^n exp(-y^2/2)`

These differ by scaling: `H_n^phys(y) = 2^(n/2) * He_n(sqrt(2)*y)`.

**Request**: Please declare which convention is used for H_n(y). This affects the recurrence relation, the explicit form for n=0,1, and any numerical evaluations in regression tests.

### 2. gamma(n+1, x) — Upper vs Lower Incomplete Gamma Function

**Found in expression**: `gamma(n+1, x)` in the term `gamma(n+1, x)`

**What is missing**: The incomplete gamma function notation `gamma(a, x)` is ambiguous. Two common conventions exist:

- **Upper incomplete gamma**: `Gamma(a, x) = ∫_x^∞ t^{a-1} exp(-t) dt`
- **Lower incomplete gamma**: `gamma(a, x) = ∫_0^x t^{a-1} exp(-t) dt`

The relationship `gamma(a, x) + Gamma(a, x) = Gamma(a)` holds.

**Request**: Please clarify which incomplete gamma function is intended. The identity declared in the scientific context (`gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k / k!` for integer n) is consistent with the **lower** incomplete gamma function when `a = n+1` is an integer, but confirmation is needed.

### 3. sin(pi*z) — Domain for Periodicity Simplifications

**Found in expression**: `sin(pi*z)` in the term `sin(pi*z) * H_n(y)`

**What is missing**: The domain of z for periodicity simplifications has not been declared. If z is restricted to integer values, `sin(pi*z) = 0` identically, which would simplify the entire expression.

**Request**: Please declare the domain of z. Is z:
- A continuous real variable → standard sine evaluation
- An integer variable → sin(pi*z) ≡ 0
- A half-integer variable → sin(pi*z) = ±1

---

## Blocked Claims

The following operations are blocked until the above definitions are resolved:

| Claim ID | Operation | Blocker |
|----------|-----------|---------|
| CLAIM-SYNTH-001 | Hermite evaluation at n=0,1 | Missing normalization convention |
| CLAIM-SYNTH-002 | gamma identity substitution | Missing upper/lower disambiguation |
| CLAIM-SYNTH-003 | sin(pi*z) periodicity simplification | Missing domain declaration |

---

## Allowed Continuation

The following operations may proceed without blocked definitions:

- Exact algebra on the (x+1)^n * exp(-x) term (does not involve H, gamma, or sin)
- Numerical sampling of the full expression at specific parameter values (using the user's intended conventions can be filled in later)
- Structural analysis (symbol inventory, index audit, term counting)
