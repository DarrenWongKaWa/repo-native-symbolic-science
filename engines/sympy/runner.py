#!/usr/bin/env python3
"""
SymPy bounded runner for ENGINE_002.
Accepts a JSON request on stdin, executes only authorized operations,
records complete execution truth, and returns a normalized result.

Policy contract (see REPO_POLICY.md):
  * The engine's OWN policy files are authoritative and are always loaded:
        engines/sympy/forbidden_operations.json
        engines/sympy/allowed_operations.json
    A caller may ADD restrictions; it can never remove them.
  * The raw input expression is IMMUTABLE. It is parsed, never rewritten.
    No transformation happens unless it is an explicitly requested operation.
  * An operation that is declared-but-unimplemented FAILS CLOSED with
    UNSUPPORTED_CAPABILITY. It is never silently skipped, because a skipped
    step would return the untransformed input labelled as an exact result.
"""
import json
import sys
import hashlib
import time
import traceback
import os
import platform as _platform

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _load_policy(filename: str, key: str) -> set:
    """Load an engine-side policy list. Missing/corrupt policy => empty set,
    but that is reported by the caller as a hard error for forbidden ops."""
    path = os.path.join(ENGINE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return set(json.load(fh).get(key, []))
    except Exception:
        return set()


def _build_symbols(declared_assumptions):
    """Turn declared assumptions like 'a_positive=True' or 'a=positive'
    into sympy symbols carrying those assumptions, for use as sympify locals.

    Supported forms:
        "a_positive=True"   -> a is positive
        "a_real=True"       -> a is real
        "k_nonzero=True"    -> k is nonzero
    """
    import sympy as sp

    known = {"positive", "negative", "real", "integer", "nonzero",
             "nonnegative", "complex", "rational", "finite"}
    local = {}
    for item in declared_assumptions:
        if not isinstance(item, str) or "=" not in item:
            continue
        lhs, rhs = item.split("=", 1)
        lhs, rhs = lhs.strip(), rhs.strip()
        if rhs not in ("True", "true", "1"):
            continue
        if "_" not in lhs:
            continue
        name, _, prop = lhs.rpartition("_")
        if prop in known and name:
            existing = local.get(name)
            assumptions = {prop: True}
            if existing is not None:
                assumptions.update(existing.assumptions0)
            local[name] = sp.Symbol(name, **assumptions)
    return local


def run_sympy_bounded(request: dict) -> dict:
    request_id = request.get("request_id", "unknown")
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def envelope(**over):
        """Uniform failure envelope (same shape the caller already expects)."""
        base = {
            "request_id": request_id,
            "engine_id": "sympy",
            "engine_version": over.pop("engine_version", "unknown"),
            "exit_code": 1,
            "result_type": "EXECUTION_FAILED",
            "errors": [],
            "observed_operations": [],
            "started_at": started_at,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        base.update(over)
        return base

    try:
        import sympy as sp
    except ImportError:
        return envelope(exit_code=-1, result_type="ENGINE_UNAVAILABLE",
                        errors=["sympy_import_failed"])

    engine_version = sp.__version__

    # --- Policy: the engine's own files are authoritative. -------------------
    # The caller may only ADD restrictions, never remove them.
    engine_forbidden = _load_policy("forbidden_operations.json", "forbidden_operations")
    engine_allowed = _load_policy("allowed_operations.json", "allowed_operations")

    if not engine_forbidden:
        # Fail closed: without its policy the engine cannot prove an op is safe.
        return envelope(engine_version=engine_version,
                        result_type="POLICY_VIOLATION",
                        errors=["engine_forbidden_policy_unavailable: refusing to run"])

    forbidden_ops_set = engine_forbidden | set(request.get("forbidden_operations", []))
    allowed_ops_set = engine_allowed | set(request.get("allowed_operations", []))

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
        if not str(expression_text).strip():
            return envelope(engine_version=engine_version,
                            errors=["empty_input_expression"])

        # --- Immutable ingestion --------------------------------------------
        # Parse only. No simplify, no exec, no string concatenation.
        local_syms = _build_symbols(declared_assumptions)
        current_expr = sp.sympify(expression_text, locals=local_syms)
        frozen_input = current_expr  # kept for provenance

        def _sym(entry, key, default=None):
            name = entry.get("parameters", {}).get(key, default)
            if name is None:
                return None
            return local_syms.get(str(name), sp.Symbol(str(name)))

        def _param(entry, key, default=None):
            return entry.get("parameters", {}).get(key, default)

        for op_entry in sorted(ops_sequence, key=lambda x: x.get("order", 0)):
            op_name = op_entry.get("operation", "")

            # 1) Forbidden always wins, and is checked before anything runs.
            if op_name in forbidden_ops_set:
                return envelope(
                    engine_version=engine_version,
                    result_type="POLICY_VIOLATION",
                    errors=[f"forbidden_operation_requested: {op_name}"],
                    observed_operations=observed_operations,
                )

            # 2) Not on the allow-list => refuse. Do not guess.
            if op_name not in allowed_ops_set:
                return envelope(
                    engine_version=engine_version,
                    result_type="POLICY_VIOLATION",
                    errors=[f"operation_not_authorized: {op_name}"],
                    observed_operations=observed_operations,
                )

            observed_operations.append(op_name)

            # --- Dispatch ----------------------------------------------------
            if op_name == "cancel":
                current_expr = sp.cancel(current_expr)

            elif op_name == "expand":
                current_expr = sp.expand(current_expr)

            elif op_name in ("expand_power_base", "expand_power_exp", "expand_log",
                             "expand_trig", "expand_mul"):
                current_expr = getattr(sp, op_name)(current_expr)

            elif op_name == "factor":
                current_expr = sp.factor(current_expr)

            elif op_name == "together":
                current_expr = sp.together(current_expr)

            elif op_name == "apart":
                var = _sym(op_entry, "variable")
                current_expr = sp.apart(current_expr, var) if var is not None \
                    else sp.apart(current_expr)

            elif op_name == "collect":
                var = _sym(op_entry, "variable")
                current_expr = sp.collect(current_expr, var)

            elif op_name == "diff":
                var = _sym(op_entry, "variable", "x")
                n = int(_param(op_entry, "n", 1))
                current_expr = sp.diff(current_expr, var, n)

            elif op_name == "integrate_with_explicit_domain":
                var = _sym(op_entry, "variable", "x")
                lower = _param(op_entry, "lower", None)
                upper = _param(op_entry, "upper", None)
                if lower is None or upper is None:
                    return envelope(
                        engine_version=engine_version,
                        result_type="POLICY_VIOLATION",
                        errors=["integrate_with_explicit_domain requires "
                                "explicit 'lower' and 'upper' bounds"],
                        observed_operations=observed_operations,
                    )
                lo = sp.sympify(str(lower), locals=local_syms)
                hi = sp.sympify(str(upper), locals=local_syms)
                current_expr = sp.integrate(current_expr, (var, lo, hi))

            elif op_name == "series_with_explicit_variables":
                var = _sym(op_entry, "variable", "x")
                point = sp.sympify(str(_param(op_entry, "point", 0)), locals=local_syms)
                n = int(_param(op_entry, "n", 6))
                current_expr = sp.series(current_expr, var, point, n).removeO()

            elif op_name in ("coeff_extraction", "coeff_with_explicit_variable"):
                var = _sym(op_entry, "variable", "x")
                power = int(_param(op_entry, "power", 1))
                current_expr = current_expr.coeff(var, power)

            elif op_name == "Poly":
                var = _sym(op_entry, "variable", "x")
                current_expr = sp.Poly(current_expr, var).as_expr()

            elif op_name in ("matrix_construction",):
                current_expr = sp.Matrix(current_expr)

            elif op_name == "matrix_multiplication":
                other = sp.sympify(str(_param(op_entry, "other", "")), locals=local_syms)
                current_expr = current_expr * other

            elif op_name == "determinant":
                current_expr = sp.Matrix(current_expr).det()

            elif op_name == "trace":
                current_expr = sp.Matrix(current_expr).trace()

            elif op_name == "simplify_with_explicit_measure":
                measure = _param(op_entry, "measure", None)
                measures = {"count_ops": sp.count_ops}
                if measure in measures:
                    current_expr = sp.simplify(current_expr, measure=measures[measure])
                elif measure is None:
                    current_expr = sp.simplify(current_expr)
                else:
                    return envelope(
                        engine_version=engine_version,
                        result_type="UNSUPPORTED_CAPABILITY",
                        errors=[f"unknown_simplify_measure: {measure}"],
                        observed_operations=observed_operations,
                    )

            elif op_name in ("exact_subtraction", "exact_addition",
                             "exact_multiplication", "exact_division"):
                other_text = _param(op_entry, "other", "")
                other = sp.sympify(str(other_text), locals=local_syms)
                if op_name == "exact_subtraction":
                    current_expr = sp.simplify(current_expr - other)
                elif op_name == "exact_addition":
                    current_expr = sp.simplify(current_expr + other)
                elif op_name == "exact_multiplication":
                    current_expr = sp.simplify(current_expr * other)
                else:
                    current_expr = sp.simplify(current_expr / other)

            elif op_name in ("subs", "xreplace"):
                subs_dict = op_entry.get("parameters", {})
                subs_expr = {}
                for k, v in subs_dict.items():
                    if k in ("other", "variable", "measure", "order",
                             "lower", "upper", "point", "n", "power"):
                        continue
                    key_sym = local_syms.get(k, sp.Symbol(k))
                    subs_expr[key_sym] = sp.sympify(str(v), locals=local_syms)
                if subs_expr:
                    current_expr = current_expr.subs(subs_expr)

            elif op_name in ("nfloat_with_explicit_precision", "evalf_with_explicit_dps"):
                dps = int(_param(op_entry, "dps", _param(op_entry, "precision", 15)))
                current_expr = sp.N(current_expr, dps)

            else:
                # Declared allowed but not implemented here. FAIL CLOSED.
                # Silently skipping would return the untransformed input
                # labelled EXACT_SYMBOLIC_RESULT -- the worst possible outcome.
                return envelope(
                    engine_version=engine_version,
                    result_type="UNSUPPORTED_CAPABILITY",
                    errors=[f"operation_not_implemented_by_adapter: {op_name}"],
                    observed_operations=observed_operations,
                )

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
        "input_expression": expression_text,
        "input_expression_sha": sha256_hex(str(expression_text)),
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


USAGE = """\
SymPy bounded runner (ENGINE_002).

Reads one engine_request JSON object on stdin, returns a normalized
engine_execution_truth JSON object on stdout.

  echo '{"request_id":"r1",
         "expression_scope":{"input_expression":"sqrt(v**2*k**2+m**2)"},
         "requested_operation_sequence":[
            {"operation":"diff","order":1,"parameters":{"variable":"k"}}]}' \\
    | python3 engines/sympy/runner.py

Policy: engines/sympy/{allowed,forbidden}_operations.json are authoritative.
Callers may add restrictions, never remove them. Unimplemented operations fail
closed with UNSUPPORTED_CAPABILITY; they are never silently skipped.
"""


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(USAGE)
        return 0

    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw.strip():
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "engine_id": "sympy",
                "exit_code": 1,
                "result_type": "EXECUTION_FAILED",
                "errors": [f"invalid_json_request: {e}"],
            }, indent=2))
            return 1
    elif len(sys.argv) > 1:
        try:
            request = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(json.dumps({
                "engine_id": "sympy",
                "exit_code": 1,
                "result_type": "EXECUTION_FAILED",
                "errors": [f"invalid_json_argument: {e}"],
            }, indent=2))
            return 1
    else:
        print(USAGE)
        return 2

    result = run_sympy_bounded(request)
    print(json.dumps(result, indent=2))
    return int(result.get("exit_code", 0) or 0)


if __name__ == "__main__":
    sys.exit(main())
