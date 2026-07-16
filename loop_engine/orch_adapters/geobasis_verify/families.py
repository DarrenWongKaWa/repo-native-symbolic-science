#!/usr/bin/env python3
"""
Deliverable 1 (嘉华 "都做掉"): extend to INDEPENDENT task families beyond F-23,
each with an independent Symbolic Gold Oracle _|_ Numerical Geobasis Verifier.
Goal: show the architecture verifies a *class* of geometric identities, not one
SHG-specific structure.

Families (each: 1 true identity + contaminated mutations):
  METRIC      identity 1:  sum'_m (v^a v^b + v^b v^a)/eps^2  = 2 g^{ab}
  RENORM      identity 2:  sum'_m (v^a v^b + v^b v^a)/eps^3  = 2 G^{ab}
  BERRY       identity 5:  sum'_m (v^a v^b - v^b v^a)/eps^2  = -i Omega^{ab}
"""
import sys
from pathlib import Path
import numpy as np
import sympy as sp

HERE = Path(__file__).resolve().parent
import geometry as geo
import tshg_numeric as tn

# ---------------- SYMBOLIC gold oracle (independent path 1, exact) ------------
# per band pair (n,m): LHS_summand vs RHS_summand, substitute v = i eps A, canonicalize.
def _sym_atoms():
    I = sp.I; eps = sp.Symbol('eps', real=True, nonzero=True)
    vnm = {x: sp.Symbol(f'v{x}', complex=True) for x in 'ab'}
    def Anm(x): return vnm[x]/(I*eps)
    def Amn(x): return sp.conjugate(vnm[x])/(-I*eps)   # Hermitian: A_mn = conj(A_nm)
    def Re(z): return sp.Rational(1,2)*(z+sp.conjugate(z))
    return I, eps, vnm, Anm, Amn, Re

def symbolic_gold(family, pw=None, sign=+1, factor=2):
    I, eps, vnm, Anm, Amn, Re = _sym_atoms()
    va, vb = vnm['a'], vnm['b']; vam, vbm = sp.conjugate(va), sp.conjugate(vb)
    p = pw if pw is not None else {"METRIC":2, "RENORM":3, "BERRY":2}[family]
    if family in ("METRIC","RENORM"):
        LHS = (va*vbm + vb*vam)/eps**p                      # v^a_nm v^b_mn + v^b_nm v^a_mn
        RHS = (factor*Re(Anm('a')*Amn('b')) if family=="METRIC"
               else factor*Re(Anm('a')*Amn('b')/eps))       # 2 g  or  2 G  (per summand)
    else:  # BERRY
        LHS = (va*vbm - vb*vam)/eps**p
        RHS = sign*(-I)*(I*(Anm('a')*Amn('b') - Anm('b')*Amn('a')))  # -i Omega summand
    return sp.simplify(sp.expand(LHS - RHS)) == 0

# ---------------- NUMERICAL verifier (independent path 2) ---------------------
def _num_lhs(H, k, family, pw=None, sign=+1):
    N=H.N; w,v,A = geo.objects(H,k)
    def e(n,m): return w[n]-w[m]
    p = pw if pw is not None else {"METRIC":2,"RENORM":3,"BERRY":2}[family]
    out=np.zeros((N,3,3),complex)
    for n in range(N):
        for a in range(3):
            for b in range(3):
                s=0j
                for m in range(N):
                    if m==n: continue
                    if family=="BERRY":
                        s += sign*(v[a][n,m]*v[b][m,n]-v[b][n,m]*v[a][m,n])/e(n,m)**p
                    else:
                        s += (v[a][n,m]*v[b][m,n]+v[b][n,m]*v[a][m,n])/e(n,m)**p
                out[n,a,b]=s
    return out

def _num_rhs(H, k, family, factor=2):
    if family=="METRIC": T=geo.g_metric(H,k)*factor
    elif family=="RENORM": T=geo.renorm_metric(H,k)*factor
    else: T=geo.berry_curv(H,k)  # -iOmega compares to (v v -)/eps^2 which is real=Omega structure
    return T

def numerical_verify(family, pw=None, sign=+1, factor=2):
    models=[geo.build_model(seed=s) for s in (7,101,2024)]
    rng=np.random.default_rng(0); kpts=[rng.uniform(-1.4,1.4,3) for _ in range(3)]
    num=den=0.0
    for H in models:
        for k in kpts:
            L=_num_lhs(H,k,family,pw,sign); R=_num_rhs(H,k,family,factor)
            if family=="BERRY":
                # LHS = (v^a v^b - v^b v^a)/eps^2 = -i*Omega  =>  Omega = i*LHS ; compare to berry_curv
                Lr=(1j*L).real; Rr=R
            else:
                Lr=L.real; Rr=R
            num += np.linalg.norm(Lr-Rr)**2; den += np.linalg.norm(Rr)**2
    return (num/den)**0.5 if den else 0.0


# self-test scaffolding (TASKS catalog / main / result-dump writer) removed from the
# shipped package: only symbolic_gold and numerical_verify are used by the ORCH adapter.
