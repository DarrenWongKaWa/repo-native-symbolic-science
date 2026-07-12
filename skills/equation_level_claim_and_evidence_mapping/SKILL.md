# Equation Level Claim and Evidence Mapping

## Purpose
Establish and document the precise relationship between every equation in a supplement and the evidence that supports it. This skill creates the one-to-one mapping between equations, derivation steps, verification evidence, claim types, and canonical status — forming the audit trail that connects final results to their provenance.

## Activation Conditions
This skill MUST be activated when:
- A supplement request requires SEC_12_EVIDENCE_MAP content.
- The routing skill emits `routing_target: "equation_level_claim_and_evidence_mapping"`.
- A set of equations needs to be mapped to their supporting evidence.
- The `supplementary_material_build_and_audit` skill requires evidence mappings.
- A human scientist requests an evidence audit.
- The `human_readability_audit` flags missing or incomplete evidence mappings.

This skill MUST NOT be activated for:
- Performing verification (that belongs to `exact_and_bounded_symbolic_verification`).
- Creating derivation steps (that belongs to `candidate_symbolic_transformation`).
- Building the derivation graph (that belongs to `verified_artifact_to_derivation_graph`).
- Producing LaTeX output (that belongs to `verified_provenance_to_latex_pdf`).

## Required Inputs
1. **Derivation steps** (mandatory): Array of all `derivation_step` objects for the supplement.
2. **Equations** (mandatory): Array of all equations with their labels from the INTERFACE CONTRACT.
3. **Verification evidence** (mandatory): Verification results from `exact_and_bounded_symbolic_verification` for each step.
4. **Canonical status registry** (mandatory): Current canonical status of all artifacts from `provenance_claim_and_canonical_state`.
5. **Human gate decisions** (conditional): For any steps requiring human gate approval.
6. **Supplement claim registry** (mandatory): All claims made in the supplement from `schemas/supplement_claim_registry.schema.json`.

## Required Outputs

### 1. equation_evidence_mapping.json (one per equation)
An evidence mapping conforming to `schemas/equation_evidence_mapping.schema.json` for each equation. Contains:
- `mapping_id`, `equation_label`, `derivation_step_id`.
- `source_task`, `source_artifact`, `source_sha` (full provenance).
- `verification_verdict` from the verification evidence.
- `claim_type` (from the 16-value relation_type enum).
- `assumption_scope` with required and satisfied assumptions.
- `human_decision` status.
- `object_role` (RESULT, INTERMEDIATE, DEFINITION, EXPLANATORY_NOTATION, CONJECTURE).
- `canonical_status`.
- `caveats`.

### 2. evidence_matrix.json (always produced)
A matrix showing the relationship between all equations, steps, claims, and evidence:
```json
{
  "matrix_id": "string",
  "supplement_request_id": "string",
  "rows": [
    {
      "equation_label": "string",
      "step_id": "string",
      "object_role": "string",
      "claim_type": "string",
      "verification_verdict": "string",
      "canonical_status": "string",
      "human_gate_status": "string",
      "parent_equations": ["string"],
      "child_equations": ["string"],
      "evidence_sha": "string"
    }
  ],
  "summary": {
    "total_equations": "integer",
    "verified_count": "integer",
    "numerically_supported_count": "integer",
    "unverified_count": "integer",
    "canonical_count": "integer",
    "gaps_count": "integer"
  }
}
```

### 3. evidence_gap_report.json (always produced)
```json
{
  "gaps": [
    {
      "gap_id": "string",
      "equation_label": "string",
      "gap_description": "string",
      "gap_severity": "CRITICAL | MAJOR | MINOR",
      "required_evidence_type": "string",
      "blocking_next_steps": "boolean",
      "recommendation": "string"
    }
  ],
  "total_gaps": "integer",
  "critical_gaps": "integer",
  "blocking_publication": "boolean"
}
```

### 4. claim_provenance_chain.json (always produced)
A document tracing each claim back through its full provenance chain:
```json
{
  "chain_id": "string",
  "chains": [
    {
      "final_claim_id": "string",
      "final_equation_label": "string",
      "chain": [
        {
          "step_id": "string",
          "equation_label": "string",
          "relation_type": "string",
          "verification_verdict": "string"
        }
      ],
      "root_equation_label": "string",
      "chain_length": "integer",
      "all_links_verified": "boolean",
      "broken_links": ["string"]
    }
  ]
}
```

## Gates

### Gate 1: Complete Coverage
- Every equation label from the INTERFACE CONTRACT must have an evidence mapping.
- Every derivation step must have its input and output equations mapped.
- Every claim in the claim registry must be traceable to specific equations.

### Gate 2: Evidence Adequacy
- Equations claimed as `pointwise_identity` must have exact symbolic verification evidence.
- Equations claimed as `integrated_identity` must have integration verification evidence.
- Equations with only numerical evidence must have `claim_type` no higher than `numerical_regression`.
- The principle "numerical agreement is not symbolic equality" must be enforced.

### Gate 3: Status Consistency
- `canonical_status` must match the canonical registry.
- `verification_status` must be consistent with the verification evidence.
- `object_role` must be consistent with the equation's role in the derivation.
- `claim_type` must be consistent with the `relation_type` of the derivation step that produced the equation.

### Gate 4: Human Gate Integration
- Equations from steps requiring human gate approval must have `human_decision` recorded.
- Steps with `human_gate_status: PENDING` must be flagged.
- Steps with `human_gate_status: FAILED` cannot have canonical status higher than `CANDIDATE`.

### Gate 5: Gap Detection
- Any equation without verification evidence is a gap.
- Any claim without supporting evidence is a gap.
- Any provenance chain break is a gap.
- Gaps are classified as CRITICAL (blocks publication), MAJOR (significant caveat required), or MINOR (document but proceed).

