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
import ast
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
_SOURCE_CONSTANTS = {"pi", "E", "I", "oo"}
_RESERVED_DECLARED_NAMES = (
    set(PARSE_POLICY["allowed_functions"])
    | _SOURCE_CONSTANTS
    | {"zoo", "nan", "Integer", "Float", "Symbol"}
)
_ALLOWED_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY_OPERATORS = (ast.UAdd, ast.USub)


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


def syms_like(expr, names):
    """Return symbol objects for `names` MATCHING the assumptions carried by `expr`.

    Reconstructing sympy.Symbol(n) by name silently fails to substitute into an expression
    parsed with real=True (different object, different assumptions), so every downstream
    subs/probe/reduction must take its symbols from the parsed expression itself.
    """
    by_name = {str(s): s for s in getattr(expr, "free_symbols", set())}
    return [by_name.get(n, sympy.Symbol(n)) for n in names]


def _validate_source_ast(expr_str, declared_symbols):
    """Validate the complete source grammar before any SymPy evaluation occurs."""
    try:
        node = ast.parse(expr_str.replace("^", "**"), mode="eval").body
    except SyntaxError:
        raise AdapterError("SYMBOLIC_PARSE_FAILED")
    declared = set(declared_symbols)
    functions = set(PARSE_POLICY["allowed_functions"])

    def visit(part):
        if isinstance(part, ast.Name):
            if part.id not in declared | functions | _SOURCE_CONSTANTS:
                raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
            return
        if isinstance(part, ast.Constant):
            if not isinstance(part.value, int) or isinstance(part.value, bool):
                raise AdapterError("UNSUPPORTED_LITERAL")
            return
        if isinstance(part, ast.UnaryOp):
            if not isinstance(part.op, _ALLOWED_UNARY_OPERATORS):
                raise AdapterError("UNSUPPORTED_SOURCE_AST")
            visit(part.operand)
            return
        if isinstance(part, ast.BinOp):
            if not isinstance(part.op, _ALLOWED_BINARY_OPERATORS):
                raise AdapterError("UNSUPPORTED_SOURCE_AST")
            visit(part.left)
            visit(part.right)
            return
        if isinstance(part, ast.Call):
            if not isinstance(part.func, ast.Name) or part.func.id not in functions or \
                    part.keywords:
                raise AdapterError("UNSUPPORTED_SOURCE_AST")
            for argument in part.args:
                visit(argument)
            return
        raise AdapterError("UNSUPPORTED_SOURCE_AST")

    visit(node)


def validate_and_parse(expr_str, declared_symbols, real=False):
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
    if not isinstance(declared_symbols, (list, tuple)) or \
            not all(isinstance(name, str) and _SYMBOL_RE.fullmatch(name)
                    for name in declared_symbols) or \
            len(set(declared_symbols)) != len(declared_symbols):
        raise AdapterError("INVALID_DECLARED_SYMBOLS")
    if set(declared_symbols) & _RESERVED_DECLARED_NAMES:
        raise AdapterError("RESERVED_DECLARED_SYMBOL")
    names = set(_SYMBOL_RE.findall(expr_str))
    allowed = set(declared_symbols) | set(PARSE_POLICY["allowed_functions"]) | {"pi", "E", "I", "oo"}
    if names - allowed:
        raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
    _validate_source_ast(expr_str, declared_symbols)
    # honour the claim's declared domain: a real-scope claim must be adjudicated over the
    # reals, not over the complex numbers (otherwise the judge answers a different question)
    declared_map = {
        s: sympy.Symbol(s, real=True) if real else sympy.Symbol(s)
        for s in declared_symbols
    }
    if not all(isinstance(symbol, sympy.Symbol) for symbol in declared_map.values()):
        raise AdapterError("INVALID_DECLARED_SYMBOLS")
    local = dict(declared_map)
    for f in PARSE_POLICY["allowed_functions"]:
        local[f] = getattr(sympy, f, None)
    local.update({"pi": sympy.pi, "E": sympy.E, "I": sympy.I, "oo": sympy.oo})
    if any(local.get(name) is not symbol for name, symbol in declared_map.items()):
        raise AdapterError("DECLARED_SYMBOL_BINDING_MISMATCH")
    try:
        expr = sympy.sympify(expr_str, locals=local, evaluate=True, convert_xor=True)
    except (sympy.SympifyError, SyntaxError, TypeError, AttributeError):
        raise AdapterError("SYMBOLIC_PARSE_FAILED")
    if expr.free_symbols - set(declared_map.values()):
        raise AdapterError("UNDECLARED_OR_DISALLOWED_NAME")
    if sympy.count_ops(expr, visual=False) > PARSE_POLICY["max_nodes"]:
        raise AdapterError("EXPRESSION_TOO_LARGE")
    return expr
