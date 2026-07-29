"""Fusion Stage 3 — the searcher cannot reach the judge.

Generalises tests/test_release_bundle_isolation.py from "runtime can't reach gold" to
"searcher can't reach judge". Two enforced layers:

  1. CODE isolation: importing the proposer must not pull the judge's scoring module into
     the process, and the proposer source must not import the judge.
  2. REGISTRY isolation: the 'proposer' profile physically omits the judge capabilities, so
     routing a proposal to the judge from a searcher context fails CAPABILITY_NOT_REGISTERED.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))


def _cli(args, stdin=""):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL)] + args, input=stdin,
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        return {"_raw": p.stdout}, p.returncode


# ---- CODE isolation --------------------------------------------------------------
def test_proposer_source_does_not_import_the_judge():
    src = (REPO / "loop_engine/orch_adapters/propose_equation_candidates/core.py").read_text()
    # no import of the judge module; the shared parser lives in the neutral module
    assert "import symbolic_identity_verify" not in src
    assert "from loop_engine.orch_adapters.symbolic_identity_verify" not in src
    assert "_symbolic_safe_parse" in src

def test_importing_proposer_does_not_load_the_judge():
    code = ("import sys;"
            "import loop_engine.orch_adapters.propose_equation_candidates_adapter as a;"
            "print('LEAK' if any('symbolic_identity_verify' in m for m in sys.modules) else 'CLEAN')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO))
    assert "CLEAN" in r.stdout, f"proposer pulled the judge into memory: {r.stdout} {r.stderr}"

def test_shared_parser_has_no_scoring_or_verdict():
    # the neutral parser may NAME gold fields it rejects (e.g. gold_certificate in FORBIDDEN),
    # but it must contain no scoring/verdict CODE.
    src = (REPO / "loop_engine/orch_adapters/_symbolic_safe_parse.py").read_text()
    for banned in ("simplify(", "combined_verdict", "VERIFIED_SYMBOLIC_IDENTITY", "_numeric_probe"):
        assert banned not in src, f"neutral parser leaks scoring surface: {banned}"


# ---- REGISTRY isolation ----------------------------------------------------------
def test_proposer_profile_omits_the_judge():
    import orch_controller as ctl
    reg = ctl.build_registry("proposer")
    ops = set(reg._adapters.keys())
    assert "propose_equation_candidates" in ops
    assert "symbolic_identity_verify" not in ops
    assert "geometric_basis_verify" not in ops

def test_judge_profile_omits_the_proposer():
    import orch_controller as ctl
    reg = ctl.build_registry("judge")
    ops = set(reg._adapters.keys())
    assert "symbolic_identity_verify" in ops
    assert "propose_equation_candidates" not in ops

def test_full_profile_has_both():
    import orch_controller as ctl
    ops = set(ctl.build_registry("full")._adapters.keys())
    assert {"propose_equation_candidates", "symbolic_identity_verify"} <= ops

def test_searcher_cannot_route_to_judge_via_cli():
    req = json.dumps({"operation": "symbolic_identity_verify", "contract_version": "1.0",
                      "verification_mode": "symbolic_only",
                      "claim": {"lhs": "x", "rhs": "x", "symbols": ["x"], "scope": "s", "assumptions": ["a"]}})
    out, rc = _cli(["--profile", "proposer", "symbolic-identity-verify"], req)
    assert out.get("orch_error") == "CAPABILITY_NOT_REGISTERED" and rc != 0

def test_judge_still_reachable_under_judge_profile():
    req = json.dumps({"operation": "symbolic_identity_verify", "contract_version": "1.0",
                      "verification_mode": "symbolic_only",
                      "claim": {"lhs": "(x+y)**2", "rhs": "x**2+2*x*y+y**2", "symbols": ["x", "y"],
                                "scope": "s", "assumptions": ["a"]}})
    out, rc = _cli(["--profile", "judge", "symbolic-identity-verify"], req)
    assert out["combined_verdict"] == "VERIFIED_SYMBOLIC_IDENTITY" and rc == 0

def test_unknown_profile_rejected():
    r = subprocess.run([sys.executable, str(CTL), "--profile", "backdoor", "list-operations"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode != 0  # argparse choices reject it
