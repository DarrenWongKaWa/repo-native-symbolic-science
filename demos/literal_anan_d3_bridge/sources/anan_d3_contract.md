# Literal Anan D^(3) contract (frozen)

Authorities: Anan, Kitamura & Morimoto arXiv:2604.04520 (2026), Eq. (7) p.2
(PDF SHA-256 fe1dea385c765608f48e2b3f0ce8b027c0433650b2cebfe4629dc9eb707cbc81;
repo-authenticated snapshot D3Reference.wl); user demo packet §3, §7.

## 1. Anan thermal function

```
f_+^A(x) = 1/4 + (1/(2πi)) ψ⁰( 1/2 + βx/(2πi) )
x_a = ε_a − μ + iΓ
f_{+,a}^{A′}  = f_+^A′(x_a),   f_{+,a}^{A″} = f_+^A″(x_a)
```

NOTATION COLLISION: f_+^A ≠ f_+^G.  The bridge (proved exactly in
proofs/thermal_dictionary.py) is f_+^A(ε_a−μ+iΓ) = ½ f_−^G(ε_a), and the
derivative dictionary f_{+,a}^{A(r)} = ½ f_−^{G(r)}(ε_a), r = 1, 2.

## 2. Literal D^(3) coefficient (Anan Eq. (7), both terms inside Re[])

```
D^{(3),A}_{abc} = Re[
   −(1/Δ_ac + 1/Δ_bc) · (8ΓΔ_ab/(Δ_ab+2iΓ)) · f_{+,a}^{A′}
   + (2ΓΔ_ab/(Δ_ab+2iΓ)) · f_{+,a}^{A″}
]
```

After the derivative dictionary (POINTWISE EXACT, proved in proofs/d3_bridge.py):

```
D^{(3),A}_{abc} = Re[
   −4Γ Δ_ab/(Δ_ab+2iΓ) (1/Δ_ac + 1/Δ_bc) f_−^{G′}(ε_a)
   +  Γ Δ_ab/(Δ_ab+2iΓ) f_−^{G″}(ε_a)
]
```

## 3. Claim boundary (packet §15)

CLAIM: literal Anan D3 thermal notation is exactly bridged to the Guo/
Supplement thermal notation, and the longitudinal all-distinct three-band vvv
block agrees after complete six-orbit reassembly with convention factor −2.
NOT_CLAIMED: complete Guo-Anan conductivity equivalence; literal D2 bridge;
complete overall prefactor bridge; generic-N proof; post-IBP BZ equivalence;
degenerate-band extension.
