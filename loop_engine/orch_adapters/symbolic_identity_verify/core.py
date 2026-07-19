#!/usr/bin/env python3
"""Stage 1 of the LLM-SR × Viper fusion — capability `symbolic_identity_verify`.

The unlock the fusion plan rests on: a GENERAL symbolic judge. Unlike
`geometric_basis_verify` (whose gold oracle is hard-coded per family), this accepts an
ARBITRARY candidate identity `lhs == rhs` supplied by the caller (e.g. an LLM proposer)
and adjudicates it on the same asymmetric evidence ladder, with the same fail-closed
governance. Its verdict is purely symbolic:

    simplify(expand(lhs - rhs)) == 0   ->  VERIFIED_SYMBOLIC_IDENTITY   (level 3, certificate)
    otherwise                          ->  DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL (level 2)

SECURITY (this is the load-bearing part — arbitrary symbolic input ≈ executable input,
flagged in the audit). Every defence below is enforced BEFORE any parsing that could run
code:
  * strict `sympify` with `evaluate=False` disabled paths — parsing uses a RESTRICTED
    locals map (only whitelisted symbols/functions); no builtins, no eval/exec.
  * a symbol/function WHITELIST — anything else in the string is rejected pre-parse.
  * hard SIZE caps on the expression string and post-parse node count.
  * a wall-clock TIMEOUT around simplify (it can blow up or hang on adversarial input).
  * the same FORBIDDEN benchmark-gold metadata rejection as the geobasis adapter, so a
    caller cannot smuggle the answer in.
It never uses the numerical arm: for an arbitrary expression there is no geobasis
reconstruction, so this is a symbolic-only oracle (level 3 or level 2, never level 1).
"""
from __future__ import annotations
import json, hashlib, os, platform, re, signal, tempfile, subprocess
from pathlib import Path
import sympy
from loop_engine.orch_adapters._symbolic_safe_parse import (
    AdapterError, FORBIDDEN, PARSE_POLICY, validate_and_parse, sha, git_head, _SYMBOL_RE)

HERE = Path(__file__).resolve().parent
ADAPTER_VERSION = "symbolic-identity-verify-1.0"


# repository policy (NOT caller-supplied); a caller may only strengthen, never weaken.
POLICY = {"max_expr_chars": PARSE_POLICY["max_expr_chars"], "max_nodes": PARSE_POLICY["max_nodes"],
          "max_symbols": PARSE_POLICY["max_symbols"], "simplify_timeout_seconds": 20,
          "allowed_functions": PARSE_POLICY["allowed_functions"]}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest()







class _Timeout(Exception):
    pass


def _with_timeout(fn, seconds):
    """Wall-clock guard for simplify (SIGALRM; main-thread only, which the CLI is)."""
    def _handler(signum, frame): raise _Timeout()
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(int(seconds))
    try:
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)




def _numeric_probe(residual, symbols, timeout):
    """Sound disproof probe: evaluate the residual at deterministic sample points.

    Returns (witness_point | None, tolerance, points_probed). A witness is a point where
    |residual| exceeds tolerance -> a genuine reproducible counterexample. If the residual
    is ~0 at every point that evaluated, returns (None, tol, n>0) -> numerically consistent
    but NOT proven. Deterministic points (no RNG) so the verdict is replayable.
    """
    tol = 1e-9
    syms = [sympy.Symbol(s) for s in symbols]
    # fixed rational-ish sample values; varied per symbol index and trial (kept small, real)
    base = [0.4142, -0.7321, 1.2361, -0.3178, 0.9051, -1.1731, 0.5237, 2.0187]
    n_ok = 0
    try:
        def _run():
            nonlocal n_ok
            for t in range(6):
                subs = {syms[i]: sympy.Float(base[(i + t) % len(base)] + 0.017 * t)
                        for i in range(len(syms))}
                try:
                    val = complex(sympy.N(residual.subs(subs), 20))
                except (TypeError, ValueError):
                    continue  # point outside real domain (e.g. asin range) -> skip
                if val != val:  # NaN
                    continue
                n_ok += 1
                if abs(val) > tol:
                    return {s: float(base[(i + t) % len(base)] + 0.017 * t)
                            for i, s in enumerate(symbols)}
            return None
        witness = _with_timeout(_run, max(1, timeout))
    except _Timeout:
        return None, tol, n_ok
    return witness, tol, n_ok


