#!/usr/bin/env python3
"""
Geometric-tensor library for the geometric-basis reconstruction capability.

Provides, on a concrete random smooth multiband model H(k):
  band-diagonal geometric tensors and their k-derivatives, all gauge-invariant:
    g_n^{ab}   quantum metric              = sum'_m Re(A^a_nm A^b_mn)
    O_n^{ab}   Berry curvature (as i*..)   = i sum'_m (A^a_nm A^b_mn - A^b_nm A^a_mn)
    G_n^{ab}   band-renormalized metric    = sum'_m Re(A^a_nm A^b_mn / eps_nm)
  and d_c of each, plus f_n-weighted band sums.

All objects are built from v^a_nm = <u_n|d_a H|u_m> and A^a_nm = -i v^a_nm/eps_nm
(the standard relation), so no explicit gauge fixing is needed for the invariant
tensors above (their k-derivatives are clean finite differences).
"""
import numpy as np


def build_model(N=3, seed=7):
    rng = np.random.default_rng(seed)
    def randH():
        M = rng.standard_normal((N, N)) + 1j*rng.standard_normal((N, N))
        return (M + M.conj().T)/2
    H0 = randH()
    Gs = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(0,1,1),(1,0,1),(1,-1,0)]
    HG = {g: (rng.standard_normal((N,N))+1j*rng.standard_normal((N,N))) for g in Gs}
    def H(k):
        M = H0.astype(complex).copy()
        for g, Mg in HG.items():
            ph = np.exp(1j*np.dot(g, k))
            M = M + Mg*ph + Mg.conj().T*np.conj(ph)
        return (M + M.conj().T)/2
    H.N = N
    return H


def _dH(H, k, a, h=1e-6):
    e = np.zeros(3); e[a] = h
    return (H(k+e) - H(k-e))/(2*h)


def objects(H, k):
    """eps_n, v[a][n,m], A[a][n,m] at k (no gauge fixing needed for invariants)."""
    N = H.N
    w, U = np.linalg.eigh(H(k))
    v = [U.conj().T @ _dH(H, k, a) @ U for a in range(3)]
    A = [np.zeros((N, N), complex) for _ in range(3)]
    for b in range(3):
        for n in range(N):
            for m in range(N):
                if n != m:
                    A[b][n, m] = -1j*v[b][n, m]/(w[n]-w[m])
    return w, v, A


def _psum(fn, n, N):
    return sum(fn(m) for m in range(N) if m != n)


def g_metric(H, k):
    """g_n^{ab} tensor, shape [N,3,3]."""
    N = H.N; w, v, A = objects(H, k)
    return np.array([[[_psum(lambda m: (A[a][n,m]*A[b][m,n]).real, n, N)
                       for b in range(3)] for a in range(3)] for n in range(N)])


def berry_curv(H, k):
    """Omega_n^{ab} = i sum'_m (A^a A^b - A^b A^a), shape [N,3,3] (real)."""
    N = H.N; w, v, A = objects(H, k)
    return np.array([[[(1j*_psum(lambda m: A[a][n,m]*A[b][m,n]-A[b][n,m]*A[a][m,n], n, N)).real
                       for b in range(3)] for a in range(3)] for n in range(N)])


def renorm_metric(H, k):
    """G_n^{ab} = sum'_m Re(A^a A^b / eps_nm), shape [N,3,3]."""
    N = H.N; w, v, A = objects(H, k)
    def e(n,m): return w[n]-w[m]
    return np.array([[[_psum(lambda m: (A[a][n,m]*A[b][m,n]/e(n,m)).real, n, N)
                       for b in range(3)] for a in range(3)] for n in range(N)])


def d_tensor(tensor_fn, H, k, c, h=2e-5):
    """d_c of any tensor-valued function tensor_fn(H,k) via central difference."""
    e = np.zeros(3); e[c] = h
    return (tensor_fn(H, k+e) - tensor_fn(H, k-e))/(2*h)
