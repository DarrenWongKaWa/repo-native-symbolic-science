"""B5 bounded multivariable derivative/base-point certificates.

This is intentionally not a general multivariable theorem prover.  It accepts only an
explicit ordered variable manifest, an exact rational base point, a connected Cartesian
product of exact real intervals, an everywhere-real differentiable expression grammar,
and one independently recheckable plus B3-confirmed ZERO partial for every variable.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import platform
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import sympy

from loop_engine.orch_adapters._symbolic_safe_parse import (
    FORBIDDEN, PARSE_POLICY, git_head, sha, syms_like, validate_and_parse,
)
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as _domain
from loop_engine.orch_adapters.symbolic_identity_verify import domain_obligations as _b4
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as _recheck

REQUEST_SCHEMA = "viper.multivariable_t3_request.v1"
CERTIFICATE_KIND = "multivariable_derivative_base_point_composite"
CERTIFICATE_VERSION = "1.1"
GRADIENT_SCHEMA = "viper.gradient_certificate_graph.v1"
CHILD_CONTEXT_SCHEMA = "viper.b5_child_context.v1"
EXACT_CHILD_SCHEMA = "viper.b5_bound_exact_child.v1"
FAILURE = {
    "request": "MULTIVARIABLE_T3_REQUEST_INVALID",
    "variables": "MULTIVARIABLE_T3_VARIABLE_MANIFEST_INVALID",
    "domain": "MULTIVARIABLE_T3_DOMAIN_UNSUPPORTED",
    "base": "MULTIVARIABLE_T3_BASE_POINT_INVALID",
    "grammar": "MULTIVARIABLE_T3_PARENT_GRAMMAR_UNSUPPORTED",
    "partial": "MULTIVARIABLE_T3_PARTIAL_UNSUPPORTED",
    "domain_obligation": "MULTIVARIABLE_T3_DOMAIN_OBLIGATION_UNRESOLVED",
    "confirmation": "MULTIVARIABLE_T3_PARTIAL_UNCONFIRMED",
    "certificate": "MULTIVARIABLE_T3_CERTIFICATE_INVALID",
}
_ENTIRE_FUNCTIONS = {sympy.sin, sympy.cos, sympy.exp, sympy.sinh, sympy.cosh, sympy.tanh}
_B5_CONSTANT_NAMES = {"pi", "E", "I", "oo", "zoo", "nan"}
_RESERVED_DECLARED_NAMES = set(PARSE_POLICY["allowed_functions"]) | \
    _B5_CONSTANT_NAMES | {"Integer", "Float", "Symbol"}
_EXACT_CHILD_FIELDS = {
    "schema", "version", "context_binding", "context_binding_hash",
    "proof_kind", "proof", "proof_hash", "artifact_hash",
}
_CHILD_CONTEXT_FIELDS = {
    "schema", "version", "parent_claim_hash", "variable_order_hash",
    "variable_slot_index", "derivative_variable", "domain_hash",
    "assumptions_hash", "scope", "scope_hash", "derivative_claim_hash",
}
_B3_EVIDENCE_FIELDS = {
    "route", "process_stdout", "process_stderr", "process_exit_status",
    "configuration_hash", "detail", "engine_identity", "exit_status",
    "implementation_version", "input_hash", "parser_version",
    "semantic_profile", "status", "stderr", "stdout", "verdict",
}
_B3_PROCESS_FIELDS = {
    "route", "process_stdout", "process_stderr", "process_exit_status",
}


class MultivariableT3Error(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fail(code):
    raise MultivariableT3Error(code)


def _artifact_hash(payload):
    body = copy.deepcopy(payload)
    body.pop("artifact_hash", None)
    return sha(body)


def _validate_b5_source_ast(source, declared_symbols):
    """Validate the complete source grammar before any SymPy parsing."""
    try:
        root = ast.parse(source, mode="eval")
    except (SyntaxError, TypeError):
        _fail(FAILURE["grammar"])
    declared = set(declared_symbols)
    functions = set(PARSE_POLICY["allowed_functions"])

    def visit(node):
        if isinstance(node, ast.Expression):
            visit(node.body)
            return
        if isinstance(node, ast.Name):
            if node.id not in declared and node.id not in _B5_CONSTANT_NAMES:
                _fail(FAILURE["grammar"])
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, int):
                _fail(FAILURE["grammar"])
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            visit(node.operand)
            return
        if isinstance(node, ast.BinOp) and type(node.op) in {
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow}:
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id in functions and not node.keywords:
            for argument in node.args:
                visit(argument)
            return
        _fail(FAILURE["grammar"])

    visit(root)


def _validate_and_parse_b5(source, declared_symbols, real=True):
    """Apply the stricter B5 grammar without changing legacy B1-B4 parsing."""
    if not isinstance(declared_symbols, list) or \
            not all(isinstance(name, str) and name.isidentifier()
                    for name in declared_symbols) or \
            len(set(declared_symbols)) != len(declared_symbols) or \
            any(name in _RESERVED_DECLARED_NAMES for name in declared_symbols):
        _fail(FAILURE["variables"])
    _validate_b5_source_ast(source, declared_symbols)
    expression = validate_and_parse(source, declared_symbols, real=real)
    declared_map = {
        name: sympy.Symbol(name, real=True) if real else sympy.Symbol(name)
        for name in declared_symbols
    }
    if not all(isinstance(symbol, sympy.Symbol) and str(symbol) == name
               for name, symbol in declared_map.items()):
        _fail(FAILURE["variables"])
    if not all(isinstance(symbol, sympy.Symbol) and
               str(symbol) in declared_map for symbol in expression.free_symbols):
        _fail(FAILURE["grammar"])
    return expression


def _exact_finite_real(expression):
    """Require exact finite real symbolic arithmetic throughout the B5 route."""
    return (
        isinstance(expression, sympy.Basic) and
        not expression.atoms(sympy.Float) and
        not expression.has(sympy.oo, -sympy.oo, sympy.zoo, sympy.nan) and
        expression.is_real is True and
        expression.is_finite is True
    )


def _exact_rational(source):
    if not isinstance(source, str) or not source or "." in source or "e" in source.lower():
        _fail(FAILURE["base"])
    try:
        value = Fraction(source)
    except (ValueError, ZeroDivisionError):
        _fail(FAILURE["base"])
    return value, sympy.Rational(value.numerator, value.denominator)


def _inside(value, interval):
    lower = None if interval["lower"] == "-inf" else Fraction(interval["lower"])
    upper = None if interval["upper"] == "+inf" else Fraction(interval["upper"])
    if lower is not None and (value < lower or value == lower and not interval["lower_closed"]):
        return False
    if upper is not None and (value > upper or value == upper and not interval["upper_closed"]):
        return False
    return True


def _entire_real_expression(expr, declared):
    """Recognize only a small grammar whose real differentiability is structural."""
    if expr.is_Number:
        return _exact_finite_real(expr)
    if expr.is_Symbol:
        return str(expr) in declared and expr.is_real is True
    if isinstance(expr, (sympy.Add, sympy.Mul)):
        return all(_entire_real_expression(arg, declared) for arg in expr.args)
    if isinstance(expr, sympy.Pow):
        return bool(expr.exp.is_Integer and expr.exp >= 0 and
                    _entire_real_expression(expr.base, declared))
    if expr.func in _ENTIRE_FUNCTIONS:
        return len(expr.args) == 1 and _entire_real_expression(expr.args[0], declared)
    return False


def _child_certificate(lhs, rhs, symbols):
    for builder in (
        _recheck.build_polynomial_certificate,
        _recheck.build_trig_cofactor_certificate,
        _recheck.build_exp_polynomial_certificate,
    ):
        try:
            certificate = builder(lhs, rhs, symbols)
        except Exception:
            _fail(FAILURE["partial"])
        # The existing T1 builder may return no cofactors when exact trig expansion makes
        # the numerator structurally zero.  Bind explicit zero cofactors so its independent
        # rechecker can still require one entry per declared Pythagorean constraint.
        if certificate and certificate.get("kind") == "trig_ideal_cofactor" and \
                certificate.get("numerator_polynomial") == "0" and \
                certificate.get("cofactors") == []:
            certificate = copy.deepcopy(certificate)
            certificate["cofactors"] = [
                "0" for _ in certificate.get("constraint_polynomials", [])]
        if certificate and _recheck.recheck(
                {"lhs": str(lhs), "rhs": str(rhs), "symbols": list(symbols)}, certificate).get("ok"):
            return certificate
    return None


def _child_context_binding(
        parent_claim_hash, variable_order_hash, variable_slot_index,
        derivative_variable, domain_hash, assumptions, scope,
        derivative_claim_hash):
    return {
        "schema": CHILD_CONTEXT_SCHEMA,
        "version": "1.0",
        "parent_claim_hash": parent_claim_hash,
        "variable_order_hash": variable_order_hash,
        "variable_slot_index": variable_slot_index,
        "derivative_variable": derivative_variable,
        "domain_hash": domain_hash,
        "assumptions_hash": sha(list(assumptions)),
        "scope": scope,
        "scope_hash": sha(scope),
        "derivative_claim_hash": derivative_claim_hash,
    }


def _bound_exact_child_certificate(proof, context_binding):
    envelope = {
        "schema": EXACT_CHILD_SCHEMA,
        "version": "1.0",
        "context_binding": copy.deepcopy(context_binding),
        "context_binding_hash": sha(context_binding),
        "proof_kind": proof.get("kind"),
        "proof": copy.deepcopy(proof),
        "proof_hash": sha(proof),
    }
    envelope["artifact_hash"] = _artifact_hash(envelope)
    return envelope


def _strict_exact_child_matches(expected, stored):
    if not isinstance(stored, dict) or set(stored) != _EXACT_CHILD_FIELDS or \
            stored.get("schema") != EXACT_CHILD_SCHEMA or \
            stored.get("version") != "1.0" or \
            stored.get("artifact_hash") != _artifact_hash(stored):
        return False
    context = stored.get("context_binding")
    proof = stored.get("proof")
    if not isinstance(context, dict) or set(context) != _CHILD_CONTEXT_FIELDS or \
            stored.get("context_binding_hash") != sha(context) or \
            not isinstance(proof, dict) or \
            stored.get("proof_kind") != proof.get("kind") or \
            stored.get("proof_hash") != sha(proof):
        return False
    return stored == expected


def _child_b3_payload(child):
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    payload = core._second_engine_payload(
        child["lhs"], child["rhs"], child["symbols"], child["scope"],
        child["engine_domain"], child["assumptions"])
    payload["b5_context_binding"] = copy.deepcopy(child["child_context_binding"])
    payload["b5_context_binding_hash"] = child["child_context_binding_hash"]
    return payload


def _run_pinned_b3_payload(payload, timeout):
    """Invoke the shipped B3 executable directly, ignoring override commands."""
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[3] /
            "tools" / "independent_zero_engine.py"),
    ]
    try:
        process = subprocess.run(
            command, input=json.dumps(payload), capture_output=True, text=True,
            timeout=max(5, timeout), check=False)
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout", "route": "shipped_wolfram_engine",
            "input_hash": sha(payload), "stdout": "", "stderr": "",
            "exit_status": None,
        }
    except Exception as exc:
        return {
            "status": "process_failure", "route": "shipped_wolfram_engine",
            "input_hash": sha(payload), "detail": type(exc).__name__,
            "stdout": "", "stderr": "", "exit_status": None,
        }
    try:
        parsed = json.loads(process.stdout)
    except Exception:
        return {
            "status": "malformed_output", "route": "shipped_wolfram_engine",
            "input_hash": sha(payload), "stdout": process.stdout,
            "stderr": process.stderr, "exit_status": process.returncode,
        }
    if not isinstance(parsed, dict):
        return {
            "status": "malformed_output", "route": "shipped_wolfram_engine",
            "input_hash": sha(payload), "stdout": process.stdout,
            "stderr": process.stderr, "exit_status": process.returncode,
        }
    return {
        "route": "shipped_wolfram_engine",
        "process_stdout": process.stdout,
        "process_stderr": process.stderr,
        "process_exit_status": process.returncode,
        **parsed,
    }


def _strict_second_zero_confirmed(confirmation, payload):
    """Require the exact stored B3 schema and raw process/JSON consistency."""
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    if not isinstance(confirmation, dict) or \
            set(confirmation) != _B3_EVIDENCE_FIELDS or \
            not core._second_zero_confirmed(confirmation, payload) or \
            confirmation.get("stdout") != "True" or \
            confirmation.get("exit_status") != 0 or \
            confirmation.get("process_exit_status") != 0:
        return False
    try:
        parsed = json.loads(confirmation["process_stdout"])
    except Exception:
        return False
    expected_parsed = {
        key: value for key, value in confirmation.items()
        if key not in _B3_PROCESS_FIELDS
    }
    return parsed == expected_parsed


def _claim_binding(claim, canonical_domain, manifest):
    body = {
        "lhs": claim["lhs"],
        "rhs": claim["rhs"],
        "symbols": list(claim["symbols"]),
        "scope": claim["scope"],
        "assumptions": list(claim["assumptions"]),
        "canonical_domain": canonical_domain,
        "multivariable_t3": copy.deepcopy(manifest),
    }
    return sha(body)


def prepare_certificate(claim, lhs, rhs):
    """Build every exact local artifact except the independent B3 confirmations."""
    manifest = claim.get("multivariable_t3")
    required = {"schema", "relevant_variables", "variable_order", "base_point"}
    if not isinstance(manifest, dict) or set(manifest) != required or \
            manifest.get("schema") != REQUEST_SCHEMA:
        _fail(FAILURE["request"])
    symbols = claim.get("symbols")
    relevant = manifest.get("relevant_variables")
    variable_order = manifest.get("variable_order")
    if not isinstance(symbols, list) or len(symbols) < 2 or len(set(symbols)) != len(symbols) or \
            relevant != symbols or variable_order != symbols or \
            any(not isinstance(variable, str) or not variable.isidentifier() or
                variable in _RESERVED_DECLARED_NAMES for variable in symbols):
        _fail(FAILURE["variables"])
    assumptions = claim.get("assumptions")
    scope = claim.get("scope")
    if assumptions != [f"{variable} real" for variable in symbols] or \
            scope != "real_scalars":
        _fail(FAILURE["request"])
    if not _exact_finite_real(lhs) or not _exact_finite_real(rhs) or \
            not _entire_real_expression(lhs, set(symbols)) or \
            not _entire_real_expression(rhs, set(symbols)):
        _fail(FAILURE["grammar"])

    raw_domain = claim.get("domain")
    raw_terms = raw_domain.get("terms") if isinstance(raw_domain, dict) and \
        raw_domain.get("kind") == "intersection" else None
    explicit_domain_variables = [
        term.get("variable") if isinstance(term, dict) and term.get("kind") != "comparison"
        else term.get("left") if isinstance(term, dict) else None
        for term in raw_terms or []
    ]
    if not raw_terms or set(explicit_domain_variables) != set(symbols):
        _fail(FAILURE["domain"])
    try:
        domain_analysis = _domain.analyze_predicate(raw_domain, symbols)
    except Exception:
        _fail(FAILURE["domain"])
    if domain_analysis.get("status") != "CONNECTED":
        _fail(FAILURE["domain"])
    canonical_domain = domain_analysis["predicate"]
    intervals = domain_analysis["intervals"]
    component = {
        "kind": "cartesian_product_intervals",
        "variables": list(symbols),
        "intervals": [copy.deepcopy(intervals[v]) for v in symbols],
    }
    component_hash = sha(component)
    domain_certificate = {
        "schema": _domain.SCHEMA,
        "profile": _domain.PROFILE,
        "variables": list(symbols),
        "predicate": copy.deepcopy(canonical_domain),
        "intervals": [copy.deepcopy(intervals[v]) for v in symbols],
        "connected_component": component,
        "connected_component_hash": component_hash,
        "connected": True,
        "nonempty": True,
        "differentiability_profile": "entire_real_elementary_v1",
    }
    domain_certificate["domain_certificate_hash"] = sha(domain_certificate)

    point = manifest.get("base_point")
    if not isinstance(point, dict) or list(point) != symbols or set(point) != set(symbols):
        _fail(FAILURE["base"])
    exact_point, substitutions = {}, {}
    symbol_objects = syms_like(lhs - rhs, symbols)
    by_name = {str(symbol): symbol for symbol in symbol_objects}
    for variable in symbols:
        rational, sympy_value = _exact_rational(point[variable])
        if not _inside(rational, intervals[variable]):
            _fail(FAILURE["base"])
        exact_point[variable] = point[variable]
        substitutions[by_name[variable]] = sympy_value
    try:
        lhs_value, rhs_value = lhs.subs(substitutions), rhs.subs(substitutions)
    except Exception:
        _fail(FAILURE["base"])
    if not _exact_finite_real(lhs_value) or not _exact_finite_real(rhs_value) or \
            lhs_value.free_symbols or rhs_value.free_symbols or lhs_value != rhs_value:
        _fail(FAILURE["base"])

    try:
        graph = _b4.build_obligation_graph(
            {k: copy.deepcopy(claim[k]) for k in ("lhs", "rhs", "symbols", "scope")},
            claim["domain"], assumptions)
        replay = _b4.recheck_obligation_graph(
            {k: copy.deepcopy(claim[k]) for k in ("lhs", "rhs", "symbols", "scope")},
            claim["domain"], assumptions, graph)
    except Exception:
        _fail(FAILURE["domain_obligation"])
    if replay.get("ok") is not True:
        _fail(FAILURE["domain_obligation"])

    parent_hash = _claim_binding(claim, canonical_domain, manifest)
    variable_order_manifest = {
        "relevant_variables": list(relevant),
        "variable_order": list(variable_order),
    }
    variable_order_manifest["variable_order_hash"] = sha(variable_order_manifest)
    base_point_certificate = {
        "point": exact_point,
        "lhs_value": str(lhs_value),
        "rhs_value": str(rhs_value),
        "parent_claim_hash": parent_hash,
        "connected_component_hash": component_hash,
    }
    base_point_certificate["base_point_hash"] = sha(base_point_certificate)
    engine_domain = {
        "schema": _domain.SCHEMA,
        "variables": list(symbols),
        "predicate": copy.deepcopy(canonical_domain),
    }

    children = []
    for index, variable in enumerate(variable_order):
        symbol = by_name[variable]
        try:
            derivative_lhs, derivative_rhs = sympy.diff(lhs, symbol), sympy.diff(rhs, symbol)
        except Exception:
            _fail(FAILURE["partial"])
        if not _exact_finite_real(derivative_lhs) or \
                not _exact_finite_real(derivative_rhs):
            _fail(FAILURE["partial"])
        derivative_claim = {
            "lhs": str(derivative_lhs),
            "rhs": str(derivative_rhs),
            "symbols": list(symbols),
            "scope": scope,
            "assumptions": list(assumptions),
        }
        derivative_claim_hash = sha(derivative_claim)
        context_binding = _child_context_binding(
            parent_hash,
            variable_order_manifest["variable_order_hash"],
            index,
            variable,
            domain_certificate["domain_certificate_hash"],
            assumptions,
            scope,
            derivative_claim_hash,
        )
        raw_proof = _child_certificate(derivative_lhs, derivative_rhs, symbols)
        if raw_proof is None:
            _fail(FAILURE["partial"])
        proof = _bound_exact_child_certificate(raw_proof, context_binding)
        children.append({
            "order_index": index,
            "differentiation_variable": variable,
            "derivative_kind": "partial_derivative",
            "lhs": str(derivative_lhs),
            "rhs": str(derivative_rhs),
            "derivative_claim_hash": derivative_claim_hash,
            "symbols": list(symbols),
            "scope": scope,
            "assumptions": list(assumptions),
            "parent_claim_hash": parent_hash,
            "variable_order_hash": variable_order_manifest["variable_order_hash"],
            "base_point_hash": base_point_certificate["base_point_hash"],
            "domain_certificate_hash": domain_certificate["domain_certificate_hash"],
            "domain_obligation_graph_hash": graph["graph_hash"],
            "child_context_binding": context_binding,
            "child_context_binding_hash": sha(context_binding),
            "proof_certificate": proof,
            "proof_certificate_hash": _artifact_hash(proof),
            "engine_domain": copy.deepcopy(engine_domain),
        })

    return {
        "kind": CERTIFICATE_KIND,
        "certificate_version": CERTIFICATE_VERSION,
        "real_domain": True,
        "parent_claim_hash": parent_hash,
        "symbols": list(symbols),
        "scope": scope,
        "assumptions": list(assumptions),
        "request_manifest": copy.deepcopy(manifest),
        "variable_order_manifest": variable_order_manifest,
        "base_point_certificate": base_point_certificate,
        "connected_domain_certificate": domain_certificate,
        "domain_obligation_graph": graph,
        "domain_obligation_graph_hash": graph["graph_hash"],
        "domain_obligation_graph_version": graph["graph_version"],
        "prepared_children": children,
    }


def finalize_certificate(prepared, confirmations):
    """Bind exactly one independently confirmed result to each ordered partial."""
    children = prepared.get("prepared_children")
    if not isinstance(confirmations, list) or not isinstance(children, list) or \
            len(confirmations) != len(children):
        _fail(FAILURE["confirmation"])
    finalized_children = []
    for child, confirmation in zip(children, confirmations):
        bound = copy.deepcopy(child)
        bound["second_engine_confirmation"] = copy.deepcopy(confirmation)
        bound["child_hash"] = sha(bound)
        finalized_children.append(bound)
    coverage = [True for _ in children]
    coverage_manifest = {
        "variable_order_hash": prepared["variable_order_manifest"]["variable_order_hash"],
        "coverage_bitmap": coverage,
        "covered_variables": [child["differentiation_variable"] for child in children],
        "ordered_context_binding_hashes": [
            child["child_context_binding_hash"] for child in children],
    }
    coverage_manifest["coverage_hash"] = sha(coverage_manifest)
    graph = {
        "schema": GRADIENT_SCHEMA,
        "graph_version": "1.0",
        "parent_claim_hash": prepared["parent_claim_hash"],
        "variable_order_hash": prepared["variable_order_manifest"]["variable_order_hash"],
        "coverage_hash": coverage_manifest["coverage_hash"],
        "base_point_hash": prepared["base_point_certificate"]["base_point_hash"],
        "domain_certificate_hash": prepared["connected_domain_certificate"]["domain_certificate_hash"],
        "domain_obligation_graph_hash": prepared["domain_obligation_graph_hash"],
        "ordered_child_hashes": [child["child_hash"] for child in finalized_children],
        "children": finalized_children,
    }
    graph["gradient_graph_hash"] = sha(graph)
    certificate = {k: copy.deepcopy(v) for k, v in prepared.items() if k != "prepared_children"}
    certificate["coverage_manifest"] = coverage_manifest
    certificate["gradient_certificate_graph"] = graph
    certificate["independently_recheckable"] = True
    certificate["recheck_procedure"] = (
        "re-derive the ordered full gradient, exact base point, connected interval product, "
        "B4 graph, each exact child proof, every pinned B3 ZERO, and all hashes")
    certificate["artifact_hash"] = _artifact_hash(certificate)
    return certificate


def recheck(claim, lhs, rhs, certificate, timeout=20):
    """Rebuild the complete certificate; no stored mathematical assertion is trusted."""
    if not isinstance(certificate, dict):
        return {"ok": False, "detail": FAILURE["certificate"]}
    try:
        prepared = prepare_certificate(claim, lhs, rhs)
    except MultivariableT3Error as exc:
        return {"ok": False, "detail": exc.code}
    graph = certificate.get("gradient_certificate_graph")
    stored_children = graph.get("children") if isinstance(graph, dict) else None
    if not isinstance(stored_children, list) or len(stored_children) != len(prepared["prepared_children"]):
        return {"ok": False, "detail": FAILURE["certificate"]}
    confirmations = []
    for expected, stored in zip(prepared["prepared_children"], stored_children):
        required_fields = set(expected) | {"second_engine_confirmation", "child_hash"}
        if not isinstance(stored, dict) or set(stored) != required_fields:
            return {"ok": False, "detail": FAILURE["certificate"]}
        stored_without_confirmation = copy.deepcopy(stored)
        confirmation = stored_without_confirmation.pop("second_engine_confirmation")
        stored_without_confirmation.pop("child_hash")
        if stored_without_confirmation != expected or \
                not _strict_exact_child_matches(
                    expected["proof_certificate"],
                    stored["proof_certificate"]):
            return {"ok": False, "detail": FAILURE["certificate"]}
        payload = _child_b3_payload(expected)
        if not _strict_second_zero_confirmed(confirmation, payload):
            return {"ok": False, "detail": FAILURE["confirmation"]}
        fresh_confirmation = _run_pinned_b3_payload(payload, timeout)
        if not _strict_second_zero_confirmed(fresh_confirmation, payload) or \
                fresh_confirmation != confirmation:
            return {"ok": False, "detail": FAILURE["confirmation"]}
        confirmations.append(confirmation)
    try:
        expected_certificate = finalize_certificate(prepared, confirmations)
    except MultivariableT3Error as exc:
        return {"ok": False, "detail": exc.code}
    if certificate != expected_certificate or certificate.get("artifact_hash") != _artifact_hash(certificate):
        return {"ok": False, "detail": FAILURE["certificate"]}
    return {
        "ok": True,
        "detail": "re-verified full ordered gradient, exact base point, connected domain, "
                  "B4 obligations, and all B3/hash bindings",
    }


def recheck_certificate(claim, certificate, timeout=20):
    """Standalone B5 recheck entry point used by the existing controller audit surface."""
    if not isinstance(certificate, dict) or certificate.get("kind") != CERTIFICATE_KIND:
        return {"ok": False, "detail": FAILURE["certificate"]}
    symbols = claim.get("symbols") if isinstance(claim, dict) else None
    if not isinstance(symbols, list):
        return {"ok": False, "detail": FAILURE["request"]}
    try:
        lhs = _validate_and_parse_b5(claim["lhs"], symbols, real=True)
        rhs = _validate_and_parse_b5(claim["rhs"], symbols, real=True)
    except Exception:
        return {"ok": False, "detail": FAILURE["request"]}
    return recheck(claim, lhs, rhs, certificate, timeout)


def verify_request(request, timeout=20):
    """Issue B5 evidence without altering the immutable B1-B4 verifier modules."""
    if not isinstance(request, dict) or request.get("operation") != "multivariable_t3_verify" or \
            request.get("contract_version") != "1.0" or \
            request.get("verification_mode") != "symbolic_only":
        return _blocked_result(request, FAILURE["request"], [], 1)
    blob = json.dumps(request)
    if any(field in blob for field in FORBIDDEN):
        return _blocked_result(request, "BENCHMARK_METADATA_NOT_ALLOWED", [], 1)
    claim = request.get("claim")
    symbols = claim.get("symbols") if isinstance(claim, dict) else None
    if not isinstance(symbols, list) or len(symbols) < 2 or len(symbols) > 40:
        return _blocked_result(request, FAILURE["variables"], [], 1)
    try:
        lhs = _validate_and_parse_b5(claim["lhs"], symbols, real=True)
        rhs = _validate_and_parse_b5(claim["rhs"], symbols, real=True)
        prepared = prepare_certificate(claim, lhs, rhs)
    except MultivariableT3Error as exc:
        return _blocked_result(request, exc.code, [], 1)
    except Exception:
        return _blocked_result(request, FAILURE["request"], [], 1)

    confirmations = []
    for child in prepared["prepared_children"]:
        payload = _child_b3_payload(child)
        second = _run_pinned_b3_payload(payload, timeout)
        confirmations.append(second)
        if second.get("verdict") == "NONZERO":
            return _blocked_result(
                request, "MULTIVARIABLE_T3_PARTIAL_NONZERO", confirmations, 1)
        if not _strict_second_zero_confirmed(second, payload):
            return _blocked_result(request, FAILURE["confirmation"], confirmations, 1)
    try:
        certificate = finalize_certificate(prepared, confirmations)
    except MultivariableT3Error as exc:
        return _blocked_result(request, exc.code, confirmations, 1)
    replay = recheck(claim, lhs, rhs, certificate, timeout)
    if replay.get("ok") is not True:
        return _blocked_result(request, FAILURE["certificate"], confirmations, 1)
    return _result(
        request,
        {
            "verdict": "VERIFIED_BY_MULTIVARIABLE_DERIVATIVE_AND_BASE_POINT",
            "evidence_level": 3,
            "certificate": certificate,
        },
        {
            "verdict": "NOT_USED_FOR_PROOF",
            "second_engine_partial_confirmations": confirmations,
        },
        "VERIFIED_BY_MULTIVARIABLE_DERIVATIVE_AND_BASE_POINT",
        3,
        "FULL_GRADIENT_AND_BASE_POINT_DECISIVE",
        [f"valid only on the explicitly certified connected domain: "
         f"{certificate['connected_domain_certificate']['predicate']}"],
        0,
    )


def _blocked_result(request, failure_code, confirmations, exit_code):
    return _result(
        request,
        {
            "verdict": "MULTIVARIABLE_T3_BLOCKED",
            "evidence_level": 0,
            "certificate": None,
            "failure_code": failure_code,
        },
        {
            "verdict": "NO_EVIDENCE_UPGRADE",
            "second_engine_partial_confirmations": confirmations,
        },
        "MULTIVARIABLE_T3_BLOCKED",
        0,
        "EXPLICIT_MULTIVARIABLE_T3_FAIL_CLOSED",
        [failure_code],
        exit_code,
    )


def _result(request, symbolic, numerical, combined, level, relation, unresolved, exit_code):
    result = {
        "operation": "multivariable_t3_verify",
        "contract_version": "1.0",
        "request_hash": sha(request),
        "symbolic_claim_verifier": symbolic,
        "numerical_geobasis_verifier": numerical,
        "oracle_relation": relation,
        "combined_verdict": combined,
        "combined_evidence_level": level,
        "scope": (request.get("claim") or {}).get("scope")
        if isinstance(request, dict) else None,
        "unresolved_obligations": unresolved,
        "provenance": {
            "repository_commit": git_head(Path(__file__).resolve().parents[3]),
            "adapter_version": "multivariable-t3-verify-1.0",
            "symbolic_verifier": "bounded full-gradient derivative/base-point certificate",
            "numerical_verifier": None,
            "input_contract_version": "1.0",
            "output_contract_version": "1.0",
            "subresult_hashes": {"symbolic": sha(symbolic)},
            "runtime_environment": {
                "python": platform.python_version(),
                "sympy": sympy.__version__,
                "platform": platform.platform(),
            },
            "replay_classification": "VERDICT_REPRODUCIBLE (B5 exact certificate replay)",
        },
    }
    out_dir = Path(os.environ.get("VIPER_OUTPUT_DIR", tempfile.gettempdir())) / \
        "viper_multivariable_t3_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(result, temporary)
    temporary.close()
    artifact_hash = sha(Path(temporary.name).read_bytes())
    final = out_dir / "last_result.json"
    os.replace(temporary.name, final)
    result["replay_artifact"] = {"path": str(final), "sha256": artifact_hash}
    return result, exit_code
