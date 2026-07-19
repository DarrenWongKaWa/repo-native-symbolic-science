#!/usr/bin/env python3
"""Stage 2 of the LLM-SR × Viper fusion — capability `propose_equation_candidates`.

The proposer organ, folded behind the ORCH boundary. It turns a problem context into a
list of candidate identity claims (lhs == rhs). It is a PURE GENERATOR:

  * it NEVER executes model-written code (this is the whole point — it removes LLM-SR's
    unsafe program-execution surface; a proposal is DATA, an expression pair, not a program);
  * it NEVER scores a candidate (no oracle here) — scoring is the held-out judge's job
    (`symbolic_identity_verify`), a separate capability the proposer cannot reach;
  * every candidate it emits is tagged UNVERIFIED / evidence_level 0. It cannot promote,
    certify, or self-verify anything.

Security posture vs LLM-SR:
  * the LLM backend is invoked as a SUBPROCESS receiving a prompt on stdin and returning
    text on stdout — its output is treated strictly as DATA and parsed, never exec'd;
  * the backend command is config-driven (`VIPER_PROPOSER_CMD`), never a hardcoded machine
    path; unset -> fail-closed PROPOSER_BACKEND_NOT_CONFIGURED;
  * every proposed lhs/rhs is run through the SAME strict whitelist/size validator the judge
    uses (single-sourced from symbolic_identity_verify.core), so the proposer cannot emit
    anything unsafe or anything the judge would reject as malformed — malformed candidates
    are DROPPED (and the dropped count reported, never silently truncated).
"""
from __future__ import annotations
import json, hashlib, os, platform, re, shlex, subprocess, tempfile
from pathlib import Path

# single-source the strict parser + error type from the Stage-1 judge
from loop_engine.orch_adapters.symbolic_identity_verify import core as _judge

HERE = Path(__file__).resolve().parent
ADAPTER_VERSION = "propose-equation-candidates-1.0"
FORBIDDEN = _judge.FORBIDDEN                      # same gold-metadata rejection
AdapterError = _judge.AdapterError

POLICY = {"max_candidates": 16, "max_symbols": 40, "backend_timeout_seconds": 180,
          "allowed_functions": _judge.POLICY["allowed_functions"]}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY, sort_keys=True, default=str).encode()).hexdigest()
_SYMBOL_RE = _judge._SYMBOL_RE


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else json.dumps(b, sort_keys=True).encode()).hexdigest()


def _build_prompt(problem: dict) -> str:
    syms = " ".join(problem["symbols"])
    funcs = " ".join(POLICY["allowed_functions"])
    n = problem["n_candidates"]
    return (
        "You are the PROPOSER in a governed equation-discovery loop. You do NOT get to check "
        "your own answers — an independent symbolic judge adjudicates every proposal.\n\n"
        f"Problem: {problem['description']}\n"
        f"Variables allowed: {syms}\n"
        f"Functions allowed: {funcs}. Operators + - * / ** ( ). Integer coefficients only.\n\n"
        f"Propose {n} candidate identities (lhs == rhs) you believe hold. Return ONLY a JSON "
        'array, no prose, no code fences: '
        '[{"lhs":"...","rhs":"...","note":"one short line"}, ...]'
    )


def _call_backend(prompt: str) -> str:
    """Run the configured proposer backend as a subprocess (prompt on stdin -> text out).

    Config-driven, no hardcoded path. The backend's output is DATA and is never executed.
    """
    cmd = os.environ.get("VIPER_PROPOSER_CMD")
    if not cmd:
        raise AdapterError("PROPOSER_BACKEND_NOT_CONFIGURED")
    try:
        p = subprocess.run(shlex.split(cmd), input=prompt, capture_output=True, text=True,
                           timeout=POLICY["backend_timeout_seconds"])
    except subprocess.TimeoutExpired:
        raise AdapterError("PROPOSER_BACKEND_TIMEOUT")
    except Exception:
        raise AdapterError("PROPOSER_BACKEND_FAILED")
    return p.stdout


def _parse_candidates(raw: str):
    """Extract a JSON array of {lhs,rhs,note} from backend output (treated as data)."""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    return arr if isinstance(arr, list) else []


def handle(req, backend=None):
    # 1. forbidden gold metadata — before anything
    blob = json.dumps(req)
    for f in FORBIDDEN:
        if f in blob:
            raise AdapterError("BENCHMARK_METADATA_NOT_ALLOWED")
    problem = req.get("problem") or {}
    symbols = problem.get("symbols") or []
    if not isinstance(symbols, list) or not symbols or len(symbols) > POLICY["max_symbols"]:
        raise AdapterError("SCHEMA_VALIDATION_FAILED")
    if not all(isinstance(s, str) and _SYMBOL_RE.fullmatch(s) for s in symbols):
        raise AdapterError("INVALID_SYMBOL_NAME")
    if not problem.get("description"):
        raise AdapterError("SCHEMA_VALIDATION_FAILED")
    n = int(problem.get("n_candidates", req.get("n_candidates", 4)))
    if n < 1 or n > POLICY["max_candidates"]:
        raise AdapterError("CANDIDATE_COUNT_OUT_OF_RANGE")
    problem = {"description": problem["description"], "symbols": symbols, "n_candidates": n}

    # 2. call the backend (subprocess or injected) — output is DATA, never exec'd
    raw = (backend or _call_backend)(_build_prompt(problem))
    proposed = _parse_candidates(raw)

    # 3. validate every candidate with the JUDGE's strict parser; DROP the bad ones
    accepted, dropped = [], 0
    for c in proposed[:n]:
        if not isinstance(c, dict):
            dropped += 1; continue
        lhs, rhs = c.get("lhs"), c.get("rhs")
        try:
            _judge._validate_and_parse(lhs, symbols)
            _judge._validate_and_parse(rhs, symbols)
        except AdapterError:
            dropped += 1; continue
        accepted.append({
            "lhs": lhs, "rhs": rhs, "note": str(c.get("note", ""))[:200],
            # a proposal carries NO verdict — it is UNVERIFIED until the judge speaks
            "status": "UNVERIFIED", "evidence_level": 0,
            "route_to": "symbolic_identity_verify"})

    result = {
        "operation": "propose_equation_candidates", "contract_version": "1.0",
        "request_hash": sha(req),
        "problem_scope": {"symbols": symbols, "description": problem["description"][:200]},
        "candidates": accepted,
        "n_requested": n, "n_accepted": len(accepted), "n_dropped_invalid": dropped,
        "authority_note": "proposer emits UNVERIFIED claims only; it cannot score, certify, "
                          "or self-verify; adjudication is the held-out symbolic judge's job",
        "provenance": {
            "repository_commit": _judge._git(), "adapter_version": ADAPTER_VERSION,
            "backend": "config-driven subprocess (VIPER_PROPOSER_CMD); output treated as data, never executed",
            "executes_model_code": False, "scores_candidates": False,
            "policy_hash": POLICY_HASH,
            "runtime_environment": {"python": platform.python_version(), "platform": platform.platform()}},
    }
    # atomic replay artifact, out of the package tree
    out_dir = Path(os.environ.get("VIPER_OUTPUT_DIR", tempfile.gettempdir())) / "viper_proposer_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(result, tmp); tmp.close()
    result["replay_artifact"] = {"path": str(out_dir / "last_result.json"),
                                 "sha256": sha(Path(tmp.name).read_bytes())}
    os.replace(tmp.name, out_dir / "last_result.json")
    return result, 0
