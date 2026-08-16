#!/usr/bin/env python3
"""Mechanical derivation of the massive Dirac Berry curvature claims.

H(k) = kx*sx + ky*sy + m*sz   (Pauli matrices),  R^2 = kx^2+ky^2+m^2,  n = (kx,ky,m)/R.

The mechanical strings below are emitted BEFORE simplification: the projector
trace route builds P_-(k) = (I - n.sigma)/2 and forms Omega = -i*Tr(P*[dP/dkx, dP/dky]);
the unit-vector route forms the scalar triple product n . (dn/dkx x dn/dky). The
judge then proves both equal -m/(2 R^3). Cross products and matrix traces live in
THIS trusted derivation layer only; the judge never sees matrix syntax.

Claims (one JSONL record per line):
  A0_projector      positive-route-boundary  -i Tr(P[Px,Py]) == -m/(2 R^3)   (long mechanical string)
  A1_triple         positive                 n.(nx x ny)     ==  m/(R^2)^(3/2)
  A2_curvature      positive                 -1/2 n.(nx x ny) == -m/(2 R^3)   [the mission identity]
  Am_signflip       mutation                 -1/2 n.(nx x ny) == +m/(2 R^3)   [flipped Omega sign]
  Au_cross          unsupported_grammar      cross(kx,ky)    == 0
"""
import json
import sympy as sp
from sympy import sqrt, I

kx, ky, m = sp.symbols("kx ky m", real=True)
R2 = kx**2 + ky**2 + m**2
R = sqrt(R2)
n = sp.Matrix([kx, ky, m]) / R

# projector route
sx = sp.Matrix([[0, 1], [1, 0]])
sy = sp.Matrix([[0, -I], [I, 0]])
sz = sp.Matrix([[1, 0], [0, -1]])
P = (sp.eye(2) - (kx * sx + ky * sy + m * sz) / R) / 2
Px = sp.diff(P, kx)
Py = sp.diff(P, ky)
trace_raw = sp.sstr(I * sp.trace(P * (Px * Py - Py * Px)))

# unit-vector route
nx = sp.diff(n, kx)
ny = sp.diff(n, ky)
tp_raw = sp.sstr(n.dot(nx.cross(ny)))

R3 = "sqrt(kx**2+ky**2+m**2)**3"
SYM = ["kx", "ky", "m"]
ASM = ["kx,ky real; m real nonzero (gapped real domain; R=sqrt(kx^2+ky^2+m^2)>0 where m!=0)"]

records = [
    {"id": "A0_projector", "kind": "positive_route_boundary",
     "obligation": "B3 second engine (may decline on this 1000+ char mechanical string; fail-closed)",
     "claim": {"lhs": "-(" + trace_raw + ")", "rhs": "-m/(2*" + R3 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "A1_triple", "kind": "positive",
     "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": tp_raw, "rhs": "m/(kx**2+ky**2+m**2)**(3/2)",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "A2_curvature", "kind": "positive",
     "obligation": "domain guard (m != 0 side conditions)",
     "claim": {"lhs": "-(" + tp_raw + ")/2", "rhs": "-m/(2*" + R3 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Am_signflip", "kind": "mutation",
     "obligation": "numeric counterexample probe (sign flip of Omega_xy must be refuted)",
     "claim": {"lhs": "-(" + tp_raw + ")/2", "rhs": "+m/(2*" + R3 + ")",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Au_cross", "kind": "unsupported_grammar",
     "obligation": "whitelist parser (cross products are not judge grammar; fail closed)",
     "claim": {"lhs": "cross(kx,ky)", "rhs": "0",
               "symbols": ["kx", "ky"], "scope": "real_scalars",
               "assumptions": ["kx,ky real"]}},
]
for r in records:
    print(json.dumps(r))
