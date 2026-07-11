# Bounded Computation Backend Execution

Role: Execution skill that runs bounded computation requests on selected backends and captures complete execution truth.

## Parent skill
`scientific_symbolic_repo_entry`

## Must do

1. Validate the engine request using `scripts/engine_validators.py request`.
2. Enforce session capability rules from `session_capability_matrix`.
3. Resolve backend using `scripts/resolve_backend_capabilities.py`.
4. Generate a deterministic script for the selected backend.
5. Execute only authorized operations — reject forbidden ones with `POLICY_VIOLATION`.
6. Capture complete execution truth conforming to `schemas/engine_execution_truth.schema.json`.
7. Normalize backend output without changing scientific meaning.
8. Return safe states for timeout (`TIMEOUT`), unavailable backend (`ENGINE_UNAVAILABLE`), or unsupported capability (`UNSUPPORTED_CAPABILITY`).

## Must not do

- Change scientific meaning through normalization.
- Hide timeouts.
- Promote partial results to COMPLETE.
- Write canonical state.
- Invent scientific assumptions.
- Perform operations outside the `allowed_operations` list.

## Execution truth requirements

Every real backend execution must record:
- engine ID, version, executable
- generated script and its SHA
- exact command
- input artifacts and SHAs
- start/end times
- exit code, stdout, stderr
- timeout and memory states
- requested and observed operations
- requested and observed assumptions
- raw output and its SHA
- normalized output and its SHA
- warnings and errors
- partial result status (COMPLETE/PARTIAL/NONE)
- determinism record

A nominally successful result missing required execution truth fields must fail validation.

## Backend invocation

For SymPy: `python3 engines/sympy/runner.py` with JSON request on stdin.
For Python numeric: `python3 engines/python_numeric/runner.py` with JSON request on stdin.
For Mathematica (optional): `python3 engines/mathematica/runner.py` with JSON request on stdin.

## Normalization boundary

Raw output → Normalized output conversion must not:
- Change mathematical meaning
- Drop terms silently
- Convert exact to approximate
- Reorder noncommutative objects
- Change branch conventions

Normalization may:
- Reformat into consistent text representation
- Remove backend-specific formatting artifacts
- Map to repo-native naming conventions (documented)

## Output artifact

`normalized_engine_result` conforming to `schemas/normalized_engine_result.schema.json`.
