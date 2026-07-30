"""B2's deliberately small, fail-closed kernel for connected real subdomains.

This is not a general domain solver.  It admits only independent real intervals and
their finite intersections, so that containment and connectedness are computed rather
than asserted by the caller.  In particular, a free-text domain, union, float bound, or
unknown Boolean construct never becomes a structured domain by fallback.
"""
from __future__ import annotations

import copy
from fractions import Fraction

import sympy

from loop_engine.orch_adapters._symbolic_safe_parse import AdapterError, sha, validate_and_parse

SCHEMA = "viper.connected_subdomain.v1"
PROFILE = "real_connected_subdomain_kernel_v1"
CERTIFICATE_KIND = "conditional_identity_on_connected_subdomain"
CERTIFICATE_VERSION = "1.0"


class DomainError(AdapterError):
    pass


def _fail(code):
    raise DomainError(code)


def _rational(value, *, infinity=False):
    if infinity and value in {"-inf", "+inf"}:
        return value
    if not isinstance(value, str) or value in {"-inf", "+inf"}:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    try:
        number = Fraction(value)
    except (ValueError, ZeroDivisionError):
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    if "." in value or "e" in value.lower():
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    return str(number.numerator) if number.denominator == 1 else f"{number.numerator}/{number.denominator}"


def _bound_value(value):
    if value == "-inf":
        return None
    if value == "+inf":
        return None
    return Fraction(value)


def _interval(variable, lower="-inf", upper="+inf", lower_closed=False, upper_closed=False):
    return {"kind": "interval", "variable": variable, "lower": lower, "upper": upper,
            "lower_closed": bool(lower_closed), "upper_closed": bool(upper_closed)}


def _normal_interval(raw, variables):
    if not isinstance(raw, dict) or raw.get("kind") not in {"interval", "real_line", "comparison"}:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    kind = raw["kind"]
    variable = raw.get("variable") if kind != "comparison" else raw.get("left")
    if not isinstance(variable, str) or variable not in variables:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    if kind == "real_line":
        if set(raw) != {"kind", "variable"}:
            _fail("UNSUPPORTED_DOMAIN_PREDICATE")
        return _interval(variable)
    if kind == "comparison":
        if set(raw) != {"kind", "left", "operator", "right"}:
            _fail("UNSUPPORTED_DOMAIN_PREDICATE")
        right = _rational(raw.get("right"))
        operator = raw.get("operator")
        if operator == ">":
            return _interval(variable, lower=right, lower_closed=False)
        if operator == ">=":
            return _interval(variable, lower=right, lower_closed=True)
        if operator == "<":
            return _interval(variable, upper=right, upper_closed=False)
        if operator == "<=":
            return _interval(variable, upper=right, upper_closed=True)
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    required = {"kind", "variable", "lower", "upper", "lower_closed", "upper_closed"}
    if set(raw) != required or not isinstance(raw["lower_closed"], bool) or not isinstance(raw["upper_closed"], bool):
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    lower, upper = _rational(raw["lower"], infinity=True), _rational(raw["upper"], infinity=True)
    if lower == "+inf" or upper == "-inf":
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    if lower == "-inf" and raw["lower_closed"] or upper == "+inf" and raw["upper_closed"]:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    return _interval(variable, lower, upper, raw["lower_closed"], raw["upper_closed"])


def _intersect(a, b):
    """Exact intersection; returns None for the empty set."""
    assert a["variable"] == b["variable"]
    la, lb = _bound_value(a["lower"]), _bound_value(b["lower"])
    ua, ub = _bound_value(a["upper"]), _bound_value(b["upper"])
    if la is None or (lb is not None and lb > la):
        lower, lower_closed = b["lower"], b["lower_closed"]
    elif lb is None or la > lb:
        lower, lower_closed = a["lower"], a["lower_closed"]
    else:
        lower, lower_closed = a["lower"], a["lower_closed"] and b["lower_closed"]
    if ua is None or (ub is not None and ub < ua):
        upper, upper_closed = b["upper"], b["upper_closed"]
    elif ub is None or ua < ub:
        upper, upper_closed = a["upper"], a["upper_closed"]
    else:
        upper, upper_closed = a["upper"], a["upper_closed"] and b["upper_closed"]
    lv, uv = _bound_value(lower), _bound_value(upper)
    if lv is not None and uv is not None and (lv > uv or (lv == uv and not (lower_closed and upper_closed))):
        return None
    return _interval(a["variable"], lower, upper, lower_closed, upper_closed)


