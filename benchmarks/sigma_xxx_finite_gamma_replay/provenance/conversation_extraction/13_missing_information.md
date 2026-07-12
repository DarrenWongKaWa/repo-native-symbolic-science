# Missing Information

## 1. Exact raw source bytes and checksum
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** `Sigma_abc_dc_1D.txt`, authoritative source version, and SHA-256.
- **Why needed:** Literal raw-object identity and immutable replay input.
- **Dependent steps:** H001–H006.
- **Probably contained in:** `low_frequency/` or `required_file/`.
- **Acceptable human completion format:** UTF-8 source plus JSON manifest with path, size, SHA-256.
- **Blocking:** blocking for from-raw non-interactive replay.

## 2. Complete 118-row machine-readable sector tables
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** exact Modify2 projected sector `.wl` tables.
- **Why needed:** Reconstruct every coefficient row and verify \(8+50+60\).
- **Dependent steps:** H004–H006.
- **Probably contained in:** Modify2 projected sector outputs.
- **Acceptable human completion format:** Wolfram Lists/Associations with stable row IDs and hashes.
- **Blocking:** blocking for exact row replay.

## 3. Complete seven-kernel and four-kernel tables
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** `pair_post_ibp_kernel_tables.wl`, `K_center.wl`, `K_pair_R.wl`, `K_loop_ReL.wl`, `K_loop_ImL.wl`.
- **Why needed:** Verify \(208\to7\to4\) without paraphrasing long formulas.
- **Dependent steps:** H011–H016.
- **Probably contained in:** final Modify4 checkpoint.
- **Acceptable human completion format:** `.wl` files plus row-to-kernel provenance and SHA-256.
- **Blocking:** blocking for full algebraic replay.

## 4. Full 17-component pair primitive
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** `input_snapshots/F_pair_total.wl`.
- **Why needed:** Verify exact pair total-derivative identity.
- **Dependent steps:** H012–H015.
- **Probably contained in:** final pair-reduction checkpoint.
- **Acceptable human completion format:** Wolfram expression plus reconstruction script.
- **Blocking:** blocking for exact IBP replay.

## 5. Deterministic symbolic verifier scripts
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** full `final_pair_reduction_validation.wl`, center/loop reconstruction verifiers, and `modify4_to_modify5_consistency_validation.wl`.
- **Why needed:** Non-interactive symbolic oracles.
- **Dependent steps:** H006, H008–H020.
- **Probably contained in:** `modify4_anan/` stage directories.
- **Acceptable human completion format:** scripts, command lines, runtime version, expected JSON/stdout.
- **Blocking:** blocking for deterministic replay.

## 6. Unambiguous local \(R_{12}\) formula
- **Authority class:** `AMBIGUOUS`
- **Missing item:** machine-readable source for the ratio formula.
- **Why needed:** Avoid product/ratio OCR corruption.
- **Dependent steps:** H007, H018, H019.
- **Probably contained in:** TeX/WL source behind `sigma_xxx_simplification_supplement.pdf`.
- **Acceptable human completion format:** one explicit LaTeX/Wolfram formula with source hash.
- **Blocking:** bounded gap for workflow; blocking for local-h identity replay.

## 7. Held-fixed differentiation convention
- **Authority class:** `AMBIGUOUS`
- **Missing item:** explicit statement that \(\mu,\beta,\Gamma\) are fixed under \(\partial_k\).
- **Why needed:** Strict PG derivative validation.
- **Dependent steps:** H012–H014.
- **Probably contained in:** pair-IBP or Modify6 source.
- **Acceptable human completion format:** one configuration record or derivation note.
- **Blocking:** bounded gap.

## 8. Explicit band-completeness and covariant-derivative formulas
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** explicit formulas requested in identity coverage but not recovered.
- **Why needed:** Only if a replay stage invokes them.
- **Dependent steps:** none in active extracted chain unless source scripts add them.
- **Probably contained in:** model-derivation notebooks.
- **Acceptable human completion format:** explicit identities with assumptions and scope.
- **Blocking:** nonblocking for active chain; blocking if invoked.

## 9. Rice–Mele eigenvectors and phase convention
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** explicit eigenstates or gauge-stable numerical construction.
- **Why needed:** Independent reconstruction of \(A_{12}\), \(R_{12}\), gauge tests.
- **Dependent steps:** H018–H021.
- **Probably contained in:** Rice–Mele numerical scripts.
- **Acceptable human completion format:** analytical eigenvectors or deterministic eigensystem/gauge routine.
- **Blocking:** blocking for independent geometric replay.

## 10. Original numerical data, fit windows, and scripts
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** CSV/HDF5 data, plotting scripts, precision, fit windows, tolerances.
- **Why needed:** Exact figure and scaling reproduction.
- **Dependent steps:** H020–H021.
- **Probably contained in:** `fullmodify4/data/`, Modify4 sampling outputs, figure scripts.
- **Acceptable human completion format:** data archive plus deterministic Python/Wolfram scripts.
- **Blocking:** blocking for exact numerical replay; nonblocking for workflow-only MVP.

## 11. Fully dimensional unit convention
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** consistent conversion from internal to physical units.
- **Why needed:** Reproduce dimensional values.
- **Dependent steps:** H020–H021.
- **Probably contained in:** plotting scripts or paper notes.
- **Acceptable human completion format:** unit manifest.
- **Blocking:** nonblocking for dimensionless regression; blocking for physical-unit output.

## 12. Runtime environment manifest
- **Authority class:** `MISSING_FROM_CONVERSATION`
- **Missing item:** Wolfram/Mathematica version, Python environment, execution commands.
- **Why needed:** Deterministic non-interactive replay.
- **Dependent steps:** all executable stages.
- **Probably contained in:** repository logs or environment files.
- **Acceptable human completion format:** `environment.json` and `replay_commands.sh`.
- **Blocking:** blocking for reproducible execution.
