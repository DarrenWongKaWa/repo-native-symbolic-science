# Contributing

Thank you for your interest in contributing to Repo-Native Symbolic Science.

## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the full validation procedure below
5. Submit a pull request

## Governance

Read `REPO_POLICY.md` (model-neutral authority) and `AGENTS.md` (scientific
workflow/agent rules) before contributing. Do not weaken the scientific
safeguards: no invented scientific assumptions, no implicit IBP authorization,
no silent limit reordering, no numerical-to-symbolic promotion, no automatic
canonical promotion, and provenance is preserved.

## Developer Setup

Use a disposable virtual environment; do not install packages globally:

```bash
python3 -m venv /tmp/rnss-venv
source /tmp/rnss-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,extended-numerics]'
```

Runtime dependencies are `sympy`, `numpy`, `jsonschema` (see
`pyproject.toml`); `[test]` adds pytest/pyyaml and `[extended-numerics]` adds
scipy/mpmath. Do not install or replace a Mathematica/Wolfram runtime
globally. The B3 second engine only accepts the fixed pinned
`/Applications/Wolfram Engine.app` installation; without it, second-engine
confirmation is withheld (fail-closed), never faked.

## Validation Procedure

Run all of the following from the repository root before submitting:

```bash
# Full test suite
python3 -m pytest -q

# Frozen release verification bundle (Gate 1-5 + full pytest + secret scan)
python3 verification/viper/run_release_verification.py

# Controller CLI smoke checks
python3 scripts/orch_controller.py --help
python3 scripts/orch_controller.py list-roles
python3 scripts/orch_controller.py list-operations
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
python3 scripts/orch_controller.py check-transition --from EXECUTING --to EXECUTION_COMPLETE
# Invalid transitions must fail closed (expected nonzero exit):
python3 scripts/orch_controller.py check-transition --from RECEIVED --to EXECUTING

# Engine fixture suite
python3 tests/engine_fixtures/run_fixture_suite.py

# Public sigma_xxx finite-Gamma replay benchmark
python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay

# C0 compactification loop
python3 -m pytest tests/test_c0_compactification_loop.py

# Literal Anan D3 bridge demo (end-to-end scientific stress test)
bash demos/literal_anan_d3_bridge/run_all.sh

# Theoretical-physics stress examples (positive claims + wrong-physics mutations)
python3 examples/physics_stress/run_all.py
```

Final hygiene checks:

```bash
git diff --check
python3 -m compileall -q loop_engine validators scripts
git status --short   # tests must not leave generated junk in the working tree
```

## Code Style

- Python: PEP 8
- JSON schemas: draft-07
- Markdown: CommonMark

## What Not to Delete

Scientific evidence is not clutter. Preserve provenance artifacts, frozen
inputs, fixtures, certificates, reviewer packets, schemas, expected outputs,
source snapshots, and historical checkpoint material. A tracked file may only
be removed when it is unreferenced, superseded, and not part of any manifest,
hash lock, fixture, or claim-evidence contract — and the full validation
procedure above still passes after its removal.
