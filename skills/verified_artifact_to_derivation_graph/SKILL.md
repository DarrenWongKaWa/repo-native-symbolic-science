# Verified Artifact to Derivation Graph

## Purpose
Convert verified symbolic artifacts into a structured derivation graph. This skill ingests a set of verified derivation steps, equations, and evidence mappings and produces a comprehensive derivation graph with typed nodes and edges that captures the logical flow of the theoretical derivation.

## Activation Conditions
This skill MUST be activated when:
- A supplement request specifies `DERIVATION_GRAPH_BUILD` as a required artifact.
- The routing skill emits `routing_target: "verified_artifact_to_derivation_graph"`.
- A human scientist requests construction of a derivation graph from verified artifacts.
- A set of verified derivation steps needs to be assembled into a graph representation.
- The derivation narrative skill needs graph input.

This skill MUST NOT be activated for:
- Producing new derivation steps (that belongs to `candidate_symbolic_transformation`).
- Verifying derivation steps (that belongs to `exact_and_bounded_symbolic_verification`).
- Producing LaTeX/PDF output (that belongs to `verified_provenance_to_latex_pdf`).
- Generating physical interpretations (that belongs to `physical_interpretation_and_limiting_cases`).

## Required Inputs
1. **Derivation steps** (mandatory): Array of `derivation_step` objects, each conforming to `schemas/derivation_step.schema.json`, with valid `step_id` values from the INTERFACE CONTRACT.
2. **Equation evidence mappings** (mandatory): Array of `equation_evidence_mapping` objects conforming to `schemas/equation_evidence_mapping.schema.json`.
3. **Manifest of source artifacts** (mandatory): List of input artifacts with their SHA-256 hashes.
4. **Human decisions** (conditional): Human gate decisions for any steps that required them.
5. **Role assertion** (mandatory): Confirmation that the agent is authorized as EXECUTOR or INTEGRATOR for graph construction.

## Required Outputs

### 1. derivation_graph.json (always produced)
A complete derivation graph conforming to `schemas/derivation_graph.schema.json` with:
- All 10 node types instantiated as appropriate for the derivation.
- Edges connecting nodes with one of the 9 authorized edge types.
- Root node and leaf nodes identified.
- Each node linked to its corresponding `derivation_step` artifact.

### 2. graph_validation_report.json (always produced)
```json
{
  "graph_id": "string",
  "validation_timestamp": "string (ISO 8601)",
  "checks": {
    "graph_connected": {"status": "PASS | FAIL", "details": "string"},
    "all_nodes_referenced": {"status": "PASS | FAIL", "details": "string"},
    "no_cycles": {"status": "PASS | FAIL", "details": "string"},
    "node_type_edge_type_consistency": {"status": "PASS | FAIL", "details": "string"},
    "step_to_node_completeness": {"status": "PASS | FAIL", "details": "string"},
    "equation_label_uniqueness": {"status": "PASS | FAIL", "details": "string"},
    "provenance_chain_integrity": {"status": "PASS | FAIL", "details": "string"}
  },
  "overall_valid": true,
  "errors": [],
  "warnings": []
}
```

### 3. node_index.json (always produced)
An index mapping equation labels to graph node IDs, step IDs to node IDs, and node types to node IDs for efficient lookup.

### 4. graph_construction_report.md (always produced)
A human-readable report describing:
- How many nodes of each type were created.
- How many edges of each type were created.
- The critical path through the graph.
- Any nodes or edges that could not be established due to missing evidence.
- Coverage statistics: which step IDs and equation labels from the INTERFACE CONTRACT appear in the graph.

## Gates

### Gate 1: Input Completeness
- Every derivation step in the input must have a valid `step_id` from the INTERFACE CONTRACT.
- Every equation label referenced must be from the INTERFACE CONTRACT.
- Every step must have provenance information.

### Gate 2: Graph Structure
- The graph must be connected (there is a path from root to every node).
- No cycles in the graph (it must be a DAG).
- Node types must be consistent with edge types (certain node types only connect via certain edge types).

### Gate 3: Node-Type Assignments
Each derivation step's `derivation_category` maps to a specific `node_type`:
- `definition` → node_type `definition` or `decomposition`
- `algebraic_manipulation` → node_type `transformation`
- `product_rule` → node_type `transformation`
- `integration_by_parts` → node_type `identity`
- `index_renaming` → node_type `identity`
- `symmetry_reduction` → node_type `identity`
- `projection` → node_type `projection`
- `integration` → node_type `integration`
- `limiting_case` → node_type `limiting_case`
- `numerical_evaluation` → node_type `verification`
- `physical_interpretation` → node_type `physical_interpretation`

### Gate 4: Edge-Type Assignments
Each `relation_type` from a derivation step determines the connecting edge type:
- `definition` → edge_type `defined_by`
- `literal_equality`, `identity_under_assumptions`, `pointwise_identity` → edge_type `equal_under_assumptions`
- `projected_identity` → edge_type `projected_to`
- `integrated_identity` → edge_type `integrated_to`
- `structural_replay`, `exact_reconstruction` → edge_type `reconstructed_from`
- `numerical_regression` → edge_type `numerically_supported_by`
- `canonical_result`, `historical_result` → edge_type `derived_from`
- `physical_interpretation` → edge_type `interpreted_as`

### Gate 5: Human Gate Integration
- Nodes derived from steps that required human gate approval must record the human decision status.
- Steps with `human_gate_status: PENDING` generate a warning but do not block graph construction.
- Steps with `human_gate_status: FAILED` are included but marked with explicit caveats.

