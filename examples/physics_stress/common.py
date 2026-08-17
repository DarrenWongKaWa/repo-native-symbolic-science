"""Shared helpers for the physics-stress examples.

Each derive_claims.py emits JSONL claim records; run_all.py (and the pytest
wrapper) submit them through the REAL controller CLI and evaluate against the
honest verdict ladder defined below.
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CTL = REPO / "scripts" / "orch_controller.py"

POSITIVE_VERDICTS = {
    "VERIFIED_SYMBOLIC_IDENTITY",
    "VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS",
    "VERIFIED_ON_EXPLICIT_SUBDOMAIN",
    "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT",
    "SYMBOLIC_ZERO_PENDING_SECOND_ENGINE",
    "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN",
}
CERTIFIED_LEVEL3 = {
    "VERIFIED_SYMBOLIC_IDENTITY",
    "VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS",
    "VERIFIED_ON_EXPLICIT_SUBDOMAIN",
    "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT",
}
REFUTATION_VERDICTS = {
    "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE",
    "DISPUTED_SECOND_ENGINE_CONFLICT",
    "SECOND_ENGINE_CONTRADICTS_CERTIFICATE",
}


def envelope(claim, symbols, scope, assumptions):
    return {"operation": "symbolic_identity_verify", "contract_version": "1.0",
            "verification_mode": "symbolic_only",
            "claim": {"lhs": claim["lhs"], "rhs": claim["rhs"],
                      "symbols": list(symbols), "scope": scope,
                      "assumptions": list(assumptions)}}


def judge(claim, timeout=480):
    """Submit one claim through the REAL controller CLI; return its JSON verdict."""
    outdir = tempfile.mkdtemp()
    env = dict(os.environ)
    env["VIPER_OUTPUT_DIR"] = outdir
    env["PYTHONPATH"] = ""
    p = subprocess.run([sys.executable, str(CTL), "symbolic-identity-verify"],
                       input=json.dumps(claim), capture_output=True, text=True,
                       cwd=str(REPO), env=env, timeout=timeout)
    try:
        return {"rc": p.returncode, "result": json.loads(p.stdout)}
    except Exception:
        return {"rc": p.returncode, "raw": p.stdout[:400], "stderr": p.stderr[:400]}


def evaluate(kind, verdict_payload):
    """Return (ok, label, detail) for a judge response against claim kind."""
    if verdict_payload.get("raw") is not None:
        return False, "JUDGE_ERROR", verdict_payload.get("raw", "")[:200]
    result = verdict_payload.get("result") or {}
    if kind == "unsupported_grammar":
        err = result.get("orch_error")
        ok = bool(err) and verdict_payload.get("rc", 0) != 0
        label = "UNSUPPORTED_BY_CURRENT_CONTRACT" if ok else "UNEXPECTED_ACCEPTANCE"
        return ok, label, err or "judge accepted unsupported syntax"
    verdict = result.get("combined_verdict")
    if kind in ("mutation", "negative_control"):
        ok = verdict in REFUTATION_VERDICTS
        return ok, verdict or "NO_VERDICT", "reproducible nonzero evidence" if ok else "mutation was not refuted"
    if kind == "positive_route_boundary":
        ok = (verdict in POSITIVE_VERDICTS) and ("DISPROVED" not in verdict)
        label = "CERTIFIED" if verdict in CERTIFIED_LEVEL3 else "PENDING_SECOND_ENGINE"
        return ok, label, verdict
    if kind == "positive":
        ok = verdict in POSITIVE_VERDICTS
        label = "CERTIFIED" if verdict in CERTIFIED_LEVEL3 else ("NOT_CERTIFIED_" + (verdict or "NONE"))
        return ok, label, verdict
    return False, "UNKNOWN_KIND", kind
