# Exact and Bounded Symbolic Verification

## Purpose
Verify exact or bounded relations between symbolic expressions with **declared assumptions, explicit scope, and counterexample search**. This skill produces `claim_relation.json` that categorizes the relationship between two expressions into one of twelve defined relation types. Verification is performed by a Verifier role that is SEPARATE from the Executor who produced the candidate expression. Numerical agreement alone MUST NOT become symbolic equality. Every claim must declare its assumptions and scope.

## Activation Conditions
This skill MUST be activated when:
- The routing skill emits `routing_target: "exact_and_bounded_symbolic_verification"` with `task_class: "verification"`.
- A candidate transformed expression needs to be verified against its source (the `old - new = 0` gate).
- A parent-child reconstruction needs independent verification.
- A regression target needs confirmation.
- Two expressions from different derivation branches need to be compared.
- An identity claim (from any source) needs verification.

This skill MUST NOT be activated for:
- Producing candidate transformations (that belongs to `candidate_symbolic_transformation`).
- Normalizing expressions before verification (normalization should already be done).
- Verifying a claim that was produced by the SAME agent (Executor-Verifier separation).

## Required Inputs
1. **Expression A** (mandatory): The first expression, often the "source" or "old" expression. Must have a known `sha256` and provenance.
2. **Expression B** (mandatory): The second expression, often the "candidate" or "new" expression. Must have a known `sha256` and provenance.
3. **Claim being verified** (mandatory): A description of the claimed relationship (e.g., "A - B = 0", "A equals B under assumption X", "A projects to B").
4. **Declared assumptions** (mandatory when applicable): All assumptions under which the claim is supposed to hold.
5. **Declared scope** (mandatory): The domain over which the claim is supposed to hold (e.g., "all real values of free parameters," "all index values in range 1..D," "at the point x=0").
6. **Verification method constraint** (optional): The human may specify which verification methods are acceptable and which are not.
7. **Role assertion** (mandatory): Proof that the Verifier is a different agent/process from the Executor who produced Expression B.
8. **Provenance of both expressions** (mandatory): Full lineage from raw ingestion through normalization and (for B) transformation.

## Required Output Directory
```
skills/exact_and_bounded_symbolic_verification/output/{verification_id}/
```
Where `{verification_id}` is a deterministic identifier based on the SHA-256 of both expressions + the claimed relation + assumptions.

## Required Output Artifacts

### 1. claim_relation.json (always produced)
```json
{
  "verification_id": "string",
  "expression_a": {
    "sha256": "string",
    "provenance_ref": "string (raw_object_id or child_id or transformation_id)",
    "role": "string (e.g. 'source', 'old', 'left_hand_side')"
  },
  "expression_b": {
    "sha256": "string",
    "provenance_ref": "string",
    "role": "string (e.g. 'candidate', 'new', 'right_hand_side')"
  },
  "claimed_relation": "string",
  "verified_relation": "literal_equality | finite_role_preserving_rename | role_labelled_analogy | structural_compatibility | pointwise_identity | projected_identity | identity_under_assumptions | integrated_identity | numerical_regression_only | not_established | contradicted | forbidden_claim",
  "verification_methods_applied": [
    {
      "method": "literal_sameq | exact_held_comparison | exact_subtraction_under_assumptions | finite_index_replay | parent_child_reconstruction | random_exact_substitution | high_precision_numerical_sampling | counterexample_search | projection_regression | scope_assumption_audit",
      "result": "PASS | FAIL | INCONCLUSIVE",
      "confidence": 0.0 - 1.0,
      "detail": "string"
    }
  ],
  "assumptions_used": [
    {
      "assumption_id": "string",
      "assumption_text": "string",
      "source": "human | adapter | raw_object | derived",
      "verified": true | false
    }
  ],
  "scope": {
    "domain": "string",
    "restrictions": ["string"],
    "verified_within_scope": true | false
  },
  "counterexamples_found": [
    {
      "counterexample_id": "string",
      "parameter_assignment": {},
      "index_assignment": {},
      "discrepancy": "string",
      "discrepancy_magnitude": "string",
      "is_valid": true | false
    }
  ],
  "numerical_agreement_only": true | false,
  "symbolic_equality_claimed": true | false,
  "caveats": ["string"],
  "status": "string (see text below)",
  "verification_role": "VERIFIER",
  "executor_role": "string (identity of the executor agent/process)",
  "role_separation_confirmed": true | false,
  "verification_timestamp": "string (ISO 8601)",
  "verification_agent": "string"
}
```

