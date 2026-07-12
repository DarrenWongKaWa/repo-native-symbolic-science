# Finite-Gamma Sigma_xxx Replay Benchmark

This benchmark publishes a curated finite-Gamma sigma_xxx replay case for the Repo-Native Symbolic Science framework.

## Purpose

The benchmark demonstrates that the framework can ingest structured scientific semantics, construct and execute a derivation DAG, replay supplied mathematical steps, evaluate sector reconstruction, compare against supplied symbolic oracles, perform numerical and Gamma-scaling regressions, evaluate scoped closure conditions, and generate provenance-backed reports.

It does not demonstrate autonomous mathematical discovery.

## Scientific Boundary

```text
DC limit first
Gamma finite and exact in the raw one-dimensional sigma_xxx object
then normalization, decomposition, simplification and closed-form processing
```

The raw object must not be described as resulting from a prior Gamma-order expansion.

## Run Command

Validate the public benchmark package:

```bash
python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay
```

Run the pytest wrapper:

```bash
python3 -m pytest benchmarks/sigma_xxx_finite_gamma_replay/tests
```

The historical replay executor is included at `execution/run_case003r1_replay.py`, but this public benchmark package does not include the private `source_snapshots/` tree needed for a full replay. Do not treat the local validation command above as an independent scientific verifier.

## Dependencies

The public validation uses Python standard library parsing plus PyYAML when available. The original replay used Python with PyYAML and optional Wolfram tooling in the private environment.

## Reference Result

Reference result: `NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS`.

Independent verification: `PENDING`.

Local exact algebra: `LOCAL_EXACT_ALGEBRA_CLOSED = PASS_WITH_CAVEAT`.

Gamma-scaling slopes are executor-generated numerical support, not exact symbolic proof:

- insulating small-Gamma slope: `1.9845925371006055`
- metallic/high-mu slope: `0.9932470742383429`
