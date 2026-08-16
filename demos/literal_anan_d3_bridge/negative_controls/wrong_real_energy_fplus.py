#!/usr/bin/env python3
"""Negative control: WRONG real-energy branch (packet section 14).

Deliberately evaluate the D3 orbit sum with the WRONG thermal branch:
replace f_+^A(eps - mu + i Gamma) by a real-energy Guo-type f_+^G(eps_a)
(equivalently: use f_+^G derivatives instead of the certified 1/2 f_-^G
dictionary).  The wrong value must be a perfectly finite number, different
from the correct value — the discriminator, not a crash.

Expected certificate: NEGATIVE_CONTROL_REAL_ENERGY_FPLUS = FAIL_AS_EXPECTED
"""
import json, subprocess, sys, time, itertools
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

E = [mp.mpf(-0.5), mp.mpf(0.3), mp.mpf(1.4)]

def Delta(e1, e2): return e1 - e2

def D3_orbit(deriv_dict):
    """orbit sum of D3 with a given derivative dictionary at the first index."""
    total = mp.mpc(0)
    for p in itertools.permutations(E):
        a, b, c = p
        Dab, Dac, Dbc = Delta(a, b), Delta(a, c), Delta(b, c)
        f1, f2 = deriv_dict(a)
        t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * f1
        t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * f2
        total += mp.re(t1 + t2)
    return total

# CORRECT dictionary (certified bridge): f_A' = 1/2 f_-^G'(e), f_A'' = 1/2 f_-^G''(e)
def correct(e): return (mp.mpf(1)/2)*gk.Phis1(e), (mp.mpf(1)/2)*gk.Phis2(e)
# WRONG dictionary: real-energy Guo f_+^G derivatives (no bridge)
def wrong(e): return gk.Phi1(e), gk.Phi2(e)

SD_correct = D3_orbit(correct)
SD_wrong = D3_orbit(wrong)
discriminates = (SD_correct != SD_wrong) and mp.isfinite(SD_wrong) and mp.isfinite(SD_correct)

cert = {
  "schema": "viper.demo.anan_d3.negative_control_real_energy.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "NEGATIVE_CONTROL_REAL_ENERGY_FPLUS": "FAIL_AS_EXPECTED" if discriminates else "NOT_DISCRIMINATING",
  "correct_value_sumD3": mp.nstr(SD_correct, 30),
  "wrong_value_sumD3": mp.nstr(SD_wrong, 30),
  "values_are_finite_and_different": bool(discriminates),
  "note": "packet expected correct -0.1438813736614977 / wrong +0.1270106832723943 at the USER certified witness; "
          "this run uses the declared demo witness energies (-0.5, 0.3, 1.4) - digits differ, discrimination holds.",
}
path = OUT / "negative_control_real_energy.json"
tmp = OUT / "negative_control_real_energy.json.tmp"
tmp.write_text(json.dumps(cert, indent=2, default=str)); tmp.replace(path)
print("correct sumD3:", mp.nstr(SD_correct, 30))
print("wrong  sumD3:", mp.nstr(SD_wrong, 30))
print("FAIL_AS_EXPECTED" if discriminates else "NOT_DISCRIMINATING")
