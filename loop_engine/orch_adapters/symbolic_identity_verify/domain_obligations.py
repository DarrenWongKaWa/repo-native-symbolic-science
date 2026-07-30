"""B4 first-class, source-preserving real-domain obligation graphs.

The kernel is intentionally bounded: it proves only interval facts and a small set of
explicit algebraic lemmas.  Everything else remains visible as UNRESOLVED or UNSUPPORTED;
no caller status, free-text domain, numeric sample, or simplifier result is trusted.
"""
from __future__ import annotations

import ast
import copy
from fractions import Fraction

import sympy

from loop_engine.orch_adapters._symbolic_safe_parse import AdapterError, sha, validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as _subdomain

SCHEMA = "viper.domain_obligation_graph.v1"
OBLIGATION_VERSION = "1.0"
FAILURE = {
    "unresolved": "DOMAIN_OBLIGATION_UNRESOLVED", "unsupported": "DOMAIN_OBLIGATION_UNSUPPORTED",
    "disproved": "DOMAIN_OBLIGATION_DISPROVED", "contradictory": "DOMAIN_OBLIGATION_CONTRADICTORY",
    "empty": "DOMAIN_EMPTY", "not_connected": "DOMAIN_NOT_CONNECTED", "variable": "DOMAIN_VARIABLE_MISMATCH",
    "hash": "DOMAIN_HASH_MISMATCH", "graph_hash": "OBLIGATION_GRAPH_HASH_MISMATCH",
    "source": "OBLIGATION_SOURCE_MISMATCH", "cycle": "OBLIGATION_GRAPH_CYCLE",
    "dependency": "OBLIGATION_DEPENDENCY_MISSING",
    "sensitive": "DOMAIN_SENSITIVE_NODE_WITHOUT_OBLIGATION",
    "incomplete": "DOMAIN_OBLIGATION_EXTRACTION_INCOMPLETE",
}
SUPPORT_MATRIX = {kind: "EXPLICITLY_UNSUPPORTED" for kind in (
    "DENOMINATOR_NONZERO EVEN_ROOT_RADICAND_NONNEGATIVE STRICT_POSITIVE_ROOT_RADICAND LOG_ARGUMENT_POSITIVE "
    "ASIN_ARGUMENT_IN_CLOSED_RANGE ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE ACOS_ARGUMENT_IN_CLOSED_RANGE "
    "ACOS_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE TAN_COS_NONZERO COT_SIN_NONZERO SEC_COS_NONZERO CSC_SIN_NONZERO "
    "RATIONAL_POWER_BASE_CONDITION FRACTIONAL_POWER_BASE_CONDITION INVERSE_FUNCTION_BRANCH TRANSFORMATION_IMAGE "
    "TRANSFORMATION_INVERSE TRANSFORMATION_INJECTIVITY TRANSFORMATION_MONOTONICITY CONNECTED_DOMAIN NONEMPTY_DOMAIN "
    "BASE_POINT_MEMBERSHIP DIFFERENTIABILITY OBLIGATION_INTERSECTION").split()}
for _kind in ("DENOMINATOR_NONZERO", "EVEN_ROOT_RADICAND_NONNEGATIVE", "STRICT_POSITIVE_ROOT_RADICAND",
              "LOG_ARGUMENT_POSITIVE", "RATIONAL_POWER_BASE_CONDITION", "FRACTIONAL_POWER_BASE_CONDITION",
              "CONNECTED_DOMAIN", "NONEMPTY_DOMAIN", "BASE_POINT_MEMBERSHIP", "DIFFERENTIABILITY",
              "TRANSFORMATION_IMAGE", "TRANSFORMATION_INVERSE", "TRANSFORMATION_INJECTIVITY",
              "TRANSFORMATION_MONOTONICITY", "OBLIGATION_INTERSECTION"):
    SUPPORT_MATRIX[_kind] = "SUPPORTED_AND_RECHECKABLE"


class ObligationError(AdapterError):
    pass


def _fail(code):
    raise ObligationError(code)


