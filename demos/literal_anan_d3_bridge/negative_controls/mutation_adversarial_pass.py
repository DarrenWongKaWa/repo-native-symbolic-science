#!/usr/bin/env python3
"""Mutation / adversarial pass (2026-08-16).

Each mutation injects a SPECIFIC wrong scientific choice and must red-flag at
least one expected gate.  Correct science -> PASS; wrong science -> caught at
the correct obligation.  This is the repo-native difference from a symbolic
notebook: the demo cannot be falsely green.

M1 F_NODE_ORDER      : F[E_c,E_c,E_c,E_a,E_b] replaced by the WRONG 3-node
                       second divided difference -> expect G7 (six-orbit) red
M2 DELTA_INDEX       : Delta_ca - Delta_bc replaced by Delta_ac - Delta_bc in
                       K -> expect G3 (K xyd normal form) red
M3 CONJUGATION_EQUALITY: M_ba = conj(M_ab) replaced by ordinary equality
                       M_ba = M_ab in the orbit reduction -> expect G4 red
M4 REAL_ENERGY_FPLUS : Anan f_+^A(E-mu+i Gamma) replaced by real-energy
                       f_+^G(E) in the D3 dictionary -> expect G7 red
"""
import json, subprocess, sys, time, itertools
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent.parent / "proofs"
OUT = Path(__file__).resolve().parent.parent / "proofs" / "out"
sys.path.insert(0, str(HERE))
from thermal_kernels import GuoKernels

I = mp.mpc(0, 1)
BETA, GAMMA, MU = 5, mp.mpf('0.08'), 0
gk = GuoKernels(BETA, GAMMA, MU)
TOL = mp.mpf('1e-20')
ea, eb, ec = mp.mpf('-0.5'), mp.mpf('0.3'), mp.mpf('1.4')
E = (ea, eb, ec)
D = lambda u, v: u - v
perms = list(itertools.permutations(E))

def orbit_sum(Kfn, D3fn):
    s = mp.mpc(0)
    for p in perms:
        s += Kfn(*p)
    for p in perms:
        s += D3fn(*p)
    return s

