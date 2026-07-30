#!/usr/bin/env python3
"""Re-checkable certificates — audit-the-auditor approach #3 ("trust the proof, not the prover").

For a POLYNOMIAL identity `lhs == rhs`, certification need not trust `sympy.simplify` at all.
By the polynomial identity lemma (exact Schwartz–Zippel): a polynomial of total degree ≤ d
over an infinite field that evaluates to EXACTLY 0 at every point of a product grid S^n with
|S| > d is identically zero. So the certificate is:

    { kind, total_degree d, per_variable_values S (|S| = d+1), grid_points }

and a third party RE-CHECKS it by evaluating lhs - rhs in EXACT arithmetic at S^n and
confirming every value is exactly 0 — using no simplification heuristic. The re-checker
below is deliberately a SEPARATE, minimal module: it parses (via the same strict whitelist)
and does exact `subs` arithmetic; it contains NO call to sympy.simplify.

`build_polynomial_certificate` (used by the judge) returns a certificate iff lhs-rhs is a
polynomial small enough to certify this way. `recheck` (usable standalone / by anyone)
independently re-verifies a claim+certificate and returns PASS/FAIL.
"""
from __future__ import annotations
import copy
import sympy
from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse, sha, syms_like
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as _subdomain

MAX_GRID_POINTS = 20000   # cap: (d+1)^n must not exceed this to be "cheaply re-checkable"
MAX_POSITIVE_SQRT_OPS = 120


def _claim_hash(lhs, rhs, symbols):
    return sha({"lhs": str(lhs), "rhs": str(rhs), "symbols": list(symbols)})


def _artifact_hash(payload):
    body = copy.deepcopy(payload)
    body.pop("artifact_hash", None)
    return sha(body)


def _exact_rational_zero(expr, symbols):
    """Check a rational identity by exact numerator expansion, never heuristically."""
    try:
        num, den = sympy.fraction(sympy.together(expr))
        if den == 0:
            return False
        return sympy.expand(num) == 0
    except Exception:
        return False


def _parse_positive_constant(value):
    try:
        constant = sympy.sympify(value)
    except Exception:
        return None
    if constant.free_symbols or not constant.is_number or constant.is_real is not True:
        return None
    return constant if constant.is_positive is True else None


def _check_sos_positivity(radicand, certificate, x):
    """Recompute the deliberately small SOS-plus-constant positivity proof."""
    if not isinstance(certificate, dict):
        return None
    if certificate.get("kind") != "sum_of_squares_plus_positive_constant":
        return None
    constant = _parse_positive_constant(certificate.get("positive_constant"))
    terms = certificate.get("square_terms")
    if constant is None or not isinstance(terms, list) or not terms:
        return None
    try:
        parsed = [validate_and_parse(t, [str(x)], real=True) for t in terms]
    except Exception:
        return None
    if any(t.free_symbols - {x} for t in parsed):
        return None
    if not _exact_rational_zero(radicand - (constant + sum(t**2 for t in parsed)), [x]):
        return None
    declared = certificate.get("polynomial")
    if not isinstance(declared, str):
        return None
    try:
        declared_expr = validate_and_parse(declared, [str(x)], real=True)
    except Exception:
        return None
    if not _exact_rational_zero(declared_expr - radicand, [x]):
        return None
    return {"positive_constant": constant, "square_terms": parsed}


def _sqrt_base(expr):
    if isinstance(expr, sympy.Pow) and expr.exp == sympy.Rational(1, 2):
        return expr.base
    return None


def _positive_sqrt_root_from_claim(lhs, rhs, x):
    """Find the one supported principal-root radicand in a derivative child."""
    bases = []
    for power in (lhs.atoms(sympy.Pow) | rhs.atoms(sympy.Pow)):
        if power.exp in (sympy.Rational(1, 2), sympy.Rational(-1, 2),
                         sympy.Rational(3, 2), sympy.Rational(-3, 2)):
            bases.append(power.base)
    unique = []
    for base in bases:
        if not any(_exact_rational_zero(base - old, [x]) for old in unique):
            unique.append(base)
    # The target has P and 1/P under square roots.  P is the non-reciprocal base.
    for base in unique:
        if all(not _exact_rational_zero(base - 1 / other, [x]) for other in unique if other != base):
            continue
        try:
            if sympy.Poly(sympy.expand(base), x).is_univariate:
                return sympy.expand(base)
        except Exception:
            continue
    for base in unique:
        try:
            if sympy.Poly(sympy.expand(base), x).is_univariate:
                return sympy.expand(base)
        except Exception:
            pass
    return None


