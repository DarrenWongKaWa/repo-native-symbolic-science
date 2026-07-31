"""B5 positive contract: complete ordered gradient plus exact connected base point."""
import copy
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


def _assert_b5_blocked(parent):
    result, rc, process = _cli("multivariable-t3-verify", request(parent))
    assert process.stderr == ""
    assert rc != 0
    assert result["combined_verdict"] == "MULTIVARIABLE_T3_BLOCKED"
    assert result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["certificate"] is None


def _valid_certificate(parent):
    result, rc, process = _cli("multivariable-t3-verify", request(parent))
    assert process.stderr == "" and rc == 0
    return result["symbolic_claim_verifier"]["certificate"]


def _reseal_exact_envelope(envelope):
    envelope["context_binding_hash"] = B5.sha(envelope["context_binding"])
    envelope["proof_hash"] = B5.sha(envelope["proof"])
    envelope["artifact_hash"] = B5._artifact_hash(envelope)


def _reseal_certificate(certificate):
    graph = certificate["gradient_certificate_graph"]
    for child in graph["children"]:
        child["proof_certificate_hash"] = B5._artifact_hash(
            child["proof_certificate"])
        child_body = copy.deepcopy(child)
        child_body.pop("child_hash", None)
        child["child_hash"] = B5.sha(child_body)
    graph["ordered_child_hashes"] = [
        child["child_hash"] for child in graph["children"]]
    graph_body = copy.deepcopy(graph)
    graph_body.pop("gradient_graph_hash", None)
    graph["gradient_graph_hash"] = B5.sha(graph_body)
    certificate["artifact_hash"] = B5._artifact_hash(certificate)


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


def test_b5_rejects_reserved_declared_symbol_shadowing():
    reserved_names = [
        "pi", "E", "I", "oo", "zoo", "nan", "Rational", "Integer",
        "Float", "Symbol", "sin", "cos", "exp", "log", "sqrt",
    ]
    for reserved in reserved_names:
        _assert_b5_blocked(claim((reserved, "y"), lhs="y", rhs="y"))


def test_b5_rejects_floor_division_source_erased_pole():
    _assert_b5_blocked(claim(
        lhs="(x**2-1)//(x-1)",
        rhs="x+1",
    ))


def test_b5_rejects_bitxor_source_operator():
    _assert_b5_blocked(claim(
        lhs="x^2 + y",
        rhs="x**2 + y",
    ))


def test_b5_rejects_rounded_float_base_equality():
    _assert_b5_blocked(claim(
        lhs="x+y+0.1+0.2",
        rhs="x+y+0.3",
    ))


def test_b5_rejects_nonfinite_parent_and_base_values():
    for source in ("oo+x+y", "zoo+x+y", "nan+x+y"):
        _assert_b5_blocked(claim(lhs=source, rhs=source))
    for point_value in ("1/0", "nan", "oo"):
        parent = claim(lhs="x+y", rhs="x+y")
        parent["multivariable_t3"]["base_point"]["x"] = point_value
        _assert_b5_blocked(parent)


def test_b5_rechecker_rejects_fabricated_resealed_b3_transcript(
        two_variable_result):
    bad = copy.deepcopy(
        two_variable_result["symbolic_claim_verifier"]["certificate"])
    confirmation = bad["gradient_certificate_graph"]["children"][0][
        "second_engine_confirmation"]
    confirmation["process_stderr"] = "REVIEWER_SYNTHETIC_NOT_PROCESS_OUTPUT"
    _reseal_certificate(bad)
    assert B5.recheck_certificate(claim(), bad)["ok"] is False


def test_b5_rechecker_rejects_resealed_malformed_exact_child(
        two_variable_result):
    bad = copy.deepcopy(
        two_variable_result["symbolic_claim_verifier"]["certificate"])
    envelope = bad["gradient_certificate_graph"]["children"][0][
        "proof_certificate"]
    envelope["proof"]["attacker_extra"] = "accepted"
    _reseal_exact_envelope(envelope)
    _reseal_certificate(bad)
    assert B5.recheck_certificate(claim(), bad)["ok"] is False


def test_b5_rejects_resealed_foreign_parent_child_with_identical_derivative(
        two_variable_result):
    original = two_variable_result["symbolic_claim_verifier"]["certificate"]
    shifted_parent = claim(
        lhs="sin(x+y)+1",
        rhs="sin(x)*cos(y)+cos(x)*sin(y)+1",
    )
    shifted = _valid_certificate(shifted_parent)
    source_child = copy.deepcopy(
        original["gradient_certificate_graph"]["children"][0])
    target_child = shifted["gradient_certificate_graph"]["children"][0]
    assert source_child["lhs"] == target_child["lhs"]
    assert source_child["rhs"] == target_child["rhs"]

    for field in (
            "parent_claim_hash", "variable_order_hash", "base_point_hash",
            "domain_certificate_hash", "domain_obligation_graph_hash",
            "derivative_claim_hash", "child_context_binding",
            "child_context_binding_hash"):
        source_child[field] = copy.deepcopy(target_child[field])
    source_envelope = source_child["proof_certificate"]
    source_envelope["context_binding"] = copy.deepcopy(
        target_child["child_context_binding"])
    _reseal_exact_envelope(source_envelope)

    bad = copy.deepcopy(shifted)
    bad["gradient_certificate_graph"]["children"][0] = source_child
    _reseal_certificate(bad)
    assert B5.recheck_certificate(shifted_parent, bad)["ok"] is False
