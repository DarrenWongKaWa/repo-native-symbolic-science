# Active Repaired Pair IBP Artifacts

Extraction source: SIGMAXXX_REPAIR_LINE_016_AUDITABLE_FREEZE, active_objects/

These are the export-safe active objects demonstrating the r-index repair:

- **SevenKernelFormulaTrusted.wl** — The last trusted checkpoint: 7 kernel types, 42 components
- **F_pair_total_repaired.wl** — Repaired explicit pair boundary term (6 components)
- **dF_pair_total_repaired.wl** — Differential of the repaired pair boundary term (8 components)
- **PairIBPResidualRepairedFinal.wl** — All-zero verification of the repaired pair IBP identity

The wrong (un-repaired) versions are in `../../historical/wrong_r_index/`.

## Scientific Content

The seven-kernel formula contains:
- K_center (3 components per ± sign, r = 2,3,4)
- K_pair_R (2 components per ± sign, r = 1,2)
- K_pair_vminus (4 components per ± sign, r = 0,1,2,3)
- K_pair_vplus (3 components per ± sign, r = 1,2,3)
- K_pair_vepsilon (3 components per ± sign, r = 0,1,2)
- K_loop_ReL (3 components per ± sign, r = 0,1,2)
- K_loop_ImL (2 components per ± sign, r = 0,2)

The repaired pair IBP identity (PairIBPResidualRepairedFinal.wl) confirms that all 8 residual components are identically zero.

## Usage

These files use Wolfram Language association notation. They are the frozen canonical form of the seven-kernel formula and its repaired pair IBP reduction. For the general closed form, see `../repaired_closed_form/`.
