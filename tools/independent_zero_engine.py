#!/usr/bin/env python3
"""B3 standalone Wolfram ZERO engine.

This executable is intentionally outside the primary SymPy verifier.  It accepts only raw,
normalized claim text and structured semantics, parses the text with Python's AST (not
SymPy), serializes a bounded expression grammar to Wolfram Language, and asks a separate
Wolfram kernel whether the equality is identically true over the declared reals.

Its stdout is one JSON object.  Diagnostics from the Wolfram process are carried in the JSON
record, never printed directly to stdout.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from fractions import Fraction

ENGINE_IDENTITY = "WOLFRAM_INDEPENDENT_ZERO"
IMPLEMENTATION_VERSION = "1.0"
PARSER_VERSION = "python_ast_to_wolfram_1"
SEMANTIC_PROFILE = "real_identity_zero_v1"
DEFAULT_TIMEOUT_SECONDS = 12
_SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_ALLOWED_FUNCTIONS = {
    "sqrt": "Sqrt", "sin": "Sin", "cos": "Cos", "tan": "Tan",
    "asin": "ArcSin", "acos": "ArcCos", "atan": "ArcTan", "exp": "Exp",
    "sinh": "Sinh", "cosh": "Cosh", "tanh": "Tanh", "log": "Log",
}


def _sha(value):
    # Match the repository-wide hash primitive so the caller can independently bind the
    # raw request without consuming any primary-engine intermediate.
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _config(wolfram_command):
    return {
        "engine_identity": ENGINE_IDENTITY,
        "implementation_version": IMPLEMENTATION_VERSION,
        "parser_version": PARSER_VERSION,
        "semantic_profile": SEMANTIC_PROFILE,
        "wolfram_command": wolfram_command,
    }


class ParseError(ValueError):
    pass


def _to_wolfram(source, symbols):
    """Parse a strict expression grammar and serialize it to Wolfram syntax."""
    if not isinstance(source, str) or len(source) > 4000:
        raise ParseError("expression size or type is invalid")
    try:
        node = ast.parse(source.replace("^", "**"), mode="eval").body
    except SyntaxError as exc:
        raise ParseError("invalid expression syntax") from exc

    def emit(part):
        if isinstance(part, ast.Name):
            if part.id not in symbols:
                raise ParseError("undeclared symbol")
            return part.id
        if isinstance(part, ast.Constant) and isinstance(part.value, int):
            return str(part.value)
        if isinstance(part, ast.UnaryOp) and isinstance(part.op, (ast.USub, ast.UAdd)):
            return ("-" if isinstance(part.op, ast.USub) else "+") + "(" + emit(part.operand) + ")"
        if isinstance(part, ast.BinOp) and type(part.op) in {
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
        }:
            op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}[type(part.op)]
            return "(" + emit(part.left) + op + emit(part.right) + ")"
        if isinstance(part, ast.Call) and isinstance(part.func, ast.Name) and \
                part.func.id in _ALLOWED_FUNCTIONS and not part.keywords:
            if part.func.id == "atan" and len(part.args) == 2:
                return "ArcTan[" + ",".join(emit(a) for a in part.args) + "]"
            if len(part.args) != 1:
                raise ParseError("unsupported function arity")
            return _ALLOWED_FUNCTIONS[part.func.id] + "[" + emit(part.args[0]) + "]"
        raise ParseError("unsupported expression node")

    return emit(node)


def _response(payload, **extra):
    command = os.environ.get("VIPER_WOLFRAM_CMD", "wolframscript")
    config = _config(command)
    base = {
        "engine_identity": ENGINE_IDENTITY,
        "implementation_version": IMPLEMENTATION_VERSION,
        "parser_version": PARSER_VERSION,
        "configuration_hash": _sha(config),
        "input_hash": _sha(payload),
        "semantic_profile": SEMANTIC_PROFILE,
    }
    base.update(extra)
    return base


def run(payload):
    if not isinstance(payload, dict):
        return _response({}, status="malformed", verdict="UNKNOWN", detail="payload must be an object")
    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or not symbols or not all(isinstance(s, str) and _SYMBOL.fullmatch(s) for s in symbols):
        return _response(payload, status="malformed", verdict="UNKNOWN", detail="invalid symbol list")
    if payload.get("scope") not in {"real_scalars", "reals", "real", "R", "s"}:
        return _response(payload, status="unsupported", verdict="UNKNOWN", detail="only approved scalar scopes are supported")
    domain = payload.get("domain")
    assumptions = []
    if isinstance(domain, dict) and domain.get("schema") == "viper.connected_subdomain.v1":
        predicate = domain.get("predicate")
        terms = predicate.get("terms") if isinstance(predicate, dict) and predicate.get("kind") == "intersection" else [predicate]
        if not isinstance(terms, list) or not terms:
            return _response(payload, status="unsupported", verdict="UNKNOWN", detail="invalid connected-subdomain predicate")
        for term in terms:
            if not isinstance(term, dict):
                return _response(payload, status="unsupported", verdict="UNKNOWN", detail="invalid connected-subdomain term")
            if term.get("kind") == "real_line" and term.get("variable") in symbols:
                continue
            if term.get("kind") != "interval" or term.get("variable") not in symbols:
                return _response(payload, status="unsupported", verdict="UNKNOWN", detail="unsupported connected-subdomain term")
            variable, lower, upper = term["variable"], term.get("lower"), term.get("upper")
            if set(term) != {"kind", "variable", "lower", "upper", "lower_closed", "upper_closed"} or \
                    not isinstance(lower, str) or not isinstance(upper, str) or \
                    not isinstance(term.get("lower_closed"), bool) or not isinstance(term.get("upper_closed"), bool):
                return _response(payload, status="unsupported", verdict="UNKNOWN", detail="malformed interval")
            if lower == "+inf" or upper == "-inf" or (lower == "-inf" and term.get("lower_closed")) or \
                    (upper == "+inf" and term.get("upper_closed")):
                return _response(payload, status="unsupported", verdict="UNKNOWN", detail="invalid interval endpoint")
            if lower not in {"-inf", "+inf"}:
                try: Fraction(lower)
                except Exception: return _response(payload, status="unsupported", verdict="UNKNOWN", detail="non-exact lower bound")
                if "." in lower or "e" in lower.lower():
                    return _response(payload, status="unsupported", verdict="UNKNOWN", detail="non-exact lower bound")
                assumptions.append(f"{variable}{'>=' if term.get('lower_closed') else '>'}{lower}")
            if upper not in {"-inf", "+inf"}:
                try: Fraction(upper)
                except Exception: return _response(payload, status="unsupported", verdict="UNKNOWN", detail="non-exact upper bound")
                if "." in upper or "e" in upper.lower():
                    return _response(payload, status="unsupported", verdict="UNKNOWN", detail="non-exact upper bound")
                assumptions.append(f"{variable}{'<=' if term.get('upper_closed') else '<'}{upper}")
    elif isinstance(domain, dict) and (domain.get("kind") != "real_line" or domain.get("variable") not in symbols):
        return _response(payload, status="unsupported", verdict="UNKNOWN", detail="unsupported structured domain")
    if domain is not None and not isinstance(domain, (dict, str)):
        return _response(payload, status="malformed", verdict="UNKNOWN", detail="invalid domain")
    try:
        lhs = _to_wolfram(payload.get("lhs"), set(symbols))
        rhs = _to_wolfram(payload.get("rhs"), set(symbols))
    except ParseError as exc:
        return _response(payload, status="unsupported", verdict="UNKNOWN", detail=str(exc))
    variables = "{" + ",".join(symbols) + "}"
    real_assumption = "Element[" + variables + ",Reals]"
    if assumptions:
        real_assumption += "&&" + "&&".join(assumptions)
    code = "FullSimplify[" + lhs + "==" + rhs + "," + real_assumption + "]"
    command = os.environ.get("VIPER_WOLFRAM_CMD", "wolframscript")
    try:
        process = subprocess.run([command, "-code", code], text=True, capture_output=True,
                                 timeout=DEFAULT_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return _response(payload, status="timeout", verdict="UNKNOWN", detail="Wolfram process timed out",
                         stdout="", stderr="", exit_status=None)
    except OSError as exc:
        return _response(payload, status="process_failure", verdict="UNKNOWN", detail=type(exc).__name__,
                         stdout="", stderr="", exit_status=None)
    stdout, stderr = process.stdout.strip(), process.stderr.strip()
    if process.returncode != 0:
        return _response(payload, status="process_failure", verdict="UNKNOWN", detail="nonzero exit",
                         stdout=stdout, stderr=stderr, exit_status=process.returncode)
    if stdout == "True":
        verdict = "ZERO"
    elif stdout == "False":
        verdict = "NONZERO"
    else:
        verdict = "UNKNOWN"
    return _response(payload, status="complete", verdict=verdict,
                     detail="Wolfram FullSimplify over declared reals", stdout=stdout,
                     stderr=stderr, exit_status=process.returncode)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps(_response({}, status="malformed", verdict="UNKNOWN", detail="invalid JSON"), sort_keys=True))
        return 1
    print(json.dumps(run(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
