#!/usr/bin/env python3
"""C0 — Minimal Certified Compactification Loop (Stage 1) — core capability.

Pure Python / SymPy. No Wolfram. No ranking, no e-graph, no termination search.

Composition of one loop step:

    certified C_i  +  candidate C~_{i+1}
        -> machine-constructed residual R_i := (lhs_{i+1} - rhs_{i+1}) == (lhs_i - rhs_i)
        -> independent Python verifier (exact SymPy, fail-closed)
        -> ZERO    : C_{i+1} certified, chain node appended
        -> NONZERO : diagnostic feedback (exact counterexample evidence)
        -> UNKNOWN : fail-closed, candidate stays UNVERIFIED

Soundness: for certified parent C_i (lhs_i - rhs_i = 0), R_i == 0 implies
lhs_{i+1} - rhs_{i+1} = 0, so R_i == 0 certifies C_{i+1} given C_i.  The
certificate of C_{i+1} is the pair (certificate of C_i, certificate of R_i).

All input expressions are parsed with the shared strict whitelist
(_symbolic_safe_parse): no eval/exec, whitelisted functions only, declared
symbols only, size-capped.
"""
from __future__ import annotations

import hashlib
import json
import platform
import time
from itertools import product
from pathlib import Path
from typing import Any

import sympy

# single-source the whitelist / token discipline from the NEUTRAL shared module
from loop_engine.orch_adapters import _symbolic_safe_parse as _safe

HERE = Path(__file__).resolve().parent
ADAPTER_VERSION = "compactification-loop-1.0"
SEEDS_DIR = HERE / "seeds"
SCHEMAS_DIR = HERE / "schemas"

VERDICT_ZERO = "ZERO"          # exact symbolic identity
VERDICT_NONZERO = "NONZERO"    # refuted by an exact counterexample
VERDICT_UNKNOWN = "UNKNOWN"    # fail-closed: simplification undecided, no counterexample found

NODE_CERTIFIED = "CERTIFIED"
NODE_DIAGNOSTIC = "DIAGNOSTIC"
NODE_UNVERIFIED = "UNVERIFIED"

# exact probe lattice for the NONZERO branch (rational reals; +/-i for complex symbols)
_REAL_PROBES = (-2, -1, -sympy.Rational(1, 2), sympy.Rational(1, 2), 1, 2)
_COMPLEX_PROBES = (1, -1, sympy.I, -sympy.I, 1 + sympy.I, 1 - sympy.I)
_MAX_PROBES = 128
_SIMPLIFY_OPS_CAP = 4000  # expressions are whitelist-capped anyway; safety net


class AdapterError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha256(data) -> str:
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------- #
# claim parsing (strict whitelist, per-symbol assumptions)
# --------------------------------------------------------------------------- #

def _normalize_symbols(symbols: Any) -> list[dict]:
    """Accept ["x", "y"] or [{"name": "x", "real": true, "nonzero": false}, ...]."""
    out = []
    for entry in symbols or []:
        if isinstance(entry, str):
            out.append({"name": entry, "real": True, "nonzero": False})
        elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
            out.append({
                "name": entry["name"],
                "real": bool(entry.get("real", True)),
                "nonzero": bool(entry.get("nonzero", False)),
            })
        else:
            raise AdapterError("CLAIM_SYMBOLS_MALFORMED")
    names = [s["name"] for s in out]
    if not names or len(names) != len(set(names)):
        raise AdapterError("CLAIM_SYMBOLS_MALFORMED")
    reserved = set(_safe.PARSE_POLICY["allowed_functions"]) | {"pi", "E", "I", "oo"}
    if reserved & set(names):
        raise AdapterError("SYMBOL_NAME_RESERVED")
    if len(names) > _safe.PARSE_POLICY["max_symbols"]:
        raise AdapterError("CLAIM_SYMBOLS_TOO_MANY")
    return out


