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
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.wolfram_runtime import (
    ENGINE_IDENTITY,
    IMPLEMENTATION_VERSION,
    PARSER_VERSION,
    SEMANTIC_PROFILE,
    TrustedRuntimeError,
    TrustedWolframRuntime,
    expected_configuration_hash,
    resolve_trusted_wolfram_runtime,
    validate_trusted_wolfram_runtime_execution_binding,
)

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


def _response(payload, runtime_identity=None, **extra):
    """Create a B3 record whose configuration comes only from trusted facts."""
    if runtime_identity is None:
        configuration_hash, runtime_binding = None, None
    else:
        configuration_hash = expected_configuration_hash(runtime_identity)
        runtime_binding = runtime_identity.binding()
    base = {
        "engine_identity": ENGINE_IDENTITY,
        "implementation_version": IMPLEMENTATION_VERSION,
        "parser_version": PARSER_VERSION,
        "configuration_hash": configuration_hash,
        "input_hash": _sha(payload),
        "semantic_profile": SEMANTIC_PROFILE,
        "trusted_runtime": runtime_binding,
    }
    base.update(extra)
    return base


def run_wolfram_code(runtime_identity, code, runner=subprocess.run):
    """Run code only after the final fixed-path provenance and descriptor binding guard."""
    if not isinstance(runtime_identity, TrustedWolframRuntime):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_INVALID")
    resolved = validate_trusted_wolfram_runtime_execution_binding(runtime_identity)
    process = runner(
        [str(resolved["canonical_candidate"]), "-local",
         str(resolved["canonical_kernel"]), "-code", code],
        text=True, capture_output=True, timeout=DEFAULT_TIMEOUT_SECONDS, check=False)
    # The signed bundle and fixed-path identity must also survive the launch/result
    # interval.  A changed path can never contribute a trusted ZERO result, even if a
    # platform-level launch race occurred after the pre-launch descriptor guard.
    validate_trusted_wolfram_runtime_execution_binding(runtime_identity)
    return process


def evaluate_with_runtime(payload, runtime_identity, runner=subprocess.run):
    """Evaluate one parsed request using a previously trusted runtime identity.

    This is intentionally the test seam: production calls :func:`run`, which resolves
    the identity itself and never accepts an executable path.
    """
    if not isinstance(payload, dict):
        return _response({}, runtime_identity, status="malformed", verdict="UNKNOWN",
                         detail="payload must be an object")
    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or not symbols or not all(isinstance(s, str) and _SYMBOL.fullmatch(s) for s in symbols):
        return _response(payload, runtime_identity, status="malformed", verdict="UNKNOWN",
                         detail="invalid symbol list")
    if payload.get("scope") not in {"real_scalars", "reals", "real", "R", "s"}:
        return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                         detail="only approved scalar scopes are supported")
    domain = payload.get("domain")
    assumptions = []
    if isinstance(domain, dict) and domain.get("schema") == "viper.connected_subdomain.v1":
        predicate = domain.get("predicate")
        terms = predicate.get("terms") if isinstance(predicate, dict) and predicate.get("kind") == "intersection" else [predicate]
        if not isinstance(terms, list) or not terms:
            return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                             detail="invalid connected-subdomain predicate")
        for term in terms:
            if not isinstance(term, dict):
                return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                 detail="invalid connected-subdomain term")
            if term.get("kind") == "real_line" and term.get("variable") in symbols:
                continue
            if term.get("kind") != "interval" or term.get("variable") not in symbols:
                return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                 detail="unsupported connected-subdomain term")
            variable, lower, upper = term["variable"], term.get("lower"), term.get("upper")
            if set(term) != {"kind", "variable", "lower", "upper", "lower_closed", "upper_closed"} or \
                    not isinstance(lower, str) or not isinstance(upper, str) or \
                    not isinstance(term.get("lower_closed"), bool) or not isinstance(term.get("upper_closed"), bool):
                return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                 detail="malformed interval")
            if lower == "+inf" or upper == "-inf" or (lower == "-inf" and term.get("lower_closed")) or \
                    (upper == "+inf" and term.get("upper_closed")):
                return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                 detail="invalid interval endpoint")
            if lower not in {"-inf", "+inf"}:
                try: Fraction(lower)
                except Exception: return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                                    detail="non-exact lower bound")
                if "." in lower or "e" in lower.lower():
                    return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                     detail="non-exact lower bound")
                assumptions.append(f"{variable}{'>=' if term.get('lower_closed') else '>'}{lower}")
            if upper not in {"-inf", "+inf"}:
                try: Fraction(upper)
                except Exception: return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                                    detail="non-exact upper bound")
                if "." in upper or "e" in upper.lower():
                    return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                                     detail="non-exact upper bound")
                assumptions.append(f"{variable}{'<=' if term.get('upper_closed') else '<'}{upper}")
    elif isinstance(domain, dict) and (domain.get("kind") != "real_line" or domain.get("variable") not in symbols):
        return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                         detail="unsupported structured domain")
    if domain is not None and not isinstance(domain, (dict, str)):
        return _response(payload, runtime_identity, status="malformed", verdict="UNKNOWN",
                         detail="invalid domain")
    try:
        lhs = _to_wolfram(payload.get("lhs"), set(symbols))
        rhs = _to_wolfram(payload.get("rhs"), set(symbols))
    except ParseError as exc:
        return _response(payload, runtime_identity, status="unsupported", verdict="UNKNOWN",
                         detail=str(exc))
    variables = "{" + ",".join(symbols) + "}"
    real_assumption = "Element[" + variables + ",Reals]"
    if assumptions:
        real_assumption += "&&" + "&&".join(assumptions)
    code = "FullSimplify[" + lhs + "==" + rhs + "," + real_assumption + "]"
    try:
        process = run_wolfram_code(runtime_identity, code, runner)
    except subprocess.TimeoutExpired:
        return _response(payload, runtime_identity, status="timeout", verdict="UNKNOWN",
                         detail="Wolfram process timed out", stdout="", stderr="", exit_status=None)
    except (OSError, TrustedRuntimeError) as exc:
        return _response(payload, runtime_identity, status="process_failure", verdict="UNKNOWN",
                         detail=type(exc).__name__, stdout="", stderr="", exit_status=None)
    stdout, stderr = process.stdout.strip(), process.stderr.strip()
    if process.returncode != 0:
        return _response(payload, runtime_identity, status="process_failure", verdict="UNKNOWN",
                         detail="nonzero exit", stdout=stdout, stderr=stderr,
                         exit_status=process.returncode)
    if stdout == "True":
        verdict = "ZERO"
    elif stdout == "False":
        verdict = "NONZERO"
    else:
        verdict = "UNKNOWN"
    return _response(payload, runtime_identity, status="complete", verdict=verdict,
                     detail="Wolfram FullSimplify over declared reals", stdout=stdout,
                     stderr=stderr, exit_status=process.returncode)


def run(payload):
    """Production entry point: resolve the trusted runtime before all evaluation."""
    try:
        runtime_identity = resolve_trusted_wolfram_runtime()
    except TrustedRuntimeError as exc:
        safe_payload = payload if isinstance(payload, dict) else {}
        return _response(
            safe_payload, status="process_failure", verdict="UNKNOWN",
            detail=exc.code, stdout="", stderr="", exit_status=None)
    return evaluate_with_runtime(payload, runtime_identity)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        result = run({})
        if result.get("status") != "process_failure":
            result.update(status="malformed", verdict="UNKNOWN", detail="invalid JSON")
        print(json.dumps(result, sort_keys=True))
        return 1
    print(json.dumps(run(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
