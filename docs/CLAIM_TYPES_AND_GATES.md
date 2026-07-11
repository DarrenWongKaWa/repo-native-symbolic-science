# Claim Types and Gates

This document explains the claim types, relation types, and gates used in the Repo-Native Symbolic Science verification and provenance system.

---

## Relation Types

Every assertion about a relationship between expressions is assigned a `relation_type`. The type determines what evidence is required and what conclusions may be drawn.

### literal_equality

Two expressions are literally identical — same symbols, same structure, same ordering.

**Required evidence**: Byte-for-byte or parse-tree identity.

**Example**: `a + b` and `a + b` (same expression object).

**Cannot conclude**: Anything about scientific correctness — only that the expressions are syntactically identical.

### identity_under_assumptions

Two expressions are mathematically equal under declared assumptions.

**Required evidence**: Exact simplification of the difference to zero, with all assumptions recorded.

**Example**: `(a + b)^2 = a^2 + 2*a*b + b^2` under commutativity of a and b.

**Caveat**: The identity only holds within the declared assumption scope.

### pointwise_identity

Two expressions agree at every point in a continuous domain.

**Required evidence**: Exact symbolic subtraction yielding zero for all parameter values in the domain.

**Example**: `sin(x)^2 + cos(x)^2 = 1` for all real x.

**Caveat**: Pointwise identity says nothing about integrals, derivatives, or distributions. A pointwise identity over a domain does not imply the integrated identity is zero.

### projected_identity

Two expressions agree when projected onto a specific basis or subspace.

**Required evidence**: Projection coefficients match exactly.

**Example**: A tensor identity `T^{ab} = S^{ab}` verified only for the diagonal components (a = b).

**Caveat**: Projection equality does not imply global equality. The result cannot be claimed for unprojected components.

### integrated_identity

An integrated quantity equals zero under declared boundary conditions.

**Required evidence**: Exact symbolic integration plus boundary condition evaluation.

**Example**: `∫_Ω ∂_a J^a dV = 0` when `J^a` vanishes on the boundary ∂Ω.

**Caveat**: Requires explicit integration domain and boundary condition declarations. Pointwise total derivative ≠ integrated zero without boundary specification.

### structural_replay

The structural form (term count, operation sequence, index structure) of a result matches an independent recomputation.

**Required evidence**: Independent engine execution yields matching structural properties.

**Example**: Two different engines produce results with the same term count and index contraction pattern.

**Caveat**: Structural agreement does not guarantee numerical or symbolic equality.

### numerical_regression

Numerical evaluation at sample points agrees within tolerance.

**Required evidence**: Numerical evaluation at declared sample points with declared tolerance.

**Example**: `|F(p_i) - G(p_i)| < 10^{-12}` for 1000 random points p_i.

**Caveat**: **Numerical agreement does not establish symbolic equality.** Numerical regression is supporting evidence only.

### counterexample

A specific counterexample disproves a claimed relation.

**Required evidence**: A concrete point or configuration where the claimed relation fails.

**Example**: If `sqrt(x^2) = x` is claimed for all real x, the counterexample `x = -1` gives `1 ≠ -1`.

**Implication**: The claimed relation is false. The counterexample must be independently verifiable.

### not_established

The claimed relation has not been verified.

**Required evidence**: None (this is the default state).

**Implication**: No conclusion may be drawn. The relation remains unverified.

### canonical_result

A verified result that has been explicitly authorized as the accepted reference form.

**Required evidence**: All verifications accepted, human gate passed, Blocker 5 lifted.

**Implication**: The result is the authoritative reference for downstream work. Canonical results may be superseded but not silently modified.

---

## Why These Distinctions Matter

### numerical_agreement != symbolic_equality

A numerical evaluation may agree to 100 decimal places at a million points and still miss a subtle symbolic identity that becomes visible only in the exact algebraic structure.

**Example**: `F(x) = sin(1/x)` and `G(x) = sin(1/(x + 10^{-50}))` agree numerically at all computable sample points but are symbolically distinct.

**Rule**: Numerical evidence is supporting only. Exact symbolic equality must be established by exact algebraic methods (difference simplification, structural transformation).

### projection_equality != global_equality

Verifying an identity on a subset of components or a specific projection does not verify it globally.

**Example**: `T^{ab} = 0` verified for a = b (diagonal) does not imply `T^{ab} = 0` for a ≠ b (off-diagonal).