## Forbidden Operations
- **Inventing derivation steps** — only steps present in the input may become nodes.
- **Reordering the logical sequence** — edge direction must respect the actual derivation order.
- **Assigning edge types without evidence** — every edge must be justified by the corresponding derivation step's `relation_type`.
- **Omitting steps with UNVERIFIED status** — these must appear but be marked as unverified.
- **Creating cycles** — the derivation graph must be a DAG.
- **Mixing pre-IBP and post-IBP steps in a single graph without explicit boundary marking**.
- **Claiming CANONICAL status for graph nodes** — canonical status is set by the lifecycle pipeline, not by the graph builder.

## Output Directory
```
skills/verified_artifact_to_derivation_graph/output/{graph_id}/
```

## Interaction with Other Skills
- **Receives from**: `exact_and_bounded_symbolic_verification` (verified derivation steps), `provenance_claim_and_canonical_state` (canonical status information).
- **Feeds into**: `theoretical_physics_derivation_narrative` (graph as input for narrative construction), `supplementary_material_build_and_audit` (graph as structural skeleton).
- **Consumes**: `derivation_step.schema.json`, `derivation_graph.schema.json`, `equation_evidence_mapping.schema.json`.
- **Produces**: `derivation_graph.json`, `graph_validation_report.json`, `node_index.json`.

## Failure Behavior
- **DERIVATION_GAP**: If a gap exists between steps (no edge can connect them), flag it as a `DERIVATION_GAP` event. Record the gap in the validation report with the endpoints and the nature of the missing connection. Include recommendations for what kind of derivation step would bridge the gap.
- **Missing node type**: If a derivation step has an unrecognized `derivation_category`, map it to the closest node type and issue a warning.
- **Cycle detection**: If a cycle is detected, halt graph construction and report the cycle. Do not create an invalid graph.
- **Provenance chain break**: If a step's `parent_step_ids` do not correspond to nodes that exist in the graph, flag the break and request the missing steps.
- **Equation label collision**: If two steps claim the same `output_equation_label`, halt and flag the collision for human resolution.

## Blocker_5 Status
**Blocker_5**: ACTIVE — prevents premature closure of scientific sectors. The derivation graph builder must not assume a sector is complete unless all required steps are verified and integrated.

## Task Lifecycle
1. **LOAD**: Receive and validate all input derivation steps and evidence mappings.
2. **MAP**: For each derivation step, create a graph node with the appropriate `node_type` based on `derivation_category`.
3. **CONNECT**: For each pair of steps where one is a child of the other (via `parent_step_ids` / `child_step_ids`), create an edge with the appropriate `edge_type` based on `relation_type`.
4. **VALIDATE**: Run all graph structure checks: connectivity, DAG, type consistency, completeness.
5. **INDEX**: Build the `node_index.json` for efficient lookup.
6. **REPORT**: Generate the `graph_construction_report.md`.
7. **OUTPUT**: Write all output artifacts to the output directory.

## Node Construction Rules

### Root Node Identification
The root node is the derivation step with no `parent_step_ids` (or only containing identifiers not in this graph). Its node_type is typically `definition` or `raw_equation`.

### Leaf Node Identification
Leaf nodes are derivation steps that are not referenced as a parent by any other step in the graph. Their node_type is typically `physical_interpretation`, `verification`, or `limiting_case`.

### Intermediate Node Handling
Intermediate nodes are connected in both directions (have both parent and child steps). Each must be assigned the node_type that reflects its mathematical operation.

### Verification Nodes
Steps with `verification_status: VERIFIED` or `NUMERICALLY_SUPPORTED` produce verification nodes that connect to the verified equation via `numerically_supported_by` edges. Verification nodes do not participate in the main derivation chain but provide lateral support.

## Edge Direction Convention
- Edges point FROM the source (earlier/input) node TO the target (later/output) node.
- The `derived_from` edge points from child to parent.
- The `decomposed_into` edge points from parent to children.
- The `reconstructed_from` edge points from the reconstruction to its components.
- Verification edges point FROM the verification node TO the verified node.

## Validation Rules

### Connectivity
Every node must be reachable from the root node. Nodes not reachable from root are orphans and indicate a graph construction error.

### DAG Property
The graph must contain no directed cycles. Cycles indicate circular dependencies that violate the derivation logic.

### Node-Type Consistency
- A `definition` node cannot have a `decomposed_into` edge as its only outgoing edge.
- An `integration` node must have at least one `integrated_to` or `derived_from` incoming edge.
- A `verification` node should only have `numerically_supported_by` outgoing edges.

### Edge-Type Consistency
- `defined_by` edges connect `definition` nodes to other `definition` or `raw_equation` nodes.
- `decomposed_into` edges connect `decomposition` nodes to child nodes.
- `projected_to` edges connect `projection` nodes to their output.
- `integrated_to` edges connect `integration` nodes to their output.
- `interpreted_as` edges connect `physical_interpretation` nodes to equations they interpret.

## Human Escalation Behavior
- **Graph gaps**: If the derivation has logical gaps that cannot be connected, escalate with a DERIVATION_GAP event specifying the gap endpoints.
- **Conflicting interpretations**: If two interpretation nodes give contradictory interpretations of the same equation, escalate for human resolution.
- **Missing derivation steps**: If a referenced parent step does not exist in the input, request the missing step rather than silently omitting the edge.
