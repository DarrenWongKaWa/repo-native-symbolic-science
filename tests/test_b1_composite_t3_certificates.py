"""B1: exact positive-root child and structured-domain T3 composite certificates."""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
sys.path.insert(0, str(REPO))

from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as RC

PARENT_LHS = "atan(x)"
PARENT_RHS = "asin(x/sqrt(1+x**2))"
STRUCTURED_DOMAIN = {"kind": "real_line", "variable": "x"}


def _cli(command, payload):
    env = dict(os.environ)
    env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp()
    env["PYTHONPATH"] = ""
    proc = subprocess.run([sys.executable, str(CTL), command], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=str(REPO), env=env)
    return json.loads(proc.stdout), proc.returncode


def _judge(domain=STRUCTURED_DOMAIN, lhs=PARENT_LHS, rhs=PARENT_RHS):
    return _cli("symbolic-identity-verify", {
        "operation": "symbolic_identity_verify", "contract_version": "1.0",
        "verification_mode": "symbolic_only",
        "claim": {"lhs": lhs, "rhs": rhs, "symbols": ["x"], "scope": "real_scalars",
                  "assumptions": ["x real"], "domain": domain},
    })


def _composite():
    out, rc = _judge()
    assert rc == 0
    cert = out["symbolic_claim_verifier"]["certificate"]
    assert cert["kind"] == "derivative_base_point_composite"
    return out, cert


def _child():
    _, cert = _composite()
    return cert["derivative_child"], cert["derivative_child"]["certificate"]


def _recheck(claim, certificate):
    return _cli("recheck-symbolic-certificate", {"claim": claim, "certificate": certificate})


def test_target_derivative_child_gets_exact_positive_root_certificate():
    child, certificate = _child()
    assert certificate["kind"] == "positive_sqrt_algebraic_cofactor"
    assert certificate["root_atoms"][0]["branch"] == "positive"
    assert certificate["applied_root_lemmas"] == [
        "positive_power_three_halves", "positive_sqrt_reciprocal"]
    assert certificate["verified_radicand_equalities"]
    result, rc = _recheck(child, certificate)
    assert rc == 0 and result["recheck_ok"] is True


def test_child_rechecker_rejects_false_or_copied_claim():
    child, certificate = _child()
    false = dict(child, rhs="0")
    result, rc = _recheck(false, certificate)
    assert rc != 0 and result["recheck_ok"] is False


def test_child_rechecker_rejects_tampered_root_branch_sos_and_relation():
    child, certificate = _child()
    for mutate in (
        lambda c: c["root_atoms"][0].update(relation="r_0**2 - x**2"),
        lambda c: c["root_atoms"][0].update(branch="negative"),
        lambda c: c["root_atoms"][0].pop("positivity_certificate"),
        lambda c: c["root_atoms"][0]["positivity_certificate"].update(positive_constant="2"),
    ):
        bad = copy.deepcopy(certificate)
        mutate(bad)
        result, rc = _recheck(child, bad)
        assert rc != 0 and result["recheck_ok"] is False


def test_child_rechecker_rejects_tampered_equality_numerator_cofactor_or_denominator_obligation():
    child, certificate = _child()
    for mutate in (
        lambda c: c["verified_radicand_equalities"][0].update(rhs="1/(x**2 + 2)"),
        lambda c: c.update(numerator_polynomial="1"),
        lambda c: c["relation_cofactors"][0].update(cofactor="1"),
        lambda c: c.update(denominator_obligations=[]),
    ):
        bad = copy.deepcopy(certificate)
        mutate(bad)
        result, rc = _recheck(child, bad)
        assert rc != 0 and result["recheck_ok"] is False


def test_nonpositive_and_nested_root_children_are_ineligible():
    x = validate_and_parse("x", ["x"], real=True)
    bad_lhs = validate_and_parse("1/sqrt(x**2-1)", ["x"], real=True)
    nested = validate_and_parse("sqrt(sqrt(x**2+1))", ["x"], real=True)
    assert RC.build_positive_sqrt_algebraic_cofactor_certificate(bad_lhs, bad_lhs, ["x"]) is None
    assert RC.build_positive_sqrt_algebraic_cofactor_certificate(nested, nested, ["x"]) is None
    assert x.is_real is True


def test_child_rechecker_source_contains_no_simplify_call():
    source = (REPO / "loop_engine/orch_adapters/symbolic_identity_verify/recheck.py").read_text()
    assert "simplify(" not in source


def test_structured_real_line_parent_gets_and_rechecks_composite():
    out, certificate = _composite()
    assert out["combined_verdict"] == "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT"
    assert certificate["independently_recheckable"] is True
    assert certificate["base_point_certificate"]["point"] == {"x": "0"}
    assert certificate["domain_certificate"]["kind"] == "real_line"
    assert certificate["domain_obligation_summary"]["status"] == "PROVED"
    result, rc = _recheck({"lhs": PARENT_LHS, "rhs": PARENT_RHS, "symbols": ["x"]}, certificate)
    assert rc == 0 and result["recheck_ok"] is True


def test_composite_rechecker_rejects_base_child_hash_domain_and_metadata_tampering():
    _, certificate = _composite()
    for mutate in (
        lambda c: c["base_point_certificate"].update(point={"x": "1"}),
        lambda c: c["derivative_child"].update(rhs="0"),
        lambda c: c["derivative_child"].update(claim_hash="wrong"),
        lambda c: c.update(parent_claim_hash="wrong"),
        lambda c: c["domain_certificate"].update(variable="y"),
        lambda c: c["domain_certificate"].update(definedness_and_differentiability_obligations=[]),
        lambda c: c.update(independently_recheckable=False),
    ):
        bad = copy.deepcopy(certificate)
        mutate(bad)
        result, rc = _recheck({"lhs": PARENT_LHS, "rhs": PARENT_RHS, "symbols": ["x"]}, bad)
        assert rc != 0 and result["recheck_ok"] is False


def test_composite_rechecker_rejects_a_copied_child_certificate():
    _, certificate = _composite()
    bad = copy.deepcopy(certificate)
    bad["derivative_child"]["certificate"] = {
        "kind": "polynomial_pointwise_nullstellensatz", "symbols": ["x"], "per_variable_values": [0]}
    result, rc = _recheck({"lhs": PARENT_LHS, "rhs": PARENT_RHS, "symbols": ["x"]}, bad)
    assert rc != 0 and result["recheck_ok"] is False


def test_free_form_or_unrecognized_domains_remain_honestly_nonrecheckable():
    for domain in ("connected: all real x", "not-a-validated-connected-domain",
                   {"kind": "not-a-validated-connected-domain", "variable": "x"}):
        out, rc = _judge(domain=domain)
        assert rc == 0
        certificate = out["symbolic_claim_verifier"]["certificate"]
        assert certificate["kind"] == "derivative_base_point"
        assert certificate["independently_recheckable"] is False