### 2. verification_report.md (always produced)
Human-readable Markdown report summarizing:
- The two expressions being compared (with identity references).
- The claimed relation.
- Every verification method applied and its result.
- All assumptions used and their sources.
- The verified relation and why it was assigned that category.
- All caveats and limitations.
- Explicit statement about whether numerical agreement was used as supporting evidence only (not proof).
- Counterexamples found (if any).

### 3. numerical_evidence.json (conditional)
Produced if numerical sampling was used as supporting evidence:
```json
{
  "verification_id": "string",
  "sampling_method": "string",
  "number_of_samples": "integer",
  "sample_strategy": "random_uniform | grid | adaptive | monte_carlo",
  "precision": "string (e.g. 'double', 'arbitrary_100_digits')",
  "results": {
    "max_absolute_difference": "string",
    "max_relative_difference": "string",
    "mean_absolute_difference": "string",
    "pass_count": "integer",
    "fail_count": "integer",
    "failures": [
      {
        "sample_id": "integer",
        "parameters": {},
        "difference": "string"
      }
    ]
  },
  "numerical_agreement_only": true | false,
  "symbolic_equality_claimed": true | false
}
```

### 4. subtraction_result.json (conditional)
Produced if exact subtraction was performed:
```json
{
  "verification_id": "string",
  "subtraction_expression": "A - B",
  "simplified_difference": "string",
  "difference_is_zero": true | false,
  "simplification_rules_applied": ["string"],
  "simplification_level": "A | B | C | D | E | F | G"
}
```

### 5. projection_regression.json (conditional)
Produced if projection regression was performed (for tensorial formulas):
```json
{
  "verification_id": "string",
  "projection_basis": "string (description of the projection basis)",
  "projection_dimension": "integer",
  "projection_results": [
    {
      "basis_element": "string",
      "a_projection": "string",
      "b_projection": "string",
      "difference": "string",
      "match": true | false
    }
  ],
  "all_projections_match": true | false
}
```

### 6. scope_assumption_audit.json (always produced)
Audit of whether the verification actually covered the declared scope:
```json
{
  "verification_id": "string",
  "declared_scope": "string",
  "verified_scope": "string",
  "scope_gaps": ["string (parts of scope not tested)"],
  "assumption_audit": [
    {
      "assumption_id": "string",
      "used_in_verification": true | false,
      "necessity_confirmed": true | false,
      "untested_if_removed": true | false
    }
  ]
}
```

## Relation Types (verified_relation values)

### 1. literal_equality
Expression A and Expression B are literally (syntactically) identical after normalization. Every symbol, index, coefficient, and structure matches exactly.
- **Method**: `literal_sameq` or `exact_held_comparison`.
- **Confidence**: Very high (limited only by the correctness of the comparison engine).

### 2. finite_role_preserving_rename
Expression A and Expression B are identical up to a finite, recorded renaming of free symbols or indices that preserves all roles (e.g., `F_{ab}` in A renamed to `G_{ab}` in B). The renaming map must be explicitly provided.
- **Method**: `exact_held_comparison` with renaming map.
- **Confidence**: Very high.

### 3. role_labelled_analogy
Expression A and Expression B have the same algebraic structure (same operators, same index topology, same term structure) but differ in the specific symbols. The structural isomorphism is labeled with role-to-role mappings.
- **Method**: Structural comparison with role mapping.
- **Confidence**: High for structural claims; does NOT imply mathematical equality.

### 4. structural_compatibility
Expression A and Expression B are structurally compatible — they have the same free index structure, same operator head, same term count, but may differ in coefficients or internal structure. This is a weak claim used for sanity checks.
- **Method**: Structure comparison (head, arity, free index topology).
- **Confidence**: Low as a mathematical claim; useful as a precondition check.

