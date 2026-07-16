#!/usr/bin/env python3
"""
Pilot-2 v2 — addresses 嘉华's four pre-Pilot-2 blockers (deterministic parts).

Blocker 1  Asymmetric numerical evidence + multi-precision:
  - numerical residual != 0  -> DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE
  - numerical residual ~ 0    -> NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE  (NOT "verified")
  - only an exact SYMBOLIC canonical(LHS-RHS)=0 earns VERIFIED_SYMBOLIC_IDENTITY
  - for the true task, show residual falls with precision (rounding, consistent with identity)
    vs a contaminated task where it plateaus (real residual).

Blocker 2  Independent gold oracle (no circular dependency):
  - GOLD  = SYMBOLIC oracle (sympy canonical(LHS-RHS)==0), a DIFFERENT code path.
  - VERIFIER = NUMERICAL geobasis reconstruction (finite-diff on a random model).
  - The two never share code; agreement is then meaningful, not "an algorithm agreeing
    with itself".

Blocker 3  Second independent task family (metric-velocity identity), to show the
  architecture is not an F-23-specific checker.
"""
import sys, json
from pathlib import Path
import numpy as np
import sympy as sp

HERE = Path(__file__).resolve().parent
import geometry as geo
from reconstruct import reconstruct
import tshg_numeric as tn

OCC = [1, 0, 0]

# ============================================================================
# GOLD ORACLE (SYMBOLIC, independent path) — parametrized mutation of F-23.
# Atoms for a fixed band pair (n,m); exact algebra; canonical(LHS-RHS)==0 ?
# ============================================================================
def symbolic_gold_F23(c2=2, c5=5, c7=-7, denom=3, drop=False, dup=False):
    I = sp.I
    eps = sp.Symbol('eps', real=True, nonzero=True)
    D = {x: sp.Symbol(f'D{x}', real=True) for x in 'abc'}
    vnm = {x: sp.Symbol(f'v{x}', complex=True) for x in 'abc'}
    def vmn(x): return sp.conjugate(vnm[x])
    L = {(x, y): sp.Symbol(f'L_{x}{y}', complex=True) for x in 'abc' for y in 'abc'}
    def Anm(y): return vnm[y]/(I*eps)
    def Amn(y): return sp.conjugate(vnm[y])/(-I*eps)
    def Re(z): return sp.Rational(1, 2)*(z + sp.conjugate(z))
    def dln(x, y, side): return L[(x, y)] if side == 'nm' else sp.conjugate(L[(x, y)])
    def vv(p, ps, q, qs):
        fp = vnm[p] if ps == 'nm' else vmn(p); fq = vnm[q] if qs == 'nm' else vmn(q)
        return fp*fq
    t1 = dln('a','c','nm')*vv('c','nm','b','mn')
    br = (0 if drop else t1) + (t1 if dup else 0)
    br += (dln('a','b','nm')*vv('b','nm','c','mn')
        + dln('a','c','mn')*vv('c','mn','b','nm') + dln('a','b','mn')*vv('b','mn','c','nm')
        + 2*dln('c','b','nm')*vv('b','nm','a','mn') + 2*dln('c','b','mn')*vv('b','mn','a','nm')
        + 2*dln('b','c','nm')*vv('c','nm','a','mn') + 2*dln('b','c','mn')*vv('c','mn','a','nm')
        + 2*dln('c','a','mn')*vv('a','mn','b','nm') + 2*dln('c','a','nm')*vv('a','nm','b','mn')
        + 2*dln('b','a','mn')*vv('a','mn','c','nm') + 2*dln('b','a','nm')*vv('a','nm','c','mn')
        - 2*dln('a','c','nm')*vv('c','nm','b','mn') - 2*dln('a','b','nm')*vv('b','nm','c','mn')
        - 2*dln('a','c','mn')*vv('c','mn','b','nm') - 2*dln('a','b','mn')*vv('b','mn','c','nm')
        + c2*D['a']*(vv('b','mn','c','nm') + vv('c','mn','b','nm'))/eps
        + c5*D['c']*(vv('a','mn','b','nm') + vv('b','mn','a','nm'))/eps
        + 5*D['b']*(vv('a','mn','c','nm') + vv('c','mn','a','nm'))/eps
        - 1*D['a']*(vv('b','mn','c','nm') + vv('c','mn','b','nm'))/eps
        + c7*D['c']*(vv('a','mn','b','nm') + vv('b','mn','a','nm'))/eps
        - 7*D['b']*(vv('a','mn','c','nm') + vv('c','mn','a','nm'))/eps)
    LHS = sp.Rational(-1, 2)*br/eps**denom
    # RHS = Re d_a(A^b A^c/eps) - 2 Re d_b(A^a A^c/eps) - 2 Re d_c(A^a A^b/eps)
    def dfac(x, y, which):
        return L[(x, y)]*Anm(y) if which == 'nm' else sp.conjugate(L[(x, y)])*Amn(y)
    def dRe(x, p, q):
        prod = Anm(p)*Amn(q)
        dprod = dfac(x, p, 'nm')*Amn(q) + Anm(p)*dfac(x, q, 'mn')
        return Re(dprod/eps - prod*D[x]/eps**2)
    RHS = dRe('a','b','c') - 2*dRe('b','a','c') - 2*dRe('c','a','b')
    return sp.simplify(sp.expand(LHS - RHS)) == 0   # True => symbolic identity holds


