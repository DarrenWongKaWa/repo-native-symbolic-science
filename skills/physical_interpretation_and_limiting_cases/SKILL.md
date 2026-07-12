# Physical Interpretation and Limiting Cases

## Purpose
Provide physical interpretation of mathematical expressions appearing in theoretical derivations. This skill maps terms to their physical origins, explains tensorial structure, documents parametric dependencies, analyzes limiting case behavior, and connects expressions to observable quantities.

## Activation Conditions
This skill MUST be activated when:
- A supplement request requires SEC_09_INTERPRETATION or SEC_10_LIMITS content.
- The routing skill emits `routing_target: "physical_interpretation_and_limiting_cases"`.
- A derivation step produces a result that needs physical interpretation.
- Limiting cases of a final result need to be checked against known benchmarks.
- The `theoretical_physics_derivation_narrative` skill requests interpretation content.
- The `human_readability_audit` flags missing physical interpretation.

This skill MUST NOT be activated for:
- Creating new mathematical derivations.
- Verifying symbolic correctness (that belongs to `exact_and_bounded_symbolic_verification`).
- Building the derivation graph (that belongs to `verified_artifact_to_derivation_graph`).
- Producing LaTeX output (that belongs to `verified_provenance_to_latex_pdf`).

## Required Inputs
1. **Target expressions** (mandatory): The final or intermediate expressions to interpret, each with equation label from the INTERFACE CONTRACT.
2. **Derivation steps** (mandatory): Steps that produced these expressions, including assumptions and caveats.
3. **Physical context** (mandatory): The `scientific_scope` from the supplement request, including physical system description, model parameters, and target quantity.
4. **Known benchmarks** (recommended): Known results for limiting cases (e.g., known limits from literature).
5. **Expression term annotations** (recommended): Term-by-term physical origin information if available from upstream skills.

## Required Outputs

### 1. physical_interpretation_mapping.json (always produced)
A physical interpretation mapping conforming to `schemas/physical_interpretation_mapping.schema.json` for each interpreted expression, containing:
- Interpretation type (one of 5 allowed types).
- Physical meaning narrative.
- Term-by-term interpretation (for term_by_term_physical_origin type).
- Tensorial interpretation (for tensorial_structure_meaning type).
- Parametric interpretation (for parametric_dependence_explanation type).
- Limiting case analysis (for limiting_case_behavior type).
- Observable connection (for connection_to_observable type).

### 2. limiting_cases_report.json (always produced when limiting cases exist)
```json
{
  "report_id": "string",
  "expression_label": "string",
  "limiting_cases": [
    {
      "case_id": "string",
      "limit_description": "string",
      "limit_parameters": {"parameter_name": "value_or_range"},
      "limit_expression_latex": "string",
      "simplified_limit_expression_latex": "string",
      "physical_meaning_in_limit": "string",
      "known_benchmark": "string",
      "benchmark_reference": "string (DOI or citation)",
      "agreement_status": "EXACT | APPROXIMATE | QUALITATIVE | DISAGREES | NOT_CHECKED",
      "agreement_details": "string",
      "recovery_method": "string (how the limit was taken)"
    }
  ],
  "benchmarks_checked": "integer",
  "benchmarks_passed": "integer",
  "benchmarks_failed": "integer",
  "novel_predictions": ["string (limits without known benchmarks)"]
}
```

### 3. interpretation_consistency_report.json (always produced)
```json
{
  "checks": {
    "all_final_results_interpreted": {"status": "PASS | FAIL", "uninterpreted": []},
    "term_origin_consistent_with_derivation": {"status": "PASS | FAIL", "issues": []},
    "limiting_cases_consistent": {"status": "PASS | FAIL", "contradictions": []},
    "observable_connections_valid": {"status": "PASS | FAIL", "issues": []},
    "assumptions_not_violated_in_interpretation": {"status": "PASS | FAIL", "violations": []}
  },
  "overall_consistent": true
}
```

### 4. physical_insight_summary.md (always produced)
A human-readable summary document:
- What physical mechanisms contribute to the result.
- Relative importance of different contributions.
- Parameter regimes where different terms dominate.
- Experimental signatures predicted.
- Connections to known physical phenomena.

## Gates

### Gate 1: Interpretation Completeness
- Every equation with `object_role: RESULT` must receive a physical interpretation.
- Intermediate equations may be interpreted if they have clear physical significance.
- Definitions (object_role: DEFINITION) do not require interpretation.

### Gate 2: Interpretation Justification
- Term-by-term interpretations must be grounded in the derivation's decomposition.
- Physical origins must be traceable to specific terms in the starting expression.
- If a term's physical origin is unclear, this must be documented, not guessed.

### Gate 3: Limiting Case Verification
- Each limiting case must be computed from the final expression (not assumed).
- If a known benchmark exists, agreement or disagreement must be documented.
- Disagreement with a known benchmark is a BLOCKING issue requiring re-examination.
- Limits that produce known results increase confidence.

### Gate 4: Observable Connection Validity
- Connections to observables must be physically plausible.
- The measurement protocol must be realistic.
- If no direct observable connection exists, this must be stated.

### Gate 5: Self-Consistency
- Physical interpretations must not contradict the assumptions used in the derivation.
- Limiting cases must be reachable within the domain of validity of the expression.
- Observable predictions must respect the accuracy limitations of the derivation.

## Forbidden Operations
- **Inventing physical interpretations** — interpretations must be grounded in the derivation, not speculation.
- **Claiming agreement with benchmarks not actually checked** — all benchmark comparisons must be computed.
- **Extrapolating beyond domain of validity** — limiting cases must stay within the expression's valid parameter regime.
- **Assigning physical meaning to arbitrary mathematical groupings** — groupings must correspond to physically meaningful decompositions.
- **Making experimental predictions without caveats** — all predictions must include uncertainty qualifications.
- **Hiding negative results** — if a limiting case disagrees with a known benchmark, this must be prominently reported.

