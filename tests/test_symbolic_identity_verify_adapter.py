"""Fusion Stage 1 conformance for the general `symbolic_identity_verify` capability.

Every check goes through the REAL CLI (CLI -> real ORCH registry -> production adapter ->
handler), the same discipline that certified geometric_basis_verify.
"""
import json, subprocess, sys, tempfile, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"


def _cli(args, stdin=""):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL)] + args, input=stdin,
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        return {"_raw": p.stdout}, p.returncode


def _req(lhs, rhs, symbols=("x", "y"), scope="real_scalars", assumptions=("x,y real",), **extra):
    claim = {"lhs": lhs, "rhs": rhs, "symbols": list(symbols), "scope": scope,
             "assumptions": list(assumptions)}
    claim.update(extra.pop("claim_extra", {}))
    r = {"operation": "symbolic_identity_verify", "contract_version": "1.0",
         "verification_mode": "symbolic_only", "claim": claim}
    r.update(extra)
    return json.dumps(r)


def test_capability_registered():
    out, _ = _cli(["list-operations"]); assert "symbolic_identity_verify" in out["operations"]

def test_true_identity_certified():
    out, rc = _cli(["symbolic-identity-verify"], _req("(x+y)**2", "x**2+2*x*y+y**2"))
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert out["combined_evidence_level"] == 3
    assert out["symbolic_claim_verifier"]["certificate"]["type"] == "canonical_zero_residual"
    assert rc == 0

def test_trig_identity_certified():
    out, _ = _cli(["symbolic-identity-verify"], _req("sin(x)**2+cos(x)**2", "1", symbols=("x",)))
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"

def test_false_identity_disproved_by_real_counterexample():
    # a genuinely false identity must be DISPROVED via a real numeric witness, not merely
    # "simplify didn't reach 0"
    out, rc = _cli(["symbolic-identity-verify"], _req("(x+y)**2", "x**2+y**2"))
    assert out["combined_verdict"] == "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"
    assert out["combined_evidence_level"] == 2
    assert out["symbolic_claim_verifier"]["certificate"] is None
    assert out["numerical_geobasis_verifier"]["witness_point"] is not None
    assert rc == 0

def test_true_but_hard_identity_is_not_falsely_disproved():
    # atan(x) == asin(x/sqrt(1+x^2)) is TRUE for all real x, but sympy.simplify cannot
    # crush it. The judge must NOT call this DISPROVED — only numerically-consistent (L1).
    out, rc = _cli(["symbolic-identity-verify"], _req("atan(x)", "asin(x/sqrt(1+x**2))", symbols=("x",)))
    assert out["combined_verdict"] == "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN"
    assert out["combined_evidence_level"] == 1
    assert out["symbolic_claim_verifier"]["certificate"] is None
    assert out["numerical_geobasis_verifier"]["witness_point"] is None
    assert out["unresolved_obligations"]  # a real open obligation, honestly recorded
    assert rc == 0

def test_certificate_is_cross_checked_by_independent_numerics():
    # audit-the-auditor: a level-3 certificate must be backed by an INDEPENDENT numeric
    # confirmation, not simplify() alone
    out, _ = _cli(["symbolic-identity-verify"], _req("(x+y)**2", "x**2+2*x*y+y**2"))
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert out["oracle_relation"] == "SYMBOLIC_AND_NUMERICAL_AGREE"
    cc = out["symbolic_claim_verifier"]["certificate"]["cross_check"]
    assert cc["method"] == "independent_numeric_evalf" and cc["points_probed"] > 0
    assert out["numerical_geobasis_verifier"]["witness_point"] is None

def test_code_injection_rejected():
    out, rc = _cli(["symbolic-identity-verify"],
                   _req("__import__('os').system('id')", "0", symbols=("x",)))
    assert out.get("orch_error") == "DISALLOWED_CHARACTERS" and rc != 0

def test_undeclared_function_rejected():
    out, rc = _cli(["symbolic-identity-verify"], _req("evilfunc(x)", "x", symbols=("x",)))
    assert out.get("orch_error") == "UNDECLARED_OR_DISALLOWED_NAME" and rc != 0

def test_undeclared_symbol_rejected():
    out, rc = _cli(["symbolic-identity-verify"], _req("x+z", "x", symbols=("x",)))
    assert out.get("orch_error") == "UNDECLARED_OR_DISALLOWED_NAME" and rc != 0

def test_gold_metadata_rejected():
    out, rc = _cli(["symbolic-identity-verify"],
                   _req("x", "x", symbols=("x",), claim_extra={"gold_verdict": "VERIFIED"}))
    assert out.get("orch_error") == "BENCHMARK_METADATA_NOT_ALLOWED" and rc != 0

def test_oversized_expression_rejected():
    big = "+".join(["x"] * 5000)
    out, rc = _cli(["symbolic-identity-verify"], _req(big, "x", symbols=("x",)))
    assert out.get("orch_error") in ("EXPRESSION_TOO_LARGE",) and rc != 0

def test_policy_timeout_cannot_be_weakened():
    out, rc = _cli(["symbolic-identity-verify"],
                   _req("x", "x", symbols=("x",), policy_overrides={"simplify_timeout_seconds": 9999}))
    assert out.get("orch_error") == "POLICY_VIOLATION" and rc != 0

def test_numerical_mode_rejected():
    r = json.loads(_req("x", "x", symbols=("x",))); r["verification_mode"] = "numerical_only"
    out, rc = _cli(["symbolic-identity-verify"], json.dumps(r))
    assert out.get("orch_error") == "UNSUPPORTED_VERIFICATION_MODE" and rc != 0

def test_replay_artifact_emitted_on_success():
    out, _ = _cli(["symbolic-identity-verify"], _req("x*(y+1)", "x*y+x"))
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY"
    assert out["replay_artifact"]["sha256"]
