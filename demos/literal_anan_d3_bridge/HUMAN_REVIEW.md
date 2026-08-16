# HUMAN_REVIEW.md — literal_anan_d3_bridge

Checklist for the human scientist before any claim from this demo may be
referenced externally.

## 1. Frozen inputs (verify hashes in sources/provenance.md)
- [ ] Anan D3 literal coefficient matches arXiv:2604.04520 Eq. (7) (PDF sha256 fe1dea38...)
- [ ] Guo z_+/- and f_+/- conventions match the theoretical-physics supplement (eq:zpm/eq:rho0)
- [ ] M_Gamma/T_Gamma kernels match FINAL_EXACT_CLOSED_FORM.md section 2
- [ ] Demo witness energies are the intended certified witness (currently DECLARED:
      eps = {-0.5, 0.3, 1.4}; the packet's expected digits +0.1438813736614977 /
      -0.1438813736614977 / +0.1270106832723943 are PENDING the user's witness)

## 2. Certified gates (PASS_EXACT)
- [ ] ANAN_ARGUMENT_TO_GUO_ZMINUS
- [ ] ANAN_FPLUS_TO_HALF_GUO_FMINUS
- [ ] ANAN_DERIVATIVE_BRIDGE_R1 / R2
- [ ] LITERAL_ANAN_D3_THERMAL_BRIDGE (POINTWISE_EXACT)
- [ ] THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT (6/6 permutations, Hermiticity assumed)

## 3. Negative controls (expected failures = evidence)
- [ ] ORDERED_TRIPLE_K_EQUALS_MINUS_D3 = FAIL_EXPECTED (pointwise nonzero)
- [ ] NEGATIVE_CONTROL_REAL_ENERGY_FPLUS = FAIL_AS_EXPECTED (finite wrong value)

## 4. OPEN item (do NOT certify)
- [ ] LITERAL_ANAN_D3_SIX_ORBIT — currently SIX_ORBIT_UNVERIFIED_UNDER_DECLARED_CONTRACT.
      Before this gate can pass, clarify M_Gamma/T_Gamma: (a) confirm they are the
      S06 kernels used here, or (b) supply the exact definitions the packet intends,
      and (c) supply the certified witness energies to reproduce the packet digits.

## 5. Claim containment
- [ ] No sub-proof upgrades the parent claim (complete Guo-Anan equivalence stays NOT_CLAIMED)
- [ ] This demo does not claim D2, prefactor bridges, generic-N, post-IBP BZ, degenerate bands

Sign-off: ______________________  Date: ____________
