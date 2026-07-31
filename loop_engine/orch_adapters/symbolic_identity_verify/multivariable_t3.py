"""B5 bounded multivariable gradient/base-point composite certificates.

This is deliberately not a general multivariable theorem prover.  It admits only finite
Cartesian products of open exact-rational intervals and real lines, reconstructs every
partial derivative in an explicit variable order, and requires an existing exact child
certificate, pinned B3 ZERO evidence, and an independently replayable B4 obligation graph
for every child.
"""
from __future__ import annotations

import copy
import json
from fractions import Fraction

import sympy

from loop_engine.orch_adapters._symbolic_safe_parse import AdapterError, sha, validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as _b2
from loop_engine.orch_adapters.symbolic_identity_verify import core as _core
from loop_engine.orch_adapters.symbolic_identity_verify import domain_obligations as _b4


_PINNED_SECOND_ENGINE_PAYLOAD = _core._second_engine_payload
_PINNED_SECOND_ZERO_CONFIRMED = _core._second_zero_confirmed


CERTIFICATE_KIND = "multivariable_gradient_base_point_composite"
CERTIFICATE_VERSION = "1.0"
THEOREM_PROFILE = "open_cartesian_gradient_base_point_v1"
GRAPH_BUNDLE_SCHEMA = "viper.b5_gradient_domain_obligation_bundle.v1"
RECHECK_PROCEDURE = (
    "re-parse the raw parent, normalize the open Cartesian domain, reconstruct the exact "
    "base point and every ordered partial derivative, replay every exact child certificate "
    "and pinned B3 ZERO, rebuild every embedded B4 graph, and recompute gradient coverage"
)

_ENTIRE_REAL_FUNCTIONS = {
    sympy.sin, sympy.cos, sympy.exp, sympy.sinh, sympy.cosh, sympy.tanh, sympy.atan,
}

_CERTIFICATE_FIELDS = {
    "kind", "certificate_version", "theorem_profile", "parent_claim", "parent_claim_hash",
    "ordered_variables", "variable_order_hash", "normalized_domain", "domain_hash",
    "scope", "scope_hash", "assumptions", "assumptions_hash", "base_point_certificate",
    "derivative_children", "differentiability_obligations", "domain_obligation_graph",
    "domain_obligation_graph_hash", "coverage", "coverage_hash", "coverage_complete",
    "independently_recheckable", "recheck_procedure", "artifact_hash",
}
_CHILD_FIELDS = {
    "variable", "ordered_variables", "variable_order_hash", "parent_claim_hash", "scope",
    "scope_hash", "assumptions", "assumptions_hash", "normalized_domain", "domain_hash",
    "derivative_claim", "derivative_claim_hash", "exact_certificate",
    "exact_certificate_hash", "second_engine", "second_engine_hash", "child_hash",
}
_BASE_FIELDS = {
    "point", "lhs_value", "rhs_value", "parent_claim_hash", "domain_hash", "base_point_hash",
}
_BUNDLE_FIELDS = {
    "schema", "version", "parent_claim_hash", "domain_hash", "assumptions_hash",
    "parent_graph", "child_graphs", "graph_hash",
}


def _artifact_hash(value):
    body = copy.deepcopy(value)
    body.pop("artifact_hash", None)
    return sha(body)


def _body_hash(value, hash_field):
    body = copy.deepcopy(value)
    body.pop(hash_field, None)
    return sha(body)


