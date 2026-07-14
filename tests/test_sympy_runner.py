"""Regression tests for the fail-closed SymPy runner."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_DIR = REPO_ROOT / "engines" / "sympy"
sys.path.insert(0, str(RUNNER_DIR))
import runner  # noqa: E402
from scripts import engine_orchestrator  # noqa: E402


def request(expression="x + 1", operations=None, allowed=None, forbidden=None):
    operations = operations or []
    return {
        "request_id": "sympy-runner-test",
        "expression_scope": {"input_expression": expression},
        "requested_operation_sequence": operations,
        "allowed_operations": allowed if allowed is not None else [o["operation"] for o in operations],
        "forbidden_operations": forbidden if forbidden is not None else [],
        "declared_assumptions": [],
    }


def policy_file(tmp_path, data, name="policy.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("operation", ["authorize_IBP", "unbounded_simplify"])
def test_packaged_forbidden_operation_is_rejected_without_caller_policy(operation):
    result = runner.run_sympy_bounded(request(operations=[{"operation": operation, "order": 1}]))
    assert result["result_type"] == "POLICY_VIOLATION"
    assert result["exit_code"] == 1
    assert result["operations_observed"] == []
    assert result["raw_output"] == ""


def test_caller_restrictions_are_additive_and_cannot_remove_packaged_policy():
    result = runner.run_sympy_bounded(request(
        operations=[{"operation": "factor", "order": 1}], forbidden=["factor"]
    ))
    assert result["result_type"] == "POLICY_VIOLATION"
    packaged = runner.run_sympy_bounded(request(
        operations=[{"operation": "authorize_IBP", "order": 1}], forbidden=[]
    ))
    assert packaged["result_type"] == "POLICY_VIOLATION"


def test_unknown_and_non_allowlisted_operations_are_rejected_before_parsing():
    unknown = runner.run_sympy_bounded(request(
        expression="not valid sympy (", operations=[{"operation": "made_up", "order": 1}], allowed=["made_up"]
    ))
    assert unknown["result_type"] == "UNSUPPORTED_OPERATION"
    assert unknown["operations_observed"] == []
    unauthorized = runner.run_sympy_bounded(request(
        operations=[{"operation": "expand", "order": 1}], allowed=[]
    ))
    assert unauthorized["result_type"] == "UNAUTHORIZED_OPERATION"
    assert unauthorized["raw_output"] == ""


def test_noop_preserves_exact_text_and_records_parse_metadata():
    expression = "(x**2 - 1)/(x - 1)"
    result = runner.run_sympy_bounded(request(expression))
    assert result["exit_code"] == 0
    assert result["raw_output"] == expression
    assert result["normalized_output"] == expression
    assert result["transformation_audit"] == []
    assert result["parsed_expression"]["parser"] == "python_ast_to_sympy"


@pytest.mark.parametrize("bad_policy, reason", [
    (None, "policy_unreadable"),
    ("{", "policy_invalid_json"),
    ({"engine_id": "other", "forbidden_operations": []}, "policy_engine_id_mismatch"),
    ({"engine_id": "sympy", "forbidden_operations": ["ok", ""]}, "invalid_member"),
    ({"engine_id": "sympy", "forbidden_operations": ["x", "x"]}, "duplicate"),
])
def test_bad_policy_fails_closed(tmp_path, bad_policy, reason):
    path = tmp_path / "missing.json" if bad_policy is None else policy_file(tmp_path, bad_policy) if isinstance(bad_policy, dict) else tmp_path / "bad.json"
    if isinstance(bad_policy, str):
        path.write_text(bad_policy, encoding="utf-8")
    result = runner.run_sympy_bounded(request("not valid sympy ("), policy_path=path)
    assert result["result_type"] == "POLICY_CONFIGURATION_ERROR"
    assert result["exit_code"] == 2
    assert reason in result["errors"][0]
    assert result["raw_output"] == ""


def test_policy_resolution_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.run_sympy_bounded(request())
    assert result["exit_code"] == 0
    assert result["policy_metadata"]["path"].endswith("engines/sympy/forbidden_operations.json")


def test_authorized_operations_and_audit_provenance():
    result = runner.run_sympy_bounded(request(
        "(x + 1)**2", [{"operation": "expand", "parameters": {}, "order": 1}]
    ))
    assert result["exit_code"] == 0
    assert result["raw_output"] == "x**2 + 2*x + 1"
    assert result["operations_observed"] == ["expand"]
    step = result["transformation_audit"][0]
    assert step["operation"] == "expand"
    assert step["input_srepr_sha256"]
    assert step["output_srepr_sha256"]
    assert step["display_text_changed"] is True


@pytest.mark.parametrize("expression", ["x + 1", "(x**2 - 1)/(x - 1)", "-x + 2*y", "(x + y)**2", "sin(x) + pi"])
def test_safe_expression_syntax_is_accepted(expression):
    result = runner.run_sympy_bounded(request(expression))
    assert result["result_type"] == "EXACT_SYMBOLIC_RESULT"
    assert result["parsed_expression"]["parser"] == "python_ast_to_sympy"


@pytest.mark.parametrize("expression", [
    'print("PARSER_EVAL") or 1', '__import__("builtins")',
    "object.__subclasses__()", "(lambda: 1)()", "x.__class__",
    "[x for x in (1, 2)]",
])
def test_unsafe_expression_is_rejected_without_output_or_audit(expression):
    result = runner.run_sympy_bounded(request(expression))
    assert result["result_type"] == "INVALID_EXPRESSION"
    assert result["exit_code"] == 1
    assert result["raw_output"] == ""
    assert result["parsed_expression"] is None
    assert result["operations_observed"] == []
    assert result["transformation_audit"] == []


def test_cli_print_attempt_is_one_json_invalid_expression_result():
    payload = json.dumps(request('print("PARSER_EVAL") or 1'))
    proc = subprocess.run([sys.executable, str(RUNNER_DIR / "runner.py")], input=payload,
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["result_type"] == "INVALID_EXPRESSION"
    assert result["raw_output"] == ""
    assert proc.stdout.count("PARSER_EVAL") == 1  # input echo only, never side-effect output
    assert proc.stderr == ""


@pytest.mark.parametrize("root", [[], None, "not-an-object", 1, True])
def test_malformed_allowed_operation_policy_root_fails_closed(tmp_path, root):
    path = policy_file(tmp_path, root, name="allowed.json")
    result = runner.run_sympy_bounded(request(), allowed_operations_path=path)
    assert result["result_type"] == "POLICY_CONFIGURATION_ERROR"
    assert result["exit_code"] == 2
    assert result["raw_output"] == ""


def test_cli_malformed_allowed_policy_root_exits_two(tmp_path):
    path = policy_file(tmp_path, [], name="allowed.json")
    code = (
        "import sys; sys.path.insert(0, %r); import runner; "
        "runner.ALLOWED_OPERATIONS_FILENAME=%r; runner.main()"
    ) % (str(RUNNER_DIR), str(path))
    proc = subprocess.run([sys.executable, "-c", code], input=json.dumps(request()),
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 2
    result = json.loads(proc.stdout)
    assert result["result_type"] == "POLICY_CONFIGURATION_ERROR"
    assert proc.stderr == ""


@pytest.mark.parametrize(("expression", "operation", "parameters", "expected"), [
    ("x + x", "expand", {}, "2*x"),
    ("x**2 - 1", "factor", {}, "(x - 1)*(x + 1)"),
    ("(x**2 - 1)/(x - 1)", "cancel", {}, "x + 1"),
    ("x + y", "subs", {"x": "2"}, "y + 2"),
    ("x**3", "diff", {"variable": "x", "n": 2}, "6*x"),
])
def test_existing_authorized_operations_remain_available(expression, operation, parameters, expected):
    result = runner.run_sympy_bounded(request(
        expression, [{"operation": operation, "parameters": parameters, "order": 1}]
    ))
    assert result["exit_code"] == 0
    assert result["raw_output"] == expected
    assert result["transformation_audit"][0]["operation"] == operation


def test_cli_emits_one_json_result_and_propagates_denial_exit_code():
    payload = json.dumps(request(operations=[{"operation": "authorize_IBP", "order": 1}]))
    proc = subprocess.run([sys.executable, str(RUNNER_DIR / "runner.py")], input=payload,
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["result_type"] == "POLICY_VIOLATION"
    assert proc.stderr == ""


def test_cli_policy_configuration_failure_exits_two(tmp_path):
    missing = tmp_path / "missing.json"
    code = (
        "import sys; sys.path.insert(0, %r); import runner; "
        "runner._policy_path=lambda _: __import__('pathlib').Path(%r); runner.main()"
    ) % (str(RUNNER_DIR), str(missing))
    proc = subprocess.run([sys.executable, "-c", code], input=json.dumps(request()),
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["result_type"] == "POLICY_CONFIGURATION_ERROR"


@pytest.mark.parametrize("operation, parameters, parameter", [
    ("subs", {"x": 'print("LATE_PARAM_EVAL") or 1'}, "x"),
    ("exact_subtraction", {"other": 'print("LATE_PARAM_EVAL") or 1'}, "other"),
])
def test_later_invalid_expression_parameter_rejects_the_entire_plan(
        operation, parameters, parameter):
    result = runner.run_sympy_bounded(request(
        "(x + 1)**2",
        [
            {"operation": "expand", "parameters": {}, "order": 1},
            {"operation": operation, "parameters": parameters, "order": 2},
        ],
    ))
    assert result["result_type"] == "INVALID_EXPRESSION"
    assert result["exit_code"] == 1
    assert f"index=1:operation={operation}:parameter={parameter}" in result["errors"][0]
    assert result["operations_observed"] == []
    assert result["transformation_audit"] == []
    assert result["raw_output"] == ""
    assert result["parsed_expression"] is None


def test_cli_later_invalid_parameter_has_no_partial_execution_or_side_effect():
    payload = json.dumps(request(
        "(x + 1)**2",
        [
            {"operation": "expand", "parameters": {}, "order": 1},
            {"operation": "subs", "parameters": {"x": 'print("LATE_PARAM_EVAL") or 1'}, "order": 2},
        ],
    ))
    proc = subprocess.run([sys.executable, str(RUNNER_DIR / "runner.py")], input=payload,
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["result_type"] == "INVALID_EXPRESSION"
    assert result["operations_observed"] == []
    assert result["transformation_audit"] == []
    assert "LATE_PARAM_EVAL" not in proc.stdout
    assert proc.stderr == ""


def test_invalid_plan_never_calls_the_executor(monkeypatch):
    calls = []

    def should_not_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("executor must not be called for an invalid plan")

    monkeypatch.setattr(runner, "_apply_operation", should_not_run)
    result = runner.run_sympy_bounded(request(
        "x + 1",
        [
            {"operation": "expand", "parameters": {}, "order": 1},
            {"operation": "exact_subtraction", "parameters": {"other": "not valid ("}, "order": 2},
        ],
    ))
    assert result["result_type"] == "INVALID_EXPRESSION"
    assert calls == []


def test_valid_multi_step_plan_executes_after_full_prevalidation():
    result = runner.run_sympy_bounded(request(
        "(x + 1)**2",
        [
            {"operation": "expand", "parameters": {}, "order": 1},
            {"operation": "subs", "parameters": {"x": "y"}, "order": 2},
            {"operation": "factor", "parameters": {}, "order": 3},
        ],
    ))
    assert result["exit_code"] == 0
    assert result["raw_output"] == "(y + 1)**2"
    assert result["operations_observed"] == ["expand", "subs", "factor"]
    assert len(result["transformation_audit"]) == 3


def test_orchestrator_resolves_runner_independently_of_caller_directory(tmp_path):
    payload = json.dumps(request())
    for cwd in (REPO_ROOT, REPO_ROOT / "scripts", tmp_path):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "engine_orchestrator.py")],
            input=payload, text=True, capture_output=True, check=False, cwd=cwd,
        )
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)["result"]
        assert result["engine_id"] == "sympy"
        assert result["result_type"] == "EXACT_SYMBOLIC_RESULT"


def test_orchestrator_propagates_policy_denial_exit_code():
    payload = json.dumps(request(
        operations=[{"operation": "authorize_IBP", "parameters": {}, "order": 1}]
    ))
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "engine_orchestrator.py")],
        input=payload, text=True, capture_output=True, check=False, cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["result"]["result_type"] == "POLICY_VIOLATION"
    assert proc.stderr == ""


def test_orchestrator_missing_runner_is_structured_and_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_orchestrator, "REPO_ROOT", tmp_path)
    result = engine_orchestrator.run_engine_bounded(
        request(), {"selected_primary_backend": "sympy"}
    )
    assert result["result_type"] == "EXECUTION_FAILED"
    assert result["exit_code"] == 1
    assert result["attempted_runner_path"] == str(tmp_path / "engines" / "sympy" / "runner.py")