def _replace_supported_positive_sqrt_forms(expr, x, radicand, root_atom):
    """Normalize only P-root forms and roots of the proved reciprocal 1/P."""
    replacements, lemmas, equalities = {}, [], []
    for power in expr.atoms(sympy.Pow):
        exponent = power.exp
        if exponent not in (sympy.Rational(1, 2), sympy.Rational(-1, 2),
                            sympy.Rational(3, 2), sympy.Rational(-3, 2)):
            continue
        base = power.base
        if _exact_rational_zero(base - radicand, [x]):
            if exponent == sympy.Rational(1, 2):
                replacements[power] = root_atom
            elif exponent == sympy.Rational(-1, 2):
                replacements[power] = 1 / root_atom
            elif exponent == sympy.Rational(3, 2):
                replacements[power] = radicand * root_atom
                lemmas.append("positive_power_three_halves")
            else:
                replacements[power] = 1 / (radicand * root_atom)
                lemmas.append("positive_power_three_halves")
        elif exponent in (sympy.Rational(1, 2), sympy.Rational(-1, 2)) and \
                _exact_rational_zero(base - 1 / radicand, [x]):
            equalities.append((base, 1 / radicand))
            lemmas.append("positive_sqrt_reciprocal")
            replacements[power] = (1 / root_atom if exponent == sympy.Rational(1, 2)
                                   else root_atom)
        else:
            return None
    normalized = expr.xreplace(replacements)
    if normalized.atoms(sympy.Function):
        return None
    for power in normalized.atoms(sympy.Pow):
        if power.exp.is_Rational and power.exp.q != 1:
            return None
    return normalized, sorted(set(lemmas)), equalities


def _clear_and_reduce_positive_sqrt(lhs, rhs, x, radicand, root_atom):
    left = _replace_supported_positive_sqrt_forms(lhs, x, radicand, root_atom)
    right = _replace_supported_positive_sqrt_forms(rhs, x, radicand, root_atom)
    if left is None or right is None:
        return None
    lhs_n, lhs_lemmas, lhs_equalities = left
    rhs_n, rhs_lemmas, rhs_equalities = right
    try:
        numerator, denominator = sympy.fraction(sympy.together(lhs_n - rhs_n))
        numerator, denominator = sympy.expand(numerator), sympy.expand(denominator)
        if denominator == 0:
            return None
        relation = sympy.expand(root_atom**2 - radicand)
        quotient, remainder = sympy.reduced(numerator, [relation], root_atom, x)
    except Exception:
        return None
    if remainder != 0:
        return None
    return {
        "normalized_lhs": lhs_n,
        "normalized_rhs": rhs_n,
        "numerator": numerator,
        "denominator": denominator,
        "relation": relation,
        "cofactor": quotient[0] if quotient else sympy.Integer(0),
        "lemmas": sorted(set(lhs_lemmas + rhs_lemmas)),
        "equalities": lhs_equalities + rhs_equalities,
    }


def _denominator_is_positive_root_product(denominator, radicand, root_atom, x):
    """Discharge D != 0 only when D is a nonzero constant times P^a r^b."""
    try:
        current = sympy.Poly(sympy.expand(denominator), root_atom, x)
        p_poly = sympy.Poly(sympy.expand(radicand), root_atom, x)
        r_poly = sympy.Poly(root_atom, root_atom, x)
        while True:
            q, rem = sympy.div(current, p_poly)
            if rem != 0:
                break
            current = q
        while True:
            q, rem = sympy.div(current, r_poly)
            if rem != 0:
                break
            current = q
        return current.total_degree() == 0 and current.as_expr() != 0
    except Exception:
        return False


def build_positive_sqrt_algebraic_cofactor_certificate(lhs, rhs, symbols):
    """Build the B1 certificate only for one real variable and one positive root atom."""
    if len(symbols) != 1 or sympy.count_ops(lhs) + sympy.count_ops(rhs) > MAX_POSITIVE_SQRT_OPS:
        return None
    x = syms_like(lhs - rhs, symbols)[0]
    if x.is_real is not True:
        return None
    radicand = _positive_sqrt_root_from_claim(lhs, rhs, x)
    if radicand is None:
        return None
    sos = {"kind": "sum_of_squares_plus_positive_constant", "polynomial": str(radicand),
           "square_terms": [str(x)], "positive_constant": "1"}
    if _check_sos_positivity(radicand, sos, x) is None:
        return None
    root_atom = sympy.Symbol("r_0", real=True, positive=True)
    reduced = _clear_and_reduce_positive_sqrt(lhs, rhs, x, radicand, root_atom)
    if reduced is None or not _denominator_is_positive_root_product(
            reduced["denominator"], radicand, root_atom, x):
        return None
    cert = {
        "kind": "positive_sqrt_algebraic_cofactor", "certificate_version": "1.0",
        "real_domain": True, "base_symbols": list(symbols),
        "claim_hash": _claim_hash(lhs, rhs, symbols),
        "root_atoms": [{"atom": "r_0", "radicand": str(radicand),
                        "relation": str(reduced["relation"]), "branch": "positive",
                        "positivity_certificate": sos}],
        "verified_radicand_equalities": [
            {"lhs": str(a), "rhs": str(b)} for a, b in reduced["equalities"]],
        "applied_root_lemmas": reduced["lemmas"],
        "normalized_lhs": str(reduced["normalized_lhs"]),
        "normalized_rhs": str(reduced["normalized_rhs"]),
        "cleared_denominator": str(reduced["denominator"]),
        "numerator_polynomial": str(reduced["numerator"]),
        "relation_cofactors": [{"relation": str(reduced["relation"]),
                                  "cofactor": str(reduced["cofactor"])}],
        "denominator_obligations": [
            {"expression": str(radicand), "relation": "> 0"},
            {"expression": "r_0", "relation": "> 0"}],
        "recheck_procedure": "re-derive the positive root normalization, clear exact rational "
                             "denominators, and reduce the numerator modulo r_0**2-P; no "
                             "heuristic canonicalization is used.",
    }
    cert["artifact_hash"] = _artifact_hash(cert)
    return cert