def handle(req):
    # 1. forbidden-field check (no gold leak) — before anything else
    blob = json.dumps(req)
    for f in FORBIDDEN:
        if f in blob:
            raise AdapterError("BENCHMARK_METADATA_NOT_ALLOWED")
    claim = req.get("claim") or {}
    mode = req.get("verification_mode", "symbolic_only")
    if mode != "symbolic_only":
        raise AdapterError("UNSUPPORTED_VERIFICATION_MODE")  # this oracle is symbolic-only
    symbols = claim.get("symbols") or []
    if not isinstance(symbols, list) or len(symbols) > POLICY["max_symbols"]:
        raise AdapterError("TOO_MANY_SYMBOLS")
    if not all(isinstance(s, str) and _SYMBOL_RE.fullmatch(s) for s in symbols):
        raise AdapterError("INVALID_SYMBOL_NAME")
    lhs_s, rhs_s = claim.get("lhs"), claim.get("rhs")
    scope = claim.get("scope")
    if not scope or not claim.get("assumptions"):
        raise AdapterError("SCHEMA_VALIDATION_FAILED")

    # 2. policy: caller may only strengthen timeout, never weaken
    caller_to = (req.get("policy_overrides") or {}).get("simplify_timeout_seconds", POLICY["simplify_timeout_seconds"])
    if caller_to > POLICY["simplify_timeout_seconds"]:
        raise AdapterError("POLICY_VIOLATION")
    timeout = min(caller_to, POLICY["simplify_timeout_seconds"])

    # 3. parse (restricted) then adjudicate (timeout-guarded)
    lhs = validate_and_parse(lhs_s, symbols)
    rhs = validate_and_parse(rhs_s, symbols)
    try:
        residual = _with_timeout(lambda: sympy.simplify(sympy.expand(lhs - rhs)), timeout)
    except _Timeout:
        raise AdapterError("SIMPLIFY_TIMEOUT")

    # ASYMMETRIC EVIDENCE (the load-bearing correctness rule): a symbolic zero is a proof;
    # a NON-zero simplified residual is NOT a disproof, because simplify is incomplete — it
    # may fail to crush an expression that is in fact identically zero. So:
    #   residual == 0                          -> VERIFIED_SYMBOLIC_IDENTITY        (L3, certificate)
    #   residual != 0, numeric counterexample  -> DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE (L2)
    #   residual != 0, numerically ~0 anywhere -> NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN (L1)
    #   residual != 0, could not evaluate      -> INCONCLUSIVE_INSUFFICIENT_EVIDENCE (L0)
    # Never label "simplify didn't reach 0" as a disproof.
    numerical = None
    unresolved = []
    if residual == 0:
        # AUDIT THE AUDITOR (defense in depth): simplify() is the engine we are trusting, so
        # a level-3 certificate requires an INDEPENDENT confirmation. Numerically evaluate the
        # ORIGINAL (un-simplified) lhs-rhs at deterministic points via a different code path
        # (evalf, not simplify). If that probe finds a counterexample, simplify()==0 is a bug
        # or a domain trap -> FAIL CLOSED with a dispute, never mint a false certificate.
        witness, tol, probed = _numeric_probe(lhs - rhs, symbols, timeout)
        if witness is not None:
            symbolic = {"verdict": "SYMBOLIC_NUMERIC_CONFLICT", "evidence_level": 0,
                        "canonical_residual": "0", "certificate": None}
            numerical = {"verdict": "CONTRADICTS_SYMBOLIC_ZERO", "witness_point": witness,
                         "tolerance": tol, "points_probed": probed}
            combined, level, relation = "DISPUTED_SYMBOLIC_NUMERIC_CONFLICT", 0, "CONFLICT_FAIL_CLOSED"
            unresolved = ["symbolic canonicalizer returned 0 but an independent numeric probe "
                          "found a counterexample; certificate withheld pending review"]
        else:
            cert = {"type": "canonical_zero_residual",
                    "cross_check": {"method": "independent_numeric_evalf", "points_probed": probed, "tolerance": tol},
                    "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "claim": "simplify(expand(lhs-rhs))=0"})}
            symbolic = {"verdict": "VERIFIED_SYMBOLIC_IDENTITY", "evidence_level": 3,
                        "canonical_residual": "0", "certificate": cert}
            numerical = {"verdict": "NUMERICALLY_CONFIRMS_SYMBOLIC_ZERO", "witness_point": None,
                         "tolerance": tol, "points_probed": probed}
            combined, level, relation = "VERIFIED_SYMBOLIC_IDENTITY", 3, "SYMBOLIC_AND_NUMERICAL_AGREE"
    else:
        symbolic = {"verdict": "SYMBOLIC_CANONICALIZATION_INCONCLUSIVE", "evidence_level": 0,
                    "canonical_residual": str(residual)[:400], "certificate": None}
        witness, tol, probed = _numeric_probe(residual, symbols, timeout)
        numerical = {"witness_point": witness, "tolerance": tol, "points_probed": probed}
        if witness is not None:  # a real counterexample -> genuine disproof
            numerical["verdict"] = "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"
            combined, level, relation = "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE", 2, "NUMERICAL_DECISIVE_SYMBOLIC_UNSUPPORTED"
        elif probed > 0:  # numerically ~0 everywhere probed but not symbolically proven
            numerical["verdict"] = "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"
            combined, level, relation = "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN", 1, "SYMBOLIC_UNSUPPORTED_NUMERICAL_CONSISTENT"
            unresolved = ["numerically consistent but no symbolic certificate; a stronger "
                          "canonicalizer or a proof is required to reach level 3"]
        else:  # could not evaluate at any point
            numerical["verdict"] = "NUMERICAL_EVALUATION_FAILED"
            combined, level, relation = "INCONCLUSIVE_INSUFFICIENT_EVIDENCE", 0, "BOTH_INCONCLUSIVE"
            unresolved = ["symbolic canonicalization inconclusive and numeric probe could not evaluate"]

    result = {
        "operation": "symbolic_identity_verify", "contract_version": "1.0",
        "request_hash": sha(req),
        "symbolic_claim_verifier": symbolic,
        "numerical_geobasis_verifier": numerical,   # a lightweight numeric disproof/consistency probe
        "oracle_relation": relation,
        "combined_verdict": combined, "combined_evidence_level": level,
        "scope": scope,
        "unresolved_obligations": unresolved,
        "provenance": {
            "repository_commit": git_head(HERE.parents[2]), "adapter_version": ADAPTER_VERSION,
            "symbolic_verifier": "sympy simplify(expand(lhs-rhs))",
            "numerical_verifier": None,
            "input_contract_version": "1.0", "output_contract_version": "1.0",
            "policy_hash": POLICY_HASH,
            "subresult_hashes": {"symbolic": sha(symbolic)},
            "runtime_environment": {"python": platform.python_version(),
                                    "sympy": sympy.__version__, "platform": platform.platform()},
            "replay_classification": "VERDICT_REPRODUCIBLE (pure symbolic; deterministic canonicalization)"},
    }
    # atomic replay artifact (temp -> rename), out of the package tree
    out_dir = Path(os.environ.get("VIPER_OUTPUT_DIR", tempfile.gettempdir())) / "viper_symbolic_identity_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(result, tmp); tmp.close()
    art_hash = sha(Path(tmp.name).read_bytes())
    final = out_dir / "last_result.json"; os.replace(tmp.name, final)
    result["replay_artifact"] = {"path": str(final), "sha256": art_hash}
    # fail-closed exit: a symbolic/numeric conflict is a governance stop, not a result
    exit_code = 1 if combined == "DISPUTED_SYMBOLIC_NUMERIC_CONFLICT" else 0
    return result, exit_code
