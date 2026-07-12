# Derivation Step

## Step Identification
- **Step ID**: `{{ step_id }}`
- **Step Label**: `{{ step_label }}`
- **Derivation Category**: `{{ derivation_category }}`
- **Object Role**: `{{ object_role }}`

## Input / Output

| | Equation Label | Object ID | SHA-256 |
|---|---------------|-----------|---------|
| **Input** | `{{ input_equation_label }}` | `{{ source_object_id }}` | `{{ source_sha256 }}` |
| **Output** | `{{ output_equation_label }}` | `{{ target_object_id }}` | `{{ target_sha256 }}` |

## Relation Type
- **Relation Type**: `{{ relation_type }}`
  (Must be one of the 16 INTERFACE CONTRACT relation types: definition, literal_equality, finite_role_preserving_rename, identity_under_assumptions, pointwise_identity, projected_identity, integrated_identity, structural_replay, exact_reconstruction, numerical_regression, counterexample, not_established, verified_candidate, canonical_result, historical_result, rejected_result)

- **Symbolic Equality Claimed**: `{{ symbolic_equality_claimed }}`

## Status
- **Canonical Status**: `{{ canonical_status }}` (CANONICAL / INTEGRATED / VERIFIED / CANDIDATE / NOT_ESTABLISHED)
- **Verification Status**: `{{ verification_status }}` (VERIFIED / NUMERICALLY_SUPPORTED / UNVERIFIED / NOT_APPLICABLE)
- **Pointwise/Integrated Scope**: `{{ pointwise_integrated_scope }}` (pointwise / integrated / not_applicable)
- **Human Gate Status**: `{{ human_gate_status }}` (NOT_REQUIRED / PENDING / PASSED / FAILED)

## Index Scope

### Free Indices
{{#each free_indices}}
- `{{ this }}`
{{/each}}

### Dummy Indices
{{#each dummy_indices}}
- `{{ this }}`
{{/each}}

### Index Domains
| Index | Domain |
|-------|--------|
{{#each index_domains}}
| `{{ index }}` | `{{ domain }}` |
{{/each}}

### Summation Conventions
{{#each summation_conventions}}
- `{{ this }}`
{{/each}}

### Symmetry Properties
{{#each symmetry_properties}}
- `{{ this }}`
{{/each}}

### Role-Preserving Renames
| Original | Renamed | Justification |
|----------|---------|---------------|
{{#each role_preserving_renames}}
| `{{ original_index }}` | `{{ renamed_index }}` | `{{ justification }}` |
{{/each}}

## Expression Scope
- **Scope Type**: `{{ expression_scope_type }}` (pointwise / integrated / projected / asymptotic / formal / unknown)
- **Domain Restrictions**: `{{ domain_restrictions }}`
- **Dimensionality**: `{{ dimensionality }}`

## Assumptions Required
{{#each assumptions}}
- `{{ this }}`
{{/each}}

## Derivative Information (F007 Fields)

| Field | Value |
|-------|-------|
| Derivative Variable | `{{ derivative_variable }}` |
| Held Fixed Variables | `{{ held_fixed_variables }}` |
| Derivative Order | `{{ derivative_order }}` |
| Mixed Derivative Ordering | `{{ mixed_derivative_ordering }}` |
| Sign Provenance | `{{ sign_provenance }}` |
| Coefficient Provenance | `{{ coefficient_provenance }}` |

## Provenance Chain
{{#each provenance_chain}}
1. `{{ this }}`
{{/each}}

## Parent and Child Steps
- **Parent Step IDs**: `{{ parent_step_ids }}`
- **Child Step IDs**: `{{ child_step_ids }}`

## Roles
- **Executor Role**: `{{ executor_role }}`
- **Verifier Role**: `{{ verifier_role }}`
- **Role Separation Valid**: `{{ role_separation_valid }}` (Executor MUST NOT equal Verifier)

## Verification Evidence

### Methods Used
{{#each verification_methods}}
- `{{ this }}`
{{/each}}

### Details
- **Verification Task ID**: `{{ verification_task_id }}`
- **Result**: `{{ verification_result }}`
- **Timestamp**: `{{ verification_timestamp }}`
- **Residual Expression**: `{{ residual_expression }}`

## Numerical Support
- **Support Level**: `{{ numerical_support_level }}` (none / weak / moderate / strong / conclusive)
- **Sample Count**: `{{ sample_count }}`
- **Agreement Level**: `{{ agreement_level }}`

## Caveats
{{#each caveats}}
- `{{ this }}`
{{/each}}

## LaTeX Content

### Input Expression
```latex
{{ latex_input }}
```

### Output Expression
```latex
{{ latex_output }}
```

### Transformation (if applicable)
```latex
{{ latex_transformation }}
```

## Metadata
- **Created At**: `{{ created_at }}`
- **Updated At**: `{{ updated_at }}`
- **Artifact SHA-256**: `{{ artifact_sha256 }}`
