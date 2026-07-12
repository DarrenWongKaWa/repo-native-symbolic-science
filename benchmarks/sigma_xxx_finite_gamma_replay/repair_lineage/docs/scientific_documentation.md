# Sigma XXX Repair Lineage — Scientific Documentation

## Scientific Problem Boundary

This benchmark concerns a one-dimensional projected example from nonlinear conductivity tensor theory. The sigma_xxx component (diagonal spatial element of the nonlinear conductivity tensor σ_abc) is computed for a finite relaxation-time parameter Γ > 0.

The original derivation followed this pipeline:

```
raw finite-Gamma integrand
  → center-pair-loop decomposition
    → seven-kernel formula (42 components, 7 kernel types)
      → pair IBP reduction (integrates pair term by parts)
        → four-kernel reduced formula (20 components, 4 surviving kernels)
          → general closed form
```

The benchmark focuses on a bounded projected example within this pipeline. It does not claim general tensorial sigma_abc correctness.

## Historical Failure

### What Went Wrong

During integration-by-parts reduction of the pair term, the original derivation used a wrong primitive-index alignment. Specifically, the mapping between derivative order and primitive index was off by one:

**Correct alignment**: `r_primitive = r_target - 1`
**Historical alignment (wrong)**: `r_primitive = r_target`

This r-index error propagated through:
1. The pair IBP identity (which became nonzero-residual)
2. The Stage-3 coupled linear solve (which became rank-deficient)
3. The four-kernel reduced formula (which inherited wrong coefficients)
4. The general closed form (which was an invalidated descendant)

### Why the Initial Validation Was Insufficient

The initial validation relied on structured result summaries (JSON reports claiming PASS) rather than fresh executable replay. When a fresh replay was performed, the exact residual was nonzero. This demonstrates a key design principle: frozen/historical PASS reports are less authoritative than fresh executable replay.

## How the Repair Was Derived

The repair was identified by systematically re-deriving the pair IBP identity from the trusted seven-kernel checkpoint:

1. **Rollback**: The seven-kernel checkpoint (42 components, 7 kernel types) was identified as the last trusted analytic state
2. **R-index audit**: The primitive-index alignment was audited against source definitions
3. **Correction**: `r_primitive = r_target - 1` replaced the wrong `r_primitive = r_target`
4. **Stage-3 re-solve**: The repaired 12x12 linear system was solved, giving rank 12 = augmented rank 12 with a unique exact solution
5. **Identity verification**: All 18 explicit entries produced exact zero residuals

## How Independent Verification Changed Claim Status

The verification process used generator-verifier separation:

1. **Wrong pair identity** → INVALIDATED (exact nonzero residual from fresh replay)
2. **Source-backed repair** → CANDIDATE (linked to 016 freeze package artifacts)
3. **Independent exact replay** → PENDING_INDEPENDENT_VERIFICATION
4. **Equation-by-equation verification** (12 equations, all zero residuals) + seven-kernel reconstruction (ΔK = 0) + boundary applicability → ACTIVE_VERIFIED

Key: the executor who generated the repair could not self-promote to ACTIVE_VERIFIED. An independent_verifier role was required.

## Why Rice-Mele Agreement Was Not a General Proof

The Rice-Mele model is a two-band reduction of the general three-band system. The projection is non-injective:

```
R_general(x, y, z) ≠ 0   (general three-band residual is nonzero)
P_model(R_general) = 0     (two-band Rice-Mele projection evaluates to zero)
```

This means:
- MODEL_SPECIFIC_EQUIVALENCE: The formula agrees with Rice-Mele — this is valid
- GENERAL_SYMBOLIC_IDENTITY: The formula is generally true for all band structures — this is NOT authorized by the projection alone

The benchmark includes a synthetic example demonstrating the same structural property without requiring Rice-Mele-specific copyrighted material.

## Why Numerical Evidence Was Retained

Numerical regression data (80 parameter grid points with all 80 passing) was derived from the raw finite-Gamma integrand through the seven-kernel checkpoint — a path independent of the invalidated pair reduction. This evidence was retained.

Numerical results derived from the invalidated historical closed form were marked RECOMPUTE_REQUIRED because they descended through the tainted analytical branch.

## How Source Authentication Restored the Literature Comparison

An exact comparison between the repaired formula and a literature reference was initially blocked because a derived Markdown transcription of the reference equations contained five categories of typographic ambiguity:

1. **Thermal-function subscript**: Could not reliably distinguish ℱ_E from ℱ_T in transcription
2. **Real-part scope**: Scope of Re[...] operator ambiguous in transcribed form
3. **Spatial vs band derivative index**: Whether index was spatial (k) or band (n)
4. **Degraded appendix transcription**: Appendix typography was unreliable in transcription
5. **Three-band gap-index placement**: Summation convention indexing was ambiguous

Resolution came from PDF-authenticated frozen equation objects (020 reference_objects), which freeze the exact mathematical content from the PDF source. The authority hierarchy is:

```
PDF-authenticated frozen equation object (most authoritative)
  >
Derived Markdown transcription (less authoritative)
```

After ambiguity resolution, the exact normalized regression passed, and the comparison claim was promoted from BLOCKED (STALE_NONAUTHORITATIVE) through CANDIDATE to ACTIVE_VERIFIED.

## What the Benchmark Proves

1. A git-native, schema-validated symbolic workflow can detect and repair exact mathematical defects
2. Fresh executable replay is more authoritative than frozen structured results
3. Projection-based equality does not prove general tensorial identity
4. Numerical evidence derived from independent branches can be retained despite analytical invalidation
5. Source authentication hierarchy resolves comparison ambiguity
6. Claim state transitions must be gated and require appropriate evidence
7. The repository framework correctly enforces all these rules via fail-closed state machine

## What the Benchmark Does NOT Prove

- That sigma_xxx is correct for all band structures (tensorial sigma_abc)
- That the repair generalizes beyond the one-dimensional projected example
- That the methodology automatically discovers scientific truth
- That numerical regression alone implies exact symbolic correctness
- Any claim about gamma → 0 limit behavior
- BZ-boundary cancellation at band crossings

## Attribution and Acknowledgment Policy

### Source Authority

All scientific claims in this benchmark derive from independently verified source packages:

- **Primary source**: SIGMAXXX_REPAIR_LINE_016_AUDITABLE_FREEZE
- **Extension source**: SIGMAXXX_REPAIR_LINE_020_REFERENCE_ALIGNED_FREEZE

These freeze packages are independently maintained and verifiable. Their extraction maps (`public_benchmark_extraction_map.json`) govern what may be publicly exported.

### Copyright

The original copyrighted paper PDF is NOT included in this benchmark. Reference-authenticated equation objects from the 020 freeze replace direct PDF material.

### Derivative Work Classification

This benchmark is a methodological demonstration using:
- Synthetic fixtures (A, B, C, D, E, G) that are independent constructions
- Export-safe source extracts (from 016 and 020) governed by explicit extraction policies
- Structural fingerprints where full data is too large for public benchmark distribution

### Suggested Citation

The repository CITATION.cff provides standard citation metadata for the framework. For this specific benchmark, cite as:

> Sigma XXX Repair Lineage Flagship Benchmark. Repository-Native Symbolic Science framework v0.1.0. Benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/. Based on independently verified source packages SIGMAXXX_REPAIR_LINE_016_AUDITABLE_FREEZE and SIGMAXXX_REPAIR_LINE_020_REFERENCE_ALIGNED_FREEZE.

## Limitations

- The benchmark is a bounded one-dimensional projected example
- The 12x12 linear system uses sanitized/synthetic coefficients that preserve structural properties without exposing private scientific content
- The full Wolfram profile requires Wolfram kernel availability
- Numerical baselines are represented by fingerprints rather than full datasets
- The benchmark demonstrates methodology, not automated scientific truth discovery