## Forbidden Operations
- **Claiming verification that was not performed** — verification_verdict must match actual verification results.
- **Promoting claim type without evidence** — claim_type must be the most specific type supported by evidence.
- **Hiding evidence gaps** — all gaps must be documented in the evidence_gap_report.
- **Mixing evidence levels** — numerical evidence cannot support a symbolic equality claim.
- **Claiming CANONICAL without human gate** — canonical status must come from the lifecycle pipeline.
- **Silent assumption violations** — if an equation's required assumptions are not satisfied, this must be flagged.

## Output Directory
```
skills/equation_level_claim_and_evidence_mapping/output/{mapping_id}/
```

## Claim Type Assignment Rules

### definition
Assigned to equations with `object_role: DEFINITION`. No verification required. These are true by definition.

### literal_equality
Assigned when two expressions are symbolically identical (same parse tree). Must pass `literal_sameq` verification.

### finite_role_preserving_rename
Assigned when expressions differ only by documented, role-preserving index renames. Requires `finite_index_replay` verification.

### identity_under_assumptions
Assigned when expressions are equal only under specific assumptions. Requires `exact_subtraction_under_assumptions` verification, and assumptions must be documented.

### pointwise_identity
Assigned when expressions are equal at every point in the domain. Requires `exact_subtraction_under_assumptions` with empty (or universally true) assumptions.

### projected_identity
Assigned when expressions are equal only after projection onto a subspace (e.g., a specific band index). Requires `projection_regression` verification.

### integrated_identity
Assigned when expressions are equal only after integration over some variables. Requires integration verification and scope of integration documented.

### structural_replay
Assigned when a derivation procedure has been replayed with a structurally identical expression. Requires `parent_child_reconstruction` verification.

### exact_reconstruction
Assigned when child expressions have been reassembled into the parent. Requires `parent_child_reconstruction` with zero residual.

### numerical_regression
Assigned when only numerical evidence supports the relationship. Cannot be promoted beyond `CANDIDATE` canonical status.

### counterexample
Assigned when a specific counterexample has been found that disproves an identity. This is a FAILED claim.

### not_established
Assigned when insufficient evidence exists to make any claim. This is the default for unverified equations.

### verified_candidate
Assigned when verification has passed but human gate is still pending. Cannot be CANONICAL.

### canonical_result
Assigned when the equation has passed through the full lifecycle pipeline and achieved CANONICAL status. Requires human gate and integration verification.

### historical_result
Assigned to equations that are cited from previous work and not re-derived in the current supplement.

### rejected_result
Assigned to equations that were previously claimed but have been formally rejected.

## Object Role Assignment Rules

### RESULT
The equation is a primary result of the derivation (typically SEC_08_FINAL_RESULT).

### INTERMEDIATE
The equation is an intermediate step in the derivation, not a final result.

### DEFINITION
The equation defines notation, a quantity, or a decomposition (typically SEC_02_CONVENTIONS).

### EXPLANATORY_NOTATION
The equation serves only to explain notation and is not part of the derivation chain.

### CONJECTURE
The equation is conjectured but not proven. Cannot have canonical_status above CANDIDATE.

## Evidence Gap Classification

### CRITICAL Gaps
- A claimed final result has no verification evidence.
- A claimed pointwise identity has only numerical evidence.
- A canonical result's provenance chain is broken.
- Results cited as benchmarks cannot be located.

### MAJOR Gaps
- An intermediate step has no verification evidence but is used in subsequent steps.
- Assumptions required for a step are not documented.
- Human gate is pending for a step that is needed for the final result.

### MINOR Gaps
- A definition or explanatory notation equation lacks formal evidence mapping.
- A limiting case has not been checked against a known benchmark.
- Reader pathway annotations are incomplete.

## Interaction with Other Skills
- **Receives from**: ALL skills (as the central evidence authority), `exact_and_bounded_symbolic_verification` (verification results), `provenance_claim_and_canonical_state` (canonical status).
- **Feeds into**: `supplementary_material_build_and_audit` (evidence map section), `theoretical_physics_derivation_narrative` (status qualifiers), `human_readability_audit` (evidence traceability).
- **Consumes**: `equation_evidence_mapping.schema.json`, `derivation_step.schema.json`, `supplement_claim_registry.schema.json`.
- **Produces**: `equation_evidence_mapping.json`, `evidence_matrix.json`, `evidence_gap_report.json`.

## Failure Behavior
- **DERIVATION_GAP**: If an equation in the derivation chain has no evidence and no upstream skill can provide it, flag DERIVATION_GAP. This blocks claims that depend on this equation.
- **Evidence conflict**: If two verification runs give contradictory results for the same equation, halt. Escalate for human resolution. Do not choose one arbitrarily.
- **Incomplete provenance**: If an equation's provenance chain cannot be traced back to a `RAW_INGESTED` source, flag it as a provenance gap.
- **Status inflation**: If an equation's `canonical_status` is higher than the evidence supports, downgrade it and flag the inconsistency.

## Blocker_5 Status
**Blocker_5**: ACTIVE — prevents premature closure of scientific sectors. Evidence mapping must not be considered complete until every equation in the derivation has a verified evidence trail or a documented gap.

## Human Escalation Behavior
- **Unresolvable evidence gap**: If an equation requires evidence that no existing skill or tool can provide, escalate with a description of what evidence is needed and why it is unavailable.
- **Canonical promotion request**: If all evidence is in place for a canonical promotion but human gate is required, prepare the promotion package and escalate.
- **Evidence quality concern**: If evidence exists but has quality issues (e.g., low-precision numerical checks for a high-precision claim), escalate for human assessment.
