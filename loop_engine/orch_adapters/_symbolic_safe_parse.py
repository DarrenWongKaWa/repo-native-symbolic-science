#!/usr/bin/env python3
"""Neutral shared primitives for the symbolic fusion capabilities.

Extracted so the PROPOSER can reuse the exact same strict parser + gold-metadata rejection
WITHOUT importing the JUDGE. This is fusion Stage 3's code-level isolation: the proposer
must have no in-process path to the judge's scoring/verdict function. Both the judge
(`symbolic_identity_verify`) and the proposer (`propose_equation_candidates`) import from
here; neither imports the other.

Contains ONLY: the error type, the gold-metadata blocklist, the parse policy, and the
strict whitelist parser. It contains NO scoring, NO verdict, NO oracle — by construction.
"""
from __future__ import annotations
import hashlib, json, re, subprocess
from pathlib import Path
import sympy

# benchmark/gold metadata a caller must never inject (shared by judge + proposer)
FORBIDDEN = {"gold_verdict", "expected_answer", "mutation_operator", "gold_residual",
             "benchmark_task_class", "gold_certificate", "is_identity"}

# parse policy (NOT caller-supplied); a caller may only strengthen, never weaken
PARSE_POLICY = {"max_expr_chars": 4000, "max_nodes": 4000, "max_symbols": 40,
                "allowed_functions": sorted([
                    "sin", "cos", "tan", "exp", "log", "sqrt", "Abs", "conjugate", "re", "im",
                    "sinh", "cosh", "tanh", "asin", "acos", "atan", "atan2", "Rational"])}

_SYMBOL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ALLOWED_TOKEN_RE = re.compile(r"^[A-Za-z0-9_+\-*/().,\s^]*$")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else json.dumps(b, sort_keys=True).encode()).hexdigest()


class AdapterError(Exception):
    def __init__(self, code): super().__init__(code); self.code = code


def git_head(cwd: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(cwd),
                              capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def validate_and_parse(expr_str, declared_symbols):
    """Reject before parsing; parse only with a restricted, whitelisted locals map.

    Blocks code-injection (character class), undeclared/disallowed names, oversized input.
    Returns a sympy expression. Raises AdapterError on any violation. No eval/exec path.
    """
    if not isinstance(expr_str, str) or not expr_str.strip():
        raise AdapterError("EMPTY_EXPRESSION")
    if len(expr_str) > PARSE_POLICY["max_expr_chars"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    if not _ALLOWED_TOKEN_RE.match(expr_str):
        raise AdapterError("DISALLOWED_CHARACTERS")
    names = set(_SYMBOL_RE.findall(expr_str))
    allowed = set(declared_symbols) | set(PARSE_POLICY["allowed_functions"]) | {"pi", "E", "I", "oo"}
    if names - allowed:
        raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
    local = {s: sympy.Symbol(s) for s in declared_symbols}
    for f in PARSE_POLICY["allowed_functions"]:
        local[f] = getattr(sympy, f, None)
    local.update({"pi": sympy.pi, "E": sympy.E, "I": sympy.I, "oo": sympy.oo})
    try:
        expr = sympy.sympify(expr_str, locals=local, evaluate=True, convert_xor=True)
    except (sympy.SympifyError, SyntaxError, TypeError, AttributeError):
        raise AdapterError("SYMBOLIC_PARSE_FAILED")
    if sympy.count_ops(expr, visual=False) > PARSE_POLICY["max_nodes"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    return expr