def _recheck_positive_sqrt(lhs, rhs, symbols, cert):
    if len(symbols) != 1 or cert.get("certificate_version") != "1.0" or \
            cert.get("real_domain") is not True or cert.get("base_symbols") != list(symbols):
        return {"ok": False, "detail": "positive-root certificate metadata is invalid"}
    x = syms_like(lhs - rhs, symbols)[0]
    if x.is_real is not True or cert.get("claim_hash") != _claim_hash(lhs, rhs, symbols):
        return {"ok": False, "detail": "claim hash or real-symbol declaration mismatch"}
    roots = cert.get("root_atoms")
    if not isinstance(roots, list) or len(roots) != 1:
        return {"ok": False, "detail": "certificate must declare exactly one root atom"}
    root = roots[0]
    if not isinstance(root, dict) or root.get("atom") != "r_0" or root.get("branch") != "positive":
        return {"ok": False, "detail": "positive root branch metadata is missing or invalid"}
    try:
        radicand = validate_and_parse(root.get("radicand"), symbols, real=True)
    except Exception:
        return {"ok": False, "detail": "root radicand is unparseable"}
    sos = _check_sos_positivity(radicand, root.get("positivity_certificate"), x)
    if sos is None:
        return {"ok": False, "detail": "strict positivity certificate does not recheck"}
    root_atom = sympy.Symbol("r_0", real=True, positive=True)
    relation = sympy.expand(root_atom**2 - radicand)
    if root.get("relation") != str(relation):
        return {"ok": False, "detail": "root relation does not match the positive radicand"}
    actual_radicand = _positive_sqrt_root_from_claim(lhs, rhs, x)
    if actual_radicand is None or not _exact_rational_zero(actual_radicand - radicand, [x]):
        return {"ok": False, "detail": "certificate root is stale or does not match the claim"}
    reduced = _clear_and_reduce_positive_sqrt(lhs, rhs, x, radicand, root_atom)
    if reduced is None:
        return {"ok": False, "detail": "claim contains an unsupported radical form"}
    equalities = [{"lhs": str(a), "rhs": str(b)} for a, b in reduced["equalities"]]
    if cert.get("verified_radicand_equalities") != equalities:
        return {"ok": False, "detail": "radicand equalities are missing or mismatched"}
    if cert.get("applied_root_lemmas") != reduced["lemmas"]:
        return {"ok": False, "detail": "root lemmas are missing, additional, or mismatched"}
    if cert.get("normalized_lhs") != str(reduced["normalized_lhs"]) or \
            cert.get("normalized_rhs") != str(reduced["normalized_rhs"]):
        return {"ok": False, "detail": "stored normalization does not match the claim"}
    if cert.get("cleared_denominator") != str(reduced["denominator"]) or \
            cert.get("numerator_polynomial") != str(reduced["numerator"]):
        return {"ok": False, "detail": "stored numerator or denominator does not match the claim"}
    expected_cofactors = [{"relation": str(reduced["relation"]),
                           "cofactor": str(reduced["cofactor"])}]
    if cert.get("relation_cofactors") != expected_cofactors:
        return {"ok": False, "detail": "cofactor does not reproduce the polynomial relation"}
    if sympy.expand(reduced["numerator"] - reduced["cofactor"] * relation) != 0:
        return {"ok": False, "detail": "cofactor identity fails exact polynomial expansion"}
    expected_obligations = [{"expression": str(radicand), "relation": "> 0"},
                            {"expression": "r_0", "relation": "> 0"}]
    if cert.get("denominator_obligations") != expected_obligations or not \
            _denominator_is_positive_root_product(reduced["denominator"], radicand, root_atom, x):
        return {"ok": False, "detail": "denominator nonzero obligations are not discharged"}
    if cert.get("artifact_hash") != _artifact_hash(cert):
        return {"ok": False, "detail": "positive-root certificate artifact hash mismatch"}
    return {"ok": True, "detail": "re-verified positive square-root algebraic cofactor certificate"}


