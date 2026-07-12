# Benchmarks

This directory contains public, repository-native benchmarks for the
repo-native-symbolic-science framework.

## Sigma XXX Finite Gamma Replay

The `sigma_xxx_finite_gamma_replay/repair_lineage/` subdirectory contains the
flagship sigma_xxx repair-lineage benchmark. It demonstrates an end-to-end
repair lineage for a bounded one-dimensional projected sigma_xxx example,
exercising:

- Exact symbolic defect detection
- Invalid promotion denial
- Checkpoint rollback to last trusted state
- Source-backed repair derivation
- Independent exact coupled solve verification
- Stale false-positive and false-negative artifact rejection
- Model-projected agreement vs general equality separation
- Dormant comparison recovery after source authentication

### Quick Start

```bash
# Fast profile (no Wolfram): 24 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile fast

# Standard profile (requires sympy): 37 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile standard

# Full profile (requires clean Wolfram): 39 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile full

# Benchmark unit tests: 14 tests
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/tests/test_repair_lineage_benchmark.py
```

### Documentation

- [Benchmark README](sigma_xxx_finite_gamma_replay/repair_lineage/README.md)
- [Public Case Study](../docs/case_studies/sigma_xxx_repair_lineage.md)
- [Full Profile Instructions](sigma_xxx_finite_gamma_replay/repair_lineage/docs/full_profile_instructions.md)
