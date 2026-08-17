#!/usr/bin/env python3
"""Mechanical derivation of the massive Dirac quantum-metric claims.

g_ij = (1/4) (d_i n) . (d_j n) with n = (kx,ky,m)/sqrt(kx^2+ky^2+m^2). The
mechanical strings below are the unsimplified dot products and the
unsimplified determinant built from them; the judge proves the closed forms.

Claims:
  B1_gxx, B2_gyy, B3_gxy   positive   metric components == closed forms
  B4_det                   positive   g_xx g_yy - g_xy^2 == m^2/(16 R^6)
  B5_det_eq_omega2_4       positive   det(g) == Omega_xy^2 / 4
  Bm_gxy_signflip          mutation   g_xy -> +kx ky/(4 R^4)
  Bm_omega2_half           mutation   Omega^2/4 -> Omega^2/2
  Bu_cross                 unsupported_grammar
"""
import json
import sympy as sp
from sympy import sqrt

kx, ky, m = sp.symbols("kx ky m", real=True)
R2 = kx**2 + ky**2 + m**2
R = sqrt(R2)
n = sp.Matrix([kx, ky, m]) / R
nx = sp.diff(n, kx)
ny = sp.diff(n, ky)

gxx = sp.expand(sp.Rational(1, 4) * nx.dot(nx))
gyy = sp.expand(sp.Rational(1, 4) * ny.dot(ny))
gxy = sp.expand(sp.Rational(1, 4) * nx.dot(ny))
gxx_raw, gyy_raw, gxy_raw = sp.sstr(gxx), sp.sstr(gyy), sp.sstr(gxy)
det_raw = "(" + gxx_raw + ")*(" + gyy_raw + ") - (" + gxy_raw + ")**2"

R4 = "(kx**2+ky**2+m**2)**2"
R6 = "(kx**2+ky**2+m**2)**3"
R3 = "sqrt(kx**2+ky**2+m**2)**3"
SYM = ["kx", "ky", "m"]
ASM = ["kx,ky real; m real nonzero (gapped real domain; R>0 where m!=0)"]

records = [
    {"id": "B1_gxx", "kind": "positive", "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": gxx_raw, "rhs": "(ky**2+m**2)/(4*" + R4 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "B2_gyy", "kind": "positive", "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": gyy_raw, "rhs": "(kx**2+m**2)/(4*" + R4 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "B3_gxy", "kind": "positive", "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": gxy_raw, "rhs": "-kx*ky/(4*" + R4 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "B4_det", "kind": "positive", "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": det_raw, "rhs": "m**2/(16*" + R6 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "B5_det_eq_omega2_4", "kind": "positive", "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": det_raw, "rhs": "((-m/(2*" + R3 + "))**2)/4",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Bm_gxy_signflip", "kind": "mutation",
     "obligation": "numeric counterexample probe (wrong g_xy sign must be refuted)",
     "claim": {"lhs": gxy_raw, "rhs": "+kx*ky/(4*" + R4 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Bm_omega2_half", "kind": "mutation",
     "obligation": "numeric counterexample probe (Omega^2/2 instead of Omega^2/4 must be refuted)",
     "claim": {"lhs": det_raw, "rhs": "((-m/(2*" + R3 + "))**2)/2",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Bu_cross", "kind": "unsupported_grammar",
     "obligation": "whitelist parser (matrix syntax is not judge grammar; fail closed)",
     "claim": {"lhs": "matrix(kx,ky)", "rhs": "0",
               "symbols": ["kx", "ky"], "scope": "real_scalars",
               "assumptions": ["kx,ky real"]}},
]
for r in records:
    print(json.dumps(r))