def D3_correct(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis1(a)
    t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis2(a)
    return mp.re(t1 + t2)

def K_correct(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    return I*(Dab*(D(c, a) - Dbc)*gk.M(a, b) - Dab*Dac*Dbc*gk.T(a, b, c))

results = []

# ---- M1: wrong 3-node divided difference in T ----
def dd3_wrong(z, x, y):
    # WRONG: 3-node second divided difference (the historical bug)
    f = gk.F
    return ((f(y) - f(x))/(y - x) - (f(z) - f(y))/(z - y)) / (x - z)
def T_m1(a, b, c):
    return (gk.M(c, b) - gk.M(a, c) + I*GAMMA*dd3_wrong(c, a, b)) / (b - a + 2*I*GAMMA)
def K_m1(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    return I*(Dab*(D(c, a) - Dbc)*gk.M(a, b) - Dab*Dac*Dbc*T_m1(a, b, c))
r1 = abs(orbit_sum(K_m1, D3_correct))
results.append({"mutation": "M1_F_NODE_ORDER",
                "injected": "F[Ec,Ec,Ec,Ea,Eb] -> 3-node second divided difference (historical bug)",
                "expected_red_gate": "G7_LITERAL_ANAN_D3_SIX_ORBIT",
                "orbit_residual": mp.nstr(r1, 25),
                "gate_red": bool(r1 > TOL)})

# ---- M2: wrong delta index in K ----
def K_m2(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    return I*(Dab*(Dac - Dbc)*gk.M(a, b) - Dab*Dac*Dbc*gk.T(a, b, c))   # WRONG: Dac - Dbc
g3_m2 = abs(K_m2(ea, eb, ec) - I*(D(ea, eb)*(D(ea, eb) - 2*D(ea, ec))*gk.M(ea, eb)
                                  - D(ea, eb)*D(ea, ec)*D(eb, ec)*gk.T(ea, eb, ec)))
results.append({"mutation": "M2_DELTA_INDEX",
                "injected": "Delta_ca - Delta_bc -> Delta_ac - Delta_bc in K",
                "expected_red_gate": "G3_K_XYD_NORMAL_FORM",
                "kxy_normal_form_residual": mp.nstr(g3_m2, 25),
                "gate_red": bool(g3_m2 > TOL)})

# ---- M3: conjugation -> equality in the orbit reduction ----
x_ab, y_ac, d_bc = D(ea, eb), D(ea, ec), D(eb, ec)
red_M_correct = (x_ab*(x_ab - 2*y_ac)*(gk.M(ea, eb) - gk.M(eb, ea))
                 + y_ac*(y_ac - 2*x_ab)*(gk.M(ea, ec) - gk.M(ec, ea))
                 + d_bc*(y_ac + x_ab)*(gk.M(eb, ec) - gk.M(ec, eb)))
sign = {"abc": 1, "acb": -1, "bac": -1, "bca": 1, "cab": 1, "cba": -1}
Tsum = mp.mpc(0)
for p in perms:
    key = "".join(["a" if v == ea else ("b" if v == eb else "c") for v in p])
    Tsum += sign[key]*gk.T(*p)
sumK_direct = mp.mpc(0)
for p in perms:
    sumK_direct += K_correct(*p)
# MUTATION: replace M_ba with M_ab (ordinary equality, no conjugation)
red_M_m3 = (x_ab*(x_ab - 2*y_ac)*(gk.M(ea, eb) - gk.M(ea, eb))
            + y_ac*(y_ac - 2*x_ab)*(gk.M(ea, ec) - gk.M(ea, ec))
            + d_bc*(y_ac + x_ab)*(gk.M(eb, ec) - gk.M(eb, ec)))
red_sumK_m3 = I*red_M_m3 - I*x_ab*y_ac*d_bc*Tsum
g4_m3 = abs(sumK_direct - red_sumK_m3)
results.append({"mutation": "M3_CONJUGATION_EQUALITY",
                "injected": "M_ba = conj(M_ab) -> M_ba = M_ab (ordinary equality) in the orbit reduction",
                "expected_red_gate": "G4_SIX_ORBIT_TO_QM_HD_REDUCTION",
                "reduction_residual": mp.nstr(g4_m3, 25),
                "gate_red": bool(g4_m3 > TOL)})

# ---- M4: real-energy f_+^G in the D3 dictionary ----
def D3_m4(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * gk.Phi1(a)   # WRONG: f_+^G
    t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * gk.Phi2(a)
    return mp.re(t1 + t2)
r4 = abs(orbit_sum(K_correct, D3_m4))
results.append({"mutation": "M4_REAL_ENERGY_FPLUS",
                "injected": "f_+^A(E-mu+i Gamma) -> real-energy f_+^G(E) in the D3 dictionary",
                "expected_red_gate": "G7_LITERAL_ANAN_D3_SIX_ORBIT",
                "orbit_residual": mp.nstr(r4, 25),
                "gate_red": bool(r4 > TOL)})

cert = {
  "schema": "viper.demo.anan_d3.mutation_adversarial_pass.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=HERE.parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "principle": "correct science -> PASS; specific wrong science -> caught at the correct obligation",
  "mutations": results,
  "overall": "PASS (every mutation red-flags at least one gate)" if all(r["gate_red"] for r in results) else "FAIL",
}
path = OUT / "mutation_adversarial_pass.json"
tmp = OUT / "mutation_adversarial_pass.json.tmp"
tmp.write_text(json.dumps(cert, indent=2, default=str)); tmp.replace(path)
for r in results:
    print(r["mutation"], "-> gate_red:", r["gate_red"], "| residual:", r["orbit_residual"] if "orbit_residual" in r else r.get("kxy_normal_form_residual") or r.get("reduction_residual"))
print("overall:", cert["overall"])
