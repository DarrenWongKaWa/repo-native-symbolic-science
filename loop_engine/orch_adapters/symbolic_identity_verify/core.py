#!/usr/bin/env python3
"""Stage 1 of the LLM-SR × Viper fusion — capability `symbolic_identity_verify`.

The unlock the fusion plan rests on: a GENERAL symbolic judge. Unlike
`geometric_basis_verify` (whose gold oracle is hard-coded per family), this accepts an
ARBITRARY candidate identity `lhs == rhs` supplied by the caller (e.g. an LLM proposer)
and adjudicates it on the same asymmetric evidence ladder, with the same fail-closed
governance:

    any canonicalizer proves lhs-rhs == 0   -> VERIFIED_SYMBOLIC_IDENTITY (L3, certificate)
    none does, numeric counterexample       -> DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE (L2)
    none does, numerically ~0 everywhere    -> NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN (L1)
    none does, cannot evaluate              -> INCONCLUSIVE_INSUFFICIENT_EVIDENCE (L0)

A non-zero canonical form is NEVER a disproof (these procedures are incomplete). Three
audit-the-auditor safeguards back the level-3 certificate: an independent numeric
cross-check (a conflict fails closed), a re-checkable polynomial certificate where
applicable (see recheck.py), and differential agreement across independent canonicalizers.

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
The geobasis numerical arm is not used (no reconstruction exists for an arbitrary
expression); the numeric field carries the lightweight disproof/consistency probe instead.
"""
from __future__ import annotations
import json, hashlib, os, platform, re, signal, tempfile, subprocess
from pathlib import Path
import sympy
from loop_engine.orch_adapters._symbolic_safe_parse import (
    AdapterError, FORBIDDEN, PARSE_POLICY, validate_and_parse, sha, git_head, _SYMBOL_RE,
    syms_like)
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as _recheck
from loop_engine.orch_adapters.symbolic_identity_verify import domain_guard as _domain

HERE = Path(__file__).resolve().parent
ADAPTER_VERSION = "symbolic-identity-verify-1.0"


# repository policy (NOT caller-supplied); a caller may only strengthen, never weaken.
POLICY = {"max_expr_chars": PARSE_POLICY["max_expr_chars"], "max_nodes": PARSE_POLICY["max_nodes"],
          "max_symbols": PARSE_POLICY["max_symbols"], "simplify_timeout_seconds": 20,
          "allowed_functions": PARSE_POLICY["allowed_functions"]}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest()







class _Timeout(Exception):
    pass


class _SecondEngineConflict(Exception):
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
    syms = syms_like(residual, symbols)
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


# AUDIT-THE-AUDITOR #4 — differential testing across INDEPENDENT canonicalizers.
# Never trust one simplification heuristic. Each route is a different algorithm; a route
# reaching 0 is a proof (modulo that route), and the number of independent routes that
# agree is a robustness signal. A claim proved by exactly ONE route is flagged fragile.
# This also RAISES RECALL: e.g. tanh(x) == (exp(2x)-1)/(exp(2x)+1) is proved only by the
# rewrite-to-exp route, so it now certifies instead of sitting at level 1.
_CANONICALIZERS = [
    ("simplify_expand", lambda d: sympy.simplify(sympy.expand(d))),
    ("factor",          lambda d: sympy.factor(d)),
    ("cancel_together", lambda d: sympy.cancel(sympy.together(d))),
    ("trigsimp",        lambda d: sympy.trigsimp(d)),
    ("rewrite_exp",     lambda d: sympy.simplify(d.rewrite(sympy.exp))),
]


