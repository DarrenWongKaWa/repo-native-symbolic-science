"""B5 positive contract: complete ordered gradient plus exact connected base point."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
sys.path.insert(0, str(REPO))

from loop_engine.orch_adapters.symbolic_identity_verify import multivariable_t3 as B5
from loop_engine.orch_adapters.symbolic_identity_verify import domain_obligations as B4


def _real_product(symbols):
    return {"kind": "intersection",
            "terms": [{"kind": "real_line", "variable": variable} for variable in symbols]}


def claim(symbols=("x", "y"), *, lhs=None, rhs=None):
    symbols = list(symbols)
    if len(symbols) == 2:
        lhs = lhs or "sin(x+y)"
        rhs = rhs or "sin(x)*cos(y)+cos(x)*sin(y)"
    else:
        lhs = lhs or "sin(x+y+z)"
        rhs = rhs or (
            "sin(x)*cos(y)*cos(z)+cos(x)*sin(y)*cos(z)+"
            "cos(x)*cos(y)*sin(z)-sin(x)*sin(y)*sin(z)")
    return {
        "lhs": lhs,
        "rhs": rhs,
        "symbols": symbols,
        "scope": "real_scalars",
        "assumptions": [f"{variable} real" for variable in symbols],
        "domain": _real_product(symbols),
        "multivariable_t3": {
            "schema": B5.REQUEST_SCHEMA,
            "relevant_variables": symbols,
            "variable_order": symbols,
            "base_point": {variable: "0" for variable in symbols},
        },
    }


def request(parent):
    return {"operation": "multivariable_t3_verify", "contract_version": "1.0",
            "verification_mode": "symbolic_only", "claim": parent}


def _cli(command, payload):
    env = dict(os.environ)
    env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp()
    env["PYTHONPATH"] = ""
    process = subprocess.run(
        [sys.executable, str(CTL), command], input=json.dumps(payload), text=True,
        capture_output=True, cwd=str(REPO), env=env)
    return json.loads(process.stdout), process.returncode, process


@pytest.fixture(scope="module")
def two_variable_result():
    result, rc, process = _cli("multivariable-t3-verify", request(claim()))
    assert process.stderr == ""
    assert rc == 0
    assert result["combined_verdict"] == \
        "VERIFIED_BY_MULTIVARIABLE_DERIVATIVE_AND_BASE_POINT"
    return result


def test_two_variable_full_gradient_has_one_b3_confirmed_child_per_ordered_variable(
        two_variable_result):
    certificate = two_variable_result["symbolic_claim_verifier"]["certificate"]
    graph = certificate["gradient_certificate_graph"]
    assert certificate["variable_order_manifest"]["variable_order"] == ["x", "y"]
    assert certificate["coverage_manifest"]["coverage_bitmap"] == [True, True]
    assert certificate["coverage_manifest"]["covered_variables"] == ["x", "y"]
    assert [child["differentiation_variable"] for child in graph["children"]] == ["x", "y"]
    assert all(child["derivative_kind"] == "partial_derivative" for child in graph["children"])
    assert all(child["second_engine_confirmation"]["verdict"] == "ZERO"
               for child in graph["children"])
    assert all(child["second_engine_confirmation"]["route"] == "shipped_wolfram_engine"
               for child in graph["children"])


def test_three_variable_full_gradient_complete_and_ordered():
    parent = claim(("x", "y", "z"))
    result, rc, process = _cli("multivariable-t3-verify", request(parent))
    assert process.stderr == "" and rc == 0
    certificate = result["symbolic_claim_verifier"]["certificate"]
    assert certificate["coverage_manifest"]["coverage_bitmap"] == [True, True, True]
    assert [child["differentiation_variable"]
            for child in certificate["gradient_certificate_graph"]["children"]] == ["x", "y", "z"]
    assert all(child["second_engine_confirmation"]["verdict"] == "ZERO"
               for child in certificate["gradient_certificate_graph"]["children"])


def test_exact_base_point_connected_domain_and_b4_obligation_binding(two_variable_result):
    certificate = two_variable_result["symbolic_claim_verifier"]["certificate"]
    assert certificate["base_point_certificate"]["point"] == {"x": "0", "y": "0"}
    assert certificate["base_point_certificate"]["lhs_value"] == "0"
    assert certificate["base_point_certificate"]["rhs_value"] == "0"
    assert certificate["connected_domain_certificate"]["connected"] is True
    assert certificate["connected_domain_certificate"]["nonempty"] is True
    assert certificate["connected_domain_certificate"]["connected_component"]["variables"] == ["x", "y"]
    graph = certificate["domain_obligation_graph"]
    assert graph["graph_hash"] == certificate["domain_obligation_graph_hash"]
    assert B4.recheck_obligation_graph(
        {k: claim()[k] for k in ("lhs", "rhs", "symbols", "scope")},
        claim()["domain"], claim()["assumptions"], graph)["ok"]


def test_certificate_serialization_is_deterministic_and_cli_rechecks_independently(
        two_variable_result):
    certificate = two_variable_result["symbolic_claim_verifier"]["certificate"]
    first = json.dumps(certificate, sort_keys=True, separators=(",", ":"))
    second = json.dumps(json.loads(first), sort_keys=True, separators=(",", ":"))
    assert first == second
    result, rc, process = _cli(
        "recheck-symbolic-certificate", {"claim": claim(), "certificate": certificate})
    assert process.stderr == "" and rc == 0 and result["recheck_ok"] is True


def test_univariate_b1_route_is_backward_compatible():
    parent = {
        "lhs": "atan(x)", "rhs": "asin(x/sqrt(1+x**2))", "symbols": ["x"],
        "scope": "real_scalars", "assumptions": ["x real"],
        "domain": {"kind": "real_line", "variable": "x"},
    }
    univariate_request = {
        "operation": "symbolic_identity_verify", "contract_version": "1.0",
        "verification_mode": "symbolic_only", "claim": parent}
    result, rc, _ = _cli("symbolic-identity-verify", univariate_request)
    assert rc == 0
    assert result["symbolic_claim_verifier"]["certificate"]["kind"] == \
        "derivative_base_point_composite"
    assert result["combined_verdict"] == "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT"
