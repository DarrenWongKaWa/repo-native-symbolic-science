# Finite-Gamma Sigma_xxx Replay Benchmark

This benchmark publishes a curated finite-Gamma sigma_xxx replay case for the Repo-Native Symbolic Science framework.

## Purpose

The benchmark demonstrates that the framework can ingest structured scientific semantics, construct and execute a derivation DAG, replay supplied mathematical steps, evaluate sector reconstruction, compare against supplied symbolic oracles, perform numerical and Gamma-scaling regressions, evaluate scoped closure conditions, and generate provenance-backed reports.

It does not demonstrate autonomous mathematical discovery.

## Repaired Verification Extension (`repair_lineage/`)

The `repair_lineage/` subdirectory contains a curated public flagship benchmark demonstrating:
- Exact symbolic defect detection
- Invalid scientific promotion denial
- Checkpoint rollback to last trusted state
- Source-backed repair derivation
- Independent exact coupled solve verification
- Stale false-positive and false-negative artifact rejection
- Model-projected agreement vs general equality separation
- Dormant comparison recovery after source authentication

The repair_lineage benchmark is self-contained and requires no private data.

## Scientific Boundary

```text
DC limit first
Gamma finite and exact in the raw one-dimensional sigma_xxx object
then normalization, decomposition, simplification,
closed-form construction and model-specific validation
```

The raw object must not be described as resulting from a prior Gamma-order expansion.

## Decision Provenance

The sanitized conversation extraction in `provenance/conversation_extraction/` is secondary provenance. It records human-confirmed scientific decisions and recovered workflow structure, but it is not the primary oracle and it is not a self-contained algebraic replay package.

The benchmark uses scoped operation authority because integration by parts is only authorized for the documented pair-sector reduction. Human authorization records permission to consider that operation under stated preconditions; it does not by itself verify the mathematical relation.

Pair-sector IBP authority does not authorize center-sector IBP, loop-sector IBP, full-integrand IBP, or any general tensorial `sigma_abc` claim. The current scoped authority status remains `AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION`, with independent verification still `PENDING`.

## Run Commands

Validate the public benchmark package:

```bash
python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay
```

Run the pytest wrapper:

```bash
python3 -m pytest benchmarks/sigma_xxx_finite_gamma_replay/tests
```

Run the repair_lineage benchmark:

```bash
python3 benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py
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

## Documentation

| Document | Purpose |
|----------|---------|
| [repair_lineage/README.md](repair_lineage/README.md) | Repair-lineage benchmark overview and quick start |
| [repair_lineage/docs/scientific_documentation.md](repair_lineage/docs/scientific_documentation.md) | Full scientific documentation |
| [repair_lineage/docs/full_profile_instructions.md](repair_lineage/docs/full_profile_instructions.md) | Wolfram full-profile instructions and caveats |
| [../../docs/case_studies/sigma_xxx_repair_lineage.md](../../docs/case_studies/sigma_xxx_repair_lineage.md) | Public scientific case study |

## Attribution

All source material derives from the independently verified SIGMAXXX_REPAIR_LINE_016 and _020 auditable freeze packages. These reference packages are independently maintained and not included.

See `repair_lineage/docs/` for detailed scientific documentation and acknowledgment policy.
