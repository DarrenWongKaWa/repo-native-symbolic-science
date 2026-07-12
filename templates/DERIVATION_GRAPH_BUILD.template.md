# Derivation Graph Build

## Graph Identification
- **Graph ID**: `{{ graph_id }}`
- **Supplement Request ID**: `{{ supplement_request_id }}`
- **Build Timestamp**: `{{ build_timestamp_iso8601 }}`
- **Builder Role**: `{{ builder_role }}`

## Input Artifacts
| Artifact | SHA-256 | Status |
|----------|---------|--------|
{{#each input_artifacts}}
| `{{ artifact_path }}` | `{{ sha256 }}` | `{{ status }}` |
{{/each}}

## Node Summary

| Node ID | Node Type | Equation Label | Step ID | Status |
|---------|-----------|----------------|---------|--------|
{{#each nodes}}
| `{{ node_id }}` | `{{ node_type }}` | `{{ equation_label }}` | `{{ step_id }}` | `{{ status }}` |
{{/each}}

### Node Type Distribution
- **definition**: `{{ count_definition }}`
- **raw_equation**: `{{ count_raw_equation }}`
- **decomposition**: `{{ count_decomposition }}`
- **identity**: `{{ count_identity }}`
- **transformation**: `{{ count_transformation }}`
- **projection**: `{{ count_projection }}`
- **integration**: `{{ count_integration }}`
- **limiting_case**: `{{ count_limiting_case }}`
- **verification**: `{{ count_verification }}`
- **physical_interpretation**: `{{ count_physical_interpretation }}`
- **Total Nodes**: `{{ total_nodes }}`

## Edge Summary

| Edge ID | Source | Target | Edge Type | Conditions |
|---------|--------|--------|-----------|------------|
{{#each edges}}
| `{{ edge_id }}` | `{{ source_node_id }}` | `{{ target_node_id }}` | `{{ edge_type }}` | `{{ conditions }}` |
{{/each}}

### Edge Type Distribution
- **derived_from**: `{{ count_derived_from }}`
- **defined_by**: `{{ count_defined_by }}`
- **decomposed_into**: `{{ count_decomposed_into }}`
- **reconstructed_from**: `{{ count_reconstructed_from }}`
- **equal_under_assumptions**: `{{ count_equal_under_assumptions }}`
- **projected_to**: `{{ count_projected_to }}`
- **integrated_to**: `{{ count_integrated_to }}`
- **numerically_supported_by**: `{{ count_numerically_supported_by }}`
- **interpreted_as**: `{{ count_interpreted_as }}`
- **Total Edges**: `{{ total_edges }}`

## Graph Structure
- **Root Node ID**: `{{ root_node_id }}`
- **Root Equation**: `{{ root_equation_label }}`
- **Leaf Node IDs**: `{{ leaf_node_ids }}`
- **Leaf Equations**: `{{ leaf_equation_labels }}`
- **Critical Path Length**: `{{ critical_path_length }}` nodes
- **Maximum Depth**: `{{ max_depth }}`

## Node-Type → Edge-Type Mapping

| Derivation Category | Node Type | Relation Type | Edge Type |
|--------------------|-----------|---------------|-----------|
| definition | definition | definition | defined_by |
| (raw input) | raw_equation | — | (incoming from definition) |
| (decomposition) | decomposition | literal_equality | decomposed_into / reconstructed_from |
| algebraic_manipulation | transformation | identity_under_assumptions | equal_under_assumptions |
| product_rule | transformation | pointwise_identity | equal_under_assumptions |
| integration_by_parts | identity | integrated_identity | integrated_to |
| index_renaming | identity | finite_role_preserving_rename | equal_under_assumptions |
| symmetry_reduction | identity | identity_under_assumptions | equal_under_assumptions |
| projection | projection | projected_identity | projected_to |
| integration | integration | integrated_identity | integrated_to |
| limiting_case | limiting_case | identity_under_assumptions | derived_from |
| numerical_evaluation | verification | numerical_regression | numerically_supported_by |
| physical_interpretation | physical_interpretation | canonical_result | interpreted_as |

## Validation Results

| Check | Status | Details |
|-------|--------|---------|
| Graph Connected | `{{ graph_connected_status }}` | `{{ graph_connected_details }}` |
| All Nodes Referenced | `{{ all_nodes_referenced_status }}` | `{{ all_nodes_referenced_details }}` |
| No Cycles (DAG) | `{{ no_cycles_status }}` | `{{ no_cycles_details }}` |
| Node-Type / Edge-Type Consistency | `{{ node_edge_consistency_status }}` | `{{ node_edge_consistency_details }}` |
| Step-to-Node Completeness | `{{ step_to_node_status }}` | `{{ step_to_node_details }}` |
| Equation Label Uniqueness | `{{ equation_uniqueness_status }}` | `{{ equation_uniqueness_details }}` |
| Provenance Chain Integrity | `{{ provenance_status }}` | `{{ provenance_details }}` |

### Overall: `{{ overall_valid }}`

## Issues and Gaps

### DERIVATION_GAP Events
{{#each derivation_gaps}}
- **Gap ID**: `{{ gap_id }}`
  - **Between**: `{{ source_node_id }}` → `{{ target_node_id }}`
  - **Nature**: `{{ gap_nature }}`
  - **Recommendation**: `{{ recommendation }}`
{{/each}}

### Warnings
{{#each warnings}}
- `{{ this }}`
{{/each}}

## Graph Visualization (Mermaid)
```
```mermaid
graph TD
{{#each mermaid_edges}}
    {{ source }} -->|{{ edge_type }}| {{ target }}
{{/each}}
```
```

## Node Index
| Equation Label | Node ID | Step ID | Node Type |
|---------------|---------|---------|-----------|
{{#each node_index}}
| `{{ equation_label }}` | `{{ node_id }}` | `{{ step_id }}` | `{{ node_type }}` |
{{/each}}

## Build Decisions
{{#each build_decisions}}
- **Decision**: `{{ decision }}`
  - **Rationale**: `{{ rationale }}`
  - **Made By**: `{{ made_by }}`
{{/each}}
