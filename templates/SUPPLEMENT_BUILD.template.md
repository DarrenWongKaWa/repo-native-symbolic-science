# Supplement Build

## Build Identification
- **Build ID**: `{{ build_id }}`
- **Supplement Request ID**: `{{ supplement_request_id }}`
- **Build Timestamp**: `{{ build_timestamp }}`
- **Version**: `{{ version }}`
- **Blocker_5 Status**: `{{ blocker_5_status }}`

## Build Inputs

### Input Artifacts
| Artifact Type | Path | SHA-256 | Status |
|--------------|------|---------|--------|
{{#each input_artifacts}}
| `{{ artifact_type }}` | `{{ artifact_path }}` | `{{ sha256 }}` | `{{ artifact_status }}` |
{{/each}}

## Section Build Status

| Section | Title | Content Source | Equations | Figures | Tables | Status |
|---------|-------|---------------|-----------|---------|--------|--------|
{{#each section_status}}
| `{{ section_code }}` | `{{ section_title }}` | `{{ content_source }}` | `{{ equation_count }}` | `{{ figure_count }}` | `{{ table_count }}` | `{{ build_status }}` |
{{/each}}

Build status values: `COMPLETE`, `PARTIAL`, `EMPTY`

## Section Details

{{#each section_details}}

### {{ section_code }}: {{ section_title }}
- **Content Source**: `{{ content_source }}`
- **Build Status**: `{{ build_status }}`
- **Issues**: `{{ issues }}`

**Equations Included:**
{{#each equations}}
- `{{ equation_label }}` (from `{{ source_skill }}`, SHA: `{{ sha256 }}`)
{{/each}}

**Derivation Steps Referenced:**
{{#each derivation_steps}}
- `{{ step_id }}`: `{{ step_label }}`
{{/each}}

{{/each}}

## Compilation

### LaTeX Compilation
- **Status**: `{{ compilation_status }}`
- **Compiler**: `{{ compiler }}`
- **Passes**: `{{ compilation_passes }}`

### Compilation Log
```
{{ compilation_log }}
```

### Warnings
{{#each compilation_warnings}}
- `{{ this }}`
{{/each}}

## Build Integrity Report

| Check | Status | Details |
|-------|--------|---------|
| All Sections Populated | `{{ all_sections_populated_status }}` | `{{ all_sections_populated_details }}` |
| All Equations Appear | `{{ all_equations_appear_status }}` | `{{ all_equations_appear_details }}` |
| Cross-References Resolve | `{{ cross_references_resolve_status }}` | `{{ cross_references_resolve_details }}` |
| Figure/Table Labels Consistent | `{{ figure_table_labels_status }}` | `{{ figure_table_labels_details }}` |
| Reader Pathways Covered | `{{ reader_pathways_covered_status }}` | `{{ reader_pathways_covered_details }}` |
| No Stale References | `{{ no_stale_references_status }}` | `{{ no_stale_references_details }}` |
| Canonical Statuses Current | `{{ canonical_statuses_current_status }}` | `{{ canonical_statuses_current_details }}` |
| Evidence Map Complete | `{{ evidence_map_complete_status }}` | `{{ evidence_map_complete_details }}` |
| Omission Ledgers Valid | `{{ omission_ledgers_valid_status }}` | `{{ omission_ledgers_valid_details }}` |
| Blocker_5 Compliant | `{{ blocker_5_compliant_status }}` | `{{ blocker_5_compliant_details }}` |

### Overall Integral: `{{ overall_integral }}`

## Blocking Issues
{{#each blocking_issues}}
- **Issue**: `{{ issue }}`
  - **Severity**: `{{ severity }}`
  - **Affected Section**: `{{ affected_section }}`
  - **Resolution**: `{{ resolution }}`
{{/each}}

## Recommended Actions
{{#each recommended_actions}}
- `{{ this }}`
{{/each}}

## Missing Content
{{#each missing_content}}
- **Item**: `{{ item }}`
  - **Expected From**: `{{ expected_from }}`
  - **Impact**: `{{ impact }}`
{{/each}}

## Readability Audit Summary
- **Overall Score**: `{{ readability_score }}` / 10
- **Publication Readiness**: `{{ publication_readiness }}`
- **Critical Issues**: `{{ readability_critical_count }}`
- **Major Issues**: `{{ readability_major_count }}`
- **Minor Issues**: `{{ readability_minor_count }}`

## Supplement Metadata
- **Title**: `{{ supplement_title }}`
- **Authors**: `{{ authors }}`
- **Date**: `{{ date }}`
- **Derivation Branch**: `{{ derivation_branch }}`
- **Source Checkpoint ID**: `{{ source_checkpoint_id }}`
- **Build SHA-256**: `{{ build_sha256 }}`
- **Total Pages**: `{{ total_pages }}`
- **Total Equations**: `{{ total_equations }}`
- **Total Figures**: `{{ total_figures }}`
- **Total Tables**: `{{ total_tables }}`
- **Canonical Results**: `{{ canonical_results_count }}`
- **Verified Results**: `{{ verified_results_count }}`

## Claim Summary
| Claim Type | Count |
|-----------|-------|
{{#each claims_by_type}}
| `{{ claim_type }}` | `{{ count }}` |
{{/each}}

## Reproduction Package
- **Package Path**: `{{ reproduction_package_path }}`
- **SHA-256**: `{{ reproduction_package_sha256 }}`
- **Tested**: `{{ reproduction_package_tested }}`
- **Test Result**: `{{ reproduction_package_test_result }}`

## Build Decisions
{{#each build_decisions}}
- **Decision**: `{{ decision }}`
  - **Made By**: `{{ made_by }}`
  - **Rationale**: `{{ rationale }}`
  - **Timestamp**: `{{ timestamp }}`
{{/each}}

## Final Status
- **Build Complete**: `{{ build_complete }}`
- **Ready for Human Review**: `{{ ready_for_review }}`
- **Blocker_5**: `{{ blocker_5_status }}`
