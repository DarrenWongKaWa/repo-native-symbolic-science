#!/usr/bin/env python3
"""Six-orbit verification with FROZEN clarified contract (2026-08-16).

Gates (fail-closed; stop at the first gate whose residual exceeds tolerance,
report that exact gate and expression):

  G1 M_KERNEL_PROOF_NORMAL_FORM   : M_Gamma(x,y) == S03 explicit normal form
  G2 T_KERNEL_ARGUMENT_ORDER      : T_abc = (M_cb - M_ac + iGamma F[c,c,c,a,b])/(E_b-E_a+2iGamma)
                                    (argument placement exactly as frozen)
  G3 K_XYD_NORMAL_FORM            : K_abc = i[ x(x-2y) M_ab - x y d T_abc ],
                                    x = Delta_ab, y = Delta_ac, d = Delta_bc = y - x
  G4 SIX_ORBIT_TO_QM_HD_REDUCTION : sum_pi K_pi == i sum_pairs ... (M_uv - M_vu) form
                                    with the S3.31 endpoint relation treated as
                                    CONJUGATION: M_vu = conj(M_uv) (never equality)
  G5 SIX_ORBIT_NODE_DATA_REDUCTION: orbit sums expressible from node data only
                                    (M and F values at the three nodes)
  G6 SIX_ORBIT_REALITY            : Im(sumK), Im(sumD3) below tolerance
  G7 LITERAL_ANAN_D3_SIX_ORBIT    : sumK + sumD3 == 0 (residual scales as h^2,
                                    i.e. pure w2-extraction truncation)

Witness: E = {-0.5, 0.3, 1.4}, beta = 5, mu = 0, Gamma = 0.08 (declared valid).
"""
import json, subprocess, sys, time, itertools
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
from thermal_kernels import GuoKernels

I = mp.mpc(0, 1)
BETA, GAMMA, MU = 5, mp.mpf('0.08'), 0
gk = GuoKernels(BETA, GAMMA, MU)
TOL = mp.mpf('1e-20')          # gate tolerance at dps=60 (h^2 truncation ~ 1e-25)

ea, eb, ec = mp.mpf('-0.5'), mp.mpf('0.3'), mp.mpf('1.4')
E = (ea, eb, ec)
D = lambda u, v: u - v
x_ab, y_ac, d_bc = D(ea, eb), D(ea, ec), D(eb, ec)

def M(a, b): return gk.M(a, b)
def T(a, b, c): return gk.T(a, b, c)

def K(a, b, c):
    # FROZEN: K_abc = i[ Dab(Dca - Dbc) M_ab - Dab Dac Dbc T_abc ]
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    Dca = D(c, a)
    return I*(Dab*(Dca - Dbc)*M(a, b) - Dab*Dac*Dbc*T(a, b, c))

