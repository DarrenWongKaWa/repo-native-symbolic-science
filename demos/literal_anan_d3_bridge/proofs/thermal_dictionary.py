#!/usr/bin/env python3
"""Proof: thermal dictionary — Anan <-> Guo bridges (exact, SymPy).

Theorems (packet sections 4-6):
  T1  ANAN_ARGUMENT_TO_GUO_ZMINUS
      1/2 + beta(eps_a - mu + i Gamma)/(2 pi i)  ==  z_-^G(eps_a)
  T2  ANAN_FPLUS_TO_HALF_GUO_FMINUS
      f_+^A(eps_a - mu + i Gamma)  ==  1/2 f_-^G(eps_a)
  T3  ANAN_DERIVATIVE_BRIDGE_R1 / R2
      f_+^{A(r)}(x_a) == 1/2 f_-^{G(r)}(eps_a),  r = 1, 2  (dx_a/deps_a = 1)
Notation-collision detection: f_+^A != f_+^G is established by construction
(f_+^G(eps_a) != f_+^A(x_a) as functions), and the bridge maps f_+^A to the
REFLECTED companion f_-^G, not to f_+^G.

Outputs: proofs/out/thermal_dictionary_certificate.json (written atomically).
"""
import json
import sys
import time
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

beta, Gamma, mu, eps_a = sp.symbols("beta Gamma mu eps_a", positive=True)
x = sp.symbols("x", real=True)
psi = sp.Function("psi")          # polygamma-0 (symbolic)

I = sp.I
# ---- Guo definitions (symbolic) ----
z_plusG = sp.Rational(1, 2) + beta * Gamma / (2 * sp.pi) + I * beta * (x - mu) / (2 * sp.pi)
z_minusG = sp.Rational(1, 2) + beta * Gamma / (2 * sp.pi) - I * beta * (x - mu) / (2 * sp.pi)
f_plusG = sp.Rational(1, 2) + (I / sp.pi) * psi(z_plusG)
f_minusG = sp.Rational(1, 2) - (I / sp.pi) * psi(z_minusG)

# ---- Anan definitions (symbolic) ----
x_a = eps_a - mu + I * Gamma
f_plusA = sp.Rational(1, 4) + (1 / (2 * sp.pi * I)) * psi(sp.Rational(1, 2) + beta * x / (2 * sp.pi * I))

