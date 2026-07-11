# Scientific Context

## Project: Synthetic Hermite-Gamma Identity Verification

### Target

Simplify `G(x, y, z, n) = (x + 1)^n * exp(-x) + gamma(n+1, x) + sin(pi*z) * H_n(y)` and verify the relationship between the incomplete gamma function and the Hermite-weighted exponential term.

### Index Roles

No tensorial indices — purely scalar expression.

### Assumptions

- x is a positive real scalar (x > 0)
- y is a real scalar
- z is a real scalar
- n is a non-negative integer (n = 0, 1, 2, ...)
- All operations are over commutative real scalars
- exp(-x) → 0 as x → ∞ (decay at infinity)

### Allowed Transformations

- Exact algebra (expand, factor, collect)
- Substitution of declared identities (Hermite recurrence, gamma identity)
- Series expansion about x = 0 for the (x+1)^n term only
- Numerical evaluation for regression testing

### Forbidden Transformations

- Integration by parts
- Boundary term discard
- Limit reordering (the limit x → ∞ is not needed here)
- Canonical promotion without human authorization
- Analytical continuation of n beyond integer values

### Symmetries

- sin(pi*z) is periodic with period 2 for integer n: sin(pi*(z + 2k)) = sin(pi*z) for integer k
- H_n(-y) = (-1)^n H_n(y) (Hermite parity)

### Regression Targets

- For n = 0: H_0(y) = 1, gamma(1, x) = exp(-x) → G(x,y,z,0) = exp(-x) + exp(-x) + sin(pi*z)
- For n = 1: H_1(y) = 2y, gamma(2, x) = exp(-x)*(1 + x) → compare with (x+1)*exp(-x)
- For z = 0: sin(0) = 0 → G(x,y,0,n) = (x+1)^n*exp(-x) + gamma(n+1,x)

### Desired Output

A verification report establishing the identity:

```
(x+1)^n * exp(-x) + gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n C(n,k) * x^k / k!
```

where C(n,k) are binomial coefficients, and the sin(pi*z)*H_n(y) term is structurally independent.

### Reporting Goal

Generate a traceable LaTeX report (`generated/report.tex`) with provenance mapping for each identity.