def _canonical_predicate(intervals, variables):
    terms = [intervals[v] for v in variables]
    if len(terms) == 1 and terms[0] == _interval(variables[0]):
        return {"kind": "real_line", "variable": variables[0]}
    return {"kind": "intersection", "terms": terms}


def analyze_predicate(predicate, variables):
    """Return canonical predicate and independently derived connectedness status."""
    if not isinstance(variables, list) or not variables or len(set(variables)) != len(variables) or \
            not all(isinstance(v, str) and v for v in variables):
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    intervals = {v: _interval(v) for v in variables}
    raw_terms = predicate.get("terms") if isinstance(predicate, dict) and predicate.get("kind") == "intersection" else [predicate]
    if not isinstance(raw_terms, list) or not raw_terms or len(raw_terms) > 64:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    for raw in raw_terms:
        item = _normal_interval(raw, variables)
        merged = _intersect(intervals[item["variable"]], item)
        if merged is None:
            return {"status": "EMPTY", "predicate": None, "intervals": None}
        intervals[item["variable"]] = merged
    return {"status": "CONNECTED", "predicate": _canonical_predicate(intervals, variables), "intervals": intervals}


def _subset(child, parent):
    for variable, c in child.items():
        p = parent[variable]
        cl, pl, cu, pu = _bound_value(c["lower"]), _bound_value(p["lower"]), _bound_value(c["upper"]), _bound_value(p["upper"])
        if pl is not None and (cl is None or cl < pl or (cl == pl and c["lower_closed"] and not p["lower_closed"])):
            return False
        if pu is not None and (cu is None or cu > pu or (cu == pu and c["upper_closed"] and not p["upper_closed"])):
            return False
    return True


def _same(a, b):
    return a == b


def _positive_on(interval, variable):
    if interval["variable"] != variable:
        return False
    lower = _bound_value(interval["lower"])
    return lower is not None and (lower > 0 or (lower == 0 and not interval["lower_closed"]))


def _claim_body(claim):
    required = {"lhs", "rhs", "symbols", "scope"}
    if not isinstance(claim, dict) or not required.issubset(claim) or not isinstance(claim["symbols"], list):
        _fail("SCHEMA_VALIDATION_FAILED")
    return {k: copy.deepcopy(claim[k]) for k in ("lhs", "rhs", "symbols", "scope")}


def _parent_claim(parent):
    body = _claim_body(parent)
    analysis = analyze_predicate(parent.get("domain"), body["symbols"])
    if analysis["status"] != "CONNECTED":
        _fail("UNSUPPORTED_CONNECTEDNESS_ANALYSIS" if analysis["status"] != "EMPTY" else "EMPTY_DOMAIN")
    return body, analysis


def _transformed_claim_hash(parent_claim_hash, source_body, source_variable, parameter_variable, transformed_body):
    return sha({"kind": "positive_exp_parameterization", "parent_claim_hash": parent_claim_hash,
                "source_claim_body_hash": sha(source_body), "source_variable": source_variable,
                "parameter_variable": parameter_variable, "transformed_claim": transformed_body})


