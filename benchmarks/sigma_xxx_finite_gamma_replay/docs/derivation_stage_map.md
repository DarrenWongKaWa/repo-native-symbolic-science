# Derivation Stage Map

## STAGE_001 - post-DC finite-Gamma raw object

- input object: `['low_frequency/abc_w1_w2_1D.txt', 'low_frequency/1D-PG2.nb']`
- operation: `dc_extraction_without_gamma_series`
- output object: `['Sigma_abc_dc_1D.txt', 'I_raw_post_DC_finite_Gamma']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/01_raw_sigma_xxx.txt`
- source SHA: `f613a4ce5bdb0972c32b7f799fbb408be237c94648fb9945e1b055914cfacace`
- required authorization: `HUMAN_CONFIRMED`
- closing test: `raw object boundary`
- status: `ACTIVE`
- claim type: `LITERAL_IDENTITY`

## STAGE_002 - exact separation and normalization

- input object: `['Sigma_abc_dc_1D.txt']`
- operation: `exact_expand_and_serialize`
- output object: `['Sigma_abc_dc_1D-separated.txt', 'I_raw_separated']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/05_derivation_steps.jsonl`
- source SHA: `7dd3e9b5c4e899d8ba4bb64f682f22cc97a65f184a2e3b375b9abf8ce2863aad`
- required authorization: `HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED`
- closing test: `workflow replay`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_003 - band-index abstraction

- input object: `['I_raw_separated', 'band_sum_abstractor.wl', 'band_sum_expression.nb']`
- operation: `band_index_abstraction`
- output object: `['I_projected_N_band']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/05_derivation_steps.jsonl`
- source SHA: `7dd3e9b5c4e899d8ba4bb64f682f22cc97a65f184a2e3b375b9abf8ce2863aad`
- required authorization: `STRUCTURALLY_VERIFIED`
- closing test: `workflow replay`
- status: `ACTIVE`
- claim type: `STRUCTURAL_EQUIVALENCE`

## STAGE_004 - PolyGamma and branch organization

- input object: `['I_projected_N_band']`
- operation: `group_by_polygamma_and_branch`
- output object: `['coefficient_row_ledger_118', 'C0', 'C1', 'C2']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/02_scientific_definitions.yaml`
- source SHA: `bb9ed5aed0bd01f55071ab8904bf183e261623b05c3caccdc8a395d1700b7876`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `row ledger`
- status: `ACTIVE`
- claim type: `EXACT_PARENT_RECONSTRUCTION`

## STAGE_005 - C0/C1/C2 decomposition

- input object: `['coefficient_row_ledger_118']`
- operation: `exact_sector_partition`
- output object: `['I_center_raw', 'I_pair_raw', 'I_loop_raw']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/06_sector_decomposition.yaml`
- source SHA: `102843f14e9b891903642ce97762bf06c8065956d53f5ff5f6f6a247edd93d23`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `sector reconstruction`
- status: `ACTIVE`
- claim type: `EXACT_PARENT_RECONSTRUCTION`

## STAGE_006 - exact reconstruction

- input object: `['I_raw_separated', 'I_center_raw', 'I_pair_raw', 'I_loop_raw']`
- operation: `subtract_and_simplify`
- output object: `['raw_sector_reconstruction_zero']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/parent_reconstruction_results.json`
- source SHA: `24993af53991f61116255a435fe7e95d2f5086ffff2e0eff61327ed499efed34`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `parent reconstruction`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_007 - h-matrix physical-basis rewrite

- input object: `['I_center_raw', 'I_pair_raw', 'I_loop_raw']`
- operation: `rewrite_h_matrix_elements`
- output object: `['I_physical_basis_unfused']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/07_identity_registry.yaml`
- source SHA: `78ef4dd6747a0b1b59cb0088ecb4ca24186a86b56bf32e2e923dbc9d6a1d5700`
- required authorization: `HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED`
- closing test: `identity replay`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_008 - pair hxx geometry closure

- input object: `['I_pair_raw', 'pair_residual_rows_clean.wl']`
- operation: `oriented_pair_closure`
- output object: `['D_pair_shift_table.wl', 'D_pair_derivative_IBP_candidates.wl', 'pair_residual_rows_after_hxx_closure']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/07_identity_registry.yaml`
- source SHA: `78ef4dd6747a0b1b59cb0088ecb4ca24186a86b56bf32e2e923dbc9d6a1d5700`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `pair closure`
- status: `ACTIVE`
- claim type: `EXACT_PARENT_RECONSTRUCTION`

## STAGE_009 - center and loop organization

- input object: `['I_center_raw', 'I_physical_basis_unfused']`
- operation: `center_velocity_power_collection`
- output object: `['I_center', 'K_c']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/06_sector_decomposition.yaml`
- source SHA: `102843f14e9b891903642ce97762bf06c8065956d53f5ff5f6f6a247edd93d23`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `sector organization`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_010 - 208-row to seven-kernel fusion

