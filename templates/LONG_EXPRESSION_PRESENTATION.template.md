# Long Expression Presentation

## Presentation Identification
- **Presentation ID**: `{{ presentation_id }}`
- **Equation Label**: `{{ equation_label }}`
- **Presentation Mode**: `{{ presentation_mode }}`
- **Term Count**: `{{ term_count }}`
- **Readability Score (Before)**: `{{ readability_before }}`
- **Readability Score (After)**: `{{ readability_after }}`

## Selected Presentation Mode: {{ presentation_mode }}

Mode must be one of the 9 allowed presentation modes:
`compact_inline`, `expanded_display`, `term_by_term_numbered`, `grouped_by_physical_origin`,
`index_structure_tree`, `tensor_component_table`, `diagrammatic_accompaniment`,
`abbreviated_with_omission_ledger`, `computational_literal_for_reproduction`

## Selection Rationale
`{{ selection_rationale }}`

## Complete LaTeX Source

### Mode: compact_inline
```latex
{{ latex_compact_inline }}
```

### Mode: expanded_display
```latex
{{ latex_expanded_display }}
```

### Mode: term_by_term_numbered
```latex
{{ latex_term_by_term_numbered }}
```

#### Term Labels
| Term Index | Label | LaTeX Snippet |
|-----------|-------|---------------|
{{#each term_labels}}
| `{{ term_index }}` | `{{ label }}` | `{{ latex_snippet }}` |
{{/each}}

### Mode: grouped_by_physical_origin
```latex
{{ latex_grouped_by_physical_origin }}
```

#### Physical Origin Groups
| Group Name | Physical Origin | Term Indices |
|-----------|----------------|--------------|
{{#each physical_origin_groups}}
| `{{ group_name }}` | `{{ physical_origin }}` | `{{ term_indices }}` |
{{/each}}

### Mode: index_structure_tree
```
{{ index_tree_ascii }}
```

### Mode: tensor_component_table
| Index Combination | Contribution |
|-------------------|-------------|
{{#each component_table}}
| `{{ index_combo }}` | `{{ contribution }}` |
{{/each}}

### Mode: diagrammatic_accompaniment
- **Diagram Reference**: `{{ diagram_reference }}`
![Diagram]({{ diagram_path }})

### Mode: abbreviated_with_omission_ledger
```latex
{{ latex_abbreviated }}
```

- **Omission Ledger Reference**: `{{ omission_ledger_ref }}`
- **Displayed Terms**: `{{ displayed_term_indices }}`
- **Omitted Terms**: `{{ omitted_term_count }}` of `{{ term_count }}`

### Mode: computational_literal_for_reproduction
```{{ language }}
{{ computational_code }}
```

## Abbreviation Rules
| Abbreviation | Expansion | Defined In |
|-------------|-----------|------------|
{{#each abbreviation_rules}}
| `{{ abbreviation }}` | `{{ expansion }}` | `{{ definition_location }}` |
{{/each}}

## Cross-References
| Target Equation | Relationship | Transformation Step |
|----------------|-------------|-------------------|
{{#each cross_references}}
| `{{ target_equation_label }}` | `{{ relationship }}` | `{{ transformation_step_id }}` |
{{/each}}

## Accessibility Notes
{{#each accessibility_notes}}
- `{{ this }}`
{{/each}}

## Metadata
- **Page Estimate**: `{{ page_estimate }}`
- **Requires Color**: `{{ requires_color }}`
- **Requires Landscape**: `{{ requires_landscape }}`
- **Created At**: `{{ created_at }}`

## Readability Assessment
| Criterion | Score (0-3) | Comment |
|-----------|-------------|---------|
| Physical meaning graspable in < 30s | `{{ score_physical }}` | `{{ comment_physical }}` |
| Index structure unambiguous | `{{ score_index }}` | `{{ comment_index }}` |
| Physical mechanism contributions identifiable | `{{ score_mechanism }}` | `{{ comment_mechanism }}` |
| Computer-algebra typeable without ambiguity | `{{ score_computational }}` | `{{ comment_computational }}` |
| Self-contained (no external notation needed) | `{{ score_selfcontained }}` | `{{ comment_selfcontained }}` |
| **Total** | **`{{ readability_score }}`** / 10 | |
