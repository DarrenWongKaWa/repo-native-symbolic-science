# Physical Interpretation

## Interpretation Identification
- **Interpretation ID**: `{{ interpretation_id }}`
- **Equation Label**: `{{ equation_label }}`
- **Interpretation Type**: `{{ interpretation_type }}`
- **Physical Domain**: `{{ physical_domain }}`

Interpretation type must be one of the 5 allowed types:
`term_by_term_physical_origin`, `tensorial_structure_meaning`, `parametric_dependence_explanation`,
`limiting_case_behavior`, `connection_to_observable`

## Physical Meaning
`{{ physical_meaning }}`

## Interpretation Type Details

---

### Term-by-Term Physical Origin
(Applies when `interpretation_type = term_by_term_physical_origin`)

| Term Index | Mathematical Form | Physical Origin | Physical Significance | Expected Magnitude | Symmetry |
|-----------|-------------------|-----------------|----------------------|-------------------|----------|
{{#each term_interpretations}}
| `{{ term_index }}` | `{{ mathematical_form }}` | `{{ physical_origin }}` | `{{ physical_significance }}` | `{{ expected_magnitude }}` | `{{ symmetry_properties }}` |
{{/each}}

#### Connections Between Terms
{{#each term_connections}}
- `{{ term_index_a }}` ↔ `{{ term_index_b }}`: `{{ connection }}`
{{/each}}

---

### Tensorial Structure Meaning
(Applies when `interpretation_type = tensorial_structure_meaning`)

- **Index Structure**: `{{ index_structure }}`
- **Tensor Rank**: `{{ tensor_rank }}`
- **Transformation Properties**: `{{ transformation_properties }}`
- **Symmetry Type**: `{{ symmetry_type }}`
- **Conservation Law Connection**: `{{ conservation_law_connection }}`

---

### Parametric Dependence Explanation
(Applies when `interpretation_type = parametric_dependence_explanation`)

| Parameter | Role in Expression | Monotonicity | Scaling Behavior |
|-----------|-------------------|--------------|-----------------|
{{#each parametric_interpretations}}
| `{{ parameter }}` | `{{ role_in_expression }}` | `{{ monotonicity }}` | `{{ scaling_behavior }}` |
{{/each}}

---

### Limiting Case Behavior
(Applies when `interpretation_type = limiting_case_behavior`)

| Limit Description | Limit Expression | Parameters | Physical Meaning | Benchmark | Agreement |
|-------------------|-----------------|------------|-----------------|-----------|------------|
{{#each limiting_cases}}
| `{{ limit_description }}` | `{{ limit_expression }}` | `{{ limit_parameters }}` | `{{ physical_meaning_in_limit }}` | `{{ known_benchmark }}` <br/> `{{ benchmark_reference }}` | `{{ agreement_with_benchmark }}` |
{{/each}}

Agreement values: `EXACT`, `APPROXIMATE`, `QUALITATIVE`, `DISAGREES`, `NOT_CHECKED`

---

### Connection to Observable
(Applies when `interpretation_type = connection_to_observable`)

- **Observable Name**: `{{ observable_name }}`
- **Measurement Protocol**: `{{ measurement_protocol }}`
- **Relationship to Expression**: `{{ relationship_to_expression }}`
- **Typical Magnitude**: `{{ typical_magnitude }}`
- **Experimental Signature**: `{{ experimental_signature }}`

---

## Assumptions
{{#each assumptions}}
- `{{ this }}`
{{/each}}

## Caveats
{{#each caveats}}
- `{{ this }}`
{{/each}}

## Limiting Cases (Full Analysis)

### Identified Limits
{{#each limiting_cases}}
#### `{{ limit_description }}`
- **Parameters**: `{{ limit_parameters }}`
- **Limit Taking Method**: `{{ recovery_method }}`

**Expression in this limit:**
```latex
{{ simplified_limit_expression_latex }}
```

**Physical Meaning:**
`{{ physical_meaning_in_limit }}`

**Benchmark Comparison:**
- **Benchmark**: `{{ known_benchmark }}`
- **Reference**: `{{ benchmark_reference }}`
- **Agreement**: `{{ agreement_status }}`
- **Details**: `{{ agreement_details }}`

{{/each}}

### Novel Predictions
{{#each novel_predictions}}
- `{{ this }}`
{{/each}}

## Metadata
- **Created At**: `{{ created_at }}`
- **Interpretation SHA-256**: `{{ interpretation_sha256 }}`