# ============================================================================
# NUMERICAL VERIFIER (independent path) — geobasis reconstruction, asymmetric labels.
# ============================================================================
def num_f23(H, k, c2=2, c5=5, c7=-7, denom=3, drop=False, dup=False):
    N = H.N; _, Uref = np.linalg.eigh(H(k)); eps, v, A, U = tn.objects_at(H, k, Uref)
    def enm(n, m): return eps[n]-eps[m]
    dlnA = {}
    for a in range(3):
        for b in range(3):
            dAb = tn.dA_dk(H, k, Uref, a, b); M = np.zeros((N, N), complex)
            for n in range(N):
                for m in range(N):
                    if n != m and abs(A[b][n, m]) > 1e-9: M[n, m] = dAb[n, m]/A[b][n, m]
            dlnA[(a, b)] = M
    out = np.zeros((3, 3, 3))
    for a in range(3):
        for b in range(3):
            for c in range(3):
                tot = 0j
                for n in range(N):
                    if OCC[n] == 0: continue
                    for m in range(N):
                        if m == n: continue
                        dl = lambda aa, nn, mm, bb: dlnA[(aa, bb)][nn, mm]
                        Dn = lambda aa: v[aa][n, n].real - v[aa][m, m].real
                        t1 = dl(a,n,m,c)*v[c][n,m]*v[b][m,n]
                        br = (0 if drop else t1) + (t1 if dup else 0)
                        br += dl(a,n,m,b)*v[b][n,m]*v[c][m,n]
                        br += dl(a,m,n,c)*v[c][m,n]*v[b][n,m]+dl(a,m,n,b)*v[b][m,n]*v[c][n,m]
                        br += 2*dl(c,n,m,b)*v[b][n,m]*v[a][m,n]+2*dl(c,m,n,b)*v[b][m,n]*v[a][n,m]
                        br += 2*dl(b,n,m,c)*v[c][n,m]*v[a][m,n]+2*dl(b,m,n,c)*v[c][m,n]*v[a][n,m]
                        br += 2*dl(c,m,n,a)*v[a][m,n]*v[b][n,m]+2*dl(c,n,m,a)*v[a][n,m]*v[b][m,n]
                        br += 2*dl(b,m,n,a)*v[a][m,n]*v[c][n,m]+2*dl(b,n,m,a)*v[a][n,m]*v[c][m,n]
                        br += -2*dl(a,n,m,c)*v[c][n,m]*v[b][m,n]-2*dl(a,n,m,b)*v[b][n,m]*v[c][m,n]
                        br += -2*dl(a,m,n,c)*v[c][m,n]*v[b][n,m]-2*dl(a,m,n,b)*v[b][m,n]*v[c][n,m]
                        br += c2*Dn(a)*(v[b][m,n]*v[c][n,m]+v[c][m,n]*v[b][n,m])/enm(n,m)
                        br += c5*Dn(c)*(v[a][m,n]*v[b][n,m]+v[b][m,n]*v[a][n,m])/enm(n,m)
                        br += 5*Dn(b)*(v[a][m,n]*v[c][n,m]+v[c][m,n]*v[a][n,m])/enm(n,m)
                        br += -1*Dn(a)*(v[b][m,n]*v[c][n,m]+v[c][m,n]*v[b][n,m])/enm(n,m)
                        br += c7*Dn(c)*(v[a][m,n]*v[b][n,m]+v[b][m,n]*v[a][n,m])/enm(n,m)
                        br += -7*Dn(b)*(v[a][m,n]*v[c][n,m]+v[c][m,n]*v[a][n,m])/enm(n,m)
                        tot += OCC[n]/enm(n,m)**denom*br
                out[a, b, c] = (-0.5*tot).real
    return out

def basis(H, k):
    d = [geo.d_tensor(geo.renorm_metric, H, k, c) for c in range(3)]
    N = H.N; fn = np.array(OCC[:N]); B = [np.zeros((3,3,3)) for _ in range(3)]
    for a in range(3):
        for b in range(3):
            for c in range(3):
                B[0][a,b,c]=sum(fn[n]*d[a][n,b,c] for n in range(N))
                B[1][a,b,c]=sum(fn[n]*d[b][n,a,c] for n in range(N))
                B[2][a,b,c]=sum(fn[n]*d[c][n,a,b] for n in range(N))
    return [("d_a G^bc",B[0]),("d_b G^ac",B[1]),("d_c G^ab",B[2])]

# self-test scaffolding (TASKS catalog / main / mpmath demo) removed from the shipped
# package: only symbolic_gold_F23, num_f23, basis are used by the ORCH adapter.
