# Literal Anan D^(3) bridge — Repo-Native Symbolic Science demo

A self-contained scientific demo exercising the four core capabilities of the
repo-native pipeline on a real physics task (Anan, Kitamura & Morimoto
arXiv:2604.04520 vs the Guo/Supplement thermal framework):

1. **Notation provenance** — f_+^A != f_+^G despite the shared name; the bridge
   maps f_+^A(eps-mu+i Gamma) to 1/2 f_-^G(eps) (the REFLECTED companion), and
   the demo detects and certifies this collision (proofs/thermal_dictionary.py).
2. **Typed equality** — POINTWISE_EXACT certificates (bridges, D3 substitution)
   are kept distinct from the SIX-ORBIT statement (K relates to -D3 only after
   complete permutation reassembly).
3. **Negative controls** — the wrong real-energy f_+ branch yields a perfectly
   finite, different value (fail-as-expected discrimination), and pointwise
   K != -D3 is proven generically.
4. **Claim containment** — the final claim is restricted to the D3 bridge; no
   parent claim (complete Guo-Anan equivalence) is upgraded by any sub-proof.

## Layout

    demos/literal_anan_d3_bridge/
      README.md              this file
      task.json              machine-readable task packet
      sources/               frozen contracts (Guo, Anan, provenance hashes)
      claims/                certified claim records (generated)
      proofs/                exact proofs + kernel machinery
      negative_controls/     adversarial discriminators
      expected/certificate.json   expected vs actual certificate table
      witness/               witness parameters
      HUMAN_REVIEW.md        human review checklist
      run_all.sh             executes every gate

## Results (2026-08-16, demo witness eps = {-0.5, 0.3, 1.4}, beta=5, Gamma=0.08)

| gate | result |
|---|---|
| ANAN_ARGUMENT_TO_GUO_ZMINUS | PASS_EXACT |
| ANAN_FPLUS_TO_HALF_GUO_FMINUS | PASS_EXACT |
| ANAN_DERIVATIVE_BRIDGE_R1 / R2 | PASS_EXACT |
| LITERAL_ANAN_D3_THERMAL_BRIDGE | PASS_EXACT (POINTWISE) |
| THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT | PASS_EXACT (6/6 perms) |
| ORDERED_TRIPLE_K_EQUALS_MINUS_D3 | FAIL_EXPECTED (pointwise nonzero) |
| NEGATIVE_CONTROL_REAL_ENERGY_FPLUS | FAIL_AS_EXPECTED (finite wrong value) |
| LITERAL_ANAN_D3_SIX_ORBIT | PASS_EXACT (frozen 2026-08-16 contract; gates G1..G7) |

Contract clarified and frozen 2026-08-16:
  T_abc = (M_cb - M_ac + i Gamma F[E_c,E_c,E_c,E_a,E_b]) / (E_b - E_a + 2 i Gamma)
  K_abc = i[ x(x-2y) M_ab - x y d T_abc ],  x = Delta_ab, y = Delta_ac, d = Delta_bc
Fail-closed gate sequence (stops at the first nonzero residual, reporting the
exact gate and expression): M_KERNEL_PROOF_NORMAL_FORM, T_KERNEL_ARGUMENT_ORDER,
K_XYD_NORMAL_FORM, SIX_ORBIT_TO_QM_HD_REDUCTION (with the S3.31 endpoint
relation as CONJUGATION, never equality), SIX_ORBIT_NODE_DATA_REDUCTION,
SIX_ORBIT_REALITY, LITERAL_ANAN_D3_SIX_ORBIT.  All seven PASS; the orbit
residual scales as h^2 (pure w2-extraction truncation): sumK = -sumD3 =
0.17914332271841625 at the declared valid witness {-0.5, 0.3, 1.4}.
The packet's printed digits belong to the historical fixture (different
witness), not to this theorem's evidence.

## Mutation / adversarial pass (2026-08-16)

| mutation | injected wrong science | expected red gate | caught |
|---|---|---|---|
| M1_F_NODE_ORDER | F[Ec,Ec,Ec,Ea,Eb] -> 3-node second divided difference | G7 six-orbit | yes (residual 0.018) |
| M2_DELTA_INDEX | Delta_ca - Delta_bc -> Delta_ac - Delta_bc in K | G3 K xyd form | yes (residual 4.64) |
| M3_CONJUGATION_EQUALITY | M_ba = conj(M_ab) -> M_ba = M_ab | G4 QM/HD reduction | yes (residual 2.62) |
| M4_REAL_ENERGY_FPLUS | f_+^A(E-mu+i Gamma) -> real-energy f_+^G(E) | G7 six-orbit | yes (residual 0.35) |

Principle demonstrated: correct science -> PASS; every specific wrong science
is caught at the correct obligation (fail-closed gates, not notebook trust).

## Derivation layer (2026-08-16) — from the clean scientific background

Starting ONLY from the source definitions (z_+/-, f_+/-, rho_e^0, divided
differences, rho^(1), rho^(2), [w^2], four-sector form), with NO TRS / IBP /
weak-Gamma / two-band / three-band / supplement-compact-formula / Anan-D2D3 /
six-orbit assumptions:

| gate | statement | result |
|---|---|---|
| G-M1 | [w^2] rho^(1)_{nm} == M kernel | PASS (3 parameter sets) |
| G-M2 | M explicit normal form == S03 closed form | PASS |
| G-T3 | rho^(2) index mapping (n,l,m)=(a,c,b) is UNIQUE | PASS |
| G-T2 | [w^2] D2(f;x,y+w,z) == f[y,y,y,x,z] (5-node Hermite dd) | PASS |
| G-T1 | [w^2] rho^(2)_{e,nlm}(w,-w) == frozen T_abc | PASS |
| G-C1 | four sectors == compact master form (POINTWISE_EXACT) | PASS |
| G-S1 | carriers P/L are b<->c exchange-symmetric | PASS |
| G-S2 | coincidence classes cover all index regimes | PASS |

Derived results: M_nm = [w^2]rho^(1)_{e,nm}; T_abc = [w^2]rho^(2)_{e,a,c,b}(w,-w)
with D^(2)_+/- inherited at (e_n, e_l + w2, e_m); compact form
sigma_abc = (q/hbar)^3 int_BZ [ sum_nm M_nm P^{a(bc)}_nm + sum_nml T_nml L^{a(bc)}_nml ].