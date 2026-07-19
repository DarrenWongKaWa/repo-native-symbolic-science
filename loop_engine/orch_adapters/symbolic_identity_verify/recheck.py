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
from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse, sha

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
    syms = [sympy.Symbol(s) for s in symbols]
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
    if not isinstance(certificate, dict) or certificate.get("kind") != "polynomial_pointwise_nullstellensatz":
        return {"ok": False, "detail": "unsupported or missing certificate kind"}
    symbols = claim.get("symbols") or certificate.get("symbols") or []
    try:
        lhs = validate_and_parse(claim["lhs"], symbols)
        rhs = validate_and_parse(claim["rhs"], symbols)
    except Exception as e:
        return {"ok": False, "detail": f"parse failed: {getattr(e, 'code', e)}"}
    syms = [sympy.Symbol(s) for s in symbols]
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
