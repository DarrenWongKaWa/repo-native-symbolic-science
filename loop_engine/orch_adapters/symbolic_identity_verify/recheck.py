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
import sympy
from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse, sha, syms_like

MAX_GRID_POINTS = 20000   # cap: (d+1)^n must not exceed this to be "cheaply re-checkable"


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
    """T1 certificate: cofactors g_i with P = sum(g_i * p_i) over the Pythagorean ideal."""
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
    """T2 certificate: after E = e^x substitution and clearing denominators, N is identically 0."""
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
