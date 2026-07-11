# Repo-Native Symbolic Science

A repo-native framework for auditable human-agent symbolic science, with semantic escalation, independent verification, provenance governance, and traceable scientific reporting.

## Purpose

This project provides a repo-native framework for auditable human-agent symbolic science. It establishes a structured environment where human scientists define semantics and assumptions, agents manage planning and governance, CAS/numerical engines perform bounded computation, and independent verifiers replay and adjudicate results.

## Human-Agent Responsibility Split

- **Human scientist**: scientific semantics, assumptions, and authorization
- **Agent**: planning, orchestration, and claim governance
- **CAS/numerical engine**: bounded computation
- **Independent verifier**: replay, comparison, and adjudication

## Supported Backends

- **SymPy**: open-source exact symbolic baseline (required)
- **NumPy / SciPy / mpmath**: numerical and high-precision support (required)
- **Mathematica**: optional verified commercial backend (optional, not mandatory)

## Scientific Safeguards

- The framework does not invent scientific assumptions
- The framework does not automatically authorize IBP (Integration By Parts)
- The framework does not silently reorder scientific limits
- Numerical agreement does not establish symbolic equality
- Automatic canonical promotion is forbidden

## End-to-End Case Boundary

- An end-to-end scientific reference case exists (private, not included)
- Public examples are synthetic and redistributable
- Private sigma_xxx and sigma_abc research content is excluded

## Limitations

1. **ENGINE_003 VERIFICATION STATUS**: The multi-backend CAS adapter layer has been verified as MINIMUM_MULTI_BACKEND_CAS_ADAPTER_LAYER_VERIFIED_WITH_CAVEAT. See below for documented caveats.

2. **Mathematica Availability**: Mathematica path is optional; release success does not require Mathematica availability outside the verified local environment.

3. **Symbolic vs Numerical Claims**: Exact symbolic claims remain separate from numerical claims; numerical agreement does not establish symbolic equality.

4. **Capability Safety**: Unsupported capability fails safely; the capability resolver returns bounded failure for unrecognized operations.

5. **Cross-Engine Verification Boundary**: A contract form with repeated up index in cross-engine verification is documented as a usage boundary; it produced valid results in the run but is treated as a form error.

6. **Alternate E2 Naming Caveat**: An alternate naming convention for E2 (end-to-end) fixtures exists as a separately documented view. This does not affect functional correctness but should be noted when comparing fixture naming across environments.

## Quick Start

```bash
# Install dependencies
pip install sympy numpy scipy mpmath jsonschema

# Run public fixture suite
python3 tests/engine_fixtures/run_fixture_suite.py

# Run reuse fixture suite
python3 scripts/run_reuse_fixture_suite.py
```

## Project Structure

```
├── README.md
├── LICENSE
├── pyproject.toml
├── engines/           # Multi-backend CAS adapter layer
├── schemas/           # JSON schemas for artifacts
├── scripts/           # Orchestration and validation scripts
├── skills/            # Agent skills for symbolic workflows
├── task_templates/    # Task definition templates
├── policies/          # Governance policies
├── tests/             # Public fixture suites
├── examples/          # Synthetic end-to-end examples
├── fixtures/          # Synthetic reporting fixtures
└── docs/              # Architectural and workflow documentation
```

## Acknowledgements

The framework was developed and stress-tested during nonlinear-transport research undertaken in collaboration with Zhichao Guo.

## License

Apache-2.0 — see [LICENSE](./LICENSE)

Copyright 2026 Kawa Wong. All rights reserved.
