# Expected Decomposition

This file shows the expected normalization and decomposition result.

---

## Decomposition Result

### Normalized Parent Expression

```
G(x, y, z, n) = T1 + T2 + T3
```

where:
- T1 = (x + 1)^n * exp(-x)
- T2 = gamma(n+1, x)
- T3 = sin(pi*z) * H_n(y)

### Child Sector 1 — Exponential-Polynomial

**Expression**: `F1(x, n) = (x + 1)^n * exp(-x)`

**Properties**:
- Variables: x (positive real), n (non-negative integer)
- Structure: polynomial in (x+1) times exponential decay
- Independent of y and z

**Normalized form**: `(x + 1)^n * exp(-x)` (already normalized)

### Child Sector 2 — Incomplete Gamma

**Expression**: `F2(x, n) = gamma(n+1, x)`

**Properties**:
- Variables: x (positive real), n (non-negative integer)
- Structure: lower incomplete gamma function
- Independent of y and z
- Authorized identity: `gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k / k!`

**Normalized form**: `gamma(n+1, x)` (already normalized; identity substitution deferred to transformation)

### Child Sector 3 — Hermite-Sine

**Expression**: `F3(y, z, n) = sin(pi*z) * H_n(y)`

**Properties**:
- Variables: y (real), z (real), n (non-negative integer)
- Structure: product of trigonometric and Hermite polynomial
- Independent of x

**Normalized form**: `sin(pi*z) * H_n(y)` (already normalized)

### Parent Reconstruction Test

```
Reconstruct = F1(x, n) + F2(x, n) + F3(y, z, n)
            = (x+1)^n * exp(-x) + gamma(n+1, x) + sin(pi*z) * H_n(y)
            = G(x, y, z, n)
```

**Result**: EXACT_RECONSTRUCTION_PASS. Each child term is independently addressable and the sum recovers the original expression exactly.

### Structural Summary

| Property | Value |
|----------|-------|
| Total terms | 3 |
| Independent sectors | 3 |
| Free variables | 4 (x, y, z, n) |
| Special functions | 3 (exp, gamma, sin, H) |
| Transcendental | Yes (exp, sin, gamma) |
| Polynomial subset | F1 is polynomial in (x+1) when n is fixed |
| Dummy indices | None |
| Noncommutative objects | None |

### Note on Sector Independence

Sectors 1 and 2 are both functions of (x, n) and are NOT completely independent — they share variables. The decomposition records this coupling so that the transformation skill can exploit the authorized gamma identity, which relates `gamma(n+1, x)` directly to `(x+1)^n * exp(-x)` through the binomial expansion of `(x+1)^n`.
