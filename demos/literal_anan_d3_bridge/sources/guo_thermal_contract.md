# Guo / Supplement thermal contract (frozen)

Authorities: `sigma_abc_theoretical_physics_supplement.tex` (z_±, f_±, eq:zpm,
eq:rho0), `FINAL_EXACT_CLOSED_FORM.md` (S06 compact closed form: master
functions, kernels 𝔐_Γ/𝔗_Γ), `Guo_Sigma_abc_dc_exact.txt` (frozen raw exact
DC artifact).  Hashes in sources/provenance.md.

## 1. Broadened occupations (Guo convention)

```
z_±(e) = 1/2 + βΓ/(2π) ± iβ(e−μ)/(2π)
Φ_Γ(e)   = 1/2 + (i/π) ψ⁰(z_+(e))          =: f_+^G(e)
Φ_Γ^♯(e) = 1 − Φ_Γ(2μ−e) = 1/2 − (i/π) ψ⁰(z_−(e))   =: f_−^G(e)
ρ⁰(e) = (f_+^G(e) + f_−^G(e))/2
```

For real (e, μ, β, Γ): f_−^G(e) = conj(f_+^G(e)).

NOTE (notation collision): Φ_Γ^♯ is a REFLECTED value of the same master
function, NOT an independent occupation.  The symbol "f_+" in the Anan
contract denotes a DIFFERENT function (see anan_d3_contract.md); the demo must
never equate f_+^A and f_+^G.

## 2. Exact thermal kernels (S06 closed form §2)

Hermite divided differences (globally confluent):

```
H_1[f;u,v] = ∫₀¹ f′((1−t)u + tv) dt          ( = (f(v)−f(u))/(v−u) for u≠v )
H_2[f;u,v,r] = ∫₀¹ds ∫₀^{1−s}dt f″((1−s−t)u + sv + tr)   ( = 2nd divided difference for distinct u,v,r )

R_{1,Γ}(w;x,y) =
  [ ½(Φ(y)+Φ^♯(y) − Φ(x)−Φ^♯(x)) + iΓ( H_1[Φ^♯;x,y+w] + H_1[Φ;x−w,y] ) ]
  / (w + y − x + 2iΓ)

M_Γ(x,y) = [w²] R_{1,Γ}(w;x,y)          ( ≡ 𝔐_Γ )

R_{2,Γ}(w;x,y,z) =
  [ R_{1,Γ}(−w;z,y) − R_{1,Γ}(w;x,z) + iΓ H_2[Φ+Φ^♯; z+w, x, y] ]
  / (y − x + 2iΓ)

T_Γ(x,y,z) = [w²] R_{2,Γ}(w;x,y,z)       ( ≡ 𝔗_Γ )
```

Confluent anchors: T_Γ(x,x,x) = F⁗(x)/48 with F = Φ + Φ^♯.

## 3. Frozen gap convention

```
Δ_ab := ε_a − ε_b        (Δ_ba = −Δ_ab; Δ_ab + Δ_bc + Δ_ca = 0)
```

## 4. Longitudinal all-distinct vvv coefficient (packet §8, contract input)

```
K_abc = i[ Δ_ab(Δ_ca−Δ_bc) M_Γ(ε_a,ε_b) − Δ_ab Δ_ac Δ_bc T_Γ(ε_a,ε_b,ε_c) ]
Λ_abc = Re( A^α_ab A^α_bc A^α_ca )        (loop geometry)
G_vvv  = 2 Σ_{all distinct} Λ_abc K_abc   (2 = longitudinal b↔c exchange completion)
```

STATUS: the packet declares the six-orbit identity Σ_{S3}K = −Σ_{S3}D³.
Independent verification under THIS contract is reported in
claims/six_orbit_status.json (see also proofs/six_orbit_identity.py).
