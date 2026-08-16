#!/usr/bin/env python3
"""Proof: literal Anan D3 thermal bridge (exact, SymPy).

Packet section 7: substituting the derivative dictionary
  f_{+,a}^{A'} = 1/2 f_-^{G'}(eps_a),  f_{+,a}^{A''} = 1/2 f_-^{G''}(eps_a)
into the literal Anan D3 coefficient yields the reduced Guo form POINTWISE
(no permutation summation, no approximations).
"""
import json, subprocess, sys, time
from pathlib import Path
import sympy as sp

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
I = sp.I
Gamma = sp.symbols("Gamma", positive=True)
ea, eb, ec = sp.symbols("eps_a eps_b eps_c", real=True)
fA1, fA2 = sp.symbols("fA1 fA2")          # f_{+,a}^{A'}, f_{+,a}^{A''}
fG1, fG2 = sp.symbols("fG1 fG2")          # f_-^{G'}(eps_a), f_-^{G''}(eps_a)
D = lambda x, y: x - y

Dab, Dac, Dbc = D(ea, eb), D(ea, ec), D(eb, ec)
Gam_ab = 8*Gamma*Dab/(Dab + 2*I*Gamma)
Gam_ab2 = 2*Gamma*Dab/(Dab + 2*I*Gamma)

D3_anan = sp.re(-(1/Dac + 1/Dbc)*Gam_ab*fA1 + Gam_ab2*fA2)
D3_reduced = sp.re(-4*Gamma*Dab/(Dab + 2*I*Gamma)*(1/Dac + 1/Dbc)*fG1
                   + Gamma*Dab/(Dab + 2*I*Gamma)*fG2)
D3_after_dict = sp.simplify(D3_anan.subs({fA1: sp.Rational(1, 2)*fG1, fA2: sp.Rational(1, 2)*fG2}))
diff = sp.simplify(sp.expand(D3_after_dict - D3_reduced))
ok = diff == 0
cert = {
  "schema": "viper.demo.anan_d3.d3_bridge.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE.parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "LITERAL_ANAN_D3_THERMAL_BRIDGE": "PASS_EXACT" if ok else "FAIL",
  "ARROW_TYPE": "POINTWISE_EXACT",
  "held_for": "every ordered triple (a,b,c) with pairwise distinct bands; no permutation summation",
  "difference_after_dictionary": "0" if ok else str(diff),
  "D3_anan_literal": str(D3_anan),
  "D3_reduced_guo": str(D3_reduced),
}
path = OUT / "d3_bridge_certificate.json"
tmp = OUT / "d3_bridge_certificate.json.tmp"
tmp.write_text(json.dumps(cert, indent=2)); tmp.replace(path)
print(cert["LITERAL_ANAN_D3_THERMAL_BRIDGE"], cert["ARROW_TYPE"])
