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
| LITERAL_ANAN_D3_SIX_ORBIT | SIX_ORBIT_UNVERIFIED_UNDER_DECLARED_CONTRACT |

The last row is the honest fail-closed outcome: under the declared
Guo-kernel interpretation of M_Gamma/T_Gamma (sources/guo_thermal_contract.md),
the orbit identity does not close numerically. The demo reports this rather
than certifying an unverified statement; the certificate records exactly what
was computed and what contract clarification is required.