### 5. pointwise_identity
Expression A and Expression B are mathematically identical for all values of free parameters and indices within the declared domain. This is the "full equality" claim.
- **Methods**: `exact_subtraction_under_assumptions`, verified by `literal_sameq` after simplification.
- **Confidence**: High when supported by exact symbolic subtraction; lower when supported only by numerical sampling.

### 6. projected_identity
Expression A and Expression B are identical when projected onto a specific basis (e.g., contracting with basis tensors, evaluating for specific index values). The identity holds only for the projections tested, not necessarily for all values.
- **Methods**: `projection_regression`, `finite_index_replay`.
- **Confidence**: Limited to the tested projections. Claims beyond the tested projections require additional verification.

### 7. identity_under_assumptions
Expression A and Expression B are identical ONLY under the declared assumptions. If any assumption is removed, the identity may fail.
- **Methods**: `exact_subtraction_under_assumptions`, verified by simplification that uses the assumptions.
- **Confidence**: Conditional on the correctness of the assumptions. If assumptions are later found to be incorrect, the identity may be invalidated.

### 8. integrated_identity
Expression A and Expression B are identical after integration over a specified domain. This includes identities that hold only up to total derivatives (after IBP) or only after summing over dummy indices.
- **Methods**: Integration and comparison, IBP verification, boundary term accounting.
- **Confidence**: Dependent on boundary condition verification and integration domain definitions.

### 9. numerical_regression_only
The only evidence for the relationship is numerical agreement. No symbolic proof has been established. This is the WEAKEST positive claim.
- **Methods**: `high_precision_numerical_sampling`.
- **Confidence**: Supporting only — this MUST NOT be confused with proof. The numerical agreement suggests but does not establish the identity.

### 10. not_established
None of the verification methods could establish the claimed relationship, but no counterexample was found either. The claim remains unproven.
- **Methods**: All methods were attempted and were inconclusive.
- **Confidence**: Zero — no positive or negative conclusion.

### 11. contradicted
A valid counterexample was found that violates the claimed relationship within the declared scope and under the declared assumptions.
- **Methods**: `counterexample_search` found a parameter assignment where the relationship fails.
- **Confidence**: Very high for the specific counterexample — the claim is FALSE. However, the counterexample must be validated to ensure it is within the declared scope.

### 12. forbidden_claim
The claimed relationship is of a type that is FORBIDDEN by the repo rules or adapter constraints. For example, claiming `literal_equality` between two expressions where one has been transformed at Level G and the other is raw.
- **Methods**: `scope_assumption_audit` detects a rule violation.
- **Confidence**: N/A — the claim is not evaluated because it should not exist.

## Verification Methods

### literal_sameq
Byte-for-byte or held-expression comparison of the two expressions after normalization. Returns PASS if identical, FAIL otherwise. This is the strongest verification method.

### exact_held_comparison
Comparison of held (unevaluated) forms, potentially with renaming maps. Returns PASS if the held forms are structurally identical, FAIL otherwise.

### exact_subtraction_under_assumptions
Compute `A - B`, then simplify using permitted rules (at the verified level) and the declared assumptions. If the result simplifies to exactly 0, the expressions are identical under those assumptions.

### finite_index_replay
For tensorial expressions: enumerate all valid index value assignments (within the declared range) and compare the evaluated expressions for each assignment. Returns PASS if all assignments match, FAIL if any mismatch.

### parent_child_reconstruction
Verify that a parent expression can be reconstructed from its children. This is the acceptance gate of `generic_expression_normalization_and_decomposition`, but should be independently verified by a different agent.

### random_exact_substitution
Substitute random exact (rational) values for free parameters and compare the resulting expressions numerically. Useful for detecting errors when full symbolic comparison is computationally prohibitive.

### high_precision_numerical_sampling
Evaluate both expressions at many random points using high-precision arithmetic. Returns statistical evidence of agreement or disagreement. **MUST NOT be used as proof of symbolic equality** — it is supporting evidence only.

### counterexample_search
Systematically search for parameter/index assignments where the expressions differ. This can disprove but not prove an identity. Methods include: grid search, random sampling with adaptive refinement, symbolic condition solving.

### projection_regression
For tensorial formulas: contract both expressions with a complete basis of projection tensors and compare the scalar results. This is a protected regression check — it verifies the identity in the "most dangerous" directions.

