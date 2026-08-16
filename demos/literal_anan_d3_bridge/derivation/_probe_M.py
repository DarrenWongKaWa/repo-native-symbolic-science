#!/usr/bin/env python3
"""Probe A: does [w^2] rho^(1)_{nm}(w) reproduce the S03 M normal form exactly?"""
import sympy as sp
w, x, y = sp.symbols("w x y", real=True)
G, b, mu = sp.symbols("Gamma beta mu", positive=True)
I = sp.I
fp, fm, rho0 = sp.symbols("fp fm rho0")  # placeholder replaced below

# symbolic functions
Fp = sp.Function("Fp"); Fm = sp.Function("Fm"); R = sp.Function("R")
def D(f, u, v): return (f(v) - f(u)) / (v - u)

num = R(y) - R(x) + I*G*(D(Fm, x, y + w) + D(Fp, x - w, y))
rho1 = num / (w + y - x + 2*I*G)
M_derived = sp.simplify(sp.Rational(1, 2) * sp.diff(rho1, w, 2).subs(w, 0))
print("M_derived (ops):", sp.count_ops(M_derived))
print(sp.simplify(M_derived))
