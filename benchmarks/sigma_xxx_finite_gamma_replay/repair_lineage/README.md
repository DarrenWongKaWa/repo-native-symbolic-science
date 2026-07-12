# Sigma XXX Repair Lineage — Public Flagship Benchmark

## Scientific Problem Boundary

This benchmark demonstrates an end-to-end repair lineage for a one-dimensional projected sigma_xxx (nonlinear conductivity tensor) example. The benchmark shows how a repository-native symbolic-science framework:

1. **Detects** an exact symbolic defect in a pair integration-by-parts (IBP) reduction
2. **Denies** an invalid scientific promotion based on insufficient verification
3. **Rolls back** to the last trusted checkpoint (seven-kernel formula)
4. **Derives** a source-backed repair (corrected r-index)
5. **Independently verifies** a 12x12 exact coupled linear solve
6. **Rejects** both stale false-positive and false-negative artifacts
7. **Separates** model-projected (Rice-Mele) agreement from general tensorial sigma_abc equality
8. **Retains** unaffected numerical evidence despite analytical invalidation
9. **Recovers** a dormant literature comparison after stronger source (PDF) authentication

## What This Benchmark Proves

- A git-native, schema-validated symbolic workflow can catch and repair exact mathematical defects
- Fresh executable replay is more authoritative than frozen structured results
- Projection-based equality (e.g., Rice-Mele) does not prove general tensorial identity
- Numerical evidence can be retained when its derivation is independent of invalidated analytical branches
- Source authentication hierarchy (PDF-authenticated > derived Markdown) resolves comparison ambiguity
- Claim state transitions must be gated and can never be promoted without qualifying evidence

## What This Benchmark Does NOT Prove

- That the sigma_xxx formula is correct for all band structures (tensorial sigma_abc)
- That the repair generalizes beyond the one-dimensional projected example
- That the methodology automatically discovers scientific truth
- That numerical regression alone implies exact symbolic correctness
- Any claim about gamma → 0 or BZ-boundary behavior

## Structure

```
repair_lineage/
├── README.md                           (this file)
├── manifest.yaml                       (benchmark manifest)
├── benchmark_status.json               (current status)
├── active/                             (repaired/verified artifacts)
├── historical/                         (wrong/stale artifacts)
├── fixtures/                           (test fixtures A-I)
├── expected/                           (expected adjudication outcomes)
├── tests/                              (benchmark-specific tests)
├── scripts/                            (benchmark runner scripts)
└── docs/                               (public documentation)
```

## Quick Start

### Fast profile (no Wolfram required)
```bash
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile fast
```

### Standard profile (requires sympy)
```bash
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile standard
```

### Full profile (requires Wolfram)
```bash
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile full
```

## Wolfram Environment Caveat

The fast and standard profiles do not require Wolfram and do not require live
private scientific objects. The full profile requires a clean Wolfram execution
environment.

Local Mathematica startup or autoload files (e.g. MathematicaMCP packages,
custom `init.m` files) may produce output that interferes with machine-readable
benchmark results. An unavailable or contaminated Wolfram environment must
produce a non-PASS result. The benchmark fails closed: it will never report a
false PASS when Wolfram output cannot be parsed.

During independent review, the local full-profile run produced 38/39 because a
MathematicaMCP autoload package corrupted stdout during the 12x12 rank test.
This result was classified as `UNRESOLVED_ENVIRONMENT_FAILURE`. No scientific
claim was promoted from that failed execution.

### Clean-kernel invocation strategy

Where technically possible, invoke Wolfram without user initialization files:

- Use `wolfram -noprompt -rawterm` or `wolframscript` with a controlled
  temporary `$UserBaseDirectory`
- Ensure no autoload packages (`Autoload/`) or `Kernel/init.m` interfere with
  script mode output
- The benchmark uses `subprocess` with `-script` flag; a clean Wolfram
  installation without user-level autoload packages will produce correct output

## Attribution

Scientific source: SIGMAXXX_REPAIR_LINE_016_AUDITABLE_FREEZE and SIGMAXXX_REPAIR_LINE_020_REFERENCE_ALIGNED_FREEZE.
These independently verified freeze packages are the authoritative source for all scientific claims in this benchmark.

## License

Apache-2.0 (consistent with repository). Original copyrighted paper PDF is NOT included.
