# Raw Expression

## Expression

```
G(x, y, z, n) = (x + 1)^n * exp(-x) + gamma(n+1, x) + sin(pi*z) * H_n(y)
```

## Expression Language

SymPy-compatible notation.

## Initial Declaration

- x, y, z are real scalar variables
- n is a positive integer (n ∈ ℕ, n ≥ 0)
- exp, sin are standard mathematical functions
- pi is the mathematical constant π ≈ 3.14159...
- Multiplication is commutative for all scalar terms

## Known Identities

The Hermite polynomial satisfies a recurrence relation:

```
H_{n+1}(y) = 2*y*H_n(y) - 2*n*H_{n-1}(y)
```

with H_0(y) = 1, H_1(y) = 2y.

The incomplete gamma function satisfies:

```
gamma(n+1, x) = n! * exp(-x) * sum_{k=0}^n x^k / k!
```

for integer n.

## Missing Definitions

The following symbols do not yet have authoritative definitions and are expected to trigger a human information request:

1. **H_n(y)** — Hermite polynomial: the normalization convention (physicist's vs probabilist's) has not been declared.
2. **gamma(n+1, x)** — The upper vs lower incomplete gamma function has not been explicitly disambiguated.
3. **sin(pi*z)** — The domain of z for periodicity simplifications has not been declared.

These missing definitions are intentional — they demonstrate the semantic escalation protocol in the workflow.