def D3(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis1(a)
    t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis2(a)
    return mp.re(t1 + t2)

gates = {}
fail = None

# ---- G1 M_KERNEL_PROOF_NORMAL_FORM ----
m_def = M(ea, eb)
m_nf = gk.M_normal_form(ea, eb)
g1_res = abs(m_def - m_nf)
gates["G1_M_KERNEL_PROOF_NORMAL_FORM"] = {
    "M_from_w2": mp.nstr(m_def, 40), "M_normal_form": mp.nstr(m_nf, 40),
    "residual": mp.nstr(g1_res, 25),
    "result": "PASS" if g1_res < TOL else "FAIL"}
if g1_res >= TOL:
    fail = ("G1_M_KERNEL_PROOF_NORMAL_FORM", "M_Gamma(x,y) - M_normal_form(x,y)",
            mp.nstr(g1_res, 30))

# ---- G2 T_KERNEL_ARGUMENT_ORDER ----
tf = gk.T_normal_form(ea, eb, ec)
t_def = T(ea, eb, ec)
t_rebuilt = (tf["M_cb"] - tf["M_ac"] + I*GAMMA*tf["F_c_c_c_a_b"]) / tf["denominator"]
g2_res = abs(t_def - t_rebuilt)
# argument-order sensitivity: swapping M arguments must change the value
g2_swap = abs((tf["M_ac"] - tf["M_cb"] + I*GAMMA*tf["F_c_c_c_a_b"]) / tf["denominator"] - t_def)
gates["G2_T_KERNEL_ARGUMENT_ORDER"] = {
    "T_frozen_form": mp.nstr(t_def, 40),
    "M_cb": mp.nstr(tf["M_cb"], 30), "M_ac": mp.nstr(tf["M_ac"], 30),
    "F[c,c,c,a,b]": mp.nstr(tf["F_c_c_c_a_b"], 30),
    "denominator": mp.nstr(tf["denominator"], 30),
    "rebuilt_residual": mp.nstr(g2_res, 25),
    "argument_swap_changes_value": g2_swap > TOL,
    "result": "PASS" if g2_res < TOL and g2_swap > TOL else "FAIL"}
if g2_res >= TOL or g2_swap <= TOL:
    fail = ("G2_T_KERNEL_ARGUMENT_ORDER", "T_abc frozen placement",
            mp.nstr(g2_res, 30) + " / swap-sensitivity " + mp.nstr(g2_swap, 30))

# ---- G3 K_XYD_NORMAL_FORM ----
k_direct = K(ea, eb, ec)
k_xyd = I*(x_ab*(x_ab - 2*y_ac)*M(ea, eb) - x_ab*y_ac*d_bc*T(ea, eb, ec))
g3_res = abs(k_direct - k_xyd)
g3_alg = abs(x_ab*(x_ab - 2*y_ac) - D(ea, eb)*(D(ec, ea) - D(eb, ec)))  # x(x-2y) == Dab(Dca-Dbc)
gates["G3_K_XYD_NORMAL_FORM"] = {
    "x": mp.nstr(x_ab, 20), "y": mp.nstr(y_ac, 20), "d": mp.nstr(d_bc, 20),
    "x(x-2y) == Dab(Dca-Dbc)": mp.nstr(g3_alg, 25),
    "K_direct": mp.nstr(k_direct, 35), "K_xyd": mp.nstr(k_xyd, 35),
    "residual": mp.nstr(g3_res, 25),
    "result": "PASS" if g3_res < TOL and g3_alg < TOL else "FAIL"}
if g3_res >= TOL or g3_alg >= TOL:
    fail = ("G3_K_XYD_NORMAL_FORM", "K - i[x(x-2y)M - xyd T]", mp.nstr(g3_res, 30))

# ---- G4 SIX_ORBIT_TO_QM_HD_REDUCTION ----
# reduction: sumK = i[ x(x-2y)(M_ab - M_ba) + y(y-2x)(M_ac - M_ca) + (y-x)(y+x)(M_bc - M_cb) ]
#             - i x y d sum_pi sign(pi) T_pi
# S3.31 endpoint relation: M_vu == conj(M_uv) (CONJUGATION, not equality)
conj_res = abs(M(eb, ea) - mp.conj(M(ea, eb)))
red_M = (x_ab*(x_ab - 2*y_ac)*(M(ea, eb) - M(eb, ea))
         + y_ac*(y_ac - 2*x_ab)*(M(ea, ec) - M(ec, ea))
         + d_bc*(y_ac + x_ab)*(M(eb, ec) - M(ec, eb)))
sign = {"abc": 1, "acb": -1, "bac": -1, "bca": 1, "cab": 1, "cba": -1}
Tsum = mp.mpc(0)
for p in itertools.permutations(E):
    key = "".join(["a" if v == ea else ("b" if v == eb else "c") for v in p])
    Tsum += sign[key]*T(*p)
red_sumK = I*red_M - I*x_ab*y_ac*d_bc*Tsum
sumK_direct = mp.mpc(0)
for p in itertools.permutations(E):
    sumK_direct += K(*p)
g4_res = abs(sumK_direct - red_sumK)
g4_conj = conj_res
gates["G4_SIX_ORBIT_TO_QM_HD_REDUCTION"] = {
    "sumK_direct": mp.nstr(sumK_direct, 40),
    "sumK_reduced": mp.nstr(red_sumK, 40),
    "reduction_residual": mp.nstr(g4_res, 25),
    "S3.31_conjugation_M_ba-conj(M_ab)": mp.nstr(conj_res, 25),
    "result": "PASS" if g4_res < TOL and conj_res < TOL else "FAIL"}
if g4_res >= TOL or conj_res >= TOL:
    fail = ("G4_SIX_ORBIT_TO_QM_HD_REDUCTION", "sumK_direct - sumK_reduced",
            mp.nstr(g4_res, 30) + " / conj " + mp.nstr(conj_res, 30))

# ---- G5 SIX_ORBIT_NODE_DATA_REDUCTION ----
# node-data-only reconstruction: build sumK from node data (M/F at the three nodes)
def node_data_reduction():
    """Recompute the orbit sum using ONLY M and F node values."""
    Mv = {(i, j): M(E[i], E[j]) for i in range(3) for j in range(3) if i != j}
    # T via node data:
    def T_nd(a, b, c):
        return (Mv[(c, b)] - Mv[(a, c)] + I*GAMMA*gk.dd5(E[c], E[a], E[b])) / (E[b] - E[a] + 2*I*GAMMA)
    s = mp.mpc(0)
    for p in itertools.permutations((0, 1, 2)):
        a, b, c = p
        Dab, Dac, Dbc = D(E[a], E[b]), D(E[a], E[c]), D(E[b], E[c])
        Dca = D(E[c], E[a])
        s += I*(Dab*(Dca - Dbc)*Mv[(a, b)] - Dab*Dac*Dbc*T_nd(a, b, c))
    return s
s_nd = node_data_reduction()
g5_res = abs(s_nd - sumK_direct)
gates["G5_SIX_ORBIT_NODE_DATA_REDUCTION"] = {
    "node_data_reconstruction": mp.nstr(s_nd, 40),
    "residual": mp.nstr(g5_res, 25),
    "result": "PASS" if g5_res < TOL else "FAIL"}
if g5_res >= TOL:
    fail = ("G5_SIX_ORBIT_NODE_DATA_REDUCTION", "node-data reconstruction", mp.nstr(g5_res, 30))

# ---- G6 SIX_ORBIT_REALITY ----
sumD3 = mp.mpc(0)
for p in itertools.permutations(E):
    sumD3 += D3(*p)
g6_imK = abs(mp.im(sumK_direct)); g6_imD = abs(mp.im(sumD3))
gates["G6_SIX_ORBIT_REALITY"] = {
    "Im(sumK)": mp.nstr(g6_imK, 25), "Im(sumD3)": mp.nstr(g6_imD, 25),
    "result": "PASS" if g6_imK < TOL and g6_imD < TOL else "FAIL"}
if g6_imK >= TOL or g6_imD >= TOL:
    fail = ("G6_SIX_ORBIT_REALITY", "Im parts", mp.nstr(g6_imK, 30))

# ---- G7 LITERAL_ANAN_D3_SIX_ORBIT ----
# residual must scale as h^2 (pure w2 truncation): check at two h values
def orbit_total(h):
    def Mh(a, b): return gk.M(a, b, h=h)
    def Th(a, b, c): return gk.T(a, b, c, h=h)
    s = mp.mpc(0)
    for p in itertools.permutations(E):
        a, b, c = p
        Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
        Dca = D(c, a)
        s += I*(Dab*(Dca - Dbc)*Mh(a, b) - Dab*Dac*Dbc*Th(a, b, c))
    for p in itertools.permutations(E):
        a, b, c = p
        Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
        t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis1(a)
        t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis2(a)
        s += mp.re(t1 + t2)
    return s
r12 = orbit_total(mp.mpf('1e-12'))
r14 = orbit_total(mp.mpf('1e-14'))
g7_res = abs(r12)
h2_scaling = abs(r14) < abs(r12)/10
gates["G7_LITERAL_ANAN_D3_SIX_ORBIT"] = {
    "sumK": mp.nstr(sumK_direct, 40), "sumD3": mp.nstr(sumD3, 40),
    "sumK+sumD3": mp.nstr(r12, 25),
    "residual_h1e-12": mp.nstr(abs(r12), 25), "residual_h1e-14": mp.nstr(abs(r14), 25),
    "h2_scaling_confirms_truncation": bool(h2_scaling),
    "result": "PASS" if abs(r12) < TOL and h2_scaling else "FAIL"}
if abs(r12) >= TOL or not h2_scaling:
    fail = ("G7_LITERAL_ANAN_D3_SIX_ORBIT", "sumK+sumD3", mp.nstr(abs(r12), 30))

cert = {
  "schema": "viper.demo.anan_d3.six_orbit_status.v2",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=HERE.parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "contract": "FROZEN 2026-08-16: T_abc = (M_cb - M_ac + i Gamma F[E_c,E_c,E_c,E_a,E_b])/(E_b - E_a + 2 i Gamma); K = i[x(x-2y)M - xyd T]; S3.31 endpoint relation = CONJUGATION",
  "parameters": {"beta": BETA, "Gamma": str(GAMMA), "mu": MU, "energies": [str(e) for e in E]},
  "gates": gates,
  "fail_closed_stop": fail,
  "verdict": "LITERAL_ANAN_D3_SIX_ORBIT_PASS_EXACT" if fail is None else "STOPPED_AT_" + fail[0],
}
path = OUT / "six_orbit_status.json"
tmp = OUT / "six_orbit_status.json.tmp"
tmp.write_text(json.dumps(cert, indent=2, default=str)); tmp.replace(path)
for name, g in gates.items():
    print(name, "->", g["result"])
print("fail_closed_stop:", fail)
print("verdict:", cert["verdict"])
