#!/usr/bin/env python3
"""Guo exact thermal kernels M_Gamma / T_Gamma — high-precision evaluation.

M_Gamma(x,y) = [w^2] R_{1,Gamma}(w;x,y);  T_Gamma(x,y,z) = [w^2] R_{2,Gamma}(w;x,y,z)
per the S06 closed form.  [w^2] extraction perturbs ONLY w (verified against the
S03 explicit noncoincident M closed form).  Shared by six_orbit_identity.py and
the negative controls.  Also anchors the confluence limit T(x,x,x) = F''''(x)/48.
"""
import mpmath as mp
mp.mp.dps = 60

I = mp.mpc(0, 1)
pi = mp.pi

class GuoKernels:
    def __init__(self, beta, Gamma, mu):
        self.beta = mp.mpf(beta); self.Gamma = mp.mpf(Gamma); self.mu = mp.mpf(mu)
        self._h = mp.mpf('1e-12')

    def zplus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) + I*self.beta*(e - self.mu)/(2*pi)
    def zminus(self, e): return mp.mpf(1)/2 + self.beta*self.Gamma/(2*pi) - I*self.beta*(e - self.mu)/(2*pi)
    def Phi(self, e):   return mp.mpf(1)/2 + (I/pi)*mp.digamma(self.zplus(e))
    def Phis(self, e):  return mp.mpf(1)/2 - (I/pi)*mp.digamma(self.zminus(e))
    def F(self, e):     return self.Phi(e) + self.Phis(e)
    def Phi1(self, e):  return (I/pi)*mp.polygamma(1, self.zplus(e))*(I*self.beta/(2*pi))
    def Phis1(self, e): return -(I/pi)*mp.polygamma(1, self.zminus(e))*(-I*self.beta/(2*pi))
    def Phi2(self, e):  return (I/pi)*mp.polygamma(2, self.zplus(e))*(I*self.beta/(2*pi))**2
    def Phis2(self, e): return -(I/pi)*mp.polygamma(2, self.zminus(e))*(-I*self.beta/(2*pi))**2

    def H1(self, f, u, v): return (f(v) - f(u)) / (v - u)

    def R1(self, wv, xx, yy):
        num = (mp.mpf(1)/2)*(self.Phi(yy) + self.Phis(yy) - self.Phi(xx) - self.Phis(xx)) + \
              I*self.Gamma*(self.H1(self.Phis, xx, yy + wv) + self.H1(self.Phi, xx - wv, yy))
        return num / (wv + yy - xx + 2*I*self.Gamma)

    def R2(self, wv, xx, yy, zz):
        def Ff(u): return self.F(u)
        num = self.R1(-wv, zz, yy) - self.R1(wv, xx, zz) + I*self.Gamma*self._H2(Ff, zz + wv, xx, yy)
        return num / (yy - xx + 2*I*self.Gamma)

    def _H2(self, f, u, v, r):
        return (self.H1(f, u, v) - self.H1(f, v, r)) / (u - r)

    def _w2(self, f):
        h = self._h
        return (f(h) - 2*f(mp.mpf(0)) + f(-h)) / (2*h*h)

    def M(self, x, y): return self._w2(lambda wv: self.R1(wv, x, y))
    def T(self, x, y, z): return self._w2(lambda wv: self.R2(wv, x, y, z))

    def M_explicit_check(self, x, y):
        """S03 noncoincident closed form (cross-check only)."""
        d = y - x
        t1 = (self.F(y) - self.F(x)) / (2*d**3)
        t2 = 2*self.Gamma*(self.Gamma - I*d)/(d**2*(d + 2*I*self.Gamma)**2) * (self.Phi1(x) + self.Phis1(y))
        t3 = self.Gamma/(2*d*(2*self.Gamma - I*d)) * (self.Phis2(y) - self.Phi2(x))
        return t1 + t2 + t3


def confluence_anchor(beta=5, Gamma=mp.mpf('0.08'), mu=0):
    """T at near-coincident nodes must approach the F4/48 limit as separation shrinks."""
    gk = GuoKernels(beta, Gamma, mu)
    x = mp.mpf('0.4')
    zp = I*beta/(2*pi); zm = -I*beta/(2*pi)
    F4 = ((I/pi)*mp.polygamma(4, gk.zplus(x))*zp**4
          - (I/pi)*mp.polygamma(4, gk.zminus(x))*zm**4)
    target = F4/48
    series = []
    for eps in (mp.mpf('1e-3'), mp.mpf('1e-6'), mp.mpf('1e-9')):
        t_num = gk.T(x, x + eps, x - eps)
        series.append({"sep": str(eps), "T": mp.nstr(t_num, 35),
                       "abs_diff": mp.nstr(abs(t_num - target), 25)})
    e1 = float(series[0]["abs_diff"]); e2 = float(series[2]["abs_diff"])
    converging = e2 < e1/10
    return {"target_F4_over_48": mp.nstr(target, 35), "series": series,
            "converging": bool(converging)}
