# HUMAN_REVIEW.md — literal_anan_d3_bridge

Checklist for the human scientist before any claim from this demo may be
referenced externally.

## 1. Frozen inputs (verify hashes in sources/provenance.md)
- [ ] Anan D3 literal coefficient matches arXiv:2604.04520 Eq. (7) (PDF sha256 fe1dea38...)
- [ ] Guo z_+/- and f_+/- conventions match the theoretical-physics supplement (eq:zpm/eq:rho0)
- [ ] M_Gamma/T_Gamma kernels match FINAL_EXACT_CLOSED_FORM.md section 2
- [x] Demo witness energies {-0.5, 0.3, 1.4} declared VALID by the controller (2026-08-16);
      packet digits are the historical fixture

## 2. Certified gates (PASS_EXACT)
- [ ] ANAN_ARGUMENT_TO_GUO_ZMINUS
- [ ] ANAN_FPLUS_TO_HALF_GUO_FMINUS
- [ ] ANAN_DERIVATIVE_BRIDGE_R1 / R2
- [ ] LITERAL_ANAN_D3_THERMAL_BRIDGE (POINTWISE_EXACT)
- [ ] THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT (6/6 permutations, Hermiticity assumed)

## 3. Negative controls (expected failures = evidence)
- [ ] ORDERED_TRIPLE_K_EQUALS_MINUS_D3 = FAIL_EXPECTED (pointwise nonzero)
- [ ] NEGATIVE_CONTROL_REAL_ENERGY_FPLUS = FAIL_AS_EXPECTED (finite wrong value)

## 4. Six-orbit gate (CLOSED 2026-08-16 with the clarified contract)
- [x] Contract frozen: T_abc = (M_cb - M_ac + i Gamma F[E_c,E_c,E_c,E_a,E_b])/(E_b - E_a + 2 i Gamma)
- [x] Gates G1..G7 all PASS (M normal form, T argument order, K xyd form, QM/HD
      reduction with the S3.31 CONJUGATION relation, node-data reduction, reality,
      sumK + sumD3 = 0 with h^2-scaling residual)
- [x] Witness {-0.5, 0.3, 1.4} declared valid; theorem established with it.
      The packet's digits (+0.1438813736614977 ...) belong to the historical fixture.

## 5. Claim containment
- [ ] No sub-proof upgrades the parent claim (complete Guo-Anan equivalence stays NOT_CLAIMED)
- [ ] This demo does not claim D2, prefactor bridges, generic-N, post-IBP BZ, degenerate bands

Sign-off: ______________________  Date: ____________