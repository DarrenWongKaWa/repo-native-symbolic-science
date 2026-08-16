#!/usr/bin/env python3
"""Probe v11: direct orbit sum vs decomposition consistency + residual scaling."""
import mpmath as mp
mp.mp.dps = 60
I = mp.mpc(0, 1)
pi = mp.pi
BETA, GAMMA, MU = mp.mpf(5), mp.mpf('0.08'), mp.mpf(0)

def zplus(e): return mp.mpf(1)/2 + BETA*GAMMA/(2*pi) + I*BETA*(e - MU)/(2*pi)
def zminus(e): return mp.mpf(1)/2 + BETA*GAMMA/(2*pi) - I*BETA*(e - MU)/(2*pi)
def Phi(e):  return mp.mpf(1)/2 + (I/pi) * mp.digamma(zplus(e))
def Phis(e): return mp.mpf(1)/2 - (I/pi) * mp.digamma(zminus(e))
def F(e):    return Phi(e) + Phis(e)
def Fp(e):   return (I/pi)*mp.polygamma(1, zplus(e))*(I*BETA/(2*pi)) - (I/pi)*mp.polygamma(1, zminus(e))*(-I*BETA/(2*pi))
def Fpp(e):  return (I/pi)*mp.polygamma(2, zplus(e))*(I*BETA/(2*pi))**2 - (I/pi)*mp.polygamma(2, zminus(e))*(-I*BETA/(2*pi))**2
def Phis1(e): return -(I/pi)*mp.polygamma(1, zminus(e))*(-I*BETA/(2*pi))
def Phis2(e): return -(I/pi)*mp.polygamma(2, zminus(e))*(-I*BETA/(2*pi))**2

def H1(f, u, v): return (f(v) - f(u)) / (v - u)
def R1(wv, xx, yy):
    num = (mp.mpf(1)/2)*(Phi(yy) + Phis(yy) - Phi(xx) - Phis(xx)) + I*GAMMA*(H1(Phis, xx, yy + wv) + H1(Phi, xx - wv, yy))
    return num / (wv + yy - xx + 2*I*GAMMA)
def w2(f, h=mp.mpf('1e-12')):
    return (f(h) - 2*f(mp.mpf(0)) + f(-h)) / (2*h*h)
def M(x, y): return w2(lambda wv: R1(wv, x, y))

def dd5(z, x, y):
    f = F
    fxy = (f(y) - f(x)) / (y - x)
    fzx = (f(x) - f(z)) / (x - z)
    fzz = Fp(z)
    fzzx = (fzx - fzz) / (x - z)
    fzxy = (fxy - fzx) / (y - z)
    fzzxy = (fzxy - fzzx) / (y - z)
    fzzz = Fpp(z) / 2
    fzzzx = (fzzx - fzzz) / (x - z)
    return (fzzxy - fzzzx) / (y - z)

def T(a, b, c):
    return (M(c, b) - M(a, c) + I*GAMMA*dd5(c, a, b)) / (b - a + 2*I*GAMMA)

ea, eb, ec = mp.mpf('-0.5'), mp.mpf('0.3'), mp.mpf('1.4')
E = (ea, eb, ec)
D = lambda u, v: u - v
x_ab, y_ac, d_bc = D(ea, eb), D(ea, ec), D(eb, ec)

# direct sum
import itertools
SK = mp.mpc(0)
for p in itertools.permutations(E):
    a, b, c = p
    SK += I*(D(a,b)*(D(c,a) - D(b,c))*M(a, b) - D(a,b)*D(a,c)*D(b,c)*T(a, b, c))
print("direct SumK:", mp.nstr(SK, 40))

# decomposed
def K(a, b, c):
    return I*(D(a,b)*(D(c,a)-D(b,c))*M(a,b) - D(a,b)*D(a,c)*D(b,c)*T(a,b,c))
SD = mp.mpc(0)
for p in itertools.permutations(E):
    a, b, c = p
    t1 = -(mp.mpf(1)/D(a,c) + mp.mpf(1)/D(b,c)) * (8*GAMMA*D(a,b)/(D(a,b) + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis1(a)
    t2 = (2*GAMMA*D(a,b)/(D(a,b) + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis2(a)
    SD += mp.re(t1 + t2)
print("direct SumD3:", mp.nstr(SD, 40))
print("SumK + SumD3:", mp.nstr(SK + SD, 30))
print("Im(SumK):", mp.nstr(mp.im(SK), 30))

# residual scaling with h (w2 truncation)
def orbit_residual(h):
    def Mh(x, y): return w2(lambda wv: R1(wv, x, y), h)
    def Th(a, b, c): return (Mh(c, b) - Mh(a, c) + I*GAMMA*dd5(c, a, b)) / (b - a + 2*I*GAMMA)
    S = mp.mpc(0)
    for p in itertools.permutations(E):
        a, b, c = p
        S += I*(D(a,b)*(D(c,a) - D(b,c))*Mh(a, b) - D(a,b)*D(a,c)*D(b,c)*Th(a, b, c))
    for p in itertools.permutations(E):
        a, b, c = p
        t1 = -(mp.mpf(1)/D(a,c) + mp.mpf(1)/D(b,c)) * (8*GAMMA*D(a,b)/(D(a,b) + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis1(a)
        t2 = (2*GAMMA*D(a,b)/(D(a,b) + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis2(a)
        S += mp.re(t1 + t2)
    return S
for h in (mp.mpf('1e-10'), mp.mpf('1e-12'), mp.mpf('1e-14')):
    print("residual h=%s:" % mp.nstr(h, 4), mp.nstr(orbit_residual(h), 20))