def _symbol_locals(symbols: list[dict]) -> dict:
    local: dict = {}
    for s in symbols:
        kwargs: dict = {"real": s["real"]}
        if s.get("nonzero"):
            kwargs["nonzero"] = True
        local[s["name"]] = sympy.Symbol(s["name"], **kwargs)
    for f in _safe.PARSE_POLICY["allowed_functions"]:
        local[f] = getattr(sympy, f, None)
    local.update({"pi": sympy.pi, "E": sympy.E, "I": sympy.I, "oo": sympy.oo})
    return local


def parse_side(expr_str: str, symbols: list[dict]) -> sympy.Expr:
    """Whitelist-parse one claim side honouring declared per-symbol assumptions."""
    symbols = _normalize_symbols(symbols)  # reserved-name / shape checks
    if not isinstance(expr_str, str) or not expr_str.strip():
        raise AdapterError("EMPTY_EXPRESSION")
    if len(expr_str) > _safe.PARSE_POLICY["max_expr_chars"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    if not _safe._ALLOWED_TOKEN_RE.match(expr_str):
        raise AdapterError("DISALLOWED_CHARACTERS")
    names = set(_safe._SYMBOL_RE.findall(expr_str))
    declared = {s["name"] for s in symbols}
    allowed = declared | set(_safe.PARSE_POLICY["allowed_functions"]) | {"pi", "E", "I", "oo"}
    if names - allowed:
        raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
    try:
        expr = sympy.sympify(expr_str, locals=_symbol_locals(symbols),
                             evaluate=True, convert_xor=True)
    except (sympy.SympifyError, SyntaxError, TypeError, AttributeError):
        raise AdapterError("SYMBOLIC_PARSE_FAILED") from None
    if sympy.count_ops(expr, visual=False) > _safe.PARSE_POLICY["max_nodes"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    return expr


def parse_claim(claim: dict) -> tuple[sympy.Expr, sympy.Expr, list[dict]]:
    """Parse a claim {lhs, rhs, symbols} -> (lhs_sym, rhs_sym, symbols)."""
    if not isinstance(claim, dict):
        raise AdapterError("CLAIM_NOT_OBJECT")
    symbols = _normalize_symbols(claim.get("symbols"))
    lhs = parse_side(claim.get("lhs", ""), symbols)
    rhs = parse_side(claim.get("rhs", ""), symbols)
    return lhs, rhs, symbols


# --------------------------------------------------------------------------- #
# independent Python verifier (exact, fail-closed)
# --------------------------------------------------------------------------- #

def _exact_probe_sets(symbols: list[dict]) -> list[list]:
    """Per-symbol exact probe value sets (rational reals; +/-i for complex symbols)."""
    sets = []
    for s in symbols:
        if s["real"]:
            sets.append(list(_REAL_PROBES))
        else:
            sets.append(list(_COMPLEX_PROBES))
    return sets


def python_verify(claim: dict, max_probes: int = _MAX_PROBES) -> dict:
    """Adjudicate one identity claim exactly in Python/SymPy.

    Returns a record with verdict ZERO | NONZERO | UNKNOWN, exact evidence, and
    provenance.  Fail-closed: only an exact symbolic zero yields ZERO; only an
    exact counterexample yields NONZERO; anything undecided is UNKNOWN.
    """
    t0 = time.time()
    lhs, rhs, symbols = parse_claim(claim)
    diff = sympy.expand(lhs - rhs)
    ops_before = sympy.count_ops(diff, visual=False)
    simp = sympy.simplify(diff)
    if sympy.count_ops(simp, visual=False) > _SIMPLIFY_OPS_CAP:
        simp = diff  # pathological growth safety net: adjudicate the expanded form
    ops_after = sympy.count_ops(simp, visual=False)

    record: dict = {
        "verdict": None,
        "diff_expanded_ops": ops_before,
        "diff_simplified_ops": ops_after,
        "simplified_difference": str(simp),
        "evidence": [],
        "seconds": round(time.time() - t0, 4),
        "verifier": "python_sympy_exact_v1",
    }

    if simp == 0:
        record["verdict"] = VERDICT_ZERO
        record["evidence"].append({"kind": "exact_symbolic_zero",
                                   "simplified_difference": "0"})
        return record

    # re/im/conjugate normalization: sympy.simplify does not canonicalize
    # re(z)/im(z)/Abs(z) compositions on its own; expand(complex=True) rewrites
    # them into re/im parts of atoms, after which many conjugate/re identities
    # simplify exactly to zero (e.g. 2*re(va*conjugate(vb)) == va*conjugate(vb)
    # + conjugate(va)*vb).  Bounded: capped by the whitelist size policy.
    try:
        complex_normalized = sympy.expand_complex(simp)
        if sympy.count_ops(complex_normalized, visual=False) <= _SIMPLIFY_OPS_CAP:
            simp2 = sympy.simplify(complex_normalized)
            if simp2 == 0:
                record["verdict"] = VERDICT_ZERO
                record["complex_normalized"] = True
                record["evidence"].append(
                    {"kind": "exact_symbolic_zero_after_complex_normalization",
                     "normalized_difference": str(complex_normalized)})
                return record
    except Exception:
        pass

    # NONZERO branch: exact rational (+ i) counterexample probes.
    probe_sets = _exact_probe_sets(symbols)
    probes: list[dict] = []
    counterexample = None
    tried = 0
    # substitution keys MUST be the expression's own symbol objects: string keys
    # create assumption-less symbols that never match Symbol('x', real=True).
    expr_symbols = {str(s): s for s in diff.free_symbols}
    for combo in product(*probe_sets):
        if tried >= max_probes:
            break
        tried += 1
        point = {expr_symbols[s["name"]]: combo[j] for j, s in enumerate(symbols)
                 if s["name"] in expr_symbols}
        try:
            value = sympy.simplify(diff.subs(point))
        except Exception:
            continue  # singular or degenerate probe: not a counterexample
        if value in (sympy.nan, sympy.oo, -sympy.oo, sympy.zoo,
                     sympy.I * sympy.oo, -sympy.I * sympy.oo):
            continue
        probes.append({"point": {str(k): str(v) for k, v in point.items()},
                       "exact_value": str(value)})
        # F-02 fix: a probe is a counterexample ONLY when sympy can PROVE the
        # exact value nonzero (value.equals(0) is False).  Nested-radical values
        # that are actually 0 but not canonicalized (equals -> True or None)
        # are skipped, never reported as counterexamples.
        if value != 0 and value.equals(0) is False:
            counterexample = {"point": {str(k): str(v) for k, v in point.items()},
                              "exact_value": str(value)}
            break

    record["probes_tried"] = tried
    record["probes_recorded"] = probes[:8]
    if counterexample is not None:
        record["verdict"] = VERDICT_NONZERO
        record["counterexample"] = counterexample
        record["evidence"].append({"kind": "exact_counterexample",
                                   **counterexample})
    else:
        record["verdict"] = VERDICT_UNKNOWN
        record["evidence"].append({"kind": "simplification_undecided_no_exact_counterexample",
                                   "probes_tried": tried})
    return record


# --------------------------------------------------------------------------- #
# machine residual construction (no LLM in this step)
# --------------------------------------------------------------------------- #

def construct_residual(parent: dict, candidate: dict) -> dict:
    """Build R_i := (lhs_{i+1} - rhs_{i+1}) == (lhs_i - rhs_i).

    Pure string composition of already-validated sub-expressions, then strict
    re-validation with the shared whitelist parser.  The candidate must use a
    subset of the parent's declared symbols and the same scope.
    """
    for tag, claim in (("parent", parent), ("candidate", candidate)):
        if not isinstance(claim, dict) or not claim.get("lhs") or not claim.get("rhs"):
            raise AdapterError(f"{tag.upper()}_CLAIM_MALFORMED")
        _normalize_symbols(claim.get("symbols"))

    parent_syms = {s["name"] for s in _normalize_symbols(parent.get("symbols"))}
    cand_syms = {s["name"] for s in _normalize_symbols(candidate.get("symbols"))}
    if not cand_syms or not cand_syms <= parent_syms:
        raise AdapterError("CANDIDATE_SYMBOLS_NOT_WITHIN_PARENT_SCOPE")
    if parent.get("scope") != candidate.get("scope"):
        raise AdapterError("SCOPE_MISMATCH_BETWEEN_PARENT_AND_CANDIDATE")

    lhs = f"({candidate['lhs']} - {candidate['rhs']})"
    rhs = f"({parent['lhs']} - {parent['rhs']})"
    symbols = [dict(s) for s in _normalize_symbols(parent.get("symbols"))]

    # strict re-validation: the composed residual must parse under the same policy
    parse_side(lhs, symbols)
    parse_side(rhs, symbols)

    residual = {
        "lhs": lhs,
        "rhs": rhs,
        "symbols": symbols,
        "scope": parent.get("scope", "declared_symbols"),
        "construction": "difference_of_differences",
        "parent_claim_id": parent.get("claim_id", "?"),
        "candidate_claim_id": candidate.get("claim_id", "?"),
        "sha256": None,
    }
    residual["sha256"] = sha256(json.dumps(
        {"lhs": residual["lhs"], "rhs": residual["rhs"],
         "symbols": residual["symbols"]}, sort_keys=True))
    return residual


# --------------------------------------------------------------------------- #
# chain records
# --------------------------------------------------------------------------- #

def claim_hash(claim: dict) -> str:
    return sha256(json.dumps(
        {"lhs": claim.get("lhs"), "rhs": claim.get("rhs"),
         "symbols": claim.get("symbols"), "scope": claim.get("scope")},
        sort_keys=True))


def build_node(parent: dict | None, candidate: dict, residual: dict,
               verdict_record: dict, chain_id: str, position: int) -> dict:
    """One chain node.  Node hash covers claim, parent edge, residual, verdict."""
    if verdict_record["verdict"] == VERDICT_ZERO:
        node_status = NODE_CERTIFIED
    elif verdict_record["verdict"] == VERDICT_NONZERO:
        node_status = NODE_DIAGNOSTIC
    else:
        node_status = NODE_UNVERIFIED

    node = {
        "chain_id": chain_id,
        "position": position,
        "claim_id": candidate.get("claim_id") or f"{chain_id}:{position}",
        "claim": {
            "lhs": candidate.get("lhs"),
            "rhs": candidate.get("rhs"),
            "symbols": candidate.get("symbols"),
            "scope": candidate.get("scope", "declared_symbols"),
        },
        "claim_sha256": claim_hash(candidate),
        "parent_claim_id": (parent or {}).get("claim_id"),
        "residual": residual,
        "residual_verdict": verdict_record["verdict"],
        "node_status": node_status,
        "evidence": verdict_record,
        "certificate": None,
        "timestamps": {"created_utc": _now_iso()},
    }
    if node_status == NODE_CERTIFIED:
        node["certificate"] = {
            "kind": "c0_python_exact_residual_chain",
            "verifier": "python_sympy_exact_v1",
            "residual_verdict": VERDICT_ZERO,
            "parent_certificate": "in_chain" if parent is not None else "seed",
            "residual_sha256": residual.get("sha256"),
            "claim_sha256": node["claim_sha256"],
        }
    node["node_sha256"] = sha256(json.dumps(
        {k: v for k, v in node.items() if k != "node_sha256"}, sort_keys=True, default=str))
    return node


# --------------------------------------------------------------------------- #
# seed loading
# --------------------------------------------------------------------------- #

def load_seed(seed_id: str) -> dict:
    """Load a certified seed claim (C_0) from the packaged seeds directory."""
    path = SEEDS_DIR / f"{seed_id}.json"
    if not path.exists():
        raise AdapterError("SEED_NOT_FOUND")
    try:
        seed = json.loads(path.read_text())
    except json.JSONDecodeError:
        raise AdapterError("SEED_MALFORMED") from None
    if seed.get("seed_id") != seed_id or seed.get("status") != "CERTIFIED":
        raise AdapterError("SEED_NOT_CERTIFIED")
    return seed


def verify_seed(seed: dict) -> dict:
    """C_0 must adjudicate ZERO with the same verifier before any loop step runs."""
    record = python_verify(seed["claim"])
    if record["verdict"] != VERDICT_ZERO:
        raise AdapterError("SEED_VERIFICATION_FAILED")
    return record


# --------------------------------------------------------------------------- #
# loop step orchestration (used by the thin ORCH adapter)
# --------------------------------------------------------------------------- #

def run_loop_step(parent_claim: dict, candidates: list[dict], chain_id: str,
                  start_position: int = 1) -> dict:
    """Run one compactification step over candidates.

    parent_claim: certified claim record (with claim_id).
    candidates:   list of UNVERIFIED candidate claims {lhs, rhs, symbols, scope}.
    Returns the chain step record (nodes + summary).
    """
    if not isinstance(parent_claim, dict) or not parent_claim.get("claim_id"):
        raise AdapterError("PARENT_CLAIM_MISSING")
    nodes = []
    summary = {"candidates": len(candidates), "certified": 0,
               "diagnostic": 0, "unverified": 0}
    seen_ids: set = set()
    for index, candidate in enumerate(candidates):
        # F-03 fix: chain edges must be unambiguous — unique claim_id per node.
        base_id = candidate.get("claim_id") or f"cand:{start_position + index}"
        if base_id in seen_ids:
            base_id = f"{base_id}:{start_position + index}"
        seen_ids.add(base_id)
        candidate = dict(candidate)
        candidate["claim_id"] = base_id
        try:
            residual = construct_residual(parent_claim, candidate)
            verdict_record = python_verify(residual)
            node = build_node(parent_claim, candidate, residual, verdict_record,
                              chain_id, start_position + index)
        except AdapterError:
            verdict_record = {"verdict": VERDICT_UNKNOWN,
                              "evidence": [{"kind": "construction_or_parse_failed"}],
                              "verifier": "python_sympy_exact_v1"}
            residual = None
            node = build_node(parent_claim, candidate,
                              {"lhs": None, "rhs": None, "symbols": None,
                               "construction": "failed", "sha256": None},
                              verdict_record, chain_id, start_position + index)
        nodes.append(node)
        summary[node["node_status"].lower()] += 1
    return {
        "operation": "compactification_step",
        "contract_version": "1.0",
        "adapter_version": ADAPTER_VERSION,
        "chain_id": chain_id,
        "parent_claim": {"claim_id": parent_claim["claim_id"],
                         "claim_sha256": claim_hash(parent_claim)},
        "nodes": nodes,
        "summary": summary,
        "provenance": {
            "repository_commit": _safe.git_head(HERE.parents[2]),
            "runtime_environment": {"python": platform.python_version(),
                                    "platform": platform.platform()},
            "calculations": "python_sympy_exact (no Wolfram)",
            "timestamp_utc": _now_iso(),
        },
    }

# --------------------------------------------------------------------------- #
# ORCH boundary (thin adapter entry)
# --------------------------------------------------------------------------- #

def _validate_against_schema(record: dict) -> None:
    """Validate a chain-step record against the packaged claim_chain schema."""
    import jsonschema
    schema_path = SCHEMAS_DIR / "claim_chain.schema.json"
    try:
        schema = json.loads(schema_path.read_text())
    except (OSError, json.JSONDecodeError):
        raise AdapterError("CHAIN_SCHEMA_UNREADABLE") from None
    try:
        jsonschema.validate(record, schema)
    except jsonschema.ValidationError as exc:
        raise AdapterError("CHAIN_RECORD_SCHEMA_FAILED") from exc


def handle(request: dict) -> tuple[dict, int]:
    """One compactification step through the ORCH boundary.

    Request fields:
      operation / contract_version      (required)
      chain_id                          (required)
      seed_id                           (required unless parent_claim given)
      parent_claim                      (optional; overrides seed_id)
      candidates                        (inline candidate claims; optional if propose)
      propose                           {"problem": {...}} -> LLM proposer via
                                        propose_equation_candidates adapter
      policy_overrides.timeout_seconds  (unused in Python-only stage; accepted
                                        for request-shape compatibility)
    """
    if not isinstance(request, dict):
        raise AdapterError("REQUEST_NOT_OBJECT")
    if request.get("operation") != "compactification_step":
        raise AdapterError("OPERATION_MISMATCH")
    if request.get("contract_version") != "1.0":
        raise AdapterError("CONTRACT_VERSION_MISMATCH")
    chain_id = request.get("chain_id")
    if not isinstance(chain_id, str) or not chain_id:
        raise AdapterError("CHAIN_ID_REQUIRED")

    # 1. parent claim (certified C_i)
    parent_claim = request.get("parent_claim")
    if parent_claim is None:
        seed_id = request.get("seed_id")
        if not isinstance(seed_id, str) or not seed_id:
            raise AdapterError("SEED_OR_PARENT_CLAIM_REQUIRED")
        seed = load_seed(seed_id)
        verify_seed(seed)  # must adjudicate ZERO before any step
        parent_claim = {
            "claim_id": seed["seed_id"],
            "lhs": seed["claim"]["lhs"],
            "rhs": seed["claim"]["rhs"],
            "symbols": seed["claim"]["symbols"],
            "scope": seed["claim"].get("scope", "declared_symbols"),
        }
    else:
        if not parent_claim.get("claim_id"):
            raise AdapterError("PARENT_CLAIM_MISSING")
        # F-01 fix: an ORCH-supplied parent is only trustworthy if it adjudicates
        # ZERO under the SAME verifier (or is bound to a previously certified
        # chain node by claim hash — a later stage).  Never build residuals on an
        # unverified parent: a false parent could certify a false child.
        parent_verdict = python_verify(parent_claim)
        if parent_verdict["verdict"] != VERDICT_ZERO:
            raise AdapterError("PARENT_CLAIM_NOT_CERTIFIED")

    # 2. candidates: inline or via the LLM proposer organ
    candidates = request.get("candidates")
    if candidates is None:
        propose = request.get("propose") or {}
        problem = propose.get("problem") or {}
        if not problem:
            raise AdapterError("CANDIDATES_OR_PROPOSE_REQUIRED")
        from loop_engine.orch_adapters.propose_equation_candidates import core as _proposer
        prop_result, _ = _proposer.handle(
            {"operation": "propose_equation_candidates",
             "contract_version": "1.0",
             "problem": problem})
        candidates = []
        for c in prop_result.get("candidates") or []:
            candidates.append({
                "claim_id": c.get("claim_id") or prop_result.get("request_hash", "?")[:12],
                "lhs": c["lhs"], "rhs": c["rhs"],
                "symbols": problem.get("symbols") or [],
                "scope": parent_claim.get("scope", "declared_symbols"),
            })
        if not candidates:
            return {"operation": "compactification_step", "contract_version": "1.0",
                    "chain_id": chain_id,
                    "error": "PROPOSER_RETURNED_NO_VALID_CANDIDATES",
                    "proposer_result": prop_result}, 1
    elif not isinstance(candidates, list) or not candidates:
        raise AdapterError("CANDIDATES_EMPTY")

    # 3. run the step
    step = run_loop_step(parent_claim, candidates, chain_id)
    _validate_against_schema(step)

    # 4. atomic replay artifact (out of the package tree)
    out_dir = Path(__import__("os").environ.get(
        "VIPER_OUTPUT_DIR", __import__("tempfile").gettempdir())) / "viper_compactification_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(step, tmp); tmp.close()
    step["replay_artifact"] = {"path": str(out_dir / "last_result.json"),
                               "sha256": sha256(Path(tmp.name).read_bytes())}
    import os as _os
    _os.replace(tmp.name, out_dir / "last_result.json")
    return step, 0