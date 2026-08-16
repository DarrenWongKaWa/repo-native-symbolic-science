#!/usr/bin/env python3
"""Proof: three-band loop geometry orbit invariance (exact, SymPy).

Packet section 11: Lambda(a,b,c) = Re(A_ab A_bc A_ca) is invariant under every
permutation in S3, given Hermiticity A_mn = conjugate(A_nm).
Cyclic permutations preserve the closed product; an orientation reversal
complex-conjugates the product; Re removes the difference.
"""
import json, subprocess, time
from pathlib import Path
import sympy as sp
import itertools

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
I = sp.I
Aab, Abc, Aca = sp.symbols("Aab Abc Aca", complex=True)
# Hermiticity: A_mn = conjugate(A_nm)  =>  A_ba=conj(Aab), A_cb=conj(Abc), A_ac=conj(Aca)
conj_map = {sp.conjugate(Aab): sp.Symbol("conj_Aab"), sp.conjugate(Abc): sp.Symbol("conj_Abc"), sp.conjugate(Aca): sp.Symbol("conj_Aca")}

# generic product P(a,b,c) = A_ab * A_bc * A_ca with arbitrary complex entries
P = lambda a, b, c: a*b*c
A = {"a": Aab, "b": Abc, "c": Aca}
# hermitian relation: A[x][y] = conj(A[y][x]); build the 3x3 symbolic table
M = {}
names = ["a", "b", "c"]
for i in names:
    for j in names:
        if i == j:
            M[(i, j)] = sp.Symbol(f"A_{i}{i}")
        elif (i, j) == ("a", "b"): M[(i, j)] = Aab
        elif (i, j) == ("b", "c"): M[(i, j)] = Abc
        elif (i, j) == ("c", "a"): M[(i, j)] = Aca
        elif (i, j) == ("b", "a"): M[(i, j)] = sp.conjugate(Aab)
        elif (i, j) == ("c", "b"): M[(i, j)] = sp.conjugate(Abc)
        elif (i, j) == ("a", "c"): M[(i, j)] = sp.conjugate(Aca)

def Product(perm):
    i, j, k = perm
    return sp.expand(M[(i, j)] * M[(j, k)] * M[(k, i)])

base = Product(("a", "b", "c"))
results = {}
for perm in itertools.permutations(names):
    prod = Product(perm)
    d1 = sp.simplify(prod - base)
    d2 = sp.simplify(prod - sp.conjugate(base))
    same = d1 == 0
    conj = d2 == 0
    results["".join(perm)] = {"product_equal": same,
                              "product_conjugate_equal": conj,
                              "re_equal": same or conj,
                              "reason": "identical closed product" if same else (
                                        "orientation reversal complex-conjugates; Re removes it" if conj else "NO MATCH")}

cert = {
  "schema": "viper.demo.anan_d3.geometry_orbit.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE.parents[2]).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT": "PASS_EXACT" if all(v["re_equal"] for v in results.values()) else "FAIL",
  "permutations_checked": list(results.keys()),
  "hermiticity_assumption": "A_mn = conjugate(A_nm)",
  "results": results,
}
path = OUT / "geometry_orbit_certificate.json"
tmp = OUT / "geometry_orbit_certificate.json.tmp"
tmp.write_text(json.dumps(cert, indent=2)); tmp.replace(path)
print(cert["THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT"], "6/6 permutations")
