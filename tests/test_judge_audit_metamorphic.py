"""Audit the auditor — metamorphic / property fuzz of the symbolic identity judge.

The judge's verdict rests on sympy; nobody audits sympy. This harness audits the judge's
DECISION PROCEDURE against two soundness properties that must never break, plus metamorphic
invariants. It is deterministic (fixed constructions, no RNG) so failures are reproducible.

Soundness properties:
  P1 NO FALSE CERTIFICATE — a constructed-FALSE identity must never be VERIFIED (level 3).
  P2 NO FALSE DISPROOF     — a constructed-TRUE identity must never be DISPROVED
     (it may be VERIFIED or NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN, but not disproved).
     (P2 is exactly the bug the fusion Stage-2 demo caught.)

Metamorphic invariants: symmetry (lhs==rhs ~ rhs==lhs) and scaling (k*lhs==k*rhs).
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"


def _judge(lhs, rhs, symbols=("x", "y")):
    req = json.dumps({"operation": "symbolic_identity_verify", "contract_version": "1.0",
                      "verification_mode": "symbolic_only",
                      "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols),
                                "scope": "real_scalars", "assumptions": ["real"]}})
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL), "symbolic-identity-verify"], input=req,
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    return json.loads(p.stdout)


# constructed-TRUE identities (rhs is an algebraically equal rewrite of lhs)
TRUE_CASES = [
    ("(x+y)**2", "x**2+2*x*y+y**2"),
    ("x*(y+1)", "x*y+x"),
    ("(x-y)*(x+y)", "x**2-y**2"),
    ("(x+y)**3", "x**3+3*x**2*y+3*x*y**2+y**3"),
    ("sin(x)**2+cos(x)**2", "1"),
    ("cos(2*x)", "2*cos(x)**2-1"),
    ("sin(2*x)", "2*sin(x)*cos(x)"),
    # true-but-hard for simplify() — must NOT be disproved (P2)
    ("atan(x)", "asin(x/sqrt(1+x**2))"),
    ("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)"),
]

# constructed-FALSE identities (a genuine nonzero perturbation)
FALSE_CASES = [
    ("(x+y)**2", "x**2+y**2"),
    ("x*(y+1)", "x*y"),
    ("(x-y)*(x+y)", "x**2+y**2"),
    ("sin(x)**2+cos(x)**2", "2"),
    ("cos(2*x)", "2*cos(x)**2+1"),
    ("x**2", "x**3"),
]

SUCCESS = {"VERIFIED_SYMBOLIC_IDENTITY"}
DISPROOF = {"DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"}


def test_P1_no_false_certificate():
    """No constructed-false identity may ever earn a level-3 certificate."""
    offenders = []
    for lhs, rhs in FALSE_CASES:
        out = _judge(lhs, rhs)
        if out.get("combined_verdict") in SUCCESS or out.get("combined_evidence_level") == 3:
            offenders.append((lhs, rhs, out.get("combined_verdict")))
    assert not offenders, f"FALSE CERTIFICATE issued: {offenders}"


def test_P2_no_false_disproof():
    """No constructed-true identity may ever be disproved."""
    offenders = []
    for lhs, rhs in TRUE_CASES:
        out = _judge(lhs, rhs)
        if out.get("combined_verdict") in DISPROOF:
            offenders.append((lhs, rhs, out.get("combined_verdict")))
    assert not offenders, f"FALSE DISPROOF issued: {offenders}"


def test_true_cases_are_verified_or_honestly_unproven():
    for lhs, rhs in TRUE_CASES:
        v = _judge(lhs, rhs).get("combined_verdict")
        assert v in (SUCCESS | {"NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN"}), f"{lhs}=={rhs} -> {v}"


def test_false_cases_are_disproved_or_inconclusive_never_verified():
    for lhs, rhs in FALSE_CASES:
        v = _judge(lhs, rhs).get("combined_verdict")
        assert v not in SUCCESS, f"false {lhs}=={rhs} -> {v}"


def test_metamorphic_symmetry():
    """Swapping sides must not change whether it certifies."""
    for lhs, rhs in TRUE_CASES + FALSE_CASES:
        a = _judge(lhs, rhs).get("combined_verdict") in SUCCESS
        b = _judge(rhs, lhs).get("combined_verdict") in SUCCESS
        assert a == b, f"symmetry broken: {lhs}=={rhs} certifies={a}, swapped={b}"


def test_metamorphic_scaling_preserves_certification():
    """If lhs==rhs certifies, 3*lhs==3*rhs must also certify."""
    for lhs, rhs in TRUE_CASES:
        base = _judge(lhs, rhs).get("combined_verdict")
        if base in SUCCESS:
            scaled = _judge(f"3*({lhs})", f"3*({rhs})").get("combined_verdict")
            assert scaled in SUCCESS, f"scaling broke certification for {lhs}=={rhs}"