def _fraction_text(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _normalize_domain(domain, variables):
    if not isinstance(domain, dict):
        raise AdapterError("B5_UNSUPPORTED_DOMAIN")
    predicate = domain.get("predicate") if domain.get("schema") == _b2.SCHEMA else domain
    analysis = _b2.analyze_predicate(predicate, list(variables))
    if analysis.get("status") == "EMPTY":
        raise AdapterError("B5_EMPTY_DOMAIN")
    if analysis.get("status") != "CONNECTED":
        raise AdapterError("B5_UNSUPPORTED_DOMAIN")
    intervals = analysis["intervals"]
    for variable in variables:
        interval = intervals[variable]
        if interval["lower_closed"] or interval["upper_closed"]:
            raise AdapterError("B5_CLOSED_BOUNDARY_UNSUPPORTED")
    normalized = {
        "schema": _b2.SCHEMA,
        "profile": _b2.PROFILE,
        "variables": list(variables),
        "predicate": analysis["predicate"],
    }
    return normalized, intervals


def _base_point(intervals, variables):
    point = {}
    for variable in variables:
        interval = intervals[variable]
        lower = None if interval["lower"] == "-inf" else Fraction(interval["lower"])
        upper = None if interval["upper"] == "+inf" else Fraction(interval["upper"])
        if lower is None and upper is None:
            value = Fraction(0)
        elif lower is None:
            value = upper - 1
        elif upper is None:
            value = lower + 1
        else:
            value = (lower + upper) / 2
        if lower is not None and not value > lower:
            raise AdapterError("B5_BASE_POINT_OUTSIDE_DOMAIN")
        if upper is not None and not value < upper:
            raise AdapterError("B5_BASE_POINT_OUTSIDE_DOMAIN")
        point[variable] = _fraction_text(value)
    return point


def _structurally_differentiable(expression):
    if expression.is_Number or expression.is_Symbol:
        return True
    if isinstance(expression, (sympy.Add, sympy.Mul)):
        return all(_structurally_differentiable(arg) for arg in expression.args)
    if isinstance(expression, sympy.Pow):
        exponent = expression.exp
        return bool(exponent.is_Integer and exponent >= 0 and
                    _structurally_differentiable(expression.base))
    if expression.func in _ENTIRE_REAL_FUNCTIONS:
        return all(_structurally_differentiable(arg) for arg in expression.args)
    return False


def _exact_finite_real(expression):
    return (
        isinstance(expression, sympy.Basic)
        and not expression.atoms(sympy.Float)
        and not expression.has(sympy.oo, -sympy.oo, sympy.zoo, sympy.nan)
        and expression.is_real is True
        and expression.is_finite is True
    )


def _parent_context(claim):
    required = {"lhs", "rhs", "symbols", "scope", "assumptions", "domain"}
    if not isinstance(claim, dict) or not required.issubset(claim):
        raise AdapterError("B5_SCHEMA_VALIDATION_FAILED")
    variables = claim["symbols"]
    if not isinstance(variables, list) or len(variables) < 2 or len(set(variables)) != len(variables):
        raise AdapterError("B5_ORDERED_VARIABLES_REQUIRED")
    if not all(isinstance(variable, str) and variable for variable in variables):
        raise AdapterError("B5_ORDERED_VARIABLES_REQUIRED")
    assumptions = claim["assumptions"]
    if not isinstance(assumptions, list) or not assumptions:
        raise AdapterError("B5_ASSUMPTIONS_REQUIRED")
    scope = claim["scope"]
    if scope not in {"real_scalars", "reals", "real", "R", "s"}:
        raise AdapterError("B5_REAL_SCOPE_REQUIRED")
    lhs = validate_and_parse(claim["lhs"], variables, real=True)
    rhs = validate_and_parse(claim["rhs"], variables, real=True)
    if not _exact_finite_real(lhs) or not _exact_finite_real(rhs):
        raise AdapterError("B5_EXACT_FINITE_REAL_REQUIRED")
    if not _structurally_differentiable(lhs) or not _structurally_differentiable(rhs):
        raise AdapterError("B5_DIFFERENTIABILITY_UNSUPPORTED")
    normalized_domain, intervals = _normalize_domain(claim["domain"], variables)
    parent_claim = {
        "lhs": claim["lhs"],
        "rhs": claim["rhs"],
        "symbols": list(variables),
        "scope": scope,
        "assumptions": copy.deepcopy(assumptions),
    }
    variable_order_hash = sha({"ordered_variables": list(variables)})
    domain_hash = sha(normalized_domain)
    scope_hash = sha(scope)
    assumptions_hash = sha(list(assumptions))
    parent_claim_hash = sha({
        "kind": CERTIFICATE_KIND,
        "certificate_version": CERTIFICATE_VERSION,
        "parent_claim": parent_claim,
        "variable_order_hash": variable_order_hash,
        "normalized_domain": normalized_domain,
        "domain_hash": domain_hash,
        "scope_hash": scope_hash,
        "assumptions_hash": assumptions_hash,
    })
    return {
        "lhs": lhs,
        "rhs": rhs,
        "variables": list(variables),
        "assumptions": copy.deepcopy(assumptions),
        "scope": scope,
        "parent_claim": parent_claim,
        "parent_claim_hash": parent_claim_hash,
        "variable_order_hash": variable_order_hash,
        "normalized_domain": normalized_domain,
        "domain_hash": domain_hash,
        "scope_hash": scope_hash,
        "assumptions_hash": assumptions_hash,
        "intervals": intervals,
    }


def _differentiability_obligations(context):
    obligations = []
    for side in ("lhs", "rhs"):
        for variable in context["variables"]:
            body = {
                "side": side,
                "variable": variable,
                "source_expression": context["parent_claim"][side],
                "parent_claim_hash": context["parent_claim_hash"],
                "domain_hash": context["domain_hash"],
                "status": "PROVED",
                "proof_route": "structural_real_entire_expression_v1",
            }
            body["obligation_hash"] = sha(body)
            obligations.append(body)
    return obligations


def _exact_child_certificate(lhs, rhs, variables):
    from loop_engine.orch_adapters.symbolic_identity_verify import recheck as _rc

    claim = {"lhs": str(lhs), "rhs": str(rhs), "symbols": list(variables)}
    for builder in (
            _rc.build_polynomial_certificate,
            _rc.build_trig_cofactor_certificate,
            _rc.build_exp_polynomial_certificate):
        try:
            certificate = builder(lhs, rhs, variables)
        except Exception:
            certificate = None
        if certificate is None:
            continue
        # The frozen T1 builder emits an empty cofactor list for the valid P=0 case,
        # while its independent rechecker requires one cofactor per ideal generator.
        # Supplying explicit zero cofactors makes that existing proof object replayable.
        if certificate.get("kind") == "trig_ideal_cofactor" and \
                certificate.get("numerator_polynomial") == "0" and \
                not certificate.get("cofactors"):
            certificate["cofactors"] = [
                "0" for _ in certificate.get("constraint_polynomials", [])]
        if _rc.recheck(claim, certificate).get("ok"):
            return certificate
    return None


def _recheck_exact_child(derivative_claim, certificate):
    if not isinstance(certificate, dict):
        return False
    from loop_engine.orch_adapters.symbolic_identity_verify import recheck as _rc
    return bool(_rc.recheck(derivative_claim, certificate).get("ok"))


def _strict_second_zero_confirmed(second, payload, validator=None):
    """Replay both the pinned semantic profile and the raw process/JSON transport."""
    checker = validator or _PINNED_SECOND_ZERO_CONFIRMED
    if not checker(second, payload) or not isinstance(second, dict):
        return False
    if second.get("stdout") != "True" or second.get("exit_status") != 0 or \
            second.get("process_exit_status") != 0:
        return False
    raw = second.get("process_stdout")
    if not isinstance(raw, str):
        return False
    try:
        parsed = json.loads(raw)
    except Exception:
        return False
    transport = {"route", "process_stdout", "process_stderr", "process_exit_status"}
    return isinstance(parsed, dict) and parsed == {
        key: value for key, value in second.items() if key not in transport
    }


def _derivative_claim(context, variable):
    symbol_by_name = {str(symbol): symbol for symbol in
                      (context["lhs"].free_symbols | context["rhs"].free_symbols)}
    symbol = symbol_by_name.get(variable, sympy.Symbol(variable, real=True))
    derivative_lhs = sympy.diff(context["lhs"], symbol)
    derivative_rhs = sympy.diff(context["rhs"], symbol)
    if not _exact_finite_real(derivative_lhs) or not _exact_finite_real(derivative_rhs):
        raise AdapterError("B5_EXACT_FINITE_REAL_DERIVATIVE_REQUIRED")
    return derivative_lhs, derivative_rhs, {
        "lhs": str(derivative_lhs),
        "rhs": str(derivative_rhs),
        "symbols": list(context["variables"]),
    }


def _derivative_claim_hash(context, variable, derivative_claim):
    return sha({
        "parent_claim_hash": context["parent_claim_hash"],
        "variable": variable,
        "ordered_variables": context["variables"],
        "variable_order_hash": context["variable_order_hash"],
        "scope_hash": context["scope_hash"],
        "assumptions_hash": context["assumptions_hash"],
        "domain_hash": context["domain_hash"],
        "derivative_claim": derivative_claim,
    })


def _base_point_certificate(context):
    point = _base_point(context["intervals"], context["variables"])
    substitutions = {
        sympy.Symbol(variable, real=True): sympy.Rational(value)
        for variable, value in point.items()
    }
    lhs_value = context["lhs"].subs(substitutions)
    rhs_value = context["rhs"].subs(substitutions)
    if lhs_value.free_symbols or rhs_value.free_symbols or \
            not _exact_finite_real(lhs_value) or not _exact_finite_real(rhs_value):
        raise AdapterError("B5_EXACT_FINITE_REAL_BASE_POINT_REQUIRED")
    if lhs_value != rhs_value:
        raise AdapterError("B5_BASE_POINT_EQUALITY_FAILED")
    base = {
        "point": point,
        "lhs_value": str(lhs_value),
        "rhs_value": str(rhs_value),
        "parent_claim_hash": context["parent_claim_hash"],
        "domain_hash": context["domain_hash"],
    }
    base["base_point_hash"] = sha(base)
    return base


def build_certificate(
        claim,
        timeout,
        second_engine_runner,
        second_engine_payload_builder,
        second_engine_validator):
    """Build a complete B5 certificate or return None without partial promotion."""
    try:
        context = _parent_context(claim)
        base = _base_point_certificate(context)
        differentiability = _differentiability_obligations(context)
        children = []
        child_graphs = []
        b4_domain = {"predicate": context["normalized_domain"]["predicate"]}
        parent_graph_claim = {
            "lhs": context["parent_claim"]["lhs"],
            "rhs": context["parent_claim"]["rhs"],
            "symbols": list(context["variables"]),
            "scope": context["scope"],
        }
        parent_graph = _b4.build_obligation_graph(
            parent_graph_claim, b4_domain, context["assumptions"])
        if not _b4.recheck_obligation_graph(
                parent_graph_claim, b4_domain, context["assumptions"],
                parent_graph).get("ok"):
            return None
        for variable in context["variables"]:
            derivative_lhs, derivative_rhs, derivative_claim = _derivative_claim(context, variable)
            exact_certificate = _exact_child_certificate(
                derivative_lhs, derivative_rhs, context["variables"])
            if exact_certificate is None:
                return None
            derivative_hash = _derivative_claim_hash(
                context, variable, derivative_claim)
            payload = second_engine_payload_builder(
                derivative_claim["lhs"], derivative_claim["rhs"], context["variables"],
                context["scope"], context["normalized_domain"], context["assumptions"])
            second = second_engine_runner(
                derivative_claim["lhs"], derivative_claim["rhs"], context["variables"],
                context["scope"], context["normalized_domain"], context["assumptions"], timeout)
            if not _strict_second_zero_confirmed(
                    second, payload, second_engine_validator):
                return None
            graph_claim = {
                "lhs": derivative_claim["lhs"],
                "rhs": derivative_claim["rhs"],
                "symbols": list(context["variables"]),
                "scope": context["scope"],
            }
            graph = _b4.build_obligation_graph(
                graph_claim, b4_domain, context["assumptions"])
            if not _b4.recheck_obligation_graph(
                    graph_claim, b4_domain, context["assumptions"], graph).get("ok"):
                return None
            child = {
                "variable": variable,
                "ordered_variables": list(context["variables"]),
                "variable_order_hash": context["variable_order_hash"],
                "parent_claim_hash": context["parent_claim_hash"],
                "scope": context["scope"],
                "scope_hash": context["scope_hash"],
                "assumptions": copy.deepcopy(context["assumptions"]),
                "assumptions_hash": context["assumptions_hash"],
                "normalized_domain": copy.deepcopy(context["normalized_domain"]),
                "domain_hash": context["domain_hash"],
                "derivative_claim": derivative_claim,
                "derivative_claim_hash": derivative_hash,
                "exact_certificate": exact_certificate,
                "exact_certificate_hash": sha(exact_certificate),
                "second_engine": copy.deepcopy(second),
                "second_engine_hash": sha(second),
            }
            child["child_hash"] = sha(child)
            children.append(child)
            child_graphs.append({
                "variable": variable,
                "derivative_claim_hash": derivative_hash,
                "graph": graph,
            })
        graph_bundle = {
            "schema": GRAPH_BUNDLE_SCHEMA,
            "version": "1.0",
            "parent_claim_hash": context["parent_claim_hash"],
            "domain_hash": context["domain_hash"],
            "assumptions_hash": context["assumptions_hash"],
            "parent_graph": parent_graph,
            "child_graphs": child_graphs,
        }
        graph_bundle["graph_hash"] = sha(graph_bundle)
        coverage = [
            {"variable": child["variable"],
             "derivative_claim_hash": child["derivative_claim_hash"]}
            for child in children
        ]
        certificate = {
            "kind": CERTIFICATE_KIND,
            "certificate_version": CERTIFICATE_VERSION,
            "theorem_profile": THEOREM_PROFILE,
            "parent_claim": copy.deepcopy(context["parent_claim"]),
            "parent_claim_hash": context["parent_claim_hash"],
            "ordered_variables": list(context["variables"]),
            "variable_order_hash": context["variable_order_hash"],
            "normalized_domain": copy.deepcopy(context["normalized_domain"]),
            "domain_hash": context["domain_hash"],
            "scope": context["scope"],
            "scope_hash": context["scope_hash"],
            "assumptions": copy.deepcopy(context["assumptions"]),
            "assumptions_hash": context["assumptions_hash"],
            "base_point_certificate": base,
            "derivative_children": children,
            "differentiability_obligations": differentiability,
            "domain_obligation_graph": graph_bundle,
            "domain_obligation_graph_hash": graph_bundle["graph_hash"],
            "coverage": coverage,
            "coverage_hash": sha(coverage),
            "coverage_complete": len(coverage) == len(context["variables"]),
            "independently_recheckable": True,
            "recheck_procedure": RECHECK_PROCEDURE,
        }
        certificate["artifact_hash"] = _artifact_hash(certificate)
        if not recheck(claim, certificate).get("ok"):
            return None
        return certificate
    except (AdapterError, Exception):
        return None


def recheck(claim, certificate):
    """Reconstruct every B5 obligation; never trust builder status or coverage fields."""
    if not isinstance(certificate, dict) or set(certificate) != _CERTIFICATE_FIELDS:
        return {"ok": False, "detail": "B5 certificate schema mismatch"}
    if certificate.get("kind") != CERTIFICATE_KIND or \
            certificate.get("certificate_version") != CERTIFICATE_VERSION or \
            certificate.get("theorem_profile") != THEOREM_PROFILE:
        return {"ok": False, "detail": "B5 certificate kind or version mismatch"}
    if certificate.get("artifact_hash") != _artifact_hash(certificate):
        return {"ok": False, "detail": "B5 artifact hash mismatch"}
    try:
        context = _parent_context(claim)
        expected_base = _base_point_certificate(context)
        expected_differentiability = _differentiability_obligations(context)
    except (AdapterError, Exception) as exc:
        return {"ok": False, "detail": f"B5 parent reconstruction failed: {getattr(exc, 'code', type(exc).__name__)}"}
    expected_parent_fields = {
        "parent_claim": context["parent_claim"],
        "parent_claim_hash": context["parent_claim_hash"],
        "ordered_variables": context["variables"],
        "variable_order_hash": context["variable_order_hash"],
        "normalized_domain": context["normalized_domain"],
        "domain_hash": context["domain_hash"],
        "scope": context["scope"],
        "scope_hash": context["scope_hash"],
        "assumptions": context["assumptions"],
        "assumptions_hash": context["assumptions_hash"],
    }
    if any(certificate.get(key) != value for key, value in expected_parent_fields.items()):
        return {"ok": False, "detail": "B5 parent, order, domain, scope, or assumption binding mismatch"}
    base = certificate.get("base_point_certificate")
    if not isinstance(base, dict) or set(base) != _BASE_FIELDS or base != expected_base:
        return {"ok": False, "detail": "B5 base-point equality or membership mismatch"}
    if certificate.get("differentiability_obligations") != expected_differentiability:
        return {"ok": False, "detail": "B5 differentiability obligations are incomplete or stale"}
    children = certificate.get("derivative_children")
    if not isinstance(children, list) or len(children) != len(context["variables"]):
        return {"ok": False, "detail": "B5 gradient child count is incomplete"}
    expected_coverage = []
    b4_domain = {"predicate": context["normalized_domain"]["predicate"]}
    expected_graph_bindings = []
    for index, variable in enumerate(context["variables"]):
        child = children[index]
        if not isinstance(child, dict) or set(child) != _CHILD_FIELDS:
            return {"ok": False, "detail": "B5 derivative child schema mismatch"}
        derivative_lhs, derivative_rhs, derivative_claim = _derivative_claim(context, variable)
        derivative_hash = _derivative_claim_hash(context, variable, derivative_claim)
        expected_bindings = {
            "variable": variable,
            "ordered_variables": context["variables"],
            "variable_order_hash": context["variable_order_hash"],
            "parent_claim_hash": context["parent_claim_hash"],
            "scope": context["scope"],
            "scope_hash": context["scope_hash"],
            "assumptions": context["assumptions"],
            "assumptions_hash": context["assumptions_hash"],
            "normalized_domain": context["normalized_domain"],
            "domain_hash": context["domain_hash"],
            "derivative_claim": derivative_claim,
            "derivative_claim_hash": derivative_hash,
        }
        if any(child.get(key) != value for key, value in expected_bindings.items()):
            return {"ok": False, "detail": "B5 derivative child does not match the ordered partial"}
        if child.get("exact_certificate_hash") != sha(child.get("exact_certificate")):
            return {"ok": False, "detail": "B5 exact child certificate hash mismatch"}
        if not _recheck_exact_child(derivative_claim, child.get("exact_certificate")):
            return {"ok": False, "detail": "B5 exact derivative child replay failed"}
        payload = _PINNED_SECOND_ENGINE_PAYLOAD(
            derivative_claim["lhs"], derivative_claim["rhs"], context["variables"],
            context["scope"], context["normalized_domain"], context["assumptions"])
        if child.get("second_engine_hash") != sha(child.get("second_engine")) or \
                not _strict_second_zero_confirmed(child.get("second_engine"), payload):
            return {"ok": False, "detail": "B5 pinned B3 derivative confirmation failed"}
        if child.get("child_hash") != _body_hash(child, "child_hash"):
            return {"ok": False, "detail": "B5 derivative child hash mismatch"}
        expected_coverage.append({
            "variable": variable,
            "derivative_claim_hash": derivative_hash,
        })
        expected_graph_bindings.append((variable, derivative_hash, derivative_claim))
    bundle = certificate.get("domain_obligation_graph")
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_FIELDS or \
            bundle.get("schema") != GRAPH_BUNDLE_SCHEMA or bundle.get("version") != "1.0":
        return {"ok": False, "detail": "B5 B4 graph bundle schema mismatch"}
    if bundle.get("graph_hash") != _body_hash(bundle, "graph_hash") or \
            certificate.get("domain_obligation_graph_hash") != bundle.get("graph_hash"):
        return {"ok": False, "detail": "B5 B4 graph bundle hash mismatch"}
    for key, value in (
        ("parent_claim_hash", context["parent_claim_hash"]),
        ("domain_hash", context["domain_hash"]),
        ("assumptions_hash", context["assumptions_hash"]),
    ):
        if bundle.get(key) != value:
            return {"ok": False, "detail": "B5 B4 graph bundle parent binding mismatch"}
    graph_entries = bundle.get("child_graphs")
    parent_graph_claim = {
        "lhs": context["parent_claim"]["lhs"],
        "rhs": context["parent_claim"]["rhs"],
        "symbols": list(context["variables"]),
        "scope": context["scope"],
    }
    if not _b4.recheck_obligation_graph(
            parent_graph_claim, b4_domain, context["assumptions"],
            bundle.get("parent_graph")).get("ok"):
        return {"ok": False, "detail": "B5 parent-source B4 graph replay failed"}
    if not isinstance(graph_entries, list) or len(graph_entries) != len(expected_graph_bindings):
        return {"ok": False, "detail": "B5 B4 child graph coverage is incomplete"}
    for entry, (variable, derivative_hash, derivative_claim) in zip(
            graph_entries, expected_graph_bindings):
        if not isinstance(entry, dict) or set(entry) != {
                "variable", "derivative_claim_hash", "graph"} or \
                entry.get("variable") != variable or \
                entry.get("derivative_claim_hash") != derivative_hash:
            return {"ok": False, "detail": "B5 B4 child graph ordering or claim binding mismatch"}
        graph_claim = {
            "lhs": derivative_claim["lhs"],
            "rhs": derivative_claim["rhs"],
            "symbols": list(context["variables"]),
            "scope": context["scope"],
        }
        if not _b4.recheck_obligation_graph(
                graph_claim, b4_domain, context["assumptions"], entry.get("graph")).get("ok"):
            return {"ok": False, "detail": "B5 embedded B4 graph replay failed"}
    if certificate.get("coverage") != expected_coverage or \
            certificate.get("coverage_hash") != sha(expected_coverage) or \
            certificate.get("coverage_complete") is not True:
        return {"ok": False, "detail": "B5 full-gradient coverage does not reconstruct"}
    if certificate.get("independently_recheckable") is not True or \
            certificate.get("recheck_procedure") != RECHECK_PROCEDURE:
        return {"ok": False, "detail": "B5 recheck metadata mismatch"}
    return {
        "ok": True,
        "detail": "re-verified complete multivariable gradient and exact base point on an open Cartesian product",
    }
