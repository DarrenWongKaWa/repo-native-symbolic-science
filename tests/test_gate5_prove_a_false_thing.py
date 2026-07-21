"""Gate 5 — adversarial "prove a false thing" attacks on the symbolic judge.

These actively try to make the judge issue a certificate for a claim that is FALSE as an
identity of functions on the declared domain. The first run of this suite found three real
false certificates ((x^2-1)/(x-1)==x+1, x/x==1, sqrt(x)*sqrt(x)==x); the domain guard was
built in response. These tests lock that in.

The governing rule: an UNCONDITIONAL certificate asserts equality everywhere on the declared
domain. Where definedness obligations can fail, the judge must say so — never issue the
unconditional verdict.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
STUB_NONZERO = REPO / "tests" / "fixtures" / "stub_second_cas_nonzero.py"

UNCONDITIONAL = {"VERIFIED_SYMBOLIC_IDENTITY", "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT"}


def _judge(lhs, rhs, symbols=("x",), scope="real_scalars", env_extra=None):
    req = {"operation": "symbolic_identity_verify", "contract_version": "1.0",
           "verification_mode": "symbolic_only",
           "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols), "scope": scope,
                     "assumptions": ["real"], "domain": "connected: all real x"}}
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    env.pop("VIPER_SECOND_CAS_CMD", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, str(CTL), "symbolic-identity-verify"],
                       input=json.dumps(req), capture_output=True, text=True, cwd=str(REPO), env=env)
    return json.loads(p.stdout)


def _cert(out):
    return (out.get("symbolic_claim_verifier") or {}).get("certificate") or {}


# ---- A. removable singularities / division traps ---------------------------------
def test_removable_singularity_is_not_certified_unconditionally():
    out = _judge("(x**2-1)/(x-1)", "x+1")
    assert out["combined_verdict"] not in UNCONDITIONAL, "false certificate: undefined at x=1"
    assert any("x - 1" in c for c in _cert(out).get("side_conditions", []))

def test_x_over_x_is_not_certified_unconditionally():
    out = _judge("x/x", "1")
    assert out["combined_verdict"] not in UNCONDITIONAL, "false certificate: undefined at x=0"
    assert any("x != 0" in c for c in _cert(out).get("side_conditions", []))

# ---- B. branch / domain traps -----------------------------------------------------
def test_sqrt_times_sqrt_is_not_certified_unconditionally():
    out = _judge("sqrt(x)*sqrt(x)", "x")
    assert out["combined_verdict"] not in UNCONDITIONAL, "false certificate: not real for x<0"
    assert any(">= 0" in c for c in _cert(out).get("side_conditions", []))

def test_sqrt_of_square_is_disproved():
    out = _judge("sqrt(x**2)", "x")          # false for x<0
    assert "DISPROVED" in out["combined_verdict"]

def test_abs_is_disproved():
    out = _judge("Abs(x)", "x")              # false for x<0
    assert "DISPROVED" in out["combined_verdict"]

# ---- C. numeric near-miss (attacks the probe, not the algebra) --------------------
def test_taylor_near_miss_is_not_certified():
    # agrees with sin(x) to 5th order — a float probe near 0 could be fooled
    out = _judge("sin(x)", "x-x**3/6+x**5/120")
    assert out["combined_verdict"] not in UNCONDITIONAL
    assert "DISPROVED" in out["combined_verdict"]

# ---- D. the judge must honour the DECLARED domain ---------------------------------
def test_declared_real_domain_is_used():
    # only provable over the reals; the judge must adjudicate the question actually asked
    out = _judge("atan(x)", "asin(x/sqrt(1+x**2))")
    assert out["combined_verdict"] == "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT"
    assert _cert(out)["domain"]

# ---- E. an independent second engine contradicting us must FAIL CLOSED ------------
def test_second_engine_contradiction_fails_closed():
    out = _judge("(x+y)**2", "x**2+2*x*y+y**2", symbols=("x", "y"),
                 env_extra={"VIPER_SECOND_CAS_CMD": f"{sys.executable} {STUB_NONZERO}"})
    assert out["combined_verdict"] == "DISPUTED_SECOND_ENGINE_CONFLICT"
    assert out["combined_evidence_level"] == 0
    assert out["symbolic_claim_verifier"]["certificate"] is None
    assert out["unresolved_obligations"]

def test_absent_second_engine_is_recorded_not_silently_passed():
    out = _judge("(x+y)**2", "x**2+2*x*y+y**2", symbols=("x", "y"))
    assert _cert(out)["second_engine"]["status"] == "not_configured"

# ---- F. genuine identities must still certify cleanly -----------------------------
def test_true_identities_still_certify_unconditionally():
    for lhs, rhs, syms in [("(x+y)**2", "x**2+2*x*y+y**2", ("x", "y")),
                           ("sin(x)**2+cos(x)**2", "1", ("x",)),
                           ("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)", ("x",))]:
        out = _judge(lhs, rhs, symbols=syms)
        assert out["combined_verdict"] in UNCONDITIONAL, f"{lhs}=={rhs} -> {out['combined_verdict']}"
        assert not _cert(out).get("side_conditions")
