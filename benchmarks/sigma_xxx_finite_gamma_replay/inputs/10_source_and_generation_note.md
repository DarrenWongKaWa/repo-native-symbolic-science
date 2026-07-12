# Source and Generation Note

Materialized by `SLOOP_SIGMAXXX_CASE_INPUT_001_MATERIALIZE_AUTHORIZED_HUMAN_SCIENTIFIC_PACKAGE` at `2026-07-12T07:48:14.849162+00:00`.

This package uses only sources explicitly authorized by `authorized_source_allowlist.yaml` after applying explicit and glob exclusions. The forbidden `reports/`, `sigma_xxx_case_study/`, and `incoming_materials/` trees were not used as scientific input.

The package preserves the scientific boundary: DC limit first; the raw object is finite-Gamma exact; pre-raw Gamma-order expansion is forbidden. No sigma_xxx mathematical replay, CAS backend, or autonomous discovery step was executed while creating this package.

Inventory and review aids:

- `source_inventory_classification.jsonl`: every allowlisted inventory record after exclusions, with full SHA-256 and role classification.
- `excluded_source_inventory.jsonl`: excluded files and the exclusion rule that removed them.
- `source_snapshot_manifest.json`: immutable snapshots of the role-resolved active source files used by the twelve targets.
- `source_to_target_mapping.yaml`: proposed source-to-target mapping for review.
- `validation/package_validation.json`: required-target content and hash validation.
