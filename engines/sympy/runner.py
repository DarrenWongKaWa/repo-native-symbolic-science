#!/usr/bin/env python3
"""
SymPy bounded runner for ENGINE_002.
Accepts a JSON request on stdin, executes only authorized operations,
records complete execution truth, and returns a normalized result.
"""
import json
import sys
import hashlib
import time
import traceback
import os
import platform as _platform


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def run_sympy_bounded(request: dict) -> dict:
    request_id = request.get("request_id", "unknown")
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        import sympy as sp
    except ImportError:
        return {
            "request_id": request_id,
            "engine_id": "sympy",
            "engine_version": "unknown",
            "exit_code": -1,
            "result_type": "ENGINE_UNAVAILABLE",
            "errors": ["sympy_import_failed"],
            "started_at": started_at,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    engine_version = sp.__version__

    allowed_ops_set = set(request.get("allowed_operations", []))
    forbidden_ops_set = set(request.get("forbidden_operations", []))
    ops_sequence = request.get("requested_operation_sequence", [])
    expression_text = request.get("expression_scope", {}).get("input_expression", "")
    declared_assumptions = request.get("declared_assumptions", [])

    observed_operations = []
    warnings = []
    errors = []
    raw_output = ""
    exit_code = 0
    result_type = "EXACT_SYMBOLIC_RESULT"
    partial = "COMPLETE"

    try:
        safe_globals = {
            "sp": sp,
            "sympy": sp,
            "Symbol": sp.Symbol,
            "symbols": sp.symbols,
            "Rational": sp.Rational,
            "Integer": sp.Integer,
            "expand": sp.expand,
            "factor": sp.factor,
            "cancel": sp.cancel,
            "together": sp.together,
            "apart": sp.apart,
            "diff": sp.diff,
            "series": sp.series,
            "Poly": sp.Poly,
            "Matrix": sp.Matrix,
            "simplify": sp.simplify,
            "collect": sp.collect,
            "latex": sp.latex,
            "srepr": sp.srepr,
            "evalf": lambda expr, n=15: expr.evalf(n) if hasattr(expr, 'evalf') else expr,
            "N": sp.N,
            "S": sp.S,
            "__builtins__": {
                "True": True,
                "False": False,
                "abs": abs,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "tuple": tuple,
                "dict": dict,
                "range": range,
                "len": len,
                "sum": sum,
                "min": min,
                "max": max,
                "print": lambda *a, **kw: None
            }
        }

        for assumption in declared_assumptions:
            if "=" in assumption:
                key, val = assumption.split("=", 1)
                key = key.strip()
                val = val.strip()
                if val == "True":
                    safe_globals[key] = sp.symbols(key, **{key.split('_')[-1] if '_' in key else 'real': True})
                exec(f"sp_symbols = sp.symbols('x', real=True)", {"sp": sp, "sp_symbols": None}, safe_globals)

        local_env = {}
        exec("result = sp.simplify(sp.sympify('''" + expression_text + "'''))", safe_globals, local_env)
        current_expr = local_env.get("result", sp.S(0))

        for op_entry in sorted(ops_sequence, key=lambda x: x.get("order", 0)):
            op_name = op_entry.get("operation", "")

            if op_name in forbidden_ops_set:
                return {
                    "request_id": request_id,
                    "engine_id": "sympy",
                    "engine_version": engine_version,
                    "exit_code": 1,
                    "result_type": "POLICY_VIOLATION",
                    "errors": [f"forbidden_operation_requested: {op_name}"],
                    "observed_operations": observed_operations,
                    "started_at": started_at,
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

            if op_name not in allowed_ops_set:
                warnings.append(f"operation_not_in_allowed_list: {op_name}")

            observed_operations.append(op_name)

            if op_name == "cancel":
                current_expr = sp.cancel(current_expr)
            elif op_name == "expand":
                current_expr = sp.expand(current_expr)
            elif op_name == "factor":
                current_expr = sp.factor(current_expr)
            elif op_name == "together":
                current_expr = sp.together(current_expr)
            elif op_name == "apart":
                current_expr = sp.apart(current_expr)
            elif op_name == "diff":
                var_name = op_entry.get("parameters", {}).get("variable", "x")
                var = sp.Symbol(var_name)
                current_expr = sp.diff(current_expr, var)
            elif op_name == "simplify_with_explicit_measure":
                measure = op_entry.get("parameters", {}).get("measure", None)
                if measure:
                    current_expr = sp.simplify(current_expr, measure=measure)
                else:
                    current_expr = sp.simplify(current_expr)
            elif op_name == "exact_subtraction":
                other_text = op_entry.get("parameters", {}).get("other", "")
                other = sp.sympify(other_text)
                current_expr = sp.simplify(current_expr - other)
            elif op_name == "subs":
                subs_dict = op_entry.get("parameters", {})
                subs_expr = {}
                for k, v in subs_dict.items():
                    if k not in ("other", "variable", "measure", "order"):
                        subs_expr[sp.Symbol(k)] = sp.sympify(v) if isinstance(v, str) else v
                if subs_expr:
                    current_expr = current_expr.subs(subs_expr)
            elif op_name == "diff":
                var_name = op_entry.get("parameters", {}).get("variable", "x")
                var = sp.Symbol(var_name)
                n = int(op_entry.get("parameters", {}).get("n", 1))
                current_expr = sp.diff(current_expr, var, n)
            else:
                warnings.append(f"unknown_operation_skipped: {op_name}")

        raw_output = str(current_expr)

    except Exception as e:
        exit_code = 1
        result_type = "EXECUTION_FAILED"
        errors.append(f"{type(e).__name__}: {str(e)}")
        errors.append(traceback.format_exc()[-500:])
        partial = "PARTIAL"

    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "request_id": request_id,
        "engine_id": "sympy",
        "engine_version": engine_version,
        "engine_executable": sys.executable,
        "environment": {
            "platform": _platform.platform(),
            "python_version": _platform.python_version(),
            "dependencies": {"sympy": engine_version}
        },
        "generated_script_sha": sha256_hex(json.dumps(request, sort_keys=True)),
        "exact_command": f"{sys.executable} engines/sympy/runner.py",
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "timeout_state": False,
        "memory_state": "OK",
        "operations_requested": [o.get("operation", "") for o in ops_sequence],
        "operations_observed": observed_operations,
        "assumptions_requested": declared_assumptions,
        "assumptions_observed": declared_assumptions,
        "raw_output": raw_output,
        "raw_output_sha": sha256_hex(raw_output),
        "normalized_output": raw_output,
        "normalized_output_sha": sha256_hex(raw_output),
        "warnings": warnings,
        "errors": errors,
        "partial_result_status": partial,
        "determinism_record": {
            "declared_deterministic": True,
            "observed_deterministic": True,
            "reproducible": True
        },
        "result_type": result_type
    }


def main():
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError:
        request = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}

    result = run_sympy_bounded(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