## Output Directory
```
skills/physical_interpretation_and_limiting_cases/output/{interpretation_id}/
```

## The 5 Interpretation Types

### 1. term_by_term_physical_origin
- **When**: The expression is a sum of terms with distinct physical origins (e.g., different bands, different scattering mechanisms).
- **Required**: `term_interpretations` array with `term_index`, `mathematical_form`, `physical_origin`, `physical_significance`.
- **Example**: "Term 3 originates from interband transitions and represents..."

### 2. tensorial_structure_meaning
- **When**: The tensor structure of the expression carries physical meaning (e.g., Hall vs. longitudinal conductivity, symmetry constraints).
- **Required**: `tensorial_interpretation` object with `index_structure`, `tensor_rank`, `transformation_properties`, `symmetry_type`.
- **Example**: "The antisymmetric part of this tensor represents the Hall response..."

### 3. parametric_dependence_explanation
- **When**: Understanding how the result depends on physical parameters is the primary goal.
- **Required**: `parametric_interpretation` objects for key parameters.
- **Example**: "The result scales as frequency^{-2} in the high-frequency limit because..."

### 4. limiting_case_behavior
- **When**: The behavior in specific limits (frequency, temperature, coupling, etc.) is physically illuminating.
- **Required**: `limiting_cases` array with limit descriptions, expressions, and physical meanings.
- **Example**: "In the DC limit, the result reduces to the Drude formula..."

### 5. connection_to_observable
- **When**: The expression directly relates to a measurable quantity.
- **Required**: `observable_connection` object with `observable_name`, `measurement_protocol`, `relationship_to_expression`.
- **Example**: "This expression gives the nonlinear Hall conductivity, measurable via second-harmonic generation..."

## Limiting Case Analysis Protocol

### Step 1: Identify Limits
For each model parameter, identify physically interesting limits:
- Frequency: DC limit, high-frequency limit, resonant frequency.
- Temperature: Zero temperature, high temperature.
- Coupling: Weak coupling, strong coupling.
- Dimensionality: 1D, 2D, 3D limits.
- Model parameters: Any parameter that can be taken to zero or infinity.

### Step 2: Compute Limit Expressions
For each identified limit:
- Take the limit analytically using the final expression.
- Simplify the resulting expression as much as possible.
- Record the limit-taking method and any intermediate steps.

### Step 3: Compare with Benchmarks
For each limit expression:
- Search for known benchmark results in the literature.
- Compute the difference between the limit expression and the benchmark.
- Classify agreement: EXACT (symbolically identical), APPROXIMATE (differ by higher-order terms), QUALITATIVE (same functional form up to prefactors), DISAGREES (structurally different), NOT_CHECKED.

### Step 4: Flag Disagreements
If a limit disagrees with a known benchmark:
- This is a CRITICAL finding.
- Re-examine the derivation, the limit-taking, and the benchmark.
- Document the disagreement with full details.
- Escalate to human immediately.

## Benchmark Sources
Accepted benchmark sources (in priority order):
1. Exact analytical results from peer-reviewed literature.
2. Numerical results from independent groups published in peer-reviewed literature.
3. Established textbook results.
4. Results from independent computational methods (e.g., exact diagonalization for small systems).
5. Experimental measurements (with appropriate caveats about experimental uncertainty).

NOT accepted as benchmarks:
- Results from the same derivation (circular).
- Results from the same codebase without independent verification.
- Unpublished preprints without peer review.
- Qualitative statements without explicit formulas.

## Interaction with Other Skills
- **Receives from**: `theoretical_physics_derivation_narrative` (derivation context), `verified_artifact_to_derivation_graph` (expression provenance).
- **Feeds into**: `theoretical_physics_derivation_narrative` (interpretation content for narrative), `supplementary_material_build_and_audit` (interpretation sections).
- **Consumes**: `physical_interpretation_mapping.schema.json`, `derivation_step.schema.json`.
- **Produces**: `physical_interpretation_mapping.json`, `limiting_cases_report.json`, `interpretation_consistency_report.json`.

## Failure Behavior
- **DERIVATION_GAP**: If the derivation does not produce expressions that can be physically interpreted (e.g., expressions are purely formal with no clear physical meaning), flag DERIVATION_GAP.
- **Benchmark disagreement**: If a limiting case disagrees with a known benchmark, this is a blocking failure. Halt and escalate.
- **No limiting cases found**: If no meaningful limiting cases can be identified, produce a report stating this and explaining why (e.g., expression is already in simplest form, no tunable parameters).
- **Uninterpretable terms**: If some terms in the expression have no identifiable physical origin, document this explicitly rather than making unsupported guesses.

## Blocker_5 Status
**Blocker_5**: ACTIVE — prevents premature closure of scientific sectors. Physical interpretations must not be considered final until all limiting cases have been checked and all benchmark comparisons completed.

## Human Escalation Behavior
- **Physical interpretation uncertainty**: If multiple physically plausible interpretations exist for the same term, present all options and request human guidance.
- **Benchmark conflict**: If a benchmark comparison reveals disagreement, escalate with the full comparison details for human review.
- **Novel prediction**: If a limiting case produces a new prediction not previously reported, flag it as a candidate novel result and request human confirmation.
- **Observable connection gap**: If the expression cannot be connected to any known observable, escalate to determine whether this is a fundamental limitation or requires additional derivation steps.
