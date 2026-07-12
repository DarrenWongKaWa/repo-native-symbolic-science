# Benchmarks

This directory contains public, repository-native benchmarks for the
repo-native-symbolic-science framework.

## Sigma XXX Finite Gamma Replay

The `sigma_xxx_finite_gamma_replay/` directory contains two related public
benchmarks:

1. **Original finite-Gamma replay benchmark** — demonstrates framework ingestion
   of structured scientific semantics, derivation-DAG replay, sector
   reconstruction checks, symbolic-oracle comparison, numerical and
   Gamma-scaling regressions, scoped closure evaluation, and provenance-backed
   reporting. Run with:
   ```bash
   python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay
   ```

2. **Repair-lineage flagship benchmark** (`repair_lineage/`) — demonstrates an
   end-to-end repair lineage for a bounded one-dimensional projected sigma_xxx
   example, exercising:
   - Exact symbolic defect detection
   - Invalid promotion denial
   - Checkpoint rollback to last trusted state
   - Source-backed repair derivation
   - Independent exact coupled solve verification
   - Stale false-positive and false-negative artifact rejection
   - Model-projected agreement vs general equality separation
   - Dormant comparison recovery after source authentication

### Repair-Lineage Quick Start

```bash
# Fast profile (no Wolfram): 24 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile fast

# Standard profile (requires sympy): 37 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile standard

# Full profile (requires clean Wolfram; known 38/39 due to env): see caveat below
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile full

# Benchmark unit tests: 14 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/tests/test_repair_lineage_benchmark.py
```

### Full Profile Caveat

The full Wolfram profile contains 39 tests. During independent review, the
local full-profile run produced **38/39** because MathematicaMCP autoload
initialization polluted the namespace during a pristine-environment requirement.
The failing test is classified as `UNRESOLVED_ENVIRONMENT_FAILURE`
(fail-closed), not a benchmark defect or scientific failure. See
[full profile instructions](sigma_xxx_finite_gamma_replay/repair_lineage/docs/full_profile_instructions.md)
for mitigation steps.

### Documentation

- [Benchmark README](sigma_xxx_finite_gamma_replay/README.md)
- [Repair-Lineage README](sigma_xxx_finite_gamma_replay/repair_lineage/README.md)
- [Public Case Study](../docs/case_studies/sigma_xxx_repair_lineage.md)
- [Full Profile Instructions](sigma_xxx_finite_gamma_replay/repair_lineage/docs/full_profile_instructions.md)
- [Scientific Documentation](sigma_xxx_finite_gamma_replay/repair_lineage/docs/scientific_documentation.md)
