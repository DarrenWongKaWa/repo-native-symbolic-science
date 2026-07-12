# Mathematical Omission Ledger

## Omission Identification
- **Omission ID**: `{{ omission_id }}`
- **Equation Label**: `{{ equation_label }}`
- **Full Expression SHA-256**: `{{ full_expression_sha256 }}`

## Term Statistics
- **Total Term Count**: `{{ total_term_count }}`
- **Displayed Term Count**: `{{ displayed_term_count }}`
- **Omitted Term Count**: `{{ omitted_term_count }}`
- **Omitted Fraction**: `{{ omitted_fraction }}`

## Omission Pattern
- **Pattern Type**: `{{ omission_pattern }}`
  (Must be one of: `first_k_displayed`, `representative_sample`, `structured_ellipsis`, `typographic_grouping`, `block_diagram_replacement`, `index_range_notation`)

- **Pattern Description**: `{{ pattern_description }}`

## Reconstruction Rule

### Rule Type
`{{ rule_type }}`
(Must be one of: `permutation_symmetry`, `index_cyclic_extension`, `tensor_symmetry_closure`, `explicit_term_list`, `generating_function_substitution`, `computational_regeneration`)

### Rule Description
`{{ rule_description }}`

### Rule in LaTeX
```latex
{{ rule_latex }}
```

### Rule as Code
```{{ rule_language }}
{{ rule_code }}
```

## Displayed Terms
| Term Index | LaTeX Snippet | Display Rationale |
|-----------|---------------|-------------------|
{{#each displayed_terms}}
| `{{ term_index }}` | `{{ term_latex_snippet }}` | `{{ display_rationale }}` |
{{/each}}

## Omitted Terms
| Term Index | LaTeX Snippet | Physical Origin | Magnitude Estimate | Symmetry Class |
|-----------|---------------|-----------------|-------------------|----------------|
{{#each omitted_terms}}
| `{{ term_index }}` | `{{ term_latex_snippet }}` | `{{ physical_origin }}` | `{{ magnitude_estimate }}` | `{{ symmetry_class }}` |
{{/each}}

## Reconstruction Verification
- **Reconstruction Verified**: `{{ reconstruction_verified }}`
- **Reconstruction Method**: `{{ reconstruction_method }}`
- **Reconstruction SHA-256**: `{{ reconstruction_sha256 }}`
- **SHA-256 Match**: `{{ sha256_match }}`
- **Reconstruction Residual**: `{{ reconstruction_residual }}`
- **Verification Timestamp**: `{{ verification_timestamp }}`

## Abbreviated Display
```latex
{{ abbreviated_display_latex }}
```

## Full Expression (for reference — not displayed in supplement)
```latex
{{ full_expression_latex }}
```

## Metadata
- **Created At**: `{{ created_at }}`
- **Source Artifact SHA-256**: `{{ source_artifact_sha256 }}`

## Validation
- **All Displayed Terms In Full Expression**: `{{ all_displayed_present }}`
- **All Omitted Terms In Full Expression**: `{{ all_omitted_present }}`
- **No Term Double-Counted**: `{{ no_double_count }}`
- **Omitted + Displayed = Total**: `{{ count_check }}`
