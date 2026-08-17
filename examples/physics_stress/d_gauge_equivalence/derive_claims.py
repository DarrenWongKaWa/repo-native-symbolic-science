#!/usr/bin/env python3
"""Gauge-equivalence claims for constant magnetic field B.

  A_sym = (-B y/2, B x/2)     (symmetric gauge)
  A_L   = (0, B x)            (Landau gauge)
  chi   = B x y / 2

The derivation layer computes the gauge difference and the curls with exact
sympy differentiation; the claims below are the resulting mechanical
pointwise residuals (componentwise A_L - A_sym - grad(chi) == 0 and
curl(A) - B == 0 for both gauges).

Claims:
  D1_gauge_x, D2_gauge_y   positive            gauge-difference residuals == 0
  D3_curl_sym, D4_curl_L   positive            curl residuals == 0
  D5_pointwise_neq         negative_control    A_L^y == A_sym^y is FALSE pointwise
  Dm_chi_no_half           mutation            chi -> B*x*y (missing 1/2)
  Du_cross                 unsupported_grammar
"""
import json
import sympy as sp

B_, x, y = sp.symbols("B x y", real=True)
# exact sympy checks (derivation layer; keep for provenance, not submitted)
A_sym = sp.Matrix([-B_ * y / 2, B_ * x / 2])
A_L = sp.Matrix([0, B_ * x])
chi = B_ * x * y / 2
assert sp.simplify(A_L - A_sym - sp.Matrix([sp.diff(chi, x), sp.diff(chi, y)])) == sp.zeros(2, 1)
assert sp.simplify(sp.diff(A_sym[1], x) - sp.diff(A_sym[0], y) - B_) == 0
assert sp.simplify(sp.diff(A_L[1], x) - sp.diff(A_L[0], y) - B_) == 0

SYM = ["B", "x", "y"]
ASM = ["B,x,y real (constant magnetic field B; chi = B*x*y/2)"]
records = [
    {"id": "D1_gauge_x", "kind": "positive",
     "obligation": "pointwise gauge-difference residual (x component)",
     "claim": {"lhs": "0-(-B*y/2)-B*y/2", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "D2_gauge_y", "kind": "positive",
     "obligation": "pointwise gauge-difference residual (y component)",
     "claim": {"lhs": "B*x-B*x/2-B*x/2", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "D3_curl_sym", "kind": "positive",
     "obligation": "gauge-invariant curl of the symmetric gauge",
     "claim": {"lhs": "B/2-(-B/2)-B", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "D4_curl_landau", "kind": "positive",
     "obligation": "gauge-invariant curl of the Landau gauge",
     "claim": {"lhs": "B-0-B", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "D5_pointwise_neq", "kind": "negative_control",
     "obligation": "pointwise inequality must be refuted (potentials are gauge-equivalent, NOT pointwise equal)",
     "claim": {"lhs": "B*x-B*x/2", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Dm_chi_no_half", "kind": "mutation",
     "obligation": "numeric counterexample probe (chi -> B*x*y without the 1/2 must be refuted)",
     "claim": {"lhs": "0-(-B*y/2)-B*y", "rhs": "0",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Du_cross", "kind": "unsupported_grammar",
     "obligation": "whitelist parser (grad/curl operators are not judge grammar; fail closed)",
     "claim": {"lhs": "curl(B*x)", "rhs": "B",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
]
for r in records:
    print(json.dumps(r))
