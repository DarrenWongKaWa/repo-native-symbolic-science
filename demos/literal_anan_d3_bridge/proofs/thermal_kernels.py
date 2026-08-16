#!/usr/bin/env python3
"""FROZEN Guo thermal kernels (2026-08-16 clarified contract).

Definitions (frozen exactly as clarified by the human controller):
  M_ab  := M_Gamma(E_a, E_b) = [w^2] R_{1,Gamma}(w; E_a, E_b)
  T_abc := T_Gamma(E_a, E_b, E_c)
         = ( M_cb - M_ac + i Gamma F[E_c,E_c,E_c,E_a,E_b] ) / (E_b - E_a + 2 i Gamma)
  with F = Phi + Phis and F[u,u,u,v,w] the 5-node Hermite divided difference
  (u repeated three times).  The i Gamma term is the F[z,z,z,x,y] divided
  difference -- NOT a 3-node second divided difference.
  Delta_ab := E_a - E_b.
"""
import mpmath as mp
mp.mp.dps = 60

I = mp.mpc(0, 1)
pi = mp.pi


class GuoKernels:
    """Frozen kernel machinery; [w^2] extraction perturbs ONLY w."""

    def __init__(self, beta, Gamma, mu):
        self.beta = mp.mpf(beta); self.Gamma = mp.mpf(Gamma); self.mu = mp.mpf(mu)
        self._h = mp.mpf('1e-12')

    # ---- master functions ----
    def zplus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) + I*self.beta*(e - self.mu)/(2*pi)
    def zminus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) - I*self.beta*(e - self.mu)/(2*pi)
    def Phi(self, e):   return mp.mpf(1)/2 + (I/pi)*mp.digamma(self.zplus(e))
    def Phis(self, e):  return mp.mpf(1)/2 - (I/pi)*mp.digamma(self.zminus(e))
    def F(self, e):     return self.Phi(e) + self.Phis(e)
    def Fp(self, e):
        zp = I*self.beta/(2*pi); zm = -I*self.beta/(2*pi)
        return (I/pi)*mp.polygamma(1, self.zplus(e))*zp - (I/pi)*mp.polygamma(1, self.zminus(e))*zm
    def Fpp(self, e):
        zp = I*self.beta/(2*pi); zm = -I*self.beta/(2*pi)
        return (I/pi)*mp.polygamma(2, self.zplus(e))*zp**2 - (I/pi)*mp.polygamma(2, self.zminus(e))*zm**2
    def F4(self, e):
        zp = I*self.beta/(2*pi); zm = -I*self.beta/(2*pi)
        return (I/pi)*mp.polygamma(4, self.zplus(e))*zp**4 - (I/pi)*mp.polygamma(4, self.zminus(e))*zm**4
    def Phis1(self, e): return -(I/pi)*mp.polygamma(1, self.zminus(e))*(-I*self.beta/(2*pi))
    def Phis2(self, e): return -(I/pi)*mp.polygamma(2, self.zminus(e))*(-I*self.beta/(2*pi))**2
    def Phi1(self, e):  return (I/pi)*mp.polygamma(1, self.zplus(e))*(I*self.beta/(2*pi))
    def Phi2(self, e):  return (I/pi)*mp.polygamma(2, self.zplus(e))*(I*self.beta/(2*pi))**2

    # ---- R1 / [w^2] ----
    def H1(self, f, u, v): return (f(v) - f(u)) / (v - u)

    def R1(self, wv, xx, yy):
        num = (mp.mpf(1)/2)*(self.Phi(yy) + self.Phis(yy) - self.Phi(xx) - self.Phis(xx)) + \
              I*self.Gamma*(self.H1(self.Phis, xx, yy + wv) + self.H1(self.Phi, xx - wv, yy))
        return num / (wv + yy - xx + 2*I*self.Gamma)

    def _w2(self, f, h=None):
        h = self._h if h is None else h
        return (f(h) - 2*f(mp.mpf(0)) + f(-h)) / (2*h*h)

    def M(self, x, y, h=None):
        """M_Gamma(x,y) = [w^2] R1 -- FROZEN."""
        return self._w2(lambda wv: self.R1(wv, x, y), h)

    # ---- 5-node Hermite divided difference F[z,z,z,x,y] ----
    def dd5(self, z, x, y):
        f = self.F
        fxy = (f(y) - f(x)) / (y - x)
        fzx = (f(x) - f(z)) / (x - z)
        fzz = self.Fp(z)
        fzzx = (fzx - fzz) / (x - z)
        fzxy = (fxy - fzx) / (y - z)
        fzzxy = (fzxy - fzzx) / (y - z)
        fzzz = self.Fpp(z) / 2
        fzzzx = (fzzx - fzzz) / (x - z)
        return (fzzxy - fzzzx) / (y - z)

    def T(self, a, b, c, h=None):
        """T_abc = (M_cb - M_ac + i Gamma F[E_c,E_c,E_c,E_a,E_b]) / (E_b - E_a + 2 i Gamma) -- FROZEN."""
        return (self.M(c, b, h) - self.M(a, c, h) + I*self.Gamma*self.dd5(c, a, b)) / (b - a + 2*I*self.Gamma)

    # ---- S03 explicit normal form of M (cross-check authority) ----
    def M_normal_form(self, x, y):
        """S03 noncoincident closed form (authority cross-check)."""
        d = y - x
        t1 = (self.F(y) - self.F(x)) / (2*d**3)
        t2 = 2*self.Gamma*(self.Gamma - I*d)/(d**2*(d + 2*I*self.Gamma)**2) * (self.Phi1(x) + self.Phis1(y))
        t3 = self.Gamma/(2*d*(2*self.Gamma - I*d)) * (self.Phis2(y) - self.Phi2(x))
        return t1 + t2 + t3

    def T_normal_form(self, a, b, c):
        """T per the FROZEN argument order, evaluated stepwise (gate check)."""
        return {"M_cb": self.M(c, b), "M_ac": self.M(a, c),
                "F_c_c_c_a_b": self.dd5(c, a, b),
                "denominator": b - a + 2*I*self.Gamma}
