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
}


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
            exponent = node.right
            if isinstance(exponent, ast.Constant) and isinstance(exponent.value, (int, float)) and exponent.value == 0.5:
                out.append(("EVEN_ROOT_RADICAND_NONNEGATIVE", node.left, path + ".left"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1:
            kind = {"sqrt": "EVEN_ROOT_RADICAND_NONNEGATIVE", "log": "LOG_ARGUMENT_POSITIVE",
                    "asin": "ASIN_ARGUMENT_IN_CLOSED_RANGE", "acos": "ACOS_ARGUMENT_IN_CLOSED_RANGE",
                    "tan": "TAN_COS_NONZERO"}.get(node.func.id)
            if kind:
                out.append((kind, node.args[0], path + ".args[0]"))
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


def _obligation(kind, source_expression, source_node_path, symbols, domain_hash, assumption_hash, intervals):
    if kind == "DENOMINATOR_NONZERO": relation = "!= 0"
    elif kind == "EVEN_ROOT_RADICAND_NONNEGATIVE": relation = ">= 0"
    elif kind == "LOG_ARGUMENT_POSITIVE": relation = "> 0"
    elif kind == "TAN_COS_NONZERO":
        # A narrow analytic lemma: cos(x) has no zero on the exact rational interval (-1,1).
        relation = "!= 0"
        if source_expression in symbols and intervals[source_expression]["lower"] == "-1" and intervals[source_expression]["upper"] == "1" and not intervals[source_expression]["lower_closed"] and not intervals[source_expression]["upper_closed"]:
            status, route = "PROVED", "cosine_nonzero_on_open_unit_interval"
        else: status, route = "UNRESOLVED", "pole_analysis_not_proved"
    elif kind in {"ASIN_ARGUMENT_IN_CLOSED_RANGE", "ACOS_ARGUMENT_IN_CLOSED_RANGE"}:
        status, route, relation = "UNRESOLVED", "bounded_kernel_no_range_solver", "in [-1,1]"
    else: status, route, relation = "UNSUPPORTED", "unsupported_obligation_kind", ""
    if kind not in {"TAN_COS_NONZERO", "ASIN_ARGUMENT_IN_CLOSED_RANGE", "ACOS_ARGUMENT_IN_CLOSED_RANGE"}:
        status, route = _interval_relation(source_expression, relation, intervals, symbols)
    body = {"obligation_version": OBLIGATION_VERSION, "kind": kind, "source_expression": source_expression,
            "source_node_path": source_node_path, "normalized_predicate": f"{source_expression} {relation}",
            "symbols": list(symbols), "domain_hash": domain_hash, "assumption_hash": assumption_hash,
            "status": status, "proof_route": route, "proof_artifact": None, "dependencies": []}
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


def build_obligation_graph(claim, domain, assumptions=None):
    """Build graph only from original source and structured exact domain data."""
    if not isinstance(claim, dict) or not isinstance(claim.get("symbols"), list) or not claim["symbols"]:
        _fail("SCHEMA_VALIDATION_FAILED")
    symbols = claim["symbols"]
    analysis = _domain(domain, symbols)
    canonical_domain = analysis["predicate"]
    domain_hash, assumption_hash = sha(canonical_domain), sha(list(assumptions or []))
    obligations = []
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
    _validate_dag(unique)
    graph = {"schema": SCHEMA, "graph_version": "1.0", "claim_hash": sha({k: claim.get(k) for k in ("lhs", "rhs", "symbols", "scope")}),
             "domain": canonical_domain, "domain_hash": domain_hash, "assumption_hash": assumption_hash,
             "obligations": unique}
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
    extended["artifact_hash"] = sha({k: v for k, v in extended.items() if k != "artifact_hash"})
    return extended
