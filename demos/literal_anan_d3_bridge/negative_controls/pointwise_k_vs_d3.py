#!/usr/bin/env python3
"""Negative control: pointwise K != -D3 (packet section 9).

For an arbitrary ordered triple, K_abc + D3_abc != 0 generically: the ordered
statement is false, and the valid identity exists only after complete
three-band permutation reassembly.  Expected certificate:
ORDERED_TRIPLE_K_EQUALS_MINUS_D3 = FAIL_EXPECTED (scientific evidence).
"""
import json, subprocess, sys, time
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent.parent / "proofs"
sys.path.insert(0, str(HERE))
from thermal_kernels import GuoKernels

OUT = Path(__file__).resolve().parent.parent / "proofs" / "out"
OUT.mkdir(exist_ok=True)
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

ea, eb, ec = mp.mpf('-0.5'), mp.mpf('0.3'), mp.mpf('1.4')
rows = []
all_nonzero = True
for perm in [(ea, eb, ec), (ea, ec, eb), (eb, ea, ec)]:
    s = K(*perm) + D3(*perm)
    rows.append({"perm": [mp.nstr(x, 10) for x in perm], "K_plus_D3": mp.nstr(s, 30)})
    if mp.fabs(s) < mp.mpf('1e-20'):
        all_nonzero = False

cert = {
  "schema": "viper.demo.anan_d3.negative_control_pointwise.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "ORDERED_TRIPLE_K_EQUALS_MINUS_D3": "FAIL_EXPECTED" if all_nonzero else "UNEXPECTED_ZERO",
  "rows": rows,
  "note": "K != -D3 pointwise (generic); identity exists only after six-orbit reassembly",
}
path = OUT / "negative_control_pointwise.json"
tmp = OUT / "negative_control_pointwise.json.tmp"
tmp.write_text(json.dumps(cert, indent=2, default=str)); tmp.replace(path)
print("FAIL_EXPECTED" if all_nonzero else "UNEXPECTED_ZERO")
for row in rows:
    print(row["perm"], row["K_plus_D3"])
