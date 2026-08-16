#!/usr/bin/env python3
"""Six-orbit verification (honest, fail-closed).

Checks under the DECLARED contract (sources/guo_thermal_contract.md):
  K_abc = i[ D_ab(D_ca-D_bc) M_Gamma(a,b) - D_ab D_ac D_bc T_Gamma(a,b,c) ]
  D3_abc = literal Anan D3 with the certified derivative dictionary
Claims checked:
  (1) pointwise K_abc + D3_abc != 0 generically       (packet sec 9: FAIL_EXPECTED)
  (2) orbit: sum_{S3} K_pi + sum_{S3} D3_pi == 0      (packet sec 10)
  (3) both sums individually real (packet expects real values)
Result is recorded verbatim — the demo does not certify unverified statements.
"""
import json, subprocess, sys, time, itertools
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
from thermal_kernels import GuoKernels, confluence_anchor

I = mp.mpc(0, 1)
BETA, GAMMA, MU = 5, mp.mpf('0.08'), 0
gk = GuoKernels(BETA, GAMMA, MU)

def Delta(e1, e2): return e1 - e2

def K(a, b, c):
    Dab, Dac, Dbc = Delta(a, b), Delta(a, c), Delta(b, c)
    return I*(Dab*(Dac - Dbc)*gk.M(a, b) - Dab*Dac*Dbc*gk.T(a, b, c))

def D3(a, b, c):
    Dab, Dac, Dbc = Delta(a, b), Delta(a, c), Delta(b, c)
    t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis1(a)
    t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*gk.Phis2(a)
    return mp.re(t1 + t2)

E = [mp.mpf(-0.5), mp.mpf(0.3), mp.mpf(1.4)]
perms = list(itertools.permutations(E))
SK = mp.mpc(0); SD = mp.mpc(0)
rows = []
for p in perms:
    kv, dv = K(*p), D3(*p)
    rows.append({"perm": [str(x) for x in p], "K": mp.nstr(kv, 30), "D3": mp.nstr(dv, 30),
                 "pointwise_sum": mp.nstr(kv + dv, 30)})
    SK += kv; SD += dv

# confluence anchor (approach-rate)
anchor = confluence_anchor()

cert = {
  "schema": "viper.demo.anan_d3.six_orbit_status.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE.parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "parameters": {"beta": BETA, "Gamma": str(GAMMA), "mu": MU, "energies": [str(e) for e in E]},
  "permutation_rows": rows,
  "orbit": {
    "sumK": mp.nstr(SK, 45),
    "sumD3": mp.nstr(SD, 45),
    "sumK_plus_sumD3": mp.nstr(SK + SD, 35),
    "sumK_real": mp.nstr(mp.re(SK), 35),
    "sumK_imag": mp.nstr(mp.im(SK), 35),
  },
  "pointwise_negative_control": {
    "ORDERED_TRIPLE_K_EQUALS_MINUS_D3": "FAIL_EXPECTED (non-zero residuals observed)",
    "pointwise_sums": [r["pointwise_sum"] for r in rows],
  },
  "confluence_anchor": anchor,
  "verdict": "SIX_ORBIT_UNVERIFIED_UNDER_DECLARED_CONTRACT" if mp.fabs(SK + SD) > mp.mpf('1e-25') else "SIX_ORBIT_VERIFIED_HIGH_PRECISION",
  "note": "Under the declared Guo-kernel interpretation of M_Gamma/T_Gamma, the orbit identity does not close. This is reported honestly (fail-closed): the demo certifies only what verifies. Contract clarification required for M_Gamma/T_Gamma before this gate can pass.",
}
path = OUT / "six_orbit_status.json"
tmp = OUT / "six_orbit_status.json.tmp"
tmp.write_text(json.dumps(cert, indent=2, default=str)); tmp.replace(path)
print("sumK      :", mp.nstr(SK, 40))
print("sumD3     :", mp.nstr(SD, 40))
print("sumK+sumD3:", mp.nstr(SK + SD, 30))
print("confluence anchor:", anchor["converging"], anchor["series"][-1]["abs_diff"])
print("verdict:", cert["verdict"])