**Rule**: The claim scope must match the verification scope. A projected verification only supports a projected claim.

### verified_candidate != canonical_result

A candidate that passes verification is a "verified candidate" — not a canonical result. Canonical promotion is a separate human-gated decision.

**Rule**: Verified candidates are trustworthy for inspection and further work, but they are not the authoritative reference until explicitly canonized by the human scientist.

### pointwise_total_derivative != integrated_zero

A total derivative `∂_a J^a` that is zero in the interior does not guarantee that its integral over the domain is zero — boundary terms may not vanish.

**Example**: In electromagnetism, `∂_μ F^{μν} = J^ν` integrates to a conserved charge only when boundary conditions (fields vanish at spatial infinity) are declared and verified.

**Rule**: Integrated zero claims require explicit domain and boundary condition declarations. Pointwise derivative identities do not automatically imply integrated identities.

---

## Verification Methods

The framework supports 10 verification methods, selected automatically by the verifier skill:

| Method | Used For | Produces |
|--------|----------|----------|
| `exact_difference_subtraction` | Exact symbolic equality | `0` or nonzero residue |
| `exact_reconstruction` | Parent-child or transformation reversibility | Reconstructed expression |
| `structural_replay` | Independent recomputation | Structural comparison |
| `projection_comparison` | Projected/basis comparisons | Projection coefficients |
| `integrated_identity_check` | Integrated identities with boundaries | Integral evaluation |
| `numerical_sampling` | Supporting numerical evidence | Numerical residuals |
| `high_precision_sampling` | High-precision numerical support | High-precision residuals |
| `counterexample_search` | Disproving false claims | Counterexamples |
| `regression_scan` | Regression against known targets | Regression report |
| `formal_scope_audit` | Auditing claim scope and assumptions | Scope/assumption validation |

---

## Claim Status Lifecycle

```
PROVISIONAL → VERIFIED → HUMAN_ACCEPTED → CANONICAL
                  ↓              ↓
             VERIFIED_WITH_CAVEAT  REJECTED
                  ↓
              SUPERSEDED
```

- **PROVISIONAL**: Initial state; unverified.
- **VERIFIED**: Passed independent verification.
- **VERIFIED_WITH_CAVEAT**: Passed verification with documented caveats (e.g., missing boundary condition, restricted domain).
- **HUMAN_ACCEPTED**: Human scientist has explicitly accepted the verified result.
- **REJECTED**: Verification failed or human rejected.
- **SUPERSEDED**: A later result supersedes this one; preserved for provenance.
- **CANONICAL**: Authoritative reference form; human-gated.
- **FORBIDDEN**: The claim crosses a forbidden boundary and may not be made.

---

## Forbidden Promotions

The following promotion paths are explicitly forbidden and will be blocked:

| From | To | Reason |
|------|----|--------|
| PROVISIONAL | VERIFIED | Requires independent verification |
| PROVISIONAL | HUMAN_ACCEPTED | Skips verification gate |
| PROVISIONAL | CANONICAL | Skips all gates |
| VERIFIED | CANONICAL | Requires human gate |
| VERIFIED_WITH_CAVEAT | CANONICAL | Caveats must be resolved or accepted |
| NUMERICAL_REGRESSION | EXACT_SYMBOLIC | Category error |
| PROJECTED_IDENTITY | GLOBAL_IDENTITY | Scope expansion without evidence |
| POINTWISE_IDENTITY | INTEGRATED_IDENTITY | Missing boundary evidence |

---

## Summary Table

| Claim | Required Evidence | Common Pitfall |
|-------|------------------|----------------|
| literal_equality | Parse-tree identity | Does not guarantee mathematical correctness |
| identity_under_assumptions | Exact difference = 0 + assumptions | Assumptions must be declared |
| pointwise_identity | Exact subtraction = 0 for all points | Not integrated |
| projected_identity | Projection coefficient match | Not global |
| integrated_identity | Exact integral + boundary evaluation | Needs boundary conditions |
| structural_replay | Independent structural match | Not a numerical guarantee |
| numerical_regression | Sampling within tolerance | ≠ symbolic equality |
| counterexample | Concrete disproof | Negates the claim |
| not_established | None (default) | Cannot conclude anything |
| canonical_result | All verifications + human gate + Blocker 5 | Cannot be created automatically |
