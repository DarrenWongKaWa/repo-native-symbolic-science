# Human Scientist Guide

This guide explains the responsibilities of the human scientist in the Repo-Native Symbolic Science workflow. The framework handles planning, orchestration, computation, verification, and provenance — but the human scientist owns the scientific semantics.

---

## Scientist Responsibilities

### 1. Definitions

Every symbol, operator, function, tensor, and special object in a raw expression must have an authoritative scientific definition. The framework will not infer definitions from notation alone.

**Good definition**:
> `sigma_ab` is the dimensionless conductivity tensor with indices a,b ∈ {x, y, z} in the lab frame. It is symmetric: `sigma_ab = sigma_ba`. It is real-valued.

**Incomplete definition**:
> `sigma` is conductivity.

The framework will escalate when definitions are incomplete.

### 2. Index Roles

For indexed (tensorial) expressions, the human scientist must declare the role of every index. The framework uses an expanded Einstein summation convention with distinct roles:

| Index Role | Description | Example |
|------------|-------------|---------|
| Free | External index not summed | `a, b` in `T^{ab}` |
| Dummy | Summed internal index | `c` in `T^{ac} W_c` |
| Band | Internal quantum number summed over bands | `m, n` in `H_{mn}` |
| Spatial | Real-space coordinate index | `x, y, z` |
| External | Index coupling to external fields | `α` in source terms |

**Good declaration**:
> Indices a, b, c are free external tensor indices. Index c in `V^c W_c` is a dummy summation index. Indices m, n, l are internal band indices summed over all bands.

**Incomplete declaration**:
> Indices run from 1 to 3.

### 3. Assumptions

Declare all scientific assumptions explicitly before computation begins. The framework does not invent assumptions.

**Required assumption categories**:
- **Domain** (real, complex, positive, compact)
- **Symmetries** (symmetric tensors, parity, time reversal)
- **Nondegeneracy** (full rank, nonzero determinants, smooth frames)
- **Convergence** (series expansions, integral convergence)
- **Commutativity** (which operators/fields commute)

**Good**:
> All variables are real scalars. The matrix M is real symmetric and positive definite. The series expansion is taken about x = 0 with radius of convergence R > 0. The limit x → 0 is taken first, then the thermodynamic limit.

**Incomplete**:
> Everything is well-behaved.

### 4. Symmetries

Declare symmetry conditions that may enable simplification:

- **Tensor symmetries**: `T_{ab} = T_{ba}`, `T_{ab} = -T_{ba}`
- **Parity**: even/odd under spatial inversion
- **Time reversal**: even/odd under T → -T
- **Gauge**: choice of gauge fixing condition
- **Rotational**: SO(3) or other group invariance

Symmetries are scientific facts, not mathematical shortcuts. The framework will not assume a symmetry unless it is explicitly declared.

### 5. Limit Order

When multiple limits, expansions, or approximations are involved, the human scientist must specify the order in which they are taken.

**Good**:
> First take the zero-frequency limit ω → 0, then take the long-wavelength limit q → 0. The two limits do not commute.

**Incomplete**:
> Take the limits.

The framework treats non-commuting limits as a semantic blocker. It will not silently reorder limits.

### 6. Allowed Transformations

Declare which transformation types are authorized for a given task.

| Transformation | Example | Requires |
|----------------|---------|----------|
| Exact algebra | expand, factor, cancel | None (always allowed) |
| Scientific identities | substitute declared identity | Identity must be in adapter |
| Differentiation | ∂/∂x | None |
| Series expansion | Taylor about x=0 | Convergence assumptions |
| Integration by parts (IBP) | ∫ u dv = uv - ∫ v du | Explicit human authorization |
| Boundary term discard | surface term → 0 | Boundary conditions + authorization |
| Integrated cancellation | ∫ (∂F) = 0 | Domain + boundary + authorization |
| Canonicalization | declare as final form | Human gate required |

**Good**:
> Allow exact algebra (expand, factor, cancel) and authorized scientific identities at levels A–C. Forbid integration by parts, boundary term discard, and canonical promotion.

**Incomplete**:
> Simplify the expression.

### 7. Forbidden Transformations

Declare explicitly which transformations must not be applied, even if the framework could apply them.

Common forbidden transformations:
- Integration by parts without explicit per-case authorization
- Discarding boundary or surface terms
- Reordering limits without checking commutativity
- Expanding protected parameters (e.g., small expansion parameters)
- Applying identities at higher transformation levels than declared

The framework treats forbidden operations as hard blockers.

### 8. Boundary Conditions

When integration, IBP, or integrated identities are involved, boundary conditions must be fully specified:

- **Domain of integration**: compact, infinite, periodic
- **Boundary behavior**: fields vanish at boundary, periodic, or fixed
- **Surface terms**: which surface terms are zero and why

### 9. Comparison Targets

Provide known results for regression testing:

- **Exact identities**: known closed-form results
- **Special limits**: known behavior as parameter → 0 or ∞
- **Numerical values**: known values at specific points
- **Conservation laws**: quantities that must be conserved

Comparison targets are used as regression checks, not as proof of symbolic identity.

### 10. Canonical Promotion Decisions

Only the human scientist may authorize canonical promotion — the declaration that a verified result is the accepted reference form. This decision:

- Is irreversible (superseded results are preserved but marked as historical)
- Requires all verifications to be accepted
- Requires the global guard (Blocker 5) to be lifted by explicit human acknowledgement
- Creates a new canonical state that downstream work may depend on

**Required for canonical promotion**:
1. Explicit authorization statement from the human scientist
2. All parent verifications accepted
3. All assumptions documented
4. All caveats recorded
5. Blocker 5 explicitly acknowledged as lifted

---

## Examples of Good Scientific Requests

### Complete Request

> My raw expression is:
> ```
> F = T^{ab} * W_{b} + V^{a} * (∂_{c} S^{c})
> ```
> Definitions:
> - `T^{ab}`: symmetric stress-energy tensor (a,b free external indices)
> - `W_b`: external vector potential (b free external index, summed against T^{ab})
> - `V^{a}`: velocity field (a free external index)
> - `S^{c}`: source current (c dummy summation index in divergence)
> - ∂_{c}: partial derivative with respect to coordinate c
>
> Assumptions: All fields are real, smooth, and decay at infinity. The domain is flat 3D Euclidean space. Einstein summation convention over repeated indices.
>
> Allowed: Exact algebra (expand, factor). Differentiation. Index contraction.
> Forbidden: Integration by parts. Boundary term discard. Limit reordering.
>
> Target: Factor common terms and identify conserved currents.
> Regression: F should reduce to T^{ab} * W_b when S^{c} = 0 (source-free case).

### Incomplete Request (Will Trigger Escalation)

> Simplify F = T^{ab} W_b + stuff.

The framework will escalate because:
- "stuff" is not defined
- Index roles for a, b are not declared
- No definitions for T^{ab} or W_b
- No assumptions or allowed operations declared
- No target form specified

---

## What the Scientist Does NOT Need to Do

The human scientist does NOT need to:
- Choose schemas or validators
- Select computation backends
- Write workflow orchestration code
- Manage task lifecycles manually
- Run fixture suites
- Generate provenance manifests or SHA hashes
- Format verification reports

These are agent responsibilities governed by the framework's skills and policies.