def _differential_canonicalize(diff, timeout):
    """Run every canonicalizer under its own timeout. Returns (votes, display_residual).

    votes[name] is True (reached 0), False (did not), or None (timeout/error = inconclusive).
    A False is NOT evidence of non-identity — these procedures are incomplete.
    """
    per = max(2, int(timeout) // max(1, len(_CANONICALIZERS)))
    votes, display = {}, None
    for name, fn in _CANONICALIZERS:
        try:
            r = _with_timeout(lambda f=fn: f(diff), per)
            votes[name] = bool(r == 0)
            if name == "simplify_expand":
                display = r
        except (_Timeout, Exception):
            votes[name] = None
    return votes, display



# AUDIT-THE-AUDITOR / tier T3 — derivative + base point.
# For analytic f, g on a CONNECTED domain: if f' == g' everywhere on it and f(a) == g(a) at
# one point a in it, then f == g on it. This proves the class no canonicalizer can crush
# directly, e.g. atan(x) == asin(x/sqrt(1+x^2)): the derivative collapses to 0 and both
# sides agree at x = 0. The domain is REQUIRED and recorded — the conclusion is only valid
# on a connected domain where both sides are differentiable.
def _derivative_base_point_certificate(lhs, rhs, symbols, domain, timeout):
    if len(symbols) != 1:
        return None                      # single-variable form only
    x = syms_like(lhs - rhs, symbols)[0]
    try:
        d = _with_timeout(lambda: sympy.diff(lhs - rhs, x), max(2, timeout // 3))
    except (_Timeout, Exception):
        return None
    dvotes, _ = _differential_canonicalize(d, max(3, timeout // 2))
    proved_by = sorted([k for k, v in dvotes.items() if v is True])
    if not proved_by:
        return None                      # derivative not shown to vanish -> no T3 proof
    # exact agreement at a base point inside the domain
    for a in (0, 1, -1, sympy.Rational(1, 2)):
        try:
            val = _with_timeout(lambda aa=a: sympy.simplify((lhs - rhs).subs(x, aa)), max(2, timeout // 4))
        except (_Timeout, Exception):
            continue
        if val == 0:
            return {"kind": "derivative_base_point",
                    "domain": domain,
                    "base_point": {symbols[0]: str(a)},
                    "base_point_residual": "0",
                    "derivative_expression": str(d)[:300],
                    "derivative_proved_zero_by": proved_by,
                    "soundness": "on a CONNECTED domain where both sides are differentiable, "
                                 "f'==g' together with f(a)==g(a) at one interior point implies f==g",
                    "independently_recheckable": False,
                    "recheck_note": "the base-point check is exact; the derivative step rests on "
                                    f"{len(proved_by)} independent canonicalizer route(s), not on a "
                                    "simplify-free certificate — so this is a proof STRUCTURE, not a "
                                    "fully re-checkable certificate",
                    "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "d": str(d)})}
    return None


# AUDIT-THE-AUDITOR #5 — a SECOND, INDEPENDENT engine.
# Every other safeguard still runs inside sympy, so a bug shared across sympy's routines is
# invisible to all of them. This calls a separate engine in a separate process (config-driven,
# no hardcoded path). A rigorous NONZERO from it while we certified ZERO is a governance stop.
def _second_opinion(lhs_s, rhs_s, symbols, timeout):
    cmd = os.environ.get("VIPER_SECOND_CAS_CMD")
    if not cmd:
        return {"status": "not_configured",
                "note": "no independent second engine configured (VIPER_SECOND_CAS_CMD); "
                        "all remaining safeguards share the sympy implementation"}
    import shlex
    try:
        p = subprocess.run(shlex.split(cmd),
                           input=json.dumps({"lhs": lhs_s, "rhs": rhs_s, "symbols": symbols}),
                           capture_output=True, text=True, timeout=max(5, timeout))
        return {"status": "ok", **json.loads(p.stdout)}
    except Exception as exc:
        return {"status": "unavailable", "note": f"second engine failed: {type(exc).__name__}"}


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
    # T3 needs an explicit CONNECTED domain; default to the reals and record it
    domain = claim.get("domain") or "connected: all real x"
    if not scope or not claim.get("assumptions"):
        raise AdapterError("SCHEMA_VALIDATION_FAILED")

    # 2. policy: caller may only strengthen timeout, never weaken
    caller_to = (req.get("policy_overrides") or {}).get("simplify_timeout_seconds", POLICY["simplify_timeout_seconds"])
    if caller_to > POLICY["simplify_timeout_seconds"]:
        raise AdapterError("POLICY_VIOLATION")
    timeout = min(caller_to, POLICY["simplify_timeout_seconds"])

    # 3. parse (restricted) then adjudicate (timeout-guarded)
    _is_real = ("real" in str(scope).lower()) or ("real" in str(domain).lower())
    lhs = validate_and_parse(lhs_s, symbols, real=_is_real)
    rhs = validate_and_parse(rhs_s, symbols, real=_is_real)
    # #4: adjudicate with SEVERAL independent canonicalizers, not one.
    votes, residual = _differential_canonicalize(lhs - rhs, timeout)
    zero_by = sorted([k for k, v in votes.items() if v is True])
    conclusive = sum(1 for v in votes.values() if v is not None)
    differential = {"votes": votes, "proved_zero_by": zero_by,
                    "agreement": f"{len(zero_by)}/{conclusive} conclusive routes",
                    "fragile_single_route": len(zero_by) == 1}
    symbolic_zero = len(zero_by) > 0
    if residual is None:
        residual = sympy.Integer(0) if symbolic_zero else (lhs - rhs)

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
    _conflict = None
    if symbolic_zero:
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
            # AUDIT-THE-AUDITOR #3: for a POLYNOMIAL identity, build a certificate a third
            # party can re-verify by exact pointwise evaluation, trusting no simplify at all.
            # Try each re-checkable form in turn: plain polynomial, then T1 (trig -> ideal
            # cofactor), then T2 (exp -> rational numerator). First that succeeds wins.
            poly_cert = None
            for _builder in (_recheck.build_polynomial_certificate,
                             _recheck.build_trig_cofactor_certificate,
                             _recheck.build_exp_polynomial_certificate):
                try:
                    poly_cert = _with_timeout(lambda b=_builder: b(lhs, rhs, symbols), timeout)
                except (_Timeout, Exception):
                    poly_cert = None
                if poly_cert:
                    break
            cert = {"type": "canonical_zero_residual",
                    "cross_check": {"method": "independent_numeric_evalf", "points_probed": probed, "tolerance": tol},
                    "differential_canonicalization": differential,
                    "independently_recheckable": poly_cert is not None,
                    "recheckable_certificate": poly_cert,   # None for transcendental / oversized
                    "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "claim": "simplify(expand(lhs-rhs))=0"})}
            # GATE 5 FIX — domain guard. Expressions can be equal as algebraic objects while
            # the claim (equality of FUNCTIONS on the declared domain) is false where they are
            # undefined: (x^2-1)/(x-1)==x+1 at x=1, x/x==1 at x=0, sqrt(x)*sqrt(x)==x for x<0.
            # If a definedness obligation can fail on the declared domain, we must NOT issue an
            # unconditional identity certificate.
            try:
                side_conditions, excluded = _with_timeout(
                    lambda: _domain.analyse(lhs, rhs, symbols, scope, lhs_s, rhs_s), timeout)
            except (_Timeout, Exception):
                side_conditions, excluded = [], None
            cert["side_conditions"] = side_conditions
            # #5: independent second engine. A rigorous NONZERO here contradicts our ZERO.
            second = _second_opinion(lhs_s, rhs_s, symbols, timeout)
            cert["second_engine"] = second
            if second.get("verdict") == "NONZERO":
                symbolic = {"verdict": "SECOND_ENGINE_CONTRADICTS_CERTIFICATE",
                            "evidence_level": 0, "canonical_residual": "0", "certificate": None}
                numerical = {"verdict": "SECOND_ENGINE_NONZERO", "witness_point": None,
                             "tolerance": tol, "points_probed": probed, "second_engine": second}
                combined, level, relation = ("DISPUTED_SECOND_ENGINE_CONFLICT", 0,
                                             "CONFLICT_FAIL_CLOSED")
                unresolved = ["an independent second engine rigorously reports a non-zero "
                              "difference while our canonicalizers reported zero; certificate "
                              "withheld pending review"]
                _conflict = (symbolic, numerical, combined, level, relation, unresolved)
            verdict_name = ("VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS" if side_conditions
                            else "VERIFIED_SYMBOLIC_IDENTITY")
            symbolic = {"verdict": verdict_name, "evidence_level": 3,
                        "canonical_residual": "0", "certificate": cert}
            numerical = {"verdict": "NUMERICALLY_CONFIRMS_SYMBOLIC_ZERO", "witness_point": None,
                         "tolerance": tol, "points_probed": probed}
            relation = ("SYMBOLIC_NUMERICAL_AGREE_POLYNOMIAL_RECHECKABLE" if poly_cert
                        else "SYMBOLIC_AND_NUMERICAL_AGREE")
            combined, level = verdict_name, 3
            if side_conditions:
                unresolved = [excluded] + [f"side condition: {c}" for c in side_conditions]
    else:
        symbolic = {"verdict": "SYMBOLIC_CANONICALIZATION_INCONCLUSIVE", "evidence_level": 0,
                    "canonical_residual": str(residual)[:400], "certificate": None,
                    "differential_canonicalization": differential}
        witness, tol, probed = _numeric_probe(residual, symbols, timeout)
        numerical = {"witness_point": witness, "tolerance": tol, "points_probed": probed}
        if witness is not None:  # a real counterexample -> genuine disproof
            numerical["verdict"] = "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"
            combined, level, relation = "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE", 2, "NUMERICAL_DECISIVE_SYMBOLIC_UNSUPPORTED"
        elif probed > 0:  # numerically ~0 everywhere probed but not symbolically proven
            numerical["verdict"] = "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"
            # tier T3: try derivative + base point before settling for level 1
            try:
                t3_cert = _derivative_base_point_certificate(lhs, rhs, symbols, domain, timeout)
            except Exception:
                t3_cert = None
            if t3_cert:
                sc, excl = [], None
                try:
                    sc, excl = _with_timeout(
                        lambda: _domain.analyse(lhs, rhs, symbols, scope, lhs_s, rhs_s), timeout)
                except (_Timeout, Exception):
                    pass
                t3_cert["side_conditions"] = sc
                vname = ("VERIFIED_BY_DERIVATIVE_AND_BASE_POINT_WITH_SIDE_CONDITIONS" if sc
                         else "VERIFIED_BY_DERIVATIVE_AND_BASE_POINT")
                symbolic = {"verdict": vname, "evidence_level": 3,
                            "canonical_residual": str(residual)[:400], "certificate": t3_cert,
                            "differential_canonicalization": differential}
                combined, level, relation = vname, 3, "DERIVATIVE_AND_BASE_POINT_DECISIVE"
                unresolved = ([excl] if excl else []) + [f"side condition: {c}" for c in sc]
                unresolved += [f"valid on the declared connected domain: {domain}"]
            else:
                combined, level, relation = "NUMERICALLY_CONSISTENT_SYMBOLIC_UNPROVEN", 1, "SYMBOLIC_UNSUPPORTED_NUMERICAL_CONSISTENT"
                unresolved = ["numerically consistent but no symbolic certificate; a stronger "
                              "canonicalizer or a proof is required to reach level 3"]
        else:  # could not evaluate at any point
            numerical["verdict"] = "NUMERICAL_EVALUATION_FAILED"
            combined, level, relation = "INCONCLUSIVE_INSUFFICIENT_EVIDENCE", 0, "BOTH_INCONCLUSIVE"
            unresolved = ["symbolic canonicalization inconclusive and numeric probe could not evaluate"]

    if _conflict is not None:
        symbolic, numerical, combined, level, relation, unresolved = _conflict

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
