"""T1/T2 — transcendental identities made independently re-checkable.

T1 trig -> polynomial modulo the Pythagorean ideal, certificate = cofactors g_i with
   P = sum(g_i * p_i); re-check is exact polynomial expansion.
T2 exp/hyperbolic -> substitute E = e^x, clear denominators, certify the numerator is
   identically zero; side conditions recorded.
Neither the builder's heuristics nor sympy.simplify are trusted by the re-checker.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"


def _cli(subcmd, payload):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL), subcmd], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        return {"_raw": p.stdout}, p.returncode


def _cert(lhs, rhs, symbols=("x",)):
    out, _ = _cli("symbolic-identity-verify",
                  {"operation": "symbolic_identity_verify", "contract_version": "1.0",
                   "verification_mode": "symbolic_only",
                   "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols),
                             "scope": "s", "assumptions": ["a"]}})
    return out, (out["symbolic_claim_verifier"]["certificate"] or {})


# ---- T1: trig ---------------------------------------------------------------------
def test_T1_trig_identity_gets_cofactor_certificate():
    out, cert = _cert("sin(x)**4-cos(x)**4", "sin(x)**2-cos(x)**2")
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert cert["independently_recheckable"] is True
    rc = cert["recheckable_certificate"]
    assert rc["kind"] == "trig_ideal_cofactor"
    assert rc["cofactors"] and rc["constraint_polynomials"] == ["c_x**2 + s_x**2 - 1"]

def test_T1_double_angle_is_recheckable():
    out, cert = _cert("cos(2*x)", "1-2*sin(x)**2")
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert cert["recheckable_certificate"]["kind"] == "trig_ideal_cofactor"

def test_T1_certificate_reverifies_independently():
    _, cert = _cert("sin(x)**4-cos(x)**4", "sin(x)**2-cos(x)**2")
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "sin(x)**4-cos(x)**4", "rhs": "sin(x)**2-cos(x)**2", "symbols": ["x"]},
                    "certificate": cert["recheckable_certificate"]})
    assert res["recheck_ok"] is True and rc == 0

def test_T1_cert_on_a_false_trig_claim_fails():
    _, cert = _cert("sin(x)**4-cos(x)**4", "sin(x)**2-cos(x)**2")
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "cos(2*x)", "rhs": "1-sin(x)**2", "symbols": ["x"]},
                    "certificate": cert["recheckable_certificate"]})
    assert res["recheck_ok"] is False and rc != 0

def test_T1_tampered_cofactor_fails():
    _, cert = _cert("sin(x)**4-cos(x)**4", "sin(x)**2-cos(x)**2")
    bad = dict(cert["recheckable_certificate"]); bad["cofactors"] = ["s_x**2"]
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "sin(x)**4-cos(x)**4", "rhs": "sin(x)**2-cos(x)**2", "symbols": ["x"]},
                    "certificate": bad})
    assert res["recheck_ok"] is False and "cofactor identity FAILS" in res["detail"]


# ---- T2: exp / hyperbolic ---------------------------------------------------------
def test_T2_tanh_gets_exp_certificate():
    out, cert = _cert("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)")
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    rc = cert["recheckable_certificate"]
    assert rc["kind"] == "exp_rational_numerator"
    assert rc["numerator_is_identically_zero"] is True

def test_T2_hyperbolic_pythagorean_is_recheckable():
    out, cert = _cert("cosh(x)**2-sinh(x)**2", "1")
    assert cert["recheckable_certificate"]["kind"] == "exp_rational_numerator"

def test_T2_certificate_reverifies_independently():
    _, cert = _cert("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)")
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "tanh(x)", "rhs": "(exp(2*x)-1)/(exp(2*x)+1)", "symbols": ["x"]},
                    "certificate": cert["recheckable_certificate"]})
    assert res["recheck_ok"] is True and rc == 0

def test_T2_cert_on_a_false_hyperbolic_claim_fails():
    _, cert = _cert("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)")
    res, rc = _cli("recheck-symbolic-certificate",
                   {"claim": {"lhs": "cosh(x)**2+sinh(x)**2", "rhs": "1", "symbols": ["x"]},
                    "certificate": cert["recheckable_certificate"]})
    assert res["recheck_ok"] is False and "NOT identically zero" in res["detail"]


# ---- scope honesty ----------------------------------------------------------------
def test_inverse_trig_still_not_recheckable_and_not_overclaimed():
    # atan == asin(x/sqrt(1+x^2)) is TRUE but needs tier T3 (derivative + base point);
    # it must not be silently claimed re-checkable, and must not be disproved.
    out, cert = _cert("atan(x)", "asin(x/sqrt(1+x**2))")
    assert out["combined_verdict"] == "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN"
    assert cert == {} or cert.get("independently_recheckable") in (None, False)

def test_rechecker_still_free_of_simplify():
    src = (REPO / "loop_engine/orch_adapters/symbolic_identity_verify/recheck.py").read_text()
    assert "simplify(" not in src
