# Source and Generation Note

## Raw expression

**[HUMAN_CONFIRMED]**

```text
DC limit first
Gamma remains finite and exact
then normalization, decomposition, simplification,
closed-form construction and model-specific validation
```

The raw one-dimensional expression was not obtained by first expanding in \(\Gamma\).

**[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** The conversation names:

```text
low_frequency/abc_w1_w2_1D.txt
low_frequency/1D-PG2.nb
Sigma_abc_dc_1D.txt
Sigma_abc_dc_1D-separated.txt
```

The end-to-end report describes DC extraction with \(\omega_2=-\omega_1\), extraction of the required
low-frequency coefficient, and no \(\Gamma\)-Laurent expansion. Exact notebook commands and the raw checksum
are not present in the conversation.

## Languages and tools

- **[EXPLICITLY_STATED_IN_CONVERSATION] Mathematica/Wolfram Language:** source notebooks, row tables,
  exact coefficient manipulation, kernel tables, primitive searches, and exact reconstruction scripts.
- **[EXPLICITLY_STATED_IN_CONVERSATION] Python:** numerical sampling, CSV/figure production, validation
  orchestration, and later workflow infrastructure.
- **[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED] Human-supplied structure:** scope correction, physical basis choices,
  claim boundaries, Rice–Mele specialization, and interpretation of final kernels.
- **[SYMBOLICALLY_VERIFIED] Automated checks:** row counts, exact reconstruction differences, pair closure,
  kernel fusion, pair IBP, and Modify4-to-Modify5 specialization.
- **[NUMERICALLY_SUPPORTED] Independent checks:** pointwise basis equality, integrated response agreement,
  heatmap-linecut consistency, mesh convergence, gauge checks, and scaling fits.

## Normalization and band abstraction

**[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** `band_sum_abstractor.wl` and `band_sum_expression.nb` mapped explicit
band labels to \(n,m,\ell\), while `Sigma_abc_dc_1D-separated.txt` exposed the exact PolyGamma and finite-\(\Gamma\)
denominator structure.

**[HUMAN_CONFIRMED]** This is projected multiband \(\sigma^{xxx}\), not full tensorial \(\sigma_{abc}\),
because independent Cartesian matrix-element heads had already collapsed to \(k\).

## Sector and kernel files

```text
Modify2 projected sector .wl tables
sigma_xxx_simplification_supplement.pdf
fullmodify4_summary_report.pdf
pair_hkk_geometry_closure/output/pair_residual_rows_clean.wl
pair_hkk_geometry_closure/output/pair_hkk_geometry_rules.wl
pair_hkk_geometry_closure/output/pair_hkk_reduced_rows.wl
pair_hkk_geometry_closure/output/D_pair_shift_table.wl
pair_hkk_geometry_closure/output/D_pair_velocity_table_updated.wl
pair_hkk_geometry_closure/output/D_pair_derivative_IBP_candidates.wl
pair_post_ibp_kernel_tables.wl
K_center.wl
K_pair_R.wl
K_loop_ReL.wl
K_loop_ImL.wl
```

The active final chain reports \(118\) raw provenance rows, a \(208\)-row post-expansion/post-orbit
inventory, seven fused kernels, and four surviving kernels after the verified pair IBP.

## Pair IBP files

```text
global_coupled_IBP_primitives.wl
final_pair_reduction_validation.wl
input_snapshots/F_pair_total.wl
```

**[SYMBOLICALLY_VERIFIED]** The final pair primitive contains \(1+4+12=17\) components. The exact oracle is

\[
I_{\rm pair}^{\rm full}
-I_{\rm pair}^{R}
-\partial_kF_{\rm pair}^{\rm total}=0.
\]

**[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** No center- or loop-sector IBP exactness is claimed.

## Final theoretical rendering

```text
sigma_xxx_theoretical_derivation_supplement.pdf
modify4_to_modify5_consistency_validation.wl
```

This supplement states that it introduces no new simplification; it translates the completed symbolic pipeline
into a bounded theoretical derivation and fixes the final claim boundary.

## Rice–Mele specialization

```text
modify5_v2_complete_1d_kkk.pdf
fullmodify4_summary_report.pdf
rice_mele_fig2_fig3_complete.pdf
```

The final exact finite-\(\Gamma\) parameter set is

```text
t0 = 1
delta_t = 0.1 t0
m = 0.1 t0
epsilon_1 = -E
epsilon_2 = +E
Delta_half = sqrt(m^2+delta_t^2)
```

The Modify5-v2 file is a target-inspired normal form of the exact Modify4 two-band kernel. It is not a
full tensorial result.

## Superseded branches

1. **[CONTRADICTED] Pre-raw \(\Gamma\)-expansion interpretation.**
   Overridden by the direct human correction and excluded from replay.

2. **[SUPERSEDED] Conservative no-nontrivial-IBP evaluator.**
   `sigma_xxx_simplification_supplement.pdf` states \(I_{\rm raw}=I_{\rm IBP}+\partial_k0\) for that earlier
   evaluator. The later theoretical supplement contains the active verified multiband pair-IBP chain.

3. **[SUPERSEDED] Truncated plotting folder.**
   `rice_mele_plot_report.pdf` used
   \(\Gamma\sigma^{(1)}+\Gamma^2\sigma^{(2)}\) with \(t_0=1,\delta t=0.5,m=0.2\), explicitly because the
   exact finite-\(\Gamma\) response was unavailable in that folder.

4. **[CONTRADICTED] Projected multiband result as full \(\sigma_{abc}\).**
   The final scope audit requires independent Cartesian matrix-element heads before projection.

## Independent-check boundary

- **[SYMBOLICALLY_VERIFIED]** exact zero differences are symbolic claims.
- **[NUMERICALLY_SUPPORTED]** finite-tolerance regressions remain numerical claims.
- **[STRUCTURALLY_VERIFIED]** matching geometric object types is not coefficient equality.
- **[HUMAN_CONFIRMED]** no new canonical formula may be promoted by the replay benchmark.
