# Theoretical Supplement Request

## Request Identification
- **Request ID**: `{{ request_id }}`
- **Date**: `{{ date_iso8601 }}`
- **Requestor**: `{{ requestor_name }}`
- **Priority**: `{{ priority }}`
- **Blocker_5 Status**: `{{ blocker_5_status }}` (must be ACTIVE for production builds)

## Scientific Scope

### Physical System
- **Description**: `{{ physical_system_description }}`
- **Dimensionality**: `{{ dimensionality }}`

### Theoretical Framework
- **Framework**: `{{ theoretical_framework }}`
- **Target Quantity**: `{{ target_quantity }}`

### Variables and Parameters
- **Independent Variables**: `{{ independent_variables }}`
- **Model Parameters**: `{{ model_parameters }}`

### Key Assumptions
{{#each assumptions}}
- `{{ this }}`
{{/each}}

## Artifact Manifest

### Derivation Steps
| Step ID | Label | Input Artifacts | Output Artifacts |
|---------|-------|-----------------|------------------|
{{#each derivation_steps}}
| `{{ step_id }}` | `{{ step_label }}` | `{{ input_artifacts }}` | `{{ output_artifacts }}` |
{{/each}}

Step ID values must be from the INTERFACE CONTRACT:
`step_def_R`, `step_def_AB`, `step_raw_eq`, `step_product_rule`, `step_reorganize`,
`step_decompose`, `step_project`, `step_integ_A`, `step_integ_B`, `step_combine`,
`step_limit`, `step_numeric`, `step_interpret`

### Equations
| Equation Label | LaTeX Representation | Source Step |
|---------------|---------------------|-------------|
{{#each equations}}
| `{{ equation_label }}` | `{{ latex_representation }}` | `{{ source_step_id }}` |
{{/each}}

Equation labels must be from the INTERFACE CONTRACT:
`eq:def_R`, `eq:def_AB`, `eq:start`, `eq:identity`, `eq:reorganized`,
`eq:sector_A`, `eq:sector_B`, `eq:projected`, `eq:integrated_A`, `eq:integrated_B`,
`eq:final`, `eq:limit_eps0`, `eq:long_expr`

### Evidence Mappings
| Equation Label | Claim Type | Verification Verdict |
|---------------|-----------|---------------------|
{{#each evidence_mappings}}
| `{{ equation_label }}` | `{{ claim_type }}` | `{{ verification_verdict }}` |
{{/each}}

## Section Profile (14 Sections)

| Code | Title | Role | Required Equations |
|------|-------|------|-------------------|
| SEC_01_SCOPE | Scope and Objectives | scoping | — |
| SEC_02_CONVENTIONS | Notation and Conventions | definitional | `{{ SEC_02_equations }}` |
| SEC_03_STARTING_RESPONSE | Starting Expression for the Response | derivation | `{{ SEC_03_equations }}` |
| SEC_04_DECOMPOSITION | Expression Decomposition | derivation | `{{ SEC_04_equations }}` |
| SEC_05_SECTORS | Sector Contributions | derivation | `{{ SEC_05_equations }}` |
| SEC_06_IDENTITIES | Algebraic Identities | derivation | `{{ SEC_06_equations }}` |
| SEC_07_IBP | Integration by Parts | derivation | `{{ SEC_07_equations }}` |
| SEC_08_FINAL_RESULT | Final Simplified Result | result | `{{ SEC_08_equations }}` |
| SEC_09_INTERPRETATION | Physical Interpretation | result | `{{ SEC_09_equations }}` |
| SEC_10_LIMITS | Limiting Cases | result | `{{ SEC_10_equations }}` |
| SEC_11_VALIDATION | Validation | validation | `{{ SEC_11_equations }}` |
| SEC_12_EVIDENCE_MAP | Equation Evidence Map | metadata | `{{ SEC_12_equations }}` |
| SEC_13_ELECTRONIC_APPENDIX | Electronic Appendix | metadata | `{{ SEC_13_equations }}` |
| SEC_14_REPRODUCTION | Reproduction Instructions | metadata | `{{ SEC_14_equations }}` |

## Claim Boundary

### Claims Included
{{#each claims_included}}
- `{{ this }}`
{{/each}}

### Claims Explicitly Excluded
{{#each claims_excluded}}
- `{{ this }}`
{{/each}}

### Boundary Justification
`{{ boundary_justification }}`

## Reader Pathway Targets

### Persona: physics_first
- **Entry Section**: `{{ physics_first_entry }}`
- **Exit Section**: `{{ physics_first_exit }}`
- **Route Sections**: `{{ physics_first_route }}`
- **Expected Time**: `{{ physics_first_time }}` minutes

### Persona: derivation_checking
- **Entry Section**: `{{ derivation_checking_entry }}`
- **Exit Section**: `{{ derivation_checking_exit }}`
- **Route Sections**: `{{ derivation_checking_route }}`
- **Expected Time**: `{{ derivation_checking_time }}` minutes

### Persona: machine_reproduction
- **Entry Section**: `{{ machine_reproduction_entry }}`
- **Exit Section**: `{{ machine_reproduction_exit }}`
- **Route Sections**: `{{ machine_reproduction_route }}`
- **Expected Time**: `{{ machine_reproduction_time }}` minutes

## Constraints
- **Maximum Equation Count**: `{{ max_equation_count }}`
- **Maximum Page Estimate**: `{{ max_page_estimate }}`
- **Required Output Formats**: `{{ required_output_formats }}`

## Status
- **Overall Status**: `{{ status }}`
- **Blocker_5**: `{{ blocker_5_status }}`
- **Human Gate Required**: `{{ human_gate_required }}`
