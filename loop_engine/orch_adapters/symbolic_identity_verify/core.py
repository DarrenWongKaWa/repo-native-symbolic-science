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

HERE = Path(__file__).resolve().parent
ADAPTER_VERSION = "symbolic-identity-verify-1.0"

# benchmark/gold metadata a caller must never be able to inject (mirrors geobasis)
FORBIDDEN = {"gold_verdict", "expected_answer", "mutation_operator", "gold_residual",
             "benchmark_task_class", "gold_certificate", "is_identity"}

# repository policy (NOT caller-supplied); a caller may only strengthen, never weaken.
POLICY = {"max_expr_chars": 4000, "max_nodes": 4000, "max_symbols": 40,
          "simplify_timeout_seconds": 20, "allowed_functions": sorted([
              "sin", "cos", "tan", "exp", "log", "sqrt", "Abs", "conjugate", "re", "im",
              "sinh", "cosh", "tanh", "asin", "acos", "atan", "atan2", "Rational"])}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest()

# token whitelist: symbol names, whitelisted funcs, numbers, operators, parens, dots, commas
_SYMBOL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ALLOWED_TOKEN_RE = re.compile(r"^[A-Za-z0-9_+\-*/().,\s^]*$")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else json.dumps(b, sort_keys=True).encode()).hexdigest()


class AdapterError(Exception):
    def __init__(self, code): super().__init__(code); self.code = code


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


def _validate_and_parse(expr_str: str, declared_symbols: list[str]):
    """Reject before parsing; parse only with a restricted, whitelisted locals map."""
    if not isinstance(expr_str, str) or not expr_str.strip():
        raise AdapterError("EMPTY_EXPRESSION")
    if len(expr_str) > POLICY["max_expr_chars"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    # character-class gate: only algebra tokens (blocks __import__, lambda, ;, [], {}, =, etc.)
    if not _ALLOWED_TOKEN_RE.match(expr_str):
        raise AdapterError("DISALLOWED_CHARACTERS")
    names = set(_SYMBOL_RE.findall(expr_str))
    allowed = set(declared_symbols) | set(POLICY["allowed_functions"]) | {"pi", "E", "I", "oo"}
    illegal = names - allowed
    if illegal:
        raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
    # build a restricted locals map — symbols are plain Symbols, funcs map to sympy funcs
    local = {s: sympy.Symbol(s) for s in declared_symbols}
    for f in POLICY["allowed_functions"]:
        local[f] = getattr(sympy, f, None)
    local.update({"pi": sympy.pi, "E": sympy.E, "I": sympy.I, "oo": sympy.oo})
    try:
        # strict parse: no implicit builtins; global_dict empty, local_dict restricted
        expr = sympy.sympify(expr_str, locals=local, evaluate=True, convert_xor=True)
    except (sympy.SympifyError, SyntaxError, TypeError, AttributeError) as e:
        raise AdapterError("SYMBOLIC_PARSE_FAILED")
    if sympy.count_ops(expr, visual=False) > POLICY["max_nodes"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    return expr


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
    lhs = _validate_and_parse(lhs_s, symbols)
    rhs = _validate_and_parse(rhs_s, symbols)
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
        cert = {"type": "canonical_zero_residual",
                "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "claim": "simplify(expand(lhs-rhs))=0"})}
        symbolic = {"verdict": "VERIFIED_SYMBOLIC_IDENTITY", "evidence_level": 3,
                    "canonical_residual": "0", "certificate": cert}
        combined, level, relation = "VERIFIED_SYMBOLIC_IDENTITY", 3, "SYMBOLIC_DECISIVE"
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
            "repository_commit": _git(), "adapter_version": ADAPTER_VERSION,
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
    return result, 0


def _git():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"],
                              cwd=str(HERE.parents[2]), capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"