- input object: `['I_center', 'pair_residual_rows_after_hxx_closure', 'I_loop']`
- operation: `kernel_fusion`
- output object: `['seven_kernel_formula', 'pair_post_ibp_kernel_tables.wl']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/symbolic_oracle_comparison.json`
- source SHA: `af1d2d0d5869d260edd67528fbb70277810b0fe543e720791b40aa21fb614bf1`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `kernel fusion`
- status: `ACTIVE`
- claim type: `EXACT_PARENT_RECONSTRUCTION`

## STAGE_011 - three-stage pair IBP

- input object: `['seven_kernel_formula']`
- operation: `exact_periodic_BZ_IBP`
- output object: `['pair_residual_after_targeted_IBP', 'F_epsilon_0']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/local_exact_algebra_results.json`
- source SHA: `d94ae866efbe75a91a7d43d02b9551be9d55edc63a18c015817cc7e37d376ede`
- required authorization: `AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION`
- closing test: `pair IBP applicability audit`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_012 - 17-component pair primitive

- input object: `['I_pair_full', 'I_pair_R', 'F_epsilon_0', 'F_second', 'F_coupled']`
- operation: `exact_pair_reconstruction`
- output object: `['F_pair_total', 'pair_reduction_zero']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/local_exact_algebra_results.json`
- source SHA: `d94ae866efbe75a91a7d43d02b9551be9d55edc63a18c015817cc7e37d376ede`
- required authorization: `AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION`
- closing test: `pair primitive reconstruction`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_013 - four surviving kernels

- input object: `['I_center', 'I_pair_R', 'I_loop', 'F_pair_total']`
- operation: `final_projected_assembly`
- output object: `['sigma_xxx_projected_closed_form']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/08_expected_symbolic_results.yaml`
- source SHA: `b34e3be2a3e12593ffea13cfbc25ba6de0e013614929eb29b33e7c8720ad2f6c`
- required authorization: `HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED`
- closing test: `closed-form target`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_014 - bounded Anan comparison

- input object: `['sigma_xxx_projected_closed_form']`
- operation: `bounded_reference_comparison`
- output object: `['Anan_pair_plus_branch_match', 'Anan_loop_structural_match']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/08_expected_symbolic_results.yaml`
- source SHA: `b34e3be2a3e12593ffea13cfbc25ba6de0e013614929eb29b33e7c8720ad2f6c`
- required authorization: `STRUCTURALLY_VERIFIED`
- closing test: `bounded comparison`
- status: `ACTIVE`
- claim type: `STRUCTURAL_EQUIVALENCE`

## STAGE_015 - Rice-Mele specialization

- input object: `['sigma_xxx_projected_closed_form', 'H_Rice_Mele']`
- operation: `model_substitution_and_symmetry_reduction`
- output object: `['sigma_xxx_Rice_Mele_shift_sector']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `inputs/03_model_and_parameters.yaml`
- source SHA: `2fca2882168ee79a7a723477cb6dd88c24fea1dd7bf9cbf5970eec48189b7bca`
- required authorization: `SYMBOLICALLY_VERIFIED`
- closing test: `model specialization`
- status: `ACTIVE`
- claim type: `EXACT_SYMBOLIC_EQUALITY`

## STAGE_016 - Modify5 regression

- input object: `['raw_two_band_h_basis', 'geometric_decomposition', 'Modify5_v2_complete_1D_kkk_normal_form']`
- operation: `high_precision_numerical_regression`
- output object: `['pointwise_regression_pass', 'integrated_consistency_pass']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/gamma_scaling_results.json`
- source SHA: `79c46a87ba9b241813276ea97eaaddb3dcde10765611c552b51d0d600ada99c9`
- required authorization: `NUMERICALLY_SUPPORTED`
- closing test: `numerical regression`
- status: `ACTIVE`
- claim type: `NUMERICAL_AGREEMENT`

## STAGE_017 - numerical and scaling validation

- input object: `['sigma_xxx_Rice_Mele_shift_sector', 'final_Rice_Mele_parameters']`
- operation: `periodic_BZ_sampling_and_asymptotic_fit`
- output object: `['Fig2_heatmap', 'Fig2_linecuts', 'Fig3_scaling_results']`
- scientific scope: `projected one-dimensional sigma_xxx finite-Gamma replay`
- source-backed artifact: `reference_run/gamma_scaling_results.json`
- source SHA: `79c46a87ba9b241813276ea97eaaddb3dcde10765611c552b51d0d600ada99c9`
- required authorization: `NUMERICALLY_SUPPORTED`
- closing test: `scaling regression`
- status: `ACTIVE`
- claim type: `ASYMPTOTIC_RELATION`
