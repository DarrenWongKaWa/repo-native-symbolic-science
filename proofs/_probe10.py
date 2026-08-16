#!/usr/bin/env python3
"""Probe v10: decompose the orbit sum; test conjugation pairing hypotheses."""
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
def w2(f):
    h = mp.mpf('1e-12')
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
    fzzzxy = (fzzxy - fzzzx) / (y - z)
    return fzzzxy

def T(a, b, c):
    return (M(c, b) - M(a, c) + I*GAMMA*dd5(c, a, b)) / (b - a + 2*I*GAMMA)

ea, eb, ec = mp.mpf('-0.5'), mp.mpf('0.3'), mp.mpf('1.4')
E = (ea, eb, ec)
D = lambda u, v: u - v
x_ab, y_ac, d_bc = D(ea, eb), D(ea, ec), D(eb, ec)
print("x=Delta_ab:", mp.nstr(x_ab, 20), " y=Delta_ac:", mp.nstr(y_ac, 20), " d=Delta_bc:", mp.nstr(d_bc, 20))
print("check d == y - x:", mp.nstr(d_bc - (y_ac - x_ab), 20))

# 1. Hermiticity of M?
print()
print("M(ea,eb)     :", mp.nstr(M(ea, eb), 30))
print("M(eb,ea)     :", mp.nstr(M(eb, ea), 30))
print("conj(M(ea,eb)):", mp.nstr(mp.conj(M(ea, eb)), 30))
print("M(eb,ea) - conj(M(ea,eb)):", mp.nstr(M(eb, ea) - mp.conj(M(ea, eb)), 25))

# 2. the M-pair orbit pieces
SM_pairs = {}
SM_pairs["ab"] = x_ab*(x_ab - 2*y_ac)*(M(ea, eb) - M(eb, ea))
SM_pairs["ac"] = y_ac*(y_ac - 2*x_ab)*(M(ea, ec) - M(ec, ea))
SM_pairs["bc"] = d_bc*(y_ac + x_ab)*(M(eb, ec) - M(ec, eb))
SM = SM_pairs["ab"] + SM_pairs["ac"] + SM_pairs["bc"]
print()
print("pair ab term:", mp.nstr(SM_pairs["ab"], 30))
print("pair ac term:", mp.nstr(SM_pairs["ac"], 30))
print("pair bc term:", mp.nstr(SM_pairs["bc"], 30))
print("S_M (no i):  ", mp.nstr(SM, 30))
print("i*S_M:       ", mp.nstr(I*SM, 30))

# 3. the T sign-sum
import itertools
sign = {"abc": 1, "acb": -1, "bac": -1, "bca": 1, "cab": 1, "cba": -1}
Tsum = mp.mpc(0)
for p in itertools.permutations((ea, eb, ec)):
    key = "".join(["a" if v == ea else ("b" if v == eb else "c") for v in p])
    Tsum += sign[key]*T(*p)
print()
print("sum_pi sign(pi) T_pi:", mp.nstr(Tsum, 30))
print("-i*xyd*Tsum:", mp.nstr(-I*x_ab*y_ac*d_bc*Tsum, 30))

# 4. total SumK = i*S_M - i*xyd*Tsum
SK = I*SM - I*x_ab*y_ac*d_bc*Tsum
print()
print("SumK = i*S_M - i*xyd*Tsum:", mp.nstr(SK, 35))

# 5. D3 orbit
def D3(a, b, c):
    Dab, Dac, Dbc = D(a, b), D(a, c), D(b, c)
    t1 = -(mp.mpf(1)/Dac + mp.mpf(1)/Dbc) * (8*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis1(a)
    t2 = (2*GAMMA*Dab/(Dab + 2*I*GAMMA)) * (mp.mpf(1)/2)*Phis2(a)
    return mp.re(t1 + t2)
SD = sum(D3(*p) for p in itertools.permutations((ea, eb, ec)))
print("SumD3:", mp.nstr(SD, 35))
print("SumK+SumD3:", mp.nstr(SK + SD, 30))