### scope_assumption_audit
Not a mathematical verification but a meta-verification: check whether the declared scope and assumptions were actually tested, and whether any gaps exist.

## Allowed Operations
- Compare two expressions using any of the listed verification methods.
- Apply simplifications to `A - B` at the verification level (which should match or be below the transformation level used to produce B).
- Record all verification methods applied, their results, and their confidence.
- Categorize the relationship into one of the 12 relation types.
- Flag when numerical agreement is the only evidence.
- Search for counterexamples and report them.
- Audit scope and assumptions for coverage gaps.
- Require Executor-Verifier role separation.
- Escalate when the claimed relationship cannot be established.

## Forbidden Operations
- **Claiming symbolic equality based on numerical agreement alone** — if `numerical_agreement_only` is `true`, `symbolic_equality_claimed` MUST be `false`.
- **Verifying a claim produced by the same agent** (Executor-Verifier separation violation).
- **Suppressing counterexamples** — all found counterexamples must be reported.
- **Expanding the scope of a claim** — if the verification covered only part of the declared scope, this must be reported as a scope gap.
- **Accepting a claim that relies on unverified assumptions** — all assumptions must be sourced and verified (or at least acknowledged as unverified).
- **Upgrading a relation type**: projected_identity must not be reported as pointwise_identity; numerical_regression_only must not be reported as identity_under_assumptions.
- **Applying transformations or simplifications beyond the authorized level during verification** — the verifier must not apply higher-level rules than the executor was authorized to use.
- **Labelling the result as CANONICAL** — verification produces a claim_relation, not canonical status.

## Semantic Blockers
The following conditions MUST block verification and require escalation:
1. **Missing assumptions**: The claimed relationship requires assumptions that have not been declared.
2. **Missing scope**: The domain over which the claim is supposed to hold is not specified.
3. **Executor-Verifier role conflict**: The verification agent is the same as the executor agent.
4. **Insufficient provenance**: One or both expressions lack complete lineage tracking.
5. **Unverifiable claim type**: The human claims a relationship that cannot be tested by any available method (e.g., "this is true for all D" when D is unbounded and no symbolic method exists).
6. **Computationally prohibitive**: Verification would require resources beyond the configured limits (time, memory, or precision).
7. **Assumption contradiction**: The declared assumptions contradict each other or contradict known facts about the expressions.
8. **Scope not testable**: The declared scope cannot be covered by available verification methods (e.g., continuous infinite domain with no symbolic method).

## Task Lifecycle
1. **RECEIVE**: Accept the two expressions, the claimed relation, assumptions, and scope.
2. **VALIDATE_ROLE**: Confirm that the Verifier is NOT the Executor. If role separation fails, halt and escalate.
3. **LOAD_EXPRESSIONS**: Load both expressions from their provenance references.
4. **LOAD_ASSUMPTIONS**: Load and validate all declared assumptions.
5. **AUDIT_SCOPE**: Determine whether the declared scope can be covered.
6. **SELECT_METHODS**: Choose appropriate verification methods based on the claimed relation type and available resources.
7. **APPLY_METHODS**: Apply each selected method. Record results.
8. **SEARCH_COUNTEREXAMPLES**: If applicable, search for counterexamples.
9. **DETERMINE_RELATION**: Based on all results, determine the `verified_relation`.
10. **CHECK_NUMERICAL_ONLY**: If only numerical methods passed, set `numerical_agreement_only: true` and `symbolic_equality_claimed: false`.
11. **WRITE**: Produce all output artifacts.
12. **LOG**: Append to the repo-level verification registry.

## Numerical Agreement Caveat
This is a CRITICAL rule of this skill:

**Numerical agreement MUST NOT become symbolic equality.**

Specifically:
- If the only evidence for a relationship is `high_precision_numerical_sampling` or `random_exact_substitution`, then `numerical_agreement_only` MUST be `true`.
- If `numerical_agreement_only` is `true`, then `symbolic_equality_claimed` MUST be `false`.
- If `symbolic_equality_claimed` is `false`, the `verified_relation` MUST be `numerical_regression_only` (or lower).
- Numerical evidence may be PRESENT alongside symbolic evidence, in which case it is supporting and `numerical_agreement_only` is `false`.
- If numerical evidence DISAGREES with symbolic evidence, the disagreement must be investigated and reported. The symbolic claim is NOT automatically invalidated (the numerical evaluation may have numerical instability), but the discrepancy must be flagged.