def _parent_domain_data(lhs, rhs, x, child_cert):
    """Recognize the deliberately bounded real-line T3 parent grammar."""
    atan_side, asin_side = None, None
    for expression in (lhs, rhs):
        if expression.func == sympy.atan and expression.args == (x,):
            atan_side = expression
        if expression.func == sympy.asin and len(expression.args) == 1:
            asin_side = expression
    if atan_side is None or asin_side is None:
        return None
    roots = child_cert.get("root_atoms") if isinstance(child_cert, dict) else None
    if not isinstance(roots, list) or len(roots) != 1:
        return None
    try:
        radicand = validate_and_parse(roots[0].get("radicand"), [str(x)], real=True)
    except Exception:
        return None
    argument = asin_side.args[0]
    try:
        numerator, denominator = sympy.fraction(sympy.together(argument))
    except Exception:
        return None
    denominator_base = _sqrt_base(denominator)
    if numerator != x or denominator_base is None or not _exact_rational_zero(
            denominator_base - radicand, [x]):
        return None
    interior = 1 - argument**2
    if not _exact_rational_zero(interior - 1 / radicand, [x]):
        return None
    return {
        "radicand": radicand,
        "interior": sympy.together(interior),
        "radicand_equality": {"lhs": str(sympy.together(interior)), "rhs": str(1 / radicand)},
    }


def _structured_real_line_domain(lhs, rhs, symbols, child_cert):
    if len(symbols) != 1:
        return None
    x = syms_like(lhs - rhs, symbols)[0]
    parent = _parent_domain_data(lhs, rhs, x, child_cert)
    if parent is None:
        return None
    root = child_cert["root_atoms"][0]
    if _check_sos_positivity(parent["radicand"], root.get("positivity_certificate"), x) is None:
        return None
    return {
        "kind": "real_line", "variable": str(x),
        "connected": True,
        "definedness_and_differentiability_obligations": [
            {"expression": str(parent["radicand"]), "relation": "> 0", "reason": "atan/inner sqrt"},
            {"expression": str(parent["interior"]), "relation": "> 0", "reason": "asin interior"},
        ],
        "verified_radicand_equalities": [parent["radicand_equality"]],
    }


def build_derivative_base_point_composite_certificate(lhs, rhs, symbols, domain):
    """Build a T3 upgrade only after every child and real-line obligation is exact."""
    if not isinstance(domain, dict) or domain.get("kind") != "real_line" or \
            len(symbols) != 1 or domain.get("variable") != symbols[0]:
        return None
    x = syms_like(lhs - rhs, symbols)[0]
    if x.is_real is not True:
        return None
    try:
        derivative_lhs, derivative_rhs = sympy.diff(lhs, x), sympy.diff(rhs, x)
    except Exception:
        return None
    child_cert = build_positive_sqrt_algebraic_cofactor_certificate(
        derivative_lhs, derivative_rhs, symbols)
    if child_cert is None:
        return None
    child_claim = {"lhs": str(derivative_lhs), "rhs": str(derivative_rhs), "symbols": list(symbols)}
    if not _recheck_positive_sqrt(derivative_lhs, derivative_rhs, symbols, child_cert)["ok"]:
        return None
    try:
        lhs_at_zero, rhs_at_zero = lhs.subs(x, sympy.Integer(0)), rhs.subs(x, sympy.Integer(0))
    except Exception:
        return None
    if lhs_at_zero != rhs_at_zero:
        return None
    domain_cert = _structured_real_line_domain(lhs, rhs, symbols, child_cert)
    if domain_cert is None:
        return None
    cert = {
        "kind": "derivative_base_point_composite", "certificate_version": "1.0",
        "real_domain": True, "parent_claim_hash": _claim_hash(lhs, rhs, symbols), "symbols": list(symbols),
        "domain_certificate": domain_cert,
        "derivative_child": {
            **child_claim, "claim_hash": _claim_hash(derivative_lhs, derivative_rhs, symbols),
            "certificate": child_cert,
        },
        "base_point_certificate": {
            "point": {symbols[0]: "0"}, "lhs_value": str(lhs_at_zero), "rhs_value": str(rhs_at_zero),
            "claim_hash": sha({"parent_claim_hash": _claim_hash(lhs, rhs, symbols), "point": {symbols[0]: "0"},
                               "lhs_value": str(lhs_at_zero), "rhs_value": str(rhs_at_zero)}),
        },
        "independently_recheckable": True,
        "recheck_procedure": "differentiate both parent sides, recheck the positive-root child, "
                             "then recheck x=0 and the structured connected real-line obligations.",
    }
    cert["artifact_hash"] = _artifact_hash(cert)
    return cert


