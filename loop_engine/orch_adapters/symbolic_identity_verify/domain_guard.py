#!/usr/bin/env python3
"""Domain guard — definedness obligations for a claimed identity.

Found by the Gate-5 "prove a false thing" attacks: the judge compared expressions as
ALGEBRAIC objects while the claim asserts equality as FUNCTIONS on a declared domain. So
it certified things that are false where the expressions are undefined:

    (x^2-1)/(x-1) == x+1        equal as rational functions, but LHS is undefined at x=1
    x/x == 1                    undefined at x=0
    sqrt(x)*sqrt(x) == x        not real-defined for x<0

This module extracts the DEFINEDNESS OBLIGATIONS of an expression (denominators that must
not vanish, even-root arguments that must be non-negative, log arguments that must be
positive) and decides whether any of them can actually fail on the declared domain.

If an obligation can fail, the judge must NOT issue an unconditional identity certificate;
it issues a side-conditioned one instead, so nobody can read the verdict as "equal
everywhere on the reals".
"""
from __future__ import annotations
import sympy

REAL_SCOPES = {"real_scalars", "reals", "R", "real"}


def _obligations(expr):
    """Collect (kind, expression) definedness obligations of `expr`."""
    obs = []
    # denominators anywhere (negative powers included)
    for p in expr.atoms(sympy.Pow):
        base, e = p.as_base_exp()
        if e.is_number and e.is_negative:
            obs.append(("nonzero", base))
        # even roots need a non-negative argument over the reals
        if getattr(e, "q", None) == 2 or e == sympy.Rational(1, 2):
            obs.append(("nonnegative", base))
    num, den = sympy.fraction(sympy.together(expr))
    if den.free_symbols:
        obs.append(("nonzero", den))
    for l in expr.atoms(sympy.log):
        obs.append(("positive", l.args[0]))
    # dedupe structurally
    seen, out = set(), []
    for kind, e in obs:
        k = (kind, sympy.srepr(e))
        if k not in seen:
            seen.add(k); out.append((kind, e))
    return out


def _can_fail_on_reals(kind, e, syms):
    """True if the obligation can be violated somewhere on the real domain."""
    try:
        if kind == "nonzero":
            sol = sympy.solveset(sympy.Eq(e, 0), syms[0], domain=sympy.S.Reals)
            return sol is not sympy.S.EmptySet and sol != sympy.S.EmptySet
        if kind == "nonnegative":
            sol = sympy.solveset(e < 0, syms[0], domain=sympy.S.Reals)
            return sol is not sympy.S.EmptySet and sol != sympy.S.EmptySet
        if kind == "positive":
            sol = sympy.solveset(e <= 0, syms[0], domain=sympy.S.Reals)
            return sol is not sympy.S.EmptySet and sol != sympy.S.EmptySet
    except Exception:
        return True          # analysis failed -> be conservative, treat as a real obligation
    return False


def _parse_unevaluated(expr_str, symbols, sym_objs=None):
    """Re-parse the ORIGINAL string with evaluate=False.

    sympy's constructor auto-simplifies at parse time: `x/x` becomes `1` and
    `sqrt(x)*sqrt(x)` becomes `x`, destroying the definedness evidence before it can be
    analysed. The string has already passed the strict whitelist in the main parse, so
    re-parsing it here adds no new attack surface — it only preserves structure.
    """
    local = ({str(o): o for o in sym_objs} if sym_objs
             else {s: sympy.Symbol(s) for s in symbols})
    for f in ("sqrt", "log", "exp", "sin", "cos", "tan", "asin", "acos", "atan",
              "sinh", "cosh", "tanh", "Abs"):
        fn = getattr(sympy, f, None)
        if fn is not None:
            local[f] = fn
    try:
        return sympy.sympify(expr_str, locals=local, evaluate=False)
    except Exception:
        return None


def analyse(lhs, rhs, symbols, scope, lhs_str=None, rhs_str=None):
    """Return (side_conditions, excluded_description).

    side_conditions is a list of human-readable conditions that must hold for the claimed
    identity to be an identity of FUNCTIONS on the declared domain. Empty list means the
    claim is unconditional there.
    """
    if not symbols:
        return [], None
    from loop_engine.orch_adapters._symbolic_safe_parse import syms_like
    syms = syms_like(lhs, symbols) if getattr(lhs,'free_symbols',None) else [sympy.Symbol(s) for s in symbols]
    conds = []
    # prefer the unevaluated parse: auto-evaluation hides x/x and sqrt(x)*sqrt(x)
    targets = []
    for expr, src in ((lhs, lhs_str), (rhs, rhs_str)):
        raw = _parse_unevaluated(src, symbols, syms) if src else None
        targets.append(raw if raw is not None else expr)
    for expr in targets:
        for kind, e in _obligations(expr):
            if not e.free_symbols:
                continue
            if _can_fail_on_reals(kind, e, syms):
                rel = {"nonzero": "!= 0", "nonnegative": ">= 0", "positive": "> 0"}[kind]
                # normalise for display/dedupe: the unevaluated parse yields forms like
                # "x - 1*1" that are the same obligation as "x - 1"
                c = f"{sympy.expand(e)} {rel}"
                if c not in conds:
                    conds.append(c)
    if not conds:
        return [], None
    where = "the declared real domain" if (scope or "").lower() in REAL_SCOPES else f"scope '{scope}'"
    return conds, (f"the identity holds only where these hold on {where}; "
                   f"it is NOT an identity of functions on all of {where}")