def _validate_positive_exp_transformation(raw, parent_claim_hash, source_body):
    """Validate an actual substitution, not merely a descriptive mapping record."""
    required = {"kind", "certificate_version", "source_variable", "parameter_variable", "forward",
                "source_domain", "image_domain", "inverse", "monotone_injective", "surjective_onto_image",
                "parent_claim_hash", "transformed_claim", "transformed_claim_hash"}
    if not isinstance(raw, dict) or (set(raw) != required and set(raw) != required | {"artifact_hash"}) or \
            ("artifact_hash" in raw and raw["artifact_hash"] != sha({k: v for k, v in raw.items() if k != "artifact_hash"})) or \
            raw.get("kind") != "positive_exp_parameterization" or \
            raw.get("certificate_version") != "1.0" or raw.get("parent_claim_hash") != parent_claim_hash:
        _fail("UNSUPPORTED_TRANSFORMATION")
    source, parameter = raw.get("source_variable"), raw.get("parameter_variable")
    if source not in source_body["symbols"] or not isinstance(parameter, str) or not parameter or parameter in source_body["symbols"]:
        _fail("UNSUPPORTED_TRANSFORMATION")
    expected_image = _interval(source, "0", "+inf", False, False)
    if raw.get("forward") != f"exp({parameter})" or raw.get("inverse") != f"log({source})" or \
            raw.get("source_domain") != {"kind": "real_line", "variable": parameter} or \
            raw.get("image_domain") != expected_image or raw.get("monotone_injective") is not True or \
            raw.get("surjective_onto_image") is not True:
        _fail("UNSUPPORTED_TRANSFORMATION")
    transformed = _claim_body(raw.get("transformed_claim"))
    expected_symbols = [parameter if v == source else v for v in source_body["symbols"]]
    if transformed["symbols"] != expected_symbols or transformed["scope"] != source_body["scope"]:
        _fail("PARENT_CHILD_SEMANTICS_MISMATCH")
    try:
        source_lhs = validate_and_parse(source_body["lhs"], source_body["symbols"], real=True)
        source_rhs = validate_and_parse(source_body["rhs"], source_body["symbols"], real=True)
        target_lhs = validate_and_parse(transformed["lhs"], transformed["symbols"], real=True)
        target_rhs = validate_and_parse(transformed["rhs"], transformed["symbols"], real=True)
        source_symbol = next(s for s in source_lhs.free_symbols | source_rhs.free_symbols if str(s) == source)
        parameter_symbol = next(s for s in target_lhs.free_symbols | target_rhs.free_symbols if str(s) == parameter)
    except (AdapterError, StopIteration):
        _fail("UNSUPPORTED_TRANSFORMATION")
    if source_lhs.xreplace({source_symbol: sympy.exp(parameter_symbol)}) != target_lhs or \
            source_rhs.xreplace({source_symbol: sympy.exp(parameter_symbol)}) != target_rhs:
        _fail("PARENT_CHILD_SEMANTICS_MISMATCH")
    expected_hash = _transformed_claim_hash(parent_claim_hash, source_body, source, parameter, transformed)
    if raw.get("transformed_claim_hash") != expected_hash:
        _fail("CHILD_CLAIM_HASH_MISMATCH")
    cert = copy.deepcopy(raw)
    cert["artifact_hash"] = sha(cert)
    return cert