def _recheck_derivative_base_point_composite(claim, lhs, rhs, symbols, cert):
    if cert.get("certificate_version") != "1.0" or cert.get("real_domain") is not True or \
            cert.get("symbols") != list(symbols) or cert.get("independently_recheckable") is not True:
        return {"ok": False, "detail": "composite certificate metadata is invalid"}
    if len(symbols) != 1 or cert.get("parent_claim_hash") != _claim_hash(lhs, rhs, symbols):
        return {"ok": False, "detail": "parent claim hash mismatch"}
    domain = cert.get("domain_certificate")
    if not isinstance(domain, dict) or domain.get("kind") != "real_line" or \
            domain.get("variable") != symbols[0] or domain.get("connected") is not True:
        return {"ok": False, "detail": "structured connected real-line domain is missing or invalid"}
    x = syms_like(lhs - rhs, symbols)[0]
    try:
        derivative_lhs, derivative_rhs = sympy.diff(lhs, x), sympy.diff(rhs, x)
    except Exception:
        return {"ok": False, "detail": "could not independently differentiate parent sides"}
    child = cert.get("derivative_child")
    if not isinstance(child, dict) or child.get("lhs") != str(derivative_lhs) or \
            child.get("rhs") != str(derivative_rhs) or child.get("symbols") != list(symbols) or \
            child.get("claim_hash") != _claim_hash(derivative_lhs, derivative_rhs, symbols):
        return {"ok": False, "detail": "derivative child does not match independently differentiated parent"}
    child_result = recheck({"lhs": str(derivative_lhs), "rhs": str(derivative_rhs),
                            "symbols": list(symbols)}, child.get("certificate"))
    if not child_result.get("ok"):
        return {"ok": False, "detail": f"derivative child failed: {child_result.get('detail')}"}
    base = cert.get("base_point_certificate")
    expected_point = {symbols[0]: "0"}
    if not isinstance(base, dict) or base.get("point") != expected_point:
        return {"ok": False, "detail": "only the independently checked x=0 base point is supported"}
    try:
        lhs_value, rhs_value = lhs.subs(x, sympy.Integer(0)), rhs.subs(x, sympy.Integer(0))
    except Exception:
        return {"ok": False, "detail": "base-point substitution failed"}
    expected_base_hash = sha({"parent_claim_hash": _claim_hash(lhs, rhs, symbols), "point": expected_point,
                              "lhs_value": str(lhs_value), "rhs_value": str(rhs_value)})
    if lhs_value != rhs_value or base.get("lhs_value") != str(lhs_value) or \
            base.get("rhs_value") != str(rhs_value) or base.get("claim_hash") != expected_base_hash:
        return {"ok": False, "detail": "base-point equality does not recheck"}
    expected_domain = _structured_real_line_domain(lhs, rhs, symbols, child.get("certificate"))
    if expected_domain is None or domain != expected_domain:
        return {"ok": False, "detail": "definedness, differentiability, or connected-domain obligations fail"}
    if cert.get("artifact_hash") != _artifact_hash(cert):
        return {"ok": False, "detail": "composite certificate artifact hash mismatch"}
    return {"ok": True, "detail": "re-verified derivative/base-point composite on the connected real line"}


def _exact_zero_on_grid(diff, syms, values):
    """Evaluate `diff` in EXACT arithmetic over the full product grid values^n.

    Returns (all_zero: bool, first_nonzero_point | None). No simplify — only subs + exact
    rational arithmetic, then a structural test that the result is the zero number.
    """
    n = len(syms)
    # iterate the product grid values^n without itertools (kept explicit + bounded)
    idx = [0] * n
    total = len(values) ** n
    for _ in range(total):
        point = {syms[i]: sympy.Integer(values[idx[i]]) for i in range(n)}
        val = diff.subs(point)
        # exact: for a polynomial with rational coeffs at integer points, subs yields an
        # exact rational number; require it to be exactly zero (no float, no simplify)
        if not (val.is_number and val == 0):
            return False, {str(syms[i]): int(values[idx[i]]) for i in range(n)}
        # increment mixed-radix counter
        j = n - 1
        while j >= 0:
            idx[j] += 1
            if idx[j] < len(values):
                break
            idx[j] = 0; j -= 1
    return True, None