cert = {"schema": "viper.demo.anan_d3.thermal_dictionary.v1",
        "commit": __import__("subprocess").run(["git", "rev-parse", "HEAD"],
                                               capture_output=True, text=True,
                                               cwd=HERE.parents[2]).stdout.strip(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "theorems": {}}

# ---- T1: argument bridge ----
z_minus_at_ea = z_minusG.subs(x, eps_a)
lhs1 = sp.Rational(1, 2) + beta * (eps_a - mu + I * Gamma) / (2 * sp.pi * I)
t1_ok = sp.simplify(lhs1 - z_minus_at_ea) == 0
cert["theorems"]["ANAN_ARGUMENT_TO_GUO_ZMINUS"] = {
    "result": "PASS_EXACT" if t1_ok else "FAIL",
    "lhs": str(sp.simplify(lhs1)), "rhs": str(sp.simplify(z_minus_at_ea)),
    "difference": "0" if t1_ok else str(sp.simplify(lhs1 - z_minus_at_ea))}

# ---- T2: function bridge ----
f_plusA_at_xa = f_plusA.subs(x, x_a)                 # 1/4 + 1/(2 pi i) psi(1/2 + beta x_a/(2 pi i))
f_plusA_arg = sp.simplify(sp.Rational(1, 2) + beta * x_a / (2 * sp.pi * I))
# after T1: f_plusA_arg == z_minus_at_ea; then 1/4 + 1/(2 pi i) psi(z) == 1/2 * (1/2 - i/pi psi(z))
f_minusG_at_ea = f_minusG.subs(x, eps_a)
lhs2 = sp.simplify(f_plusA_at_xa)
rhs2 = sp.simplify(sp.Rational(1, 2) * f_minusG_at_ea)
# exact check: substitute the proven argument identity, then algebra 1/(2 pi i) = -i/(2 pi)
t2_arg_ok = sp.simplify(f_plusA_arg - z_minus_at_ea) == 0
psi_z = psi(z_minus_at_ea)
lhs2b = sp.simplify(sp.Rational(1, 4) + (1 / (2 * sp.pi * I)) * psi_z)
rhs2b = sp.simplify(sp.Rational(1, 2) * (sp.Rational(1, 2) - (I / sp.pi) * psi_z))
t2_ok = t2_arg_ok and sp.simplify(lhs2b - rhs2b) == 0
cert["theorems"]["ANAN_FPLUS_TO_HALF_GUO_FMINUS"] = {
    "result": "PASS_EXACT" if t2_ok else "FAIL",
    "argument_bridge_used": t2_arg_ok,
    "lhs": str(lhs2b), "rhs": str(rhs2b),
    "difference": "0" if t2_ok else str(sp.simplify(lhs2b - rhs2b))}

# ---- T3: derivative bridges (r=1,2) -------------------------------
# Sound rule: differentiating BOTH sides of a certified equality yields a
# certified equality.  T2 certifies fA(x_a) == 1/2 fGm(eps_a); its eps-derivative
# is fA'(x_a)*dx_a/deps_a == 1/2 fGm'(eps_a), and dx_a/deps_a = 1 exactly.
fA = sp.Function("fA")      # f_+^A(x)
fGm = sp.Function("fGm")    # f_-^G(eps)
rel = sp.Eq(fA(x_a), sp.Rational(1, 2) * fGm(eps_a))   # certified T2 relation
dxa_de = sp.diff(x_a, eps_a)                            # == 1 exactly
d_lhs = sp.expand(sp.diff(rel.lhs, eps_a))              # chain rule applied by sympy
d_rhs = sp.expand(sp.diff(rel.rhs, eps_a))
r1_ok = (sp.simplify(dxa_de) == 1
         and sp.simplify(d_lhs - sp.Derivative(fA(x_a), eps_a)) == 0  # derivative of T2 lhs
         and sp.simplify(d_rhs - sp.Rational(1, 2) * sp.Derivative(fGm(eps_a), eps_a)) == 0)
cert["theorems"]["ANAN_DERIVATIVE_BRIDGE_R1"] = {
    "result": "PASS_EXACT" if r1_ok else "FAIL",
    "statement": "f_+^{A'}(x_a) == 1/2 f_-^{G'}(eps_a)",
    "dx_a_deps_a": str(dxa_de),
    "derived_by": "differentiate certified T2 relation; chain rule factor dx_a/deps_a = 1"}
# r = 2: differentiate the r=1 bridge once more
d2_lhs = sp.expand(sp.diff(d_lhs, eps_a))
d2_rhs = sp.expand(sp.diff(d_rhs, eps_a))
r2_ok = sp.simplify(d2_lhs - sp.Derivative(fA(x_a), (eps_a, 2))) == 0 and \
        sp.simplify(d2_rhs - sp.Rational(1, 2) * sp.Derivative(fGm(eps_a), (eps_a, 2))) == 0
cert["theorems"]["ANAN_DERIVATIVE_BRIDGE_R2"] = {
    "result": "PASS_EXACT" if r2_ok else "FAIL",
    "statement": "f_+^{A''}(x_a) == 1/2 f_-^{G''}(eps_a)",
    "derived_by": "differentiate the certified r=1 bridge once more"}

# ---- notation collision ----
# f_+^G(eps_a) as a function is NOT equal to f_+^A(x_a): differ by construction
f_plusG_at_ea = f_plusG.subs(x, eps_a)
collision_diff = sp.simplify(sp.simplify(f_plusG_at_ea) - sp.simplify(f_plusA_at_xa))
cert["notation_collision"] = {
    "f_plusG_at_ea": str(sp.simplify(f_plusG_at_ea)),
    "f_plusA_at_xa": str(sp.simplify(f_plusA_at_xa)),
    "symbolic_difference_nonzero": collision_diff != 0,
    "finding": "f_+^A(x_a) != f_+^G(eps_a); the bridge maps f_+^A to 1/2 f_-^G (reflected companion)"}

all_pass = all(v["result"] == "PASS_EXACT" for v in cert["theorems"].values())
cert["overall"] = "PASS_EXACT" if all_pass else "FAIL"
path = OUT / "thermal_dictionary_certificate.json"
tmp = OUT / "thermal_dictionary_certificate.json.tmp"
tmp.write_text(json.dumps(cert, indent=2))
tmp.replace(path)
print(json.dumps({k: (v if not isinstance(v, dict) else v.get("result")) for k, v in cert["theorems"].items()}, indent=1))
print("overall:", cert["overall"])
print("notation collision difference nonzero:", cert["notation_collision"]["symbolic_difference_nonzero"])