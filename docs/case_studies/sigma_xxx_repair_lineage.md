# Sigma XXX Repair Lineage — Public Scientific Case Study

## Scientific Scope

This case study documents the bounded, public scientific story of the sigma_xxx
repair lineage. The benchmark covers:

- A **projected one-dimensional sigma_xxx** example (diagonal element of the
  nonlinear conductivity tensor)
- **DC limit** taken before closed-form derivation
- **Finite Gamma** kept exact — no pre-raw Gamma expansion
- No claim of general tensorial sigma_abc verification

The exercise demonstrates how a repository-native symbolic-science framework
detects an exact mathematical defect, rolls back to the last trusted
checkpoint, derives a source-backed repair, independently verifies the result,
and enforces rigorous claim-state governance.

## Trusted Checkpoint: The Seven-Kernel Formula

The last trusted analytic checkpoint before the historical IBP reduction is the
seven-kernel formula:

```
I_seven = I_center + I_pair,R + I_v- + I_v+ + I_v_epsilon + I_loop,ReL + I_loop,ImL
```

Where the seven kernel types contain, per ± sign:

| Kernel | Components per ± sign | r-indices |
|--------|----------------------|-----------|
| K_center | 3 | r = 2,3,4 |
| K_pair,R | 2 | r = 1,2 |
| K_v- | 4 | r = 0,1,2,3 |
| K_v+ | 3 | r = 1,2,3 |
| K_v_epsilon | 3 | r = 0,1,2 |
| K_loop,ReL | 3 | r = 0,1,2 |
| K_loop,ImL | 2 | r = 0,2 |

Total: 42 components under 7 kernel types.

This checkpoint is frozen in `active/repaired_pair_ibp/SevenKernelFormulaTrusted.wl`
and is the rollback target for all invalidated descendants.

## Historical Failure

### What went wrong

During integration-by-parts (IBP) reduction of the pair term, four
second-pass velocity primitives used the **wrong thermal order**. The r-index
mapping between primitive and derivative target was off by one:

- **Correct (source-backed)**: `r_primitive = r_target - 1`
- **Historical (wrong)**: `r_primitive = r_target`

The reasoning: differentiation of the Bose-Einstein distribution raises the
thermal order by one. To produce a target at order `r_target`, the primitive
must be at order `r_target - 1`.

The wrong candidate produced an **exact nonzero residual** when replayed.
Promotion was denied. Stale PASS summaries were not accepted as authoritative
evidence.

### The pipeline affected

```
raw finite-Gamma integrand
  → center-pair-loop decomposition
    → seven-kernel formula (42 components)
      → pair IBP reduction  ← CONTAINS WRONG R-INDEX
        → four-kernel reduced formula (inherits wrong coefficients)
          → general closed form (invalidated descendant)
```

## Rollback

When the wrong r-index was detected, the analytic line rolled back to the
seven-kernel checkpoint (`CP_SEVEN_KERNEL`). All descendants of the invalid
pair reduction lost authority:

- `CP_PAIR_REDUCTION_HISTORICAL` → INVALIDATED
- `CP_CLOSED_FORM_HISTORICAL` → SUPERSEDED

The independent pre-IBP numerical baseline (`CP_NUMERICAL_BASELINE`), which
descends from the decomposition checkpoint rather than the pair reduction,
remains retainable.

## Repair and Verification

### Source-backed Candidate A

The repair corrects the primitive-index alignment using source-backed
definitions from the 016 auditable freeze package. The 18 explicit primitive
entries produce 17 irreducible structures.

### Exact 12×12 coupled solve

The repaired pair IBP identity generates a 12×12 exact linear system for the
unknown pair coefficients. Solved exactly:

- **Rank**: 12
- **Augmented rank**: 12
- **Nullity**: 0
- **Unique solution**: yes
- **All 12 equation residuals**: zero

### Repaired local pair identity

The repaired pair total-derivative identity (`PairIBPResidualRepairedFinal.wl`)
confirms all 8 residual components are identically zero. The BZ-boundary
applicability gate passes. The exact seven-to-four-kernel reconstruction
(DeltaK = 0) completes the verification.

### Historical coefficient status

The historical proof certificate was invalid, but the **surviving four-kernel
coefficients were nevertheless unchanged** by the repair. The repaired
derivation supplies the valid proof chain. The old closed form is not claimed
to be scientifically false — only that its proof chain is invalid.

## Projection Boundary

Rice-Mele or another two-band projection can satisfy:

```
P_model(R_general) = 0
```

while:

```
R_general != 0
```

Therefore model-specific agreement cannot prove a general symbolic identity.
The benchmark correctly separates:

- **MODEL_SPECIFIC_EQUIVALENCE** — authorized under projection
- **GENERAL_SYMBOLIC_IDENTITY** — cannot be promoted from projection alone

## Numerical Provenance

Numerical artifacts descending from the raw/pre-IBP line may be retained
because their derivation path is independent of the invalidated pair reduction:

| Baseline | Derivation path | Status |
|----------|----------------|--------|
| Raw finite-Gamma numerical | raw → decomposition → seven_kernel → numerical | RETAINABLE_BASELINE |
| Historical closed-form numerical | raw → … → pair_reduction → closed_form → numerical | RECOMPUTE_REQUIRED |

## Reference Authentication

The public methodological sequence for comparing the repaired formula against a
literature reference is:

1. **Derived Markdown transcription** → exact comparison **blocked** by five
   categories of typographic ambiguity
2. **PDF-authenticated equation objects** → ambiguities resolved
3. **Explicit recovery event** → comparison returns to candidate state
4. **Exact normalized comparison** → verified

### Ambiguity categories resolved by source authentication

- Thermal-function subscript (ℱ_E vs ℱ_T)
- Real-part operator scope (Re[...])
- Spatial versus band derivative index (k vs n)
- Degraded appendix transcription
- Three-band gap-index placement

The repaired projected sigma_xxx formula matched the PDF-authenticated
reference Eq. (5) after declared notation and normalization conversion.

The original copyrighted source PDF is **not** included in the repository.

## What Is Proved

- A git-native symbolic workflow can detect and repair exact mathematical defects
- Fresh executable replay is more authoritative than frozen structured results
- Projection-based equality does not prove general tensorial identity
- Numerical evidence from independent derivation branches survives analytical invalidation
- Source authentication hierarchy (PDF > derived Markdown) resolves comparison ambiguity
- Claim state transitions must be gated and cannot be promoted without qualifying evidence

## What Is Not Claimed

- Full sigma_abc verification is not claimed
- General proof from model projection is not claimed
- Exact proof from numerical agreement alone is not claimed
- Automatic scientific truth discovery is not claimed
- Authority of OCR/Markdown over original source typography is not claimed

## Benchmark Fixtures

All fixtures are located under `benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/`. See `manifest.yaml` for the complete fixture manifest.

| Fixture | Description |
|---------|------------|
| A | Wrong r-index vs source-backed repair |
| B | 12×12 exact coupled linear solve |
| C | Stale false positive rejection |
| D | Stale false negative dormancy and recovery |
| E | Checkpoint rollback to seven-kernel |
| F | Full promotion chain (wrong → invalidated → candidate → verified) |
| G | Non-injective projection trap |
| H | Numerical provenance retention |
| I | Reference source authentication recovery |

## Commands

```bash
# Fast profile (no Wolfram)
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile fast

# Standard profile (requires sympy)
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile standard

# Full profile (requires clean Wolfram environment)
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile full

# Benchmark tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/tests/test_repair_lineage_benchmark.py
```