def _claim_degree(lhs, rhs, syms):
    """Total-degree upper bound of the CLAIM = max(deg lhs, deg rhs), each as a polynomial.

    Sizing the grid by the CLAIM's degree (not the possibly-canceled lhs-rhs) is what makes
    the certificate sound: for a true identity lhs-rhs cancels to 0 (degree -inf), so using
    its degree would give a 1-point grid that certifies nothing.
    """
    degs = []
    for e in (lhs, rhs):
        try:
            p = sympy.Poly(sympy.expand(e), *syms)   # expand + Poly, NOT simplify
        except Exception:
            return None
        if p.free_symbols - set(syms):               # symbolic coefficients -> not a plain poly
            return None
        d = p.total_degree()
        degs.append(0 if d < 0 else d)
    return max(degs) if degs else 0


def build_polynomial_certificate(lhs, rhs, symbols):
    """Return a re-checkable polynomial certificate, or None if not applicable/too large."""
    syms = syms_like(lhs - rhs, symbols)
    if not syms:
        return None
    d = _claim_degree(lhs, rhs, syms)
    if d is None:
        return None
    values = list(range(-(d // 2), -(d // 2) + (d + 1)))  # d+1 distinct integers, centered
    if len(values) ** len(syms) > MAX_GRID_POINTS:
        return None
    all_zero, witness = _exact_zero_on_grid(lhs - rhs, syms, values)
    if not all_zero:
        return None
    return {
        "kind": "polynomial_pointwise_nullstellensatz",
        "real_domain": bool(getattr(lhs, "free_symbols", set()) and
                            all(getattr(t, "is_real", None) for t in (lhs - rhs).free_symbols)),
        "total_degree": int(d), "symbols": list(symbols),
        "per_variable_values": values, "grid_points": len(values) ** len(syms),
        "all_residuals_exactly_zero": True,
        "recheck_procedure": "evaluate lhs-rhs in exact arithmetic at the product grid of "
                             "per_variable_values; identically zero iff every value is 0 "
                             "(polynomial identity lemma, |S| = deg+1). No simplify required.",
        "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "degree": int(d), "values": values})}


def recheck(claim, certificate):
    """Independently re-verify a claim + certificate WITHOUT sympy.simplify.

    claim: {lhs, rhs, symbols}. certificate: a polynomial_pointwise_nullstellensatz cert.
    Returns {"ok": bool, "detail": str}.
    """
    if not isinstance(certificate, dict):
        return {"ok": False, "detail": "unsupported or missing certificate kind"}
    kind = certificate.get("kind")
    if kind == _subdomain.CERTIFICATE_KIND:
        return _subdomain.recheck(claim, certificate)
    symbols = (claim.get("symbols") or certificate.get("symbols")
               or certificate.get("base_symbols") or [])
    _real = bool(certificate.get("real_domain"))
    try:
        lhs = validate_and_parse(claim["lhs"], symbols, real=_real)
        rhs = validate_and_parse(claim["rhs"], symbols, real=_real)
    except Exception as e:
        return {"ok": False, "detail": f"parse failed: {getattr(e, 'code', e)}"}
    # dispatch: T1 trig-ideal cofactor / T2 exp-rational numerator / polynomial grid
    if kind == "trig_ideal_cofactor":
        return _recheck_trig(lhs, rhs, symbols, certificate)
    if kind == "exp_rational_numerator":
        return _recheck_exp(lhs, rhs, symbols, certificate)
    if kind == "positive_sqrt_algebraic_cofactor":
        return _recheck_positive_sqrt(lhs, rhs, symbols, certificate)
    if kind == "derivative_base_point_composite":
        return _recheck_derivative_base_point_composite(claim, lhs, rhs, symbols, certificate)
    if kind != "polynomial_pointwise_nullstellensatz":
        return {"ok": False, "detail": "unsupported or missing certificate kind"}
    syms = syms_like(lhs - rhs, symbols)
    values = certificate.get("per_variable_values")
    if not isinstance(values, list) or not values or len(set(values)) != len(values):
        return {"ok": False, "detail": "invalid or non-distinct grid values"}
    # RECOMPUTE the required degree from the CLAIM itself — do not trust the cert's degree.
    # This is what defeats a tampered cert that under-states the degree of a false identity.
    d_required = _claim_degree(lhs, rhs, syms)
    if d_required is None:
        return {"ok": False, "detail": "claim is not a polynomial in the declared symbols"}
    if len(values) < d_required + 1:
        return {"ok": False, "detail": f"grid too small: |S|={len(values)} but claim degree "
                                       f"{d_required} needs |S| > {d_required}"}
    if len(values) ** len(syms) > MAX_GRID_POINTS:
        return {"ok": False, "detail": "grid too large to re-check"}
    all_zero, witness = _exact_zero_on_grid(lhs - rhs, syms, values)
    if not all_zero:
        return {"ok": False, "detail": f"non-zero residual at {witness} — certificate is INVALID"}
    return {"ok": True, "detail": f"re-verified: lhs-rhs exactly 0 at all {len(values)**len(syms)} "
                                  f"grid points (deg {d_required}); independent of simplify"}


# ---------------------------------------------------------------------------------
# T1 / T2 — make TRANSCENDENTAL identities independently re-checkable by reducing them
# to a POLYNOMIAL problem plus explicitly stated side conditions.
#
# Design principle: the BUILDER may use heuristic rewrites (expand_trig, together) — the
# certificate is only worth anything because the RE-CHECKER independently re-derives the
# polynomial and verifies the algebra with exact expansion — never a simplify call.
# ---------------------------------------------------------------------------------

def _expand_tanlike(d):
    """Expand tan/cot/sec/csc into sin/cos WITHOUT rewriting sin<->cos.

    (A sin<->cos rewrite would turn sin(x) into cos(x - pi/2) and destroy the atom map.)
    """
    d = d.replace(sympy.tan, lambda a: sympy.sin(a) / sympy.cos(a))
    d = d.replace(sympy.cot, lambda a: sympy.cos(a) / sympy.sin(a))
    d = d.replace(sympy.sec, lambda a: 1 / sympy.cos(a))
    d = d.replace(sympy.csc, lambda a: 1 / sympy.sin(a))
    return d


def _trig_reduce(lhs, rhs, symbols):
    """T1 reduction: trig claim -> (numerator polynomial P, ideal, gens, denominator, atom map).

    Deterministic structural steps only. Returns None if the claim does not reduce to a
    polynomial in the sin/cos atoms of the declared base symbols.
    """
    syms = syms_like(lhs - rhs, symbols)
    d = _expand_tanlike(sympy.expand_trig(lhs - rhs))
    num, den = sympy.fraction(sympy.together(d))
    amap, ideal, gens, readable = {}, [], [], {}
    for v in syms:
        s_v, c_v = sympy.Symbol(f"s_{v}"), sympy.Symbol(f"c_{v}")
        amap[sympy.sin(v)] = s_v; amap[sympy.cos(v)] = c_v
        readable[f"sin({v})"] = str(s_v); readable[f"cos({v})"] = str(c_v)
        ideal.append(s_v**2 + c_v**2 - 1); gens += [s_v, c_v]
    P = sympy.expand(num.subs(amap))
    if P.free_symbols - set(gens):        # leftover transcendental atoms -> not T1
        return None
    return P, ideal, gens, sympy.expand(den.subs(amap)), readable


def build_trig_cofactor_certificate(lhs, rhs, symbols):
    """T1 certificate: cofactors g_i with P = sum(g_i * p_i) over the Pythagorean ideal.

    Only applies to claims that ACTUALLY contain circular-trig atoms. Without this guard the
    reduction degenerates (a difference that cancels to 0 before the substitution yields a
    vacuous P=0 with empty cofactors) and a polynomial or exp claim would be handed a
    certificate labelled "trig_ideal_cofactor" — a valid proof, but a misdescribed one.
    """
    if not any((lhs - rhs).atoms(f) for f in (sympy.sin, sympy.cos, sympy.tan,
                                              sympy.cot, sympy.sec, sympy.csc)):
        return None
    r = _trig_reduce(lhs, rhs, symbols)
    if r is None:
        return None
    P, ideal, gens, den, readable = r
    if den == 0:
        return None
    try:
        q, rem = sympy.reduced(P, ideal, *gens)
    except Exception:
        return None
    if rem != 0 or sympy.expand(sum(qi * pi for qi, pi in zip(q, ideal)) - P) != 0:
        return None
    return {
        "kind": "trig_ideal_cofactor",
        "real_domain": bool(getattr(lhs, "free_symbols", set()) and
                            all(getattr(t, "is_real", None) for t in (lhs - rhs).free_symbols)),
        "base_symbols": list(symbols),
        "atom_encoding": readable,
        "constraint_polynomials": [str(p) for p in ideal],
        "cofactors": [str(t) for t in q],
        "numerator_polynomial": str(P),
        "denominator_side_condition": f"{den} != 0",
        "soundness": "x -> (sin x, cos x) covers the unit circle, so a polynomial in the "
                     "ideal <s^2+c^2-1> vanishes for every real x",
        "recheck_procedure": "re-derive P from the claim (expand_trig, expand tan/cot/sec/csc, "
                             "together, substitute sin/cos atoms), then verify "
                             "expand(sum(g_i*p_i) - P) == 0 by exact polynomial arithmetic",
        "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "P": str(P)})}


def _exp_reduce(lhs, rhs, symbols):
    """T2 reduction: exp/hyperbolic claim -> (numerator N, denominator D, gens, encoding)."""
    syms = syms_like(lhs - rhs, symbols)
    d = sympy.together(sympy.expand((lhs - rhs).rewrite(sympy.exp)))
    num, den = sympy.fraction(d)
    emap, gens, readable = {}, [], {}
    for v in syms:
        E = sympy.Symbol(f"E_{v}", positive=True); gens.append(E)
        for a in (num.atoms(sympy.exp) | den.atoms(sympy.exp)):
            k = sympy.expand(a.args[0] / v)
            if k.is_Integer:
                emap[a] = E**int(k); readable[str(a)] = f"{E}**{int(k)}"
    N = sympy.expand(num.subs(emap)); D = sympy.expand(den.subs(emap))
    if (N.free_symbols | D.free_symbols) - set(gens):
        return None
    return N, D, gens, readable


def build_exp_polynomial_certificate(lhs, rhs, symbols):
    """T2 certificate: after E = e^x substitution and clearing denominators, N is identically 0.

    Same guard as T1: require actual exponential/hyperbolic content, so a claim of another
    kind is never handed a certificate that misdescribes how it was proved.
    """
    if not any((lhs - rhs).atoms(f) for f in (sympy.exp, sympy.sinh, sympy.cosh, sympy.tanh)):
        return None
    r = _exp_reduce(lhs, rhs, symbols)
    if r is None:
        return None
    N, D, gens, readable = r
    if D == 0 or N != 0:
        return None
    return {
        "kind": "exp_rational_numerator",
        "real_domain": bool(getattr(lhs, "free_symbols", set()) and
                            all(getattr(t, "is_real", None) for t in (lhs - rhs).free_symbols)),
        "base_symbols": list(symbols),
        "exp_encoding": readable,
        "numerator_polynomial": str(N),
        "numerator_is_identically_zero": True,
        "denominator_side_condition": f"{D} != 0 (and E_v > 0)",
        "soundness": "E = e^x ranges over the infinite set (0, inf), so a polynomial in E "
                     "vanishing there is identically zero",
        "recheck_procedure": "re-derive N from the claim (rewrite to exp, substitute "
                             "exp(k*v) -> E_v**k, together, take numerator) and verify "
                             "expand(N) == 0; also verify the denominator is not identically 0",
        "artifact_hash": sha({"lhs": str(lhs), "rhs": str(rhs), "N": str(N)})}


def _recheck_trig(lhs, rhs, symbols, cert):
    r = _trig_reduce(lhs, rhs, symbols)
    if r is None:
        return {"ok": False, "detail": "claim does not reduce to the declared trig atoms"}
    P, ideal, gens, den, _ = r
    if den == 0:
        return {"ok": False, "detail": "denominator side condition violated (identically zero)"}
    # the cert's own numerator must match the independently re-derived one
    try:
        P_cert = sympy.sympify(cert.get("numerator_polynomial"), locals={str(g): g for g in gens})
        cofs = [sympy.sympify(c, locals={str(g): g for g in gens}) for c in cert.get("cofactors", [])]
        ideal_cert = [sympy.sympify(p, locals={str(g): g for g in gens})
                      for p in cert.get("constraint_polynomials", [])]
    except Exception:
        return {"ok": False, "detail": "certificate polynomials are unparseable"}
    if sympy.expand(P_cert - P) != 0:
        return {"ok": False, "detail": "certificate numerator does not match the claim"}
    if len(cofs) != len(ideal_cert):
        return {"ok": False, "detail": "cofactor/constraint count mismatch"}
    for p_declared, p_true in zip(ideal_cert, ideal):
        if sympy.expand(p_declared - p_true) != 0:
            return {"ok": False, "detail": "declared constraint is not the Pythagorean relation"}
    residual = sympy.expand(sum(g * p for g, p in zip(cofs, ideal_cert)) - P)
    if residual != 0:
        return {"ok": False, "detail": f"cofactor identity FAILS: residual {residual}"}
    return {"ok": True, "detail": "re-verified: P = sum(g_i*p_i) exactly over the Pythagorean "
                                  "ideal; identity holds for all real x. No simplify used."}


def _recheck_exp(lhs, rhs, symbols, cert):
    r = _exp_reduce(lhs, rhs, symbols)
    if r is None:
        return {"ok": False, "detail": "claim does not reduce to polynomials in E = e^x"}
    N, D, gens, _ = r
    if D == 0:
        return {"ok": False, "detail": "denominator side condition violated (identically zero)"}
    if sympy.expand(N) != 0:
        return {"ok": False, "detail": f"numerator is NOT identically zero: {N}"}
    return {"ok": True, "detail": "re-verified: cleared-denominator numerator is exactly 0 as a "
                                  "polynomial in E = e^x. No simplify used."}
