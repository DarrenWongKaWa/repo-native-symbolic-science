#!/usr/bin/env python3
"""Formalization of the clean scientific background (2026-08-16).

Source definitions ONLY (no compact formulas, no Anan D2/D3, no six-orbit):
  z_+/-(e), f_+/-(e), rho_e^0(e) = (f_+ + f_-)/2
  D_f(x,y) first divided difference (confluent by continuation)
  D2_f(u,v,r) second divided difference (Hermite)
  rho^(1)_{e,nm}(w) = [rho^0(e_m)-rho^0(e_n) + iG D_{f_-}(e_n,e_m+w)
                       + iG D_{f_+}(e_n-w,e_m)] / (w + e_mn + 2iG)
  rho^(2)_{e,nlm}(w1,w2) = [rho^(1)_{e,lm}(w2) - rho^(1)_{e,nl}(w1)
                       + iG D^(2)_+ + iG D^(2)_-] / (w1+w2+e_mn+2iG)
  [w^2]X = (1/2) d2/dw2 at w=0
  e_nm := e_n - e_m
M_nm := [w^2] rho^(1)_{e,nm}(w);  T_nml := [w^2] rho^(2)_{e,nlm}(w,-w)
"""
import mpmath as mp
mp.mp.dps = 60
I = mp.mpc(0, 1)
pi = mp.pi


class SourceResponse:
    """Formalized source: thermal functions + divided differences + rho kernels."""

    def __init__(self, beta, Gamma, mu):
        self.beta = mp.mpf(beta); self.Gamma = mp.mpf(Gamma); self.mu = mp.mpf(mu)

    # -- thermal functions (section 5) --
    def zplus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) + I*self.beta*(e - self.mu)/(2*pi)
    def zminus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) - I*self.beta*(e - self.mu)/(2*pi)
    def fplus(self, e):  return mp.mpf(1)/2 + (I/pi)*mp.digamma(self.zplus(e))
    def fminus(self, e): return mp.mpf(1)/2 - (I/pi)*mp.digamma(self.zminus(e))
    def rho0(self, e):   return (self.fplus(e) + self.fminus(e))/2

    # -- divided differences (section 6) --
    def D1(self, f, u, v):
        return (f(v) - f(u)) / (v - u)

    def D2(self, f, u, v, r):
        return (self.D1(f, u, v) - self.D1(f, v, r)) / (u - r)

    # -- first-order density response (section 7) --
    def rho1(self, wv, n, m):
        num = (self.rho0(m) - self.rho0(n)
               + I*self.Gamma*(self.D1(self.fminus, n, m + wv)
                               + self.D1(self.fplus, n - wv, m)))
        return num / (wv + (m - n) + 2*I*self.Gamma)

    # -- second-order density response (section 8), D^(2) inherited: shift on the l node
    def rho2(self, w1, w2, n, l, m):
        d2 = self.D2(self.fminus, n, l + w2, m) + self.D2(self.fplus, n, l + w2, m)
        num = (self.rho1(w2, l, m) - self.rho1(w1, n, l)
               + I*self.Gamma*d2)
        return num / (w1 + w2 + (m - n) + 2*I*self.Gamma)

    # -- [w^2] extraction (section 9) --
    def w2(self, f, h=mp.mpf('1e-12')):
        return (f(h) - 2*f(mp.mpf(0)) + f(-h)) / (2*h*h)

    # -- coefficients (section 10) --
    def M(self, n, m):  return self.w2(lambda wv: self.rho1(wv, n, m))
    def T(self, n, l, m): return self.w2(lambda wv: self.rho2(wv, -wv, n, l, m))
