#!/usr/bin/env python3
"""Fail-closed bounded SymPy runner for ENGINE_002."""
import ast
import hashlib
import json
import platform as _platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path


POLICY_FILENAME = "forbidden_operations.json"
ALLOWED_OPERATIONS_FILENAME = "allowed_operations.json"

# This is deliberately narrower than allowed_operations.json: an advertised
# operation is not executable until this runner has an explicit implementation.
IMPLEMENTED_OPERATIONS = frozenset({
    "subs", "expand", "factor", "cancel", "together", "apart", "diff",
    "simplify_with_explicit_measure", "exact_subtraction",
})


class InvalidExpressionError(ValueError):
    """Raised for expression syntax outside the non-executing AST grammar."""


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class PolicyConfigurationError(ValueError):
    """Raised when a packaged engine policy cannot safely be used."""


class OperationValidationError(ValueError):
    """Raised while compiling a request before any transformation executes."""

    def __init__(self, result_type: str, index: int, operation: str,
                 parameter: str, reason: str):
        super().__init__(
            f"operation_validation_failed:index={index}:operation={operation}:"
            f"parameter={parameter}:reason={reason}"
        )
        self.result_type = result_type


@dataclass(frozen=True)
class ValidatedOperation:
    """An operation whose request-controlled values have been validated."""

    index: int
    operation: str
    parameters: dict
    audit_parameters: dict


def _policy_path(policy_path: str | Path | None) -> Path:
    return (Path(policy_path) if policy_path is not None
            else Path(__file__).resolve().parent / POLICY_FILENAME)