## Executor-Verifier Role Separation
This is a HARD requirement:

- The Executor (the agent that produced Expression B via transformation) MUST NOT also act as the Verifier.
- The Verifier MUST be a different agent, process, or (at minimum) a different invocation with explicit role separation recorded.
- `role_separation_confirmed` in `claim_relation.json` MUST be `true` for the verification to be valid.
- If role separation cannot be confirmed (e.g., in a single-agent system), this must be flagged as a caveat and the claim's confidence must be reduced.
- The Verifier may re-run the Executor's transformation as part of verification (reproducibility check), but must independently verify the result.

## Relation / Claim Types
This skill categorizes the relationship into exactly one of the 12 `verified_relation` values. It does NOT produce canonical status, provenance claims, or transformation artifacts.

## Artifact Contract
- `claim_relation.json` MUST contain exactly one `verified_relation` value from the 12 defined types.
- If `numerical_agreement_only` is `true`, `verified_relation` MUST be `numerical_regression_only` or `not_established` or `contradicted`.
- If `symbolic_equality_claimed` is `true`, `verified_relation` MUST be one of: `literal_equality`, `pointwise_identity`, `identity_under_assumptions`, or `integrated_identity`.
- `role_separation_confirmed` MUST be present and ideally `true`.
- `scope_assumption_audit.json` MUST be produced for every verification.
- All counterexamples in `counterexamples_found` MUST include the parameter/index assignment and the discrepancy.
- All timestamps MUST be ISO 8601 UTC.

## Downstream Eligibility
A verified claim is eligible for integration and canonical promotion ONLY if:
1. `claim_relation.json` exists.
2. `verified_relation` is one of: `literal_equality`, `pointwise_identity`, `identity_under_assumptions`, or `integrated_identity`.
3. `symbolic_equality_claimed` is `true`.
4. `numerical_agreement_only` is `false`.
5. `role_separation_confirmed` is `true`.
6. No valid counterexamples exist.
7. No scope gaps exist that would invalidate the claim in the declared domain.

A claim that does not meet these criteria may still be useful (e.g., `numerical_regression_only` for sanity checks), but it cannot be promoted to canonical.

## Human Escalation Behavior
- Missing assumptions are escalated via `human_scientist_semantic_escalation`.
- Missing scope is escalated.
- A `contradicted` result is presented to the human with the counterexample details. The human may: accept the contradiction (the claim is false), argue that the counterexample is invalid (out of scope, misapplied assumptions), or revise the claim.
- A `not_established` result is presented with: which methods were tried, why they failed, what additional information would enable verification.
- Role separation failures are escalated — the human must provide a separate verifier or explicitly authorize single-agent verification with reduced confidence.
- If numerical evidence disagrees with symbolic evidence, the human is presented with both and asked to resolve the discrepancy.

## Interaction with Other Skills
- **Receives from**: `scientific_symbolic_repo_entry` (routing decision), `candidate_symbolic_transformation` (Expression B), `generic_expression_normalization_and_decomposition` (Expression A or B), `generic_raw_expression_ingestion` (original source for regression).
- **Escalates to**: `human_scientist_semantic_escalation` (missing assumptions, counterexample resolution, role separation failure).
- **Feeds into**: `provenance_claim_and_canonical_state` (verified claims are the input to the integration lifecycle).
- **Referenced by**: `verified_provenance_to_latex_pdf` (verification results appear in `verification_summary.tex`).

## Error Handling
- **Expression not found**: Halt — the provenance reference cannot be resolved.
- **Assumption file not found**: Halt — escalate for the missing assumption definition.
- **Verification method fails**: Record the method as `INCONCLUSIVE` with the error detail. Try alternative methods.
- **All methods inconclusive**: Set `verified_relation: not_established`. This is a valid outcome.
- **Verification timeout**: Record partial results, set `verified_relation: not_established` with caveat `VERIFICATION_TIMEOUT`.
- **Memory exceeded**: Record partial results, escalate to human with size estimates and ask whether to continue with reduced precision/methods.