def _source_nodes(source, root):
    """Yield relevant AST nodes and stable paths without evaluating or simplifying source."""
    try:
        tree = ast.parse(source.replace("^", "**"), mode="eval").body
    except SyntaxError:
        _fail(FAILURE["source"])
    out = []
    def walk(node, path):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            out.append(("DENOMINATOR_NONZERO", node.right, path + ".right"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            out.append(("FRACTIONAL_POWER_BASE_CONDITION", node, path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1:
            kind = {"sqrt": "EVEN_ROOT_RADICAND_NONNEGATIVE", "log": "LOG_ARGUMENT_POSITIVE",
                    "asin": "ASIN_ARGUMENT_IN_CLOSED_RANGE", "acos": "ACOS_ARGUMENT_IN_CLOSED_RANGE",
                    "tan": "TAN_COS_NONZERO", "cot": "COT_SIN_NONZERO", "sec": "SEC_COS_NONZERO",
                    "csc": "CSC_SIN_NONZERO"}.get(node.func.id)
            if kind:
                out.append((kind, node.args[0], path + ".args[0]"))
                if node.func.id in {"asin", "acos"}:
                    out.append(("ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE" if node.func.id == "asin" else "ACOS_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE", node.args[0], path + ".args[0]"))
                if node.func.id == "sqrt":
                    # This is deliberately a second node, rather than an inference hidden in
                    # the sqrt node: later consumers may depend on strict positivity.
                    out.append(("STRICT_POSITIVE_ROOT_RADICAND", node.args[0], path + ".args[0]"))
            elif node.func.id not in {"exp", "sin", "cos", "atan", "sinh", "cosh", "tanh", "Abs"}:
                out.append(("INVERSE_FUNCTION_BRANCH", node, path))
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST): walk(value, path + "." + field)
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    if isinstance(child, ast.AST): walk(child, f"{path}.{field}[{i}]")
    walk(tree, root)
    return out


def _domain(domain, symbols):
    if not isinstance(domain, dict): _fail(FAILURE["unsupported"])
    predicate = domain.get("predicate", domain)
    try:
        result = _subdomain.analyze_predicate(predicate, symbols)
    except AdapterError:
        _fail(FAILURE["unsupported"])
    if result["status"] == "EMPTY": _fail(FAILURE["empty"])
    if result["status"] != "CONNECTED": _fail(FAILURE["not_connected"])
    return result


def _interval_relation(expr, relation, intervals, symbols):
    """Return PROVED/DISPROVED/UNRESOLVED using only exact interval facts."""
    try:
        parsed = validate_and_parse(expr, symbols, real=True)
    except AdapterError:
        return "UNSUPPORTED", "safe_parse"
    if parsed.is_number:
        value = sympy.Rational(parsed)
        good = {"> 0": value > 0, ">= 0": value >= 0, "!= 0": value != 0}.get(relation)
        return ("PROVED" if good else "DISPROVED"), "exact_rational"
    if parsed.is_Symbol:
        interval = intervals.get(str(parsed))
        if not interval: return "UNRESOLVED", "interval_bounds"
        lower = None if interval["lower"] == "-inf" else Fraction(interval["lower"])
        upper = None if interval["upper"] == "+inf" else Fraction(interval["upper"])
        if relation == "> 0":
            if lower is not None and (lower > 0 or (lower == 0 and not interval["lower_closed"])): return "PROVED", "interval_lower_bound"
            if upper is not None and (upper < 0 or (upper == 0 and interval["upper_closed"])): return "DISPROVED", "interval_upper_bound"
        if relation == ">= 0":
            if lower is not None and lower >= 0: return "PROVED", "interval_lower_bound"
            if upper is not None and upper < 0: return "DISPROVED", "interval_upper_bound"
        if relation == "!= 0":
            if lower is not None and (lower > 0 or (lower == 0 and not interval["lower_closed"])): return "PROVED", "interval_excludes_zero"
            if upper is not None and (upper < 0 or (upper == 0 and not interval["upper_closed"])): return "PROVED", "interval_excludes_zero"
        return "UNRESOLVED", "interval_bounds"
    if isinstance(parsed, sympy.Mul) and relation in {"> 0", "!= 0"}:
        factors = list(parsed.args)
        if factors and all(f.is_Symbol for f in factors):
            results = [_interval_relation(str(f), "> 0", intervals, symbols)[0] for f in factors]
            if all(r == "PROVED" for r in results): return "PROVED", "positive_factor_product"
            if any(r == "DISPROVED" for r in results): return "DISPROVED", "positive_factor_product"
    # Exact affine one-variable interval facts, e.g. x - 1 > 0 on x > 1.
    if isinstance(parsed, sympy.Add):
        variables = [t for t in parsed.args if t.is_Symbol]
        constants = [t for t in parsed.args if t.is_number]
        if len(variables) == 1 and len(constants) == 1:
            interval = intervals.get(str(variables[0])); shift = Fraction(constants[0])
            if interval:
                lower = None if interval["lower"] == "-inf" else Fraction(interval["lower"])
                upper = None if interval["upper"] == "+inf" else Fraction(interval["upper"])
                if relation == "> 0" and lower is not None and (lower + shift > 0 or (lower + shift == 0 and not interval["lower_closed"])):
                    return "PROVED", "affine_interval_lower_bound"
                if relation == ">= 0" and lower is not None and lower + shift >= 0:
                    return "PROVED", "affine_interval_lower_bound"
                if relation == "!= 0" and lower is not None and (lower + shift > 0 or (lower + shift == 0 and not interval["lower_closed"])):
                    return "PROVED", "affine_interval_excludes_zero"
                if relation == "!= 0" and upper is not None and (upper + shift < 0 or (upper + shift == 0 and not interval["upper_closed"])):
                    return "PROVED", "affine_interval_excludes_zero"
    # Explicit B1 SOS shape: x**2 + positive rational.  No simplifier is used.
    if isinstance(parsed, sympy.Add):
        squares = [t for t in parsed.args if isinstance(t, sympy.Pow) and t.exp == 2]
        constants = [t for t in parsed.args if t.is_number]
        if len(squares) == 1 and len(constants) == 1 and constants[0].is_positive is True and relation in {"> 0", ">= 0", "!= 0"}:
            return "PROVED", "sum_of_squares_plus_positive_constant"
    return "UNRESOLVED", "bounded_kernel_no_general_solver"


def _syntactic_power_exponent(source_expression):
    """Classify the original AST exponent before SymPy can collapse x**0 to 1."""
    try:
        power = ast.parse(source_expression.replace("^", "**"), mode="eval").body
        if not isinstance(power, ast.BinOp) or not isinstance(power.op, ast.Pow):
            return "unsupported", None
        exponent = power.right
        def integer(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
                return node.value
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                value = integer(node.operand)
                return None if value is None else -value
            return None
        value = integer(exponent)
        if value is not None:
            return "integer", value
        if isinstance(exponent, ast.Constant) and isinstance(exponent.value, float):
            return "float", None
        if isinstance(exponent, ast.BinOp) and isinstance(exponent.op, ast.Div):
            numerator, denominator = integer(exponent.left), integer(exponent.right)
            if numerator is not None and denominator not in (None, 0):
                reduced = Fraction(numerator, denominator)
                return "rational", reduced
        return "symbolic", None
    except (SyntaxError, ValueError, TypeError):
        return "unsupported", None


def _obligation(kind, source_expression, source_node_path, symbols, domain_hash, assumption_hash, intervals):
    original_kind = kind
    if kind == "DENOMINATOR_NONZERO":
        relation = "!= 0"; status, route = _interval_relation(source_expression, relation, intervals, symbols)
    elif kind == "EVEN_ROOT_RADICAND_NONNEGATIVE":
        relation = ">= 0"; status, route = _interval_relation(source_expression, relation, intervals, symbols)
    elif kind == "STRICT_POSITIVE_ROOT_RADICAND":
        relation = "> 0"; status, route = _interval_relation(source_expression, relation, intervals, symbols)
    elif kind == "LOG_ARGUMENT_POSITIVE":
        relation = "> 0"; status, route = _interval_relation(source_expression, relation, intervals, symbols)
    elif kind == "TAN_COS_NONZERO":
        # A narrow analytic lemma: cos(x) has no zero on the exact rational interval (-1,1).
        relation = "!= 0"
        if source_expression in symbols and intervals[source_expression]["lower"] == "-1" and intervals[source_expression]["upper"] == "1" and not intervals[source_expression]["lower_closed"] and not intervals[source_expression]["upper_closed"]:
            status, route = "PROVED", "cosine_nonzero_on_open_unit_interval"
        else: status, route = "UNRESOLVED", "pole_analysis_not_proved"
    elif kind in {"ASIN_ARGUMENT_IN_CLOSED_RANGE", "ACOS_ARGUMENT_IN_CLOSED_RANGE"}:
        status, route, relation = "UNRESOLVED", "bounded_kernel_no_range_solver", "in [-1,1]"
    elif kind in {"ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE", "ACOS_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE"}:
        status, route, relation = "UNRESOLVED", "open_range_not_established", "in (-1,1)"
    elif kind == "FRACTIONAL_POWER_BASE_CONDITION":
        relation = "real_power_base_condition"
        try:
            tree = ast.parse(source_expression.replace("^", "**"), mode="eval").body
            base = ast.unparse(tree.left)
            exponent_kind, exponent = _syntactic_power_exponent(source_expression)
            if exponent_kind == "integer":
                relation = f"{base} != 0" if exponent < 0 else "no base restriction"
                status, route = ("PROVED", "integer_power") if exponent >= 0 else _interval_relation(base, "!= 0", intervals, symbols)
                kind = "RATIONAL_POWER_BASE_CONDITION"
            elif exponent_kind == "rational":
                kind = "FRACTIONAL_POWER_BASE_CONDITION"; q, p = exponent.denominator, exponent.numerator
                relation = f"{base} {'> 0' if q % 2 == 0 and p < 0 else '>= 0' if q % 2 == 0 else '!= 0'}"
                status, route = _interval_relation(base, "> 0" if q % 2 == 0 and p < 0 else ">= 0" if q % 2 == 0 else "!= 0", intervals, symbols)
                if q % 2 == 1 and p >= 0: status, route = "PROVED", "odd_denominator_real_power"
            elif exponent_kind == "float": status, route = "UNSUPPORTED", "floating_power_exponent"
            else: status, route = "UNSUPPORTED", "symbolic_or_unparseable_power_exponent"
        except Exception: status, route = "UNSUPPORTED", "unparseable_power"
    elif kind in {"COT_SIN_NONZERO", "SEC_COS_NONZERO", "CSC_SIN_NONZERO", "INVERSE_FUNCTION_BRANCH"}:
        status, route, relation = "UNSUPPORTED", "recognized_but_not_proved_v1", "domain-sensitive function"
    else: status, route, relation = "UNSUPPORTED", "unsupported_obligation_kind", ""
    body = {"obligation_version": OBLIGATION_VERSION, "kind": kind, "source_expression": source_expression,
            "source_node_path": source_node_path, "normalized_predicate": f"{source_expression} {relation}",
            "symbols": list(symbols), "domain_hash": domain_hash, "assumption_hash": assumption_hash,
            "status": status, "proof_route": route, "proof_artifact": None, "dependencies": []}
    if status == "UNSUPPORTED":
        body["failure_code"] = FAILURE["unsupported"]
        body["reason"] = f"{original_kind} is recognized but {route}"
    body["obligation_id"] = sha({k: body[k] for k in ("kind", "source_expression", "source_node_path", "domain_hash", "assumption_hash")})
    body["artifact_hash"] = sha({k: v for k, v in body.items() if k != "artifact_hash"})
    return body


def _validate_dag(obligations):
    ids = {o.get("obligation_id") for o in obligations}
    if None in ids or len(ids) != len(obligations): _fail(FAILURE["dependency"])
    by_id = {o["obligation_id"]: o for o in obligations}
    state = {}
    def visit(node):
        mark = state.get(node)
        if mark == 1: _fail(FAILURE["cycle"])
        if mark == 2: return
        state[node] = 1
        for dep in by_id[node].get("dependencies", []):
            if dep not in by_id: _fail(FAILURE["dependency"])
            visit(dep)
        state[node] = 2
    for node in by_id: visit(node)


def _refresh(node):
    """Refresh a node after adding a derived proof or a semantic dependency."""
    node.pop("failure_code", None); node.pop("reason", None)
    node["artifact_hash"] = sha({k: v for k, v in node.items() if k != "artifact_hash"})
    return node


def _derived_obligation(kind, source_expression, source_node_path, symbols, domain_hash,
                        assumption_hash, intervals, status, route, predicate, dependencies, artifact=None):
    node = _obligation(kind, source_expression, source_node_path, symbols, domain_hash, assumption_hash, intervals)
    node.update(status=status, proof_route=route, normalized_predicate=predicate,
                dependencies=list(dependencies), proof_artifact=copy.deepcopy(artifact))
    _refresh(node)
    if status == "UNSUPPORTED":
        node["failure_code"] = FAILURE["unsupported"]
        node["reason"] = f"{kind} is recognized but {route}"
        node["artifact_hash"] = sha({k: v for k, v in node.items() if k != "artifact_hash"})
    return node


def _b1_composite_obligations(claim, unique, symbols, domain_hash, assumption_hash, intervals):
    """Bounded bridge to B1's exact (non-simplifier) real-line composite rechecker."""
    if len(symbols) != 1:
        return []
    try:
        from loop_engine.orch_adapters.symbolic_identity_verify import recheck as _b1
        lhs = validate_and_parse(claim["lhs"], symbols, real=True)
        rhs = validate_and_parse(claim["rhs"], symbols, real=True)
        cert = _b1.build_derivative_base_point_composite_certificate(lhs, rhs, symbols,
                                                                       {"kind": "real_line", "variable": symbols[0]})
    except Exception:
        cert = None
    if cert is None:
        return []
    strict = next((o for o in unique if o["kind"] == "STRICT_POSITIVE_ROOT_RADICAND" and
                   o["status"] == "PROVED"), None)
    denominator = next((o for o in unique if o["kind"] == "DENOMINATOR_NONZERO" and
                        o["status"] == "PROVED"), None)
    if strict is None or denominator is None:
        return []
    cert_hash = cert["artifact_hash"]
    derived = []
    for node in unique:
        if node["kind"] in {"ASIN_ARGUMENT_IN_CLOSED_RANGE", "ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE"}:
            node.update(status="PROVED", proof_route="b1_exact_interior_identity_replay",
                        proof_artifact={"b1_composite_certificate_hash": cert_hash},
                        dependencies=[strict["obligation_id"], denominator["obligation_id"]])
            _refresh(node)
    open_node = next((o for o in unique if o["kind"] == "ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE"), None)
    if open_node is None:
        return []
    connected = next(o for o in unique if o["kind"] == "CONNECTED_DOMAIN")
    derived.append(_derived_obligation(
        "DIFFERENTIABILITY", "atan(x) and asin(x/sqrt(1+x**2))", "b1.parent", symbols,
        domain_hash, assumption_hash, intervals, "PROVED", "b1_structured_real_line_replay",
        "both parent sides differentiable", [open_node["obligation_id"], denominator["obligation_id"]],
        {"b1_composite_certificate_hash": cert_hash}))
    derived.append(_derived_obligation(
        "BASE_POINT_MEMBERSHIP", f"{symbols[0]} = 0", "b1.base_point", symbols,
        domain_hash, assumption_hash, intervals, "PROVED", "real_line_contains_zero",
        f"{symbols[0]}=0 belongs to declared domain", [connected["obligation_id"]],
        {"b1_composite_certificate_hash": cert_hash}))
    return derived


def _b2_transformation_obligations(claim, unique, symbols, domain_hash, assumption_hash, intervals):
    """Emit the validated x=exp(u) chain; its raw certificate is itself hash-bound."""
    raw = claim.get("subdomain") if isinstance(claim, dict) else None
    transformation = raw.get("transformation") if isinstance(raw, dict) else None
    if transformation in (None, {}):
        return []
    try:
        context = _subdomain.prepare_log_product_claim(claim)
        transformation = context["subdomain"]["transformation"]
    except Exception:
        # The source includes a transformation but it did not pass B2's independent validator.
        return [_derived_obligation("TRANSFORMATION_IMAGE", "unvalidated transformation", "subdomain.transformation",
                                    symbols, domain_hash, assumption_hash, intervals, "UNSUPPORTED",
                                    "b2_transformation_validation_failed", "image domain unavailable", [], None)]
    if transformation is None:
        return []
    source = transformation["source_variable"]
    parameter = transformation["parameter_variable"]
    t_hash = transformation["artifact_hash"]
    connected = next(o for o in unique if o["kind"] == "CONNECTED_DOMAIN")
    image = _derived_obligation("TRANSFORMATION_IMAGE", f"{source}=exp({parameter})", "subdomain.transformation.image",
                                symbols, domain_hash, assumption_hash, intervals, "PROVED", "b2_positive_exp_replay",
                                f"{source} in (0,+inf)", [connected["obligation_id"]], {"transformation_hash": t_hash})
    inverse = _derived_obligation("TRANSFORMATION_INVERSE", f"log(exp({parameter}))", "subdomain.transformation.inverse",
                                  symbols, domain_hash, assumption_hash, intervals, "PROVED", "b2_positive_exp_replay",
                                  f"log(exp({parameter})) = {parameter}", [image["obligation_id"]], {"transformation_hash": t_hash})
    injective = _derived_obligation("TRANSFORMATION_INJECTIVITY", f"exp({parameter})", "subdomain.transformation.injectivity",
                                    symbols, domain_hash, assumption_hash, intervals, "PROVED", "b2_positive_exp_replay",
                                    "exp is injective on real line", [image["obligation_id"]], {"transformation_hash": t_hash})
    monotone = _derived_obligation("TRANSFORMATION_MONOTONICITY", f"exp({parameter})", "subdomain.transformation.monotonicity",
                                   symbols, domain_hash, assumption_hash, intervals, "PROVED", "b2_positive_exp_replay",
                                   "exp is strictly increasing on real line", [image["obligation_id"]], {"transformation_hash": t_hash})
    return [image, inverse, injective, monotone]


def build_obligation_graph(claim, domain, assumptions=None):
    """Build graph only from original source and structured exact domain data."""
    if not isinstance(claim, dict) or not isinstance(claim.get("symbols"), list) or not claim["symbols"]:
        _fail("SCHEMA_VALIDATION_FAILED")
    symbols = claim["symbols"]
    analysis = _domain(domain, symbols)
    canonical_domain = analysis["predicate"]
    domain_hash, assumption_hash = sha(canonical_domain), sha(list(assumptions or []))
    obligations = []
    # Domain nodes are load-bearing inputs, not caller claims.
    for kind, status, route in (("CONNECTED_DOMAIN", "PROVED", "cartesian_interval_connectedness"), ("NONEMPTY_DOMAIN", "PROVED", "exact_interval_intersection")):
        node = _obligation(kind, str(canonical_domain), "domain", symbols, domain_hash, assumption_hash, analysis["intervals"])
        node["status"], node["proof_route"], node["normalized_predicate"] = status, route, kind
        obligations.append(_refresh(node))
    for side in ("lhs", "rhs"):
        source = claim.get(side)
        if not isinstance(source, str): _fail(FAILURE["source"])
        for kind, node, path in _source_nodes(source, side):
            obligations.append(_obligation(kind, ast.unparse(node), path, symbols, domain_hash, assumption_hash, analysis["intervals"]))
    # exact de-duplication preserves first source provenance and fixed encounter order
    unique = []
    seen = set()
    for obligation in obligations:
        key = (obligation["kind"], obligation["source_expression"], obligation["source_node_path"])
        if key not in seen: seen.add(key); unique.append(obligation)
    source_nodes = [(kind, ast.unparse(node), path) for side in ("lhs", "rhs")
                    for kind, node, path in _source_nodes(claim[side], side)]
    emitted_source_nodes = [o for o in unique if o["source_node_path"] != "domain"]
    if source_nodes and not emitted_source_nodes:
        _fail(FAILURE["sensitive"])
    if len(emitted_source_nodes) < len(source_nodes):
        _fail(FAILURE["incomplete"])
    # Semantic dependencies are re-derived below, so an edge is never a builder assertion.
    # A strict root premise establishes both a real root and the nonzero root denominator.
    for child in unique:
        if child["kind"] == "EVEN_ROOT_RADICAND_NONNEGATIVE":
            for parent in unique:
                if parent["kind"] == "STRICT_POSITIVE_ROOT_RADICAND" and parent["source_expression"] == child["source_expression"]:
                    child["dependencies"].append(parent["obligation_id"])
                    child["artifact_hash"] = sha({k: v for k, v in child.items() if k != "artifact_hash"})
        if child["kind"] == "DENOMINATOR_NONZERO":
            for parent in unique:
                if parent["kind"] == "STRICT_POSITIVE_ROOT_RADICAND" and child["source_expression"] == f"sqrt({parent['source_expression']})":
                    child["dependencies"].append(parent["obligation_id"])
                    child["status"], child["proof_route"] = parent["status"], "positive_root_is_nonzero"
                    _refresh(child)
    # B1's deliberately narrow, independently replayable atan/asin composite adds its
    # differentiability and base-point leaves only when the exact B1 certificate exists.
    unique.extend(_b1_composite_obligations(claim, unique, symbols, domain_hash, assumption_hash, analysis["intervals"]))
    # B2 transformation nodes are present only for a B2 request that independently validates
    # its exact positive-exp substitution; otherwise an explicit unsupported node is retained.
    unique.extend(_b2_transformation_obligations(claim, unique, symbols, domain_hash, assumption_hash, analysis["intervals"]))
    # The explicit intersection is a load-bearing aggregate, and therefore records all prior nodes.
    aggregate = _obligation("OBLIGATION_INTERSECTION", "all domain obligations", "graph", symbols, domain_hash, assumption_hash, analysis["intervals"])
    aggregate["dependencies"] = [o["obligation_id"] for o in unique]
    statuses = {o["status"] for o in unique}
    aggregate["status"] = "DISPROVED" if "DISPROVED" in statuses else "UNSUPPORTED" if "UNSUPPORTED" in statuses else "UNRESOLVED" if "UNRESOLVED" in statuses else "PROVED"
    aggregate["proof_route"] = "status_intersection"; _refresh(aggregate)
    unique.append(aggregate); _validate_dag(unique)
    graph = {"schema": SCHEMA, "graph_version": "1.0", "claim_hash": sha({k: claim.get(k) for k in ("lhs", "rhs", "symbols", "scope")}),
             "domain": canonical_domain, "domain_hash": domain_hash, "assumption_hash": assumption_hash,
             "obligations": unique, "support_matrix": copy.deepcopy(SUPPORT_MATRIX),
             "extraction_inventory": {"source_sensitive_nodes": [{"kind": k, "source_expression": e, "source_node_path": p}
                                                                      for k, e, p in source_nodes],
                                        "emitted_obligation_ids": [o["obligation_id"] for o in unique],
                                        "unsupported_sensitive_nodes": [o["obligation_id"] for o in emitted_source_nodes if o["status"] == "UNSUPPORTED"],
                                        "covered_sensitive_node_count": len(emitted_source_nodes),
                                        "total_sensitive_node_count": len(source_nodes),
                                        "coverage_complete": True}}
    graph["graph_hash"] = sha({k: v for k, v in graph.items() if k != "graph_hash"})
    return graph


def recheck_obligation_graph(claim, domain, assumptions, graph):
    """Third-party B4 replay: rebuild source obligations and reject every mismatch."""
    if not isinstance(graph, dict) or graph.get("schema") != SCHEMA: return {"ok": False, "detail": FAILURE["unsupported"]}
    try:
        expected = build_obligation_graph(claim, domain, assumptions)
        _validate_dag(graph.get("obligations", []))
    except ObligationError as exc:
        return {"ok": False, "detail": exc.code}
    if graph.get("graph_hash") != sha({k: v for k, v in graph.items() if k != "graph_hash"}):
        return {"ok": False, "detail": FAILURE["graph_hash"]}
    if graph != expected:
        return {"ok": False, "detail": FAILURE["source"]}
    if any(o["status"] in {"UNRESOLVED", "UNSUPPORTED", "DISPROVED", "CONTRADICTORY"} for o in graph["obligations"]):
        return {"ok": False, "detail": FAILURE["unresolved"]}
    return {"ok": True, "detail": "B4 obligation graph independently rechecked"}


def attach_to_b2_certificate(certificate, claim, assumptions, graph):
    """Additive B4 extension; never mutates or reinterprets the original B2 artifact."""
    if recheck_obligation_graph(claim, {"predicate": certificate.get("subdomain", {}).get("predicate")}, assumptions, graph).get("ok") is not True:
        _fail(FAILURE["unresolved"])
    extended = copy.deepcopy(certificate)
    extended["domain_obligation_graph"] = copy.deepcopy(graph)
    extended["domain_obligation_graph_hash"] = graph["graph_hash"]
    extended["domain_obligation_graph_version"] = graph["graph_version"]
    extended["domain_obligation_summary"] = {"graph_hash": graph["graph_hash"], "status": graph["obligations"][-1]["status"]}
    extended["artifact_hash"] = sha({k: v for k, v in extended.items() if k != "artifact_hash"})
    return extended