def prepare_log_product_claim(claim):
    """Validate the B2 request and return all hash-bound data except B3 confirmation."""
    if not isinstance(claim, dict) or "subdomain" not in claim or "parent_claim" not in claim:
        _fail("SCHEMA_VALIDATION_FAILED")
    body = _claim_body(claim)
    parent_body, parent = _parent_claim(claim["parent_claim"])
    if body != parent_body:
        _fail("PARENT_CHILD_SEMANTICS_MISMATCH")
    raw = claim["subdomain"]
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("variables") != body["symbols"]:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    allowed_subdomain_fields = {"schema", "parent_claim_hash", "variables", "predicate", "connected_component",
                                "definedness_obligations", "side_conditions", "scope_mapping", "transformation"}
    if set(raw) - allowed_subdomain_fields:
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    child = analyze_predicate(raw.get("predicate"), body["symbols"])
    if child["status"] == "EMPTY":
        _fail("EMPTY_DOMAIN")
    if child["status"] != "CONNECTED":
        _fail("UNSUPPORTED_CONNECTEDNESS_ANALYSIS")
    if not _subset(child["intervals"], parent["intervals"]):
        _fail("SUBDOMAIN_NOT_CONTAINED_IN_PARENT")
    scope_relation = "SAME_DOMAIN_AS_PARENT" if _same(child["intervals"], parent["intervals"]) else "STRICT_SUBDOMAIN_OF_PARENT"
    parent_hash = sha({"schema": SCHEMA, "claim": parent_body, "predicate": parent["predicate"], "profile": PROFILE})
    if raw.get("parent_claim_hash") != parent_hash:
        _fail("PARENT_CLAIM_HASH_MISMATCH")
    component = raw.get("connected_component")
    expected_component = {"kind": "positive_orthant", "variables": body["symbols"]} if all(
        _positive_on(child["intervals"][v], v) for v in body["symbols"]) else {"kind": "cartesian_product_intervals", "variables": body["symbols"]}
    if component != expected_component:
        _fail("UNSUPPORTED_CONNECTEDNESS_ANALYSIS")
    if raw.get("definedness_obligations", []) not in ([], None) or raw.get("side_conditions", []) not in ([], None) or not isinstance(raw.get("scope_mapping", {}), dict):
        _fail("UNSUPPORTED_DOMAIN_PREDICATE")
    transformation = raw.get("transformation")
    try:
        lhs = validate_and_parse(body["lhs"], body["symbols"], real=True)
        rhs = validate_and_parse(body["rhs"], body["symbols"], real=True)
    except AdapterError:
        raise
    if not (lhs.func == sympy.log and lhs.args and lhs.args[0].is_Mul and rhs.is_Add):
        _fail("UNSUPPORTED_CONDITIONAL_PROOF_ROUTE")
    factors = list(lhs.args[0].args)
    rhs_terms = list(rhs.args)
    if len(factors) != 2 or len(rhs_terms) != 2 or any(not x.is_Symbol for x in factors):
        _fail("UNSUPPORTED_CONDITIONAL_PROOF_ROUTE")
    if {str(x) for x in factors} != set(body["symbols"]) or len(body["symbols"]) != 2 or \
            {str(x.args[0]) for x in rhs_terms if x.func == sympy.log} != set(body["symbols"]) or any(x.func != sympy.log for x in rhs_terms):
        _fail("UNSUPPORTED_CONDITIONAL_PROOF_ROUTE")
    if not all(_positive_on(child["intervals"][v], v) for v in body["symbols"]):
        _fail("DEFINEDNESS_NOT_PROVED_ON_SUBDOMAIN")
    claim_body_hash = sha(body)
    transformation_cert = None if transformation in (None, {}) else _validate_positive_exp_transformation(
        transformation, parent_hash, body)
    normalized = {"schema": SCHEMA, "profile": PROFILE, "parent_claim_hash": parent_hash,
                  "claim_body_hash": claim_body_hash, "variables": body["symbols"],
                  "predicate": child["predicate"], "connected_component": expected_component,
                  "definedness_obligations": [{"kind": "strict_positive", "variable": v} for v in body["symbols"]],
                  "side_conditions": [f"{v} > 0" for v in body["symbols"]],
                  "transformation": transformation_cert, "scope_mapping": copy.deepcopy(raw.get("scope_mapping", {})),
                  "scope_relation": scope_relation}
    subdomain_hash = sha(normalized)
    child_hash = sha({"schema": SCHEMA, "profile": PROFILE, "claim_body_hash": claim_body_hash,
                      "subdomain_hash": subdomain_hash, "scope_relation": scope_relation})
    normalized["normalized_subdomain_hash"] = subdomain_hash
    normalized["child_claim_hash"] = child_hash
    return {"body": body, "parent_claim_hash": parent_hash, "claim_body_hash": claim_body_hash,
            "subdomain": normalized, "subdomain_hash": subdomain_hash, "child_claim_hash": child_hash,
            "scope_relation": scope_relation}


