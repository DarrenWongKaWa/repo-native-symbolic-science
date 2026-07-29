"""Fusion Stage 2 conformance for `propose_equation_candidates` via the real CLI.

Uses a committed deterministic stub backend (tests/fixtures/stub_proposer.py) so there is
no LLM dependency and no machine path. The load-bearing assertions are the GOVERNANCE ones:
the proposer emits only UNVERIFIED claims, never executes model code, never scores, and
drops anything unsafe/malformed.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
STUB = REPO / "tests" / "fixtures" / "stub_proposer.py"


def _cli(args, stdin="", proposer=True):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp(); env["PYTHONPATH"] = ""
    if proposer:
        env["VIPER_PROPOSER_CMD"] = f"{sys.executable} {STUB}"
    else:
        env.pop("VIPER_PROPOSER_CMD", None)
    p = subprocess.run([sys.executable, str(CTL)] + args, input=stdin,
                       capture_output=True, text=True, cwd=str(REPO), env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        return {"_raw": p.stdout}, p.returncode


def _req(symbols=("x", "y"), n=4, desc="algebraic identities", **extra):
    problem = {"description": desc, "symbols": list(symbols), "n_candidates": n}
    problem.update(extra.pop("problem_extra", {}))
    r = {"operation": "propose_equation_candidates", "contract_version": "1.0", "problem": problem}
    r.update(extra)
    return json.dumps(r)


def test_capability_registered():
    out, _ = _cli(["list-operations"]); assert "propose_equation_candidates" in out["operations"]

def test_proposer_authority_is_proposal_not_verification():
    # governance: the registered role must have proposal authority + be forbidden to verify
    src = (REPO / "scripts" / "orch_controller.py").read_text()
    assert '"claim_authority": "proposal"' in src
    assert '"verify_results"' in src and '"self_verify"' in src and '"score_candidates"' in src

def test_emits_only_unverified_claims():
    out, rc = _cli(["propose-equation-candidates"], _req(n=4))
    assert rc == 0 and out["n_accepted"] >= 1
    for c in out["candidates"]:
        assert c["status"] == "UNVERIFIED" and c["evidence_level"] == 0
        assert c["route_to"] == "symbolic_identity_verify"
        assert "verdict" not in c and "certificate" not in c

def test_never_executes_model_code_or_scores():
    out, _ = _cli(["propose-equation-candidates"], _req())
    assert out["provenance"]["executes_model_code"] is False
    assert out["provenance"]["scores_candidates"] is False

def test_unsafe_and_malformed_candidates_are_dropped_not_truncated_silently():
    out, _ = _cli(["propose-equation-candidates"], _req(n=4))
    # stub emits 2 valid + 1 code-injection + 1 undeclared-symbol -> 2 accepted, 2 dropped
    assert out["n_accepted"] == 2
    assert out["n_dropped_invalid"] == 2
    lhs = [c["lhs"] for c in out["candidates"]]
    assert not any("__import__" in x for x in lhs)

def test_gold_metadata_rejected():
    out, rc = _cli(["propose-equation-candidates"], _req(problem_extra={"gold_verdict": "VERIFIED"}))
    assert out.get("orch_error") == "BENCHMARK_METADATA_NOT_ALLOWED" and rc != 0

def test_backend_unconfigured_fails_closed():
    out, rc = _cli(["propose-equation-candidates"], _req(), proposer=False)
    assert out.get("orch_error") == "PROPOSER_BACKEND_NOT_CONFIGURED" and rc != 0

def test_candidate_count_capped():
    out, rc = _cli(["propose-equation-candidates"], _req(n=999))
    assert out.get("orch_error") == "CANDIDATE_COUNT_OUT_OF_RANGE" and rc != 0

def test_adapter_source_has_no_exec_or_eval():
    # the whole point of Stage 2: no code-execution surface in the proposer
    for f in ("propose_equation_candidates/core.py", "propose_equation_candidates_adapter.py"):
        src = (REPO / "loop_engine" / "orch_adapters" / f).read_text()
        assert "exec(" not in src and "eval(" not in src
