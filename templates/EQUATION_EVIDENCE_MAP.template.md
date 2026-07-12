# Equation Evidence Map

## Mapping Identification
- **Mapping ID**: `{{ mapping_id }}`
- **Equation Label**: `{{ equation_label }}`
- **Derivation Step ID**: `{{ derivation_step_id }}`

## Source Provenance
- **Source Task**: `{{ source_task }}`
- **Source Artifact**: `{{ source_artifact }}`
- **Source SHA-256**: `{{ source_sha }}`

## Equation Content
```latex
{{ latex_content }}
```

## Claim Information
- **Claim Type**: `{{ claim_type }}`
  (Must be one of the 16 INTERFACE CONTRACT relation types: definition, literal_equality, finite_role_preserving_rename, identity_under_assumptions, pointwise_identity, projected_identity, integrated_identity, structural_replay, exact_reconstruction, numerical_regression, counterexample, not_established, verified_candidate, canonical_result, historical_result, rejected_result)

- **Object Role**: `{{ object_role }}` (RESULT / INTERMEDIATE / DEFINITION / EXPLANATORY_NOTATION / CONJECTURE)

## Status
- **Canonical Status**: `{{ canonical_status }}`
- **Verification Verdict**: `{{ verification_verdict }}`
- **Human Gate Status**: `{{ human_gate_status }}`

## Verification Evidence

### Methods Used
{{#each verification_methods}}
- `{{ this }}`
{{/each}}

### Results
- **Verification Result**: `{{ verification_result }}`
- **Verification Task ID**: `{{ verification_task_id }}`
- **Verification Timestamp**: `{{ verification_timestamp }}`
- **Residual Expression**: `{{ residual_expression }}`

### Numerical Evidence
- **Sample Count**: `{{ sample_count }}`
- **Agreement Level**: `{{ agreement_level }}`
- **Residual Statistics**: `{{ residual_statistics }}`
- **Numerical Agreement ≠ Symbolic Equality**: `{{ numerical_agreement_is_not_symbolic_equality }}`

## Assumption Scope

### Assumptions Required
{{#each assumptions_required}}
- `{{ this }}`
{{/each}}

### Assumptions Satisfied
- **Status**: `{{ assumptions_satisfied }}`

### Domain Restrictions
{{#each domain_restrictions}}
- `{{ this }}`
{{/each}}

## Human Decision
- **Decision**: `{{ human_decision }}`
- **Reviewer**: `{{ reviewer }}`
- **Timestamp**: `{{ decision_timestamp }}`
- **Rationale**: `{{ rationale }}`
- **Decision ID**: `{{ decision_id }}`

## Provenance Chain
| Level | Step ID | Equation Label | Relation Type | Verified |
|-------|---------|---------------|---------------|----------|
{{#each provenance_chain}}
| `{{ level }}` | `{{ step_id }}` | `{{ equation_label }}` | `{{ relation_type }}` | `{{ verified }}` |
{{/each}}

## Parent and Child Mappings
- **Parent Mapping IDs**: `{{ parent_mapping_ids }}`
- **Child Mapping IDs**: `{{ child_mapping_ids }}`

## Evidence Gap Assessment
- **Is Gap**: `{{ is_gap }}`
- **Gap Severity**: `{{ gap_severity }}` (CRITICAL / MAJOR / MINOR / NONE)
- **Gap Description**: `{{ gap_description }}`
- **Required Evidence**: `{{ required_evidence_type }}`
- **Blocks Next Steps**: `{{ blocking_next_steps }}`

## Caveats
{{#each caveats}}
- `{{ this }}`
{{/each}}

## Metadata
- **Created At**: `{{ created_at }}`
- **Updated At**: `{{ updated_at }}`
- **Mapping SHA-256**: `{{ mapping_sha256 }}`
