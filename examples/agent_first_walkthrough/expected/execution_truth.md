# Expected Execution Truth

This file shows the expected execution truth record from the bounded computation.

---

## Execution Truth Record

### Primary Execution (SymPy — Exact Symbolic)

```json
{
  "request_id": "EXEC-SYNTHETIC-WALKTHROUGH-001",
  "engine_id": "sympy",
  "engine_version": "1.14.0",
  "engine_executable": "python3 engines/sympy/runner.py",
  "input_artifacts": [
    "raw_object.json (sha256: <computed>)",
    "normalized_parent.json (sha256: <computed>)",
    "adapter_config.json (sha256: <computed>)"
  ],
  "input_shas": {
    "raw_object": "<sha256>",
    "normalized_parent": "<sha256>",
    "adapter_config": "<sha256>"
  },
  "generated_script_sha": "<sha256>",
  "exact_command": "python3 engines/sympy/runner.py",
  "started_at": "<ISO-8601 timestamp>",
  "completed_at": "<ISO-8601 timestamp>",
  "exit_code": 0,
  "operations_requested": ["expand", "subs"],
  "operations_observed": ["expand", "subs"],
  "assumptions_requested": ["x>0", "n>=0 integer", "commutative_scalars"],
  "assumptions_observed": ["x>0", "n>=0 integer", "commutative_scalars"],
  "raw_output": "n!*exp(-x)*Sum(x**k/factorial(k), (k, 0, n)) + (x+1)**n*exp(-x) + sin(pi*z)*H_n(y)",
  "raw_output_sha": "<sha256>",
  "normalized_output": "exp(-x)*(n!*Sum(x**k/k!, (k, 0, n)) + (x+1)**n) + sin(pi*z)*H_n(y)",
  "normalized_output_sha": "<sha256>",
  "warnings": [],
  "errors": [],
  "timeout_state": false,
  "memory_state": "ok",
  "partial_result_status": "complete"
}
```

### Supporting Execution (Python Numeric — Regression)

```json
{
  "request_id": "EXEC-SYNTHETIC-WALKTHROUGH-002-NUM",
  "engine_id": "python_numeric",
  "result_type": "NUMERICAL_REGRESSION_PASS",
  "sample_points": 100,
  "tolerance": 1e-12,
  "max_residual": "<max|F - G|>",
  "mean_residual": "<mean|F - G|>",
  "symbolic_equality_claimed": false
}
```

### Key Observations

1. **Exact execution succeeded**: SymPy expanded the gamma identity and the (x+1)^n term without warnings or errors.
2. **Normalized output preserves structure**: The sin(pi*z)*H_n(y) term is unchanged and structurally independent.
3. **Numerical regression passed**: 100 random sample points confirmed agreement within 1e-12 tolerance. This is **supporting evidence only** — not a claim of symbolic equality.
4. **No timeout**: The computation completed within the 30-second default timeout.
5. **No memory issues**: Memory usage stayed well within the 1024 MB limit.