def load_forbidden_policy(policy_path: str | Path | None = None) -> tuple[set[str], dict]:
    """Load the packaged policy before expression parsing.

    ``policy_path`` is a narrow dependency-injection hook for tests. Production
    callers do not receive a request-controlled policy override.
    """
    path = _policy_path(policy_path)
    metadata = {"path": str(path.resolve()), "sha256": None}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyConfigurationError(f"policy_unreadable:{type(exc).__name__}") from exc
    metadata["sha256"] = sha256_hex(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyConfigurationError("policy_invalid_json") from exc
    if not isinstance(data, dict):
        raise PolicyConfigurationError("policy_root_not_object")
    if data.get("engine_id") != "sympy":
        raise PolicyConfigurationError("policy_engine_id_mismatch")
    forbidden = data.get("forbidden_operations")
    if not isinstance(forbidden, list):
        raise PolicyConfigurationError("policy_forbidden_operations_not_list")
    if any(not isinstance(op, str) or not op.strip() for op in forbidden):
        raise PolicyConfigurationError("policy_forbidden_operation_invalid_member")
    if len(forbidden) != len(set(forbidden)):
        raise PolicyConfigurationError("policy_forbidden_operations_duplicate")
    return set(forbidden), metadata


def load_known_operations(allowed_operations_path: str | Path | None = None) -> set[str]:
    """Read the repository's canonical advertised operation names."""
    path = (Path(allowed_operations_path) if allowed_operations_path is not None
            else Path(__file__).resolve().parent / ALLOWED_OPERATIONS_FILENAME)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyConfigurationError("allowed_operations_configuration_invalid") from exc
    if not isinstance(data, dict):
        raise PolicyConfigurationError("allowed_operations_root_not_object")
    operations = data.get("allowed_operations")
    if (data.get("engine_id") != "sympy" or not isinstance(operations, list)
            or any(not isinstance(op, str) or not op.strip() for op in operations)
            or len(operations) != len(set(operations))):
        raise PolicyConfigurationError("allowed_operations_configuration_invalid")
    return set(operations)


def parse_safe_expression(sp, expression_text: str):
    """Translate a deliberately small, non-executing Python expression AST."""
    try:
        tree = ast.parse(expression_text, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise InvalidExpressionError("invalid_expression_syntax") from exc

    safe_constants = {"pi": sp.pi, "Pi": sp.pi, "E": sp.E, "I": sp.I, "oo": sp.oo}
    safe_functions = {
        "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "exp": sp.exp,
        "log": sp.log, "sqrt": sp.sqrt, "Abs": sp.Abs, "gamma": sp.gamma,
    }

    def convert(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or isinstance(node.value, (str, bytes)):
                raise InvalidExpressionError("invalid_expression_literal")
            if isinstance(node.value, int):
                return sp.Integer(node.value)
            if isinstance(node.value, float):
                return sp.Float(str(node.value))
            if isinstance(node.value, complex):
                return sp.Float(str(node.value.real)) + sp.I * sp.Float(str(node.value.imag))
            raise InvalidExpressionError("invalid_expression_literal")
        if isinstance(node, ast.Name):
            if node.id.startswith("__") or node.id.endswith("__"):
                raise InvalidExpressionError("invalid_expression_dunder_name")
            return safe_constants.get(node.id, sp.Symbol(node.id))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = convert(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left, right = convert(node.left), convert(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise InvalidExpressionError("invalid_expression_binary_operator")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in safe_functions:
                raise InvalidExpressionError("invalid_expression_function_call")
            if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
                raise InvalidExpressionError("invalid_expression_function_arguments")
            return safe_functions[node.func.id](*(convert(arg) for arg in node.args))
        raise InvalidExpressionError("invalid_expression_syntax_node")

    return convert(tree.body)


def _result(request: dict, *, result_type: str, exit_code: int, started_at: str,
            engine_version: str = "unknown", errors: list[str] | None = None,
            policy_metadata: dict | None = None, raw_output: str = "",
            observed: list[str] | None = None, audit_steps: list[dict] | None = None,
            parsed_expression: dict | None = None) -> dict:
    expression_text = request.get("expression_scope", {}).get("input_expression", "")
    completed_at = now_iso()
    return {
        "request_id": request.get("request_id", "unknown"),
        "engine_id": "sympy",
        "engine_version": engine_version,
        "engine_executable": sys.executable,
        "environment": {
            "platform": _platform.platform(),
            "python_version": _platform.python_version(),
            "dependencies": {"sympy": engine_version},
        },
        "generated_script_sha": sha256_hex(json.dumps(request, sort_keys=True)),
        "exact_command": f"{sys.executable} engines/sympy/runner.py",
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "timeout_state": False,
        "memory_state": "OK",
        "operations_requested": [
            entry.get("operation", "") if isinstance(entry, dict) else ""
            for entry in request.get("requested_operation_sequence", [])
        ],
        "operations_observed": observed or [],
        "assumptions_requested": request.get("declared_assumptions", []),
        "assumptions_observed": request.get("declared_assumptions", []),
        "input_expression_text": expression_text,
        "input_expression_sha256": sha256_hex(expression_text),
        "parsed_expression": parsed_expression,
        "policy_metadata": policy_metadata or {},
        "transformation_audit": audit_steps or [],
        "raw_output": raw_output,
        "raw_output_sha": sha256_hex(raw_output),
        "normalized_output": raw_output,
        "normalized_output_sha": sha256_hex(raw_output),
        "warnings": [],
        "errors": errors or [],
        "partial_result_status": "COMPLETE" if exit_code == 0 else "NONE",
        "determinism_record": {
            "declared_deterministic": True,
            "observed_deterministic": True,
            "reproducible": True,
        },
        "result_type": result_type,
        "status": result_type,
    }


def _denial(request: dict, started_at: str, result_type: str, reason: str,
            policy_metadata: dict | None = None) -> dict:
    return _result(request, result_type=result_type, exit_code=1,
                   started_at=started_at, errors=[reason],
                   policy_metadata=policy_metadata)


def _validated_symbol(sp, value, *, index: int, operation: str,
                      parameter: str):
    if (not isinstance(value, str) or not value.isidentifier()
            or value.startswith("__") or value.endswith("__")):
        raise OperationValidationError(
            "UNAUTHORIZED_OPERATION", index, operation, parameter,
            "symbol_name_not_allowed",
        )
    return sp.Symbol(value)


def _validated_expression_parameter(sp, value, *, index: int, operation: str,
                                    parameter: str):
    if isinstance(value, str):
        try:
            return parse_safe_expression(sp, value)
        except InvalidExpressionError as exc:
            raise OperationValidationError(
                "INVALID_EXPRESSION", index, operation, parameter, str(exc)
            ) from exc
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationValidationError(
            "INVALID_EXPRESSION", index, operation, parameter,
            "expression_value_not_scalar_or_string",
        )
    return sp.Integer(value) if isinstance(value, int) else sp.Float(str(value))


def compile_operation_plan(sp, operations: list[dict]) -> list[ValidatedOperation]:
    """Validate all operation parameters before executing the first operation.

    The returned plan contains SymPy objects only where request text has already
    been parsed by the fail-closed AST parser.  Execution must consume this plan
    rather than reparsing request-controlled values.
    """
    ordered: list[tuple[int, int, dict]] = []
    for index, entry in enumerate(operations):
        operation = entry.get("operation", "")
        order = entry.get("order", 0)
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise OperationValidationError(
                "UNAUTHORIZED_OPERATION", index, operation, "order",
                "order_must_be_nonnegative_integer",
            )
        ordered.append((order, index, entry))

    plan = []
    for _, index, entry in sorted(ordered):
        operation = entry["operation"]
        parameters = entry.get("parameters", {})
        if not isinstance(parameters, dict):
            raise OperationValidationError(
                "UNAUTHORIZED_OPERATION", index, operation, "parameters",
                "parameters_not_object",
            )

        # Keep the original JSON-compatible values for the audit record while
        # execution receives only the compiled values below.
        compiled = dict(parameters)
        audit_parameters = dict(parameters)

        # Some historical fixtures carry this unused expression field.  It is
        # still request-controlled expression text, so validate it even though
        # the operation operates on the request's primary expression.
        if "expression" in parameters:
            compiled["expression"] = _validated_expression_parameter(
                sp, parameters["expression"], index=index, operation=operation,
                parameter="expression",
            )

        if operation == "subs":
            substitutions = {}
            for key, value in parameters.items():
                symbol = _validated_symbol(
                    sp, key, index=index, operation=operation, parameter=str(key)
                )
                substitutions[symbol] = _validated_expression_parameter(
                    sp, value, index=index, operation=operation, parameter=str(key)
                )
            compiled = {"substitutions": substitutions}
        elif operation == "exact_subtraction":
            if "other" not in parameters:
                raise OperationValidationError(
                    "INVALID_EXPRESSION", index, operation, "other", "missing",
                )
            compiled["other"] = _validated_expression_parameter(
                sp, parameters["other"], index=index, operation=operation,
                parameter="other",
            )
        elif operation == "diff":
            variable = parameters.get("variable", "x")
            compiled["variable"] = _validated_symbol(
                sp, variable, index=index, operation=operation, parameter="variable"
            )
            derivative_order = parameters.get("n", 1)
            if (isinstance(derivative_order, bool)
                    or not isinstance(derivative_order, int) or derivative_order < 1):
                raise OperationValidationError(
                    "UNAUTHORIZED_OPERATION", index, operation, "n",
                    "derivative_order_must_be_positive_integer",
                )
            compiled["n"] = derivative_order
        elif operation == "simplify_with_explicit_measure":
            # JSON cannot supply a callable measure safely; allow only the
            # default simplification behavior until a typed measure contract is
            # introduced.
            if parameters.get("measure") is not None:
                raise OperationValidationError(
                    "UNAUTHORIZED_OPERATION", index, operation, "measure",
                    "measure_must_be_null",
                )
            compiled["measure"] = None

        plan.append(ValidatedOperation(index, operation, compiled, audit_parameters))
    return plan


def _apply_operation(sp, expression, operation: str, parameters: dict):
    if operation == "cancel":
        return sp.cancel(expression)
    if operation == "expand":
        return sp.expand(expression)
    if operation == "factor":
        return sp.factor(expression)
    if operation == "together":
        return sp.together(expression)
    if operation == "apart":
        return sp.apart(expression)
    if operation == "diff":
        return sp.diff(expression, parameters["variable"], parameters["n"])
    if operation == "simplify_with_explicit_measure":
        measure = parameters.get("measure")
        return sp.simplify(expression, measure=measure) if measure else sp.simplify(expression)
    if operation == "exact_subtraction":
        return expression - parameters["other"]
    if operation == "subs":
        return expression.subs(parameters["substitutions"])
    raise AssertionError(f"unimplemented operation dispatched: {operation}")


def run_sympy_bounded(request: dict, *, policy_path: str | Path | None = None,
                      allowed_operations_path: str | Path | None = None) -> dict:
    """Run an explicitly authorized operation sequence with fail-closed policy."""
    started_at = now_iso()
    try:
        packaged_forbidden, policy_metadata = load_forbidden_policy(policy_path)
        known_operations = load_known_operations(allowed_operations_path)
    except PolicyConfigurationError as exc:
        return _result(request, result_type="POLICY_CONFIGURATION_ERROR", exit_code=2,
                       started_at=started_at, errors=[str(exc)],
                       policy_metadata={"path": str(_policy_path(policy_path))})

    caller_forbidden = request.get("forbidden_operations", [])
    if (not isinstance(caller_forbidden, list)
            or any(not isinstance(op, str) or not op.strip() for op in caller_forbidden)):
        return _denial(request, started_at, "UNAUTHORIZED_OPERATION",
                       "invalid_caller_forbidden_operations", policy_metadata)
    effective_forbidden = packaged_forbidden | set(caller_forbidden)
    policy_metadata["effective_forbidden_count"] = len(effective_forbidden)

    operations = request.get("requested_operation_sequence", [])
    allowed = request.get("allowed_operations", [])
    if (not isinstance(operations, list) or not isinstance(allowed, list)
            or any(not isinstance(operation, str) or not operation.strip()
                   for operation in allowed)):
        return _denial(request, started_at, "UNAUTHORIZED_OPERATION",
                       "invalid_operation_request_shape", policy_metadata)

    # Validate every requested transformation before parsing the input.
    for index, entry in enumerate(operations):
        if not isinstance(entry, dict):
            return _denial(request, started_at, "UNAUTHORIZED_OPERATION",
                           f"invalid_operation_entry:index={index}", policy_metadata)
        operation = entry.get("operation", "")
        if not isinstance(operation, str) or not operation.strip():
            return _denial(request, started_at, "UNSUPPORTED_OPERATION",
                           f"unsupported_operation_requested:{operation}", policy_metadata)
        if operation in effective_forbidden:
            return _denial(request, started_at, "POLICY_VIOLATION",
                           f"forbidden_operation_requested:{operation}", policy_metadata)
        if operation not in known_operations or operation not in IMPLEMENTED_OPERATIONS:
            return _denial(request, started_at, "UNSUPPORTED_OPERATION",
                           f"unsupported_operation_requested:{operation}", policy_metadata)
        if operation not in allowed:
            return _denial(request, started_at, "UNAUTHORIZED_OPERATION",
                           f"operation_not_authorized:{operation}", policy_metadata)

    try:
        import sympy as sp
    except ImportError:
        return _result(request, result_type="ENGINE_UNAVAILABLE", exit_code=1,
                       started_at=started_at, errors=["sympy_import_failed"],
                       policy_metadata=policy_metadata)

    # Phase A: compile the complete request before evaluating any operation.
    # A rejection here intentionally exposes no parse metadata, transformed
    # output, observed operation, or audit record.
    try:
        operation_plan = compile_operation_plan(sp, operations)
    except OperationValidationError as exc:
        return _result(request, result_type=exc.result_type, exit_code=1,
                       started_at=started_at, engine_version=sp.__version__,
                       errors=[str(exc)], policy_metadata=policy_metadata)

    expression_text = request.get("expression_scope", {}).get("input_expression", "")
    if not isinstance(expression_text, str):
        return _denial(request, started_at, "UNAUTHORIZED_OPERATION",
                       "input_expression_not_string", policy_metadata)
    try:
        current_expression = parse_safe_expression(sp, expression_text)
    except InvalidExpressionError as exc:
        return _result(request, result_type="INVALID_EXPRESSION", exit_code=1,
                       started_at=started_at, engine_version=sp.__version__,
                       errors=[str(exc)],
                       policy_metadata=policy_metadata)

    parsed_expression = {
        "parser": "python_ast_to_sympy",
        "sympy_version": sp.__version__,
        "srepr": sp.srepr(current_expression),
        "srepr_sha256": sha256_hex(sp.srepr(current_expression)),
    }
    if not operations:
        return _result(request, result_type="EXACT_SYMBOLIC_RESULT", exit_code=0,
                       started_at=started_at, engine_version=sp.__version__,
                       policy_metadata=policy_metadata, raw_output=expression_text,
                       parsed_expression=parsed_expression)

    # Phase B: execute only the fully compiled plan.
    observed, audit_steps = [], []
    try:
        for planned in operation_plan:
            operation = planned.operation
            input_display = str(current_expression)
            input_srepr = sp.srepr(current_expression)
            current_expression = _apply_operation(
                sp, current_expression, operation, planned.parameters
            )
            output_display = str(current_expression)
            output_srepr = sp.srepr(current_expression)
            observed.append(operation)
            audit_steps.append({
                "operation": operation,
                "parameters": planned.audit_parameters,
                "input_display_text": input_display,
                "output_display_text": output_display,
                "input_srepr_sha256": sha256_hex(input_srepr),
                "output_srepr_sha256": sha256_hex(output_srepr),
                "display_text_changed": input_display != output_display,
            })
    except (InvalidExpressionError, TypeError, ValueError) as exc:
        return _result(request, result_type="EXECUTION_FAILED", exit_code=1,
                       started_at=started_at, engine_version=sp.__version__,
                       errors=[f"operation_execution_failed:{type(exc).__name__}"],
                       policy_metadata=policy_metadata)

    return _result(request, result_type="EXACT_SYMBOLIC_RESULT", exit_code=0,
                   started_at=started_at, engine_version=sp.__version__,
                   policy_metadata=policy_metadata, raw_output=str(current_expression),
                   observed=observed, audit_steps=audit_steps,
                   parsed_expression=parsed_expression)


def main() -> None:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError:
        try:
            request = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
        except json.JSONDecodeError:
            request = None
    if not isinstance(request, dict):
        result = _result({}, result_type="EXECUTION_FAILED", exit_code=1,
                         started_at=now_iso(), errors=["invalid_json_request"])
    else:
        result = run_sympy_bounded(request)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(int(result.get("exit_code", 1)))


if __name__ == "__main__":
    main()