def build_certificate(context, second_engine):
    cert = {"kind": CERTIFICATE_KIND, "certificate_version": CERTIFICATE_VERSION, "schema": SCHEMA,
            "profile": PROFILE, "parent_claim_hash": context["parent_claim_hash"],
            "child_claim_hash": context["child_claim_hash"], "claim_body_hash": context["claim_body_hash"],
            "subdomain_hash": context["subdomain_hash"], "scope_relation": context["scope_relation"],
            "subdomain": context["subdomain"],
            "connectedness_certificate": {"status": "CONNECTED", "method": "cartesian_product_of_nonempty_real_intervals_v1"},
            "definedness_certificate": {"method": "strict_positive_interval_bounds_v1", "all_log_arguments_real_and_positive": True},
            "proof_certificate": {"kind": "real_log_product_positive", "version": "1.0",
                                  "rule": "log(a*b) == log(a) + log(b) for real a>0,b>0", "matched_claim": context["body"]},
            "second_engine_confirmation": copy.deepcopy(second_engine),
            "side_conditions": context["subdomain"]["side_conditions"]}
    cert["artifact_hash"] = sha({k: v for k, v in cert.items() if k != "artifact_hash"})
    return cert


def recheck(claim, cert):
    """Rebuild every B2 binding and check the stored independent-engine confirmation."""
    if not isinstance(cert, dict) or cert.get("kind") != CERTIFICATE_KIND or cert.get("certificate_version") != CERTIFICATE_VERSION:
        return {"ok": False, "detail": "unsupported or invalid B2 certificate kind"}
    try:
        context = prepare_log_product_claim(claim)
    except AdapterError as exc:
        return {"ok": False, "detail": f"B2 claim/domain validation failed: {exc.code}"}
    expected = build_certificate(context, cert.get("second_engine_confirmation"))
    if cert != expected:
        return {"ok": False, "detail": "B2 certificate hash-bound metadata does not re-derive"}
    second = cert["second_engine_confirmation"]
    try:
        from loop_engine.orch_adapters.symbolic_identity_verify import core
        payload = core._second_engine_payload(context["body"]["lhs"], context["body"]["rhs"], context["body"]["symbols"],
                                              context["body"]["scope"], context["subdomain"], claim.get("assumptions"))
        if not core._second_zero_confirmed(second, payload):
            return {"ok": False, "detail": "B3 independent ZERO confirmation is absent or does not bind this scope"}
    except Exception:
        return {"ok": False, "detail": "could not validate B3 confirmation"}
    return {"ok": True, "detail": "re-verified conditional real-log identity on its explicit connected subdomain"}


def build_positive_exp_transformation(parent_claim_hash, source_body, source_variable, parameter_variable, transformed_body):
    transformed_hash = _transformed_claim_hash(parent_claim_hash, source_body, source_variable, parameter_variable, transformed_body)
    raw = {"kind": "positive_exp_parameterization", "certificate_version": "1.0", "source_variable": source_variable,
           "parameter_variable": parameter_variable, "forward": f"exp({parameter_variable})",
           "source_domain": {"kind": "real_line", "variable": parameter_variable},
           "image_domain": _interval(source_variable, "0", "+inf", False, False), "inverse": f"log({source_variable})",
           "monotone_injective": True, "surjective_onto_image": True, "parent_claim_hash": parent_claim_hash,
           "transformed_claim": transformed_body, "transformed_claim_hash": transformed_hash}
    return _validate_positive_exp_transformation(raw, parent_claim_hash, source_body)


def recheck_positive_exp_transformation(cert, source_body):
    try:
        raw = {k: v for k, v in cert.items() if k != "artifact_hash"}
        expected = _validate_positive_exp_transformation(raw, cert["parent_claim_hash"], source_body)
    except (KeyError, AdapterError):
        return {"ok": False, "detail": "invalid positive-exp transformation"}
    return {"ok": cert == expected, "detail": "positive-exp transformation rechecked" if cert == expected else "positive-exp transformation metadata mismatch"}
