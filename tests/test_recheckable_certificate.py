"""Audit-the-auditor #3 — re-checkable certificates ("trust the proof, not the prover").

For a polynomial identity, the judge emits a certificate a third party re-verifies by exact
pointwise evaluation, using NO sympy.simplify. These tests confirm: valid certs re-verify,
tampered/misapplied certs FAIL, the re-checker never calls simplify, and the grid is sized by
the CLAIM's degree (the soundness fix — a canceled difference must not shrink the grid).
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
sys.path.insert(0, str(REPO))
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as RC


def _cli(subcmd, payload):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL), subcmd], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        return {"_raw": p.stdout}, p.returncode


def _certify(lhs, rhs, symbols=("x", "y")):
    req = {"operation": "symbolic_identity_verify", "contract_version": "1.0",
           "verification_mode": "symbolic_only",
           "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols), "scope": "s", "assumptions": ["a"]}}
    out, _ = _cli("symbolic-identity-verify", req)
    return out


# ---- certificate emission ---------------------------------------------------------
def test_polynomial_identity_gets_recheckable_certificate():
    out = _certify("(x+y)**3", "x**3+3*x**2*y+3*x*y**2+y**3")
    cert = out["symbolic_claim_verifier"]["certificate"]
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert cert["independently_recheckable"] is True
    rc = cert["recheckable_certificate"]
    assert rc["kind"] == "polynomial_pointwise_nullstellensatz"
    assert rc["total_degree"] == 3 and len(rc["per_variable_values"]) == 4  # sized by CLAIM degree

def test_trig_identity_is_now_recheckable_via_T1():
    # superseded by tier T1 (trig -> Pythagorean-ideal cofactor certificate): this used to be
    # "certified but not independently re-checkable"; it now carries a real certificate.
    out = _certify("sin(x)**2+cos(x)**2", "1", symbols=("x",))
    cert = out["symbolic_claim_verifier"]["certificate"]
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert cert["independently_recheckable"] is True
    assert cert["recheckable_certificate"]["kind"] == "trig_ideal_cofactor"


def test_a_class_still_outside_recheckability_is_not_overclaimed():
    # inverse-trig needs tier T3 (derivative + base point), which is not built: it must stay
    # honestly unproven rather than be handed a certificate it hasn't earned.
    out = _certify("atan(x)", "asin(x/sqrt(1+x**2))", symbols=("x",))
    assert out["combined_verdict"] == "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN"
    assert (out["symbolic_claim_verifier"].get("certificate") or {}) == {} or \
           out["symbolic_claim_verifier"]["certificate"] is None


# ---- independent re-check (the third-party surface) -------------------------------
def test_valid_certificate_reverifies():
    out = _certify("(x+y)**2", "x**2+2*x*y+y**2")
    cert = out["symbolic_claim_verifier"]["certificate"]["recheckable_certificate"]
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "(x+y)**2", "rhs": "x**2+2*x*y+y**2", "symbols": ["x", "y"]},
                    "certificate": cert})
    assert res["recheck_ok"] is True and rc == 0

def test_certificate_reused_for_a_false_claim_fails():
    out = _certify("(x+y)**3", "x**3+3*x**2*y+3*x*y**2+y**3")
    cert = out["symbolic_claim_verifier"]["certificate"]["recheckable_certificate"]
    # same (valid-degree) grid, but a FALSE claim -> must fail with a witness
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "(x+y)**3", "rhs": "x**3+y**3", "symbols": ["x", "y"]},
                    "certificate": cert})
    assert res["recheck_ok"] is False and rc != 0
    assert "non-zero residual" in res["detail"]

def test_understated_degree_grid_is_rejected():
    # a tampered cert that claims degree 0 (1-point grid at origin) for a degree-3 false claim
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "(x+y)**3", "rhs": "x**3+y**3", "symbols": ["x", "y"]},
                    "certificate": {"kind": "polynomial_pointwise_nullstellensatz",
                                    "total_degree": 0, "per_variable_values": [0], "symbols": ["x", "y"]}})
    assert res["recheck_ok"] is False and "grid too small" in res["detail"]

def test_recheck_of_a_true_polynomial_identity_via_api():
    r = RC.build_polynomial_certificate(*_parse("(x-y)*(x+y)", "x**2-y**2", ["x", "y"]), ["x", "y"])
    assert r is not None
    out = RC.recheck({"lhs": "(x-y)*(x+y)", "rhs": "x**2-y**2", "symbols": ["x", "y"]}, r)
    assert out["ok"] is True


def _parse(lhs, rhs, symbols):
    from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse
    return validate_and_parse(lhs, symbols), validate_and_parse(rhs, symbols)


# ---- the re-checker must not trust simplify --------------------------------------
def test_rechecker_does_not_call_simplify():
    src = (REPO / "loop_engine/orch_adapters/symbolic_identity_verify/recheck.py").read_text()
    assert "simplify(" not in src, "the re-checker must be independent of simplify"
