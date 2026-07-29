"""Audit-the-auditor #4 — differential testing across independent canonicalizers.

Never trust one simplification heuristic. The judge runs several independent routes; a
route reaching 0 is a proof, the count of agreeing routes is a robustness signal, and a
claim proved by exactly ONE route is flagged fragile for higher scrutiny.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"


def _judge(lhs, rhs, symbols=("x",)):
    req = {"operation": "symbolic_identity_verify", "contract_version": "1.0",
           "verification_mode": "symbolic_only",
           "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols),
                     "scope": "s", "assumptions": ["a"]}}
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL), "symbolic-identity-verify"],
                       input=json.dumps(req), capture_output=True, text=True, cwd=str(REPO), env=env)
    return json.loads(p.stdout)


def _differential(out):
    sym = out.get("symbolic_claim_verifier") or {}
    cert = sym.get("certificate") or {}
    return cert.get("differential_canonicalization") or sym.get("differential_canonicalization") or {}


def test_multiple_independent_routes_are_recorded():
    out = _judge("sin(x)**2+cos(x)**2", "1")
    d = _differential(out)
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert len(d["proved_zero_by"]) >= 2, d          # several routes agree
    assert d["fragile_single_route"] is False

def test_single_route_proof_is_flagged_fragile():
    # tanh(x) == (exp(2x)-1)/(exp(2x)+1) is proved ONLY by the rewrite-to-exp route
    out = _judge("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)")
    d = _differential(out)
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert d["proved_zero_by"] == ["rewrite_exp"]
    assert d["fragile_single_route"] is True

def test_differential_raises_recall_beyond_plain_simplify():
    # plain simplify(expand(.)) does NOT prove this; the differential judge does
    import sympy
    x = sympy.Symbol("x")
    diff = sympy.tanh(x) - (sympy.exp(2*x) - 1)/(sympy.exp(2*x) + 1)
    assert sympy.simplify(sympy.expand(diff)) != 0          # single route fails
    assert _judge("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)")["combined_evidence_level"] == 3

def test_no_canonicalizer_route_proves_the_inverse_trig_case():
    # no canonicalizer can crush this one — that remains true. It is now proven by tier T3
    # (derivative + base point) instead, which is a different mechanism.
    out = _judge("atan(x)", "asin(x/sqrt(1+x**2))")
    assert _differential(out)["proved_zero_by"] == []
    assert out["combined_verdict"] == "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT"

def test_false_identity_still_disproved_under_differential():
    out = _judge("(x+y)**2", "x**2+y**2", symbols=("x", "y"))
    assert out["combined_verdict"] == "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"
    assert _differential(out)["proved_zero_by"] == []

def test_a_failing_route_is_not_treated_as_disproof():
    # factor/trigsimp do NOT prove sin^2+cos^2-1; that must not count as evidence against
    out = _judge("sin(x)**2+cos(x)**2", "1")
    votes = _differential(out)["votes"]
    assert any(v is False for v in votes.values())   # some routes did not reach 0
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"  # still certified
