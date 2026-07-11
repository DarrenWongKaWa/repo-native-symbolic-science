# Candidate Symbolic Transformation

## Purpose
Generate symbolic transformation candidates at an **explicitly authorized transformation level** without claiming verification. Every transformation must be traceable to a specific rule, every rule must be assigned a level (A–G), and the output must be labelled `CANDIDATE_TRANSFORMED` — never `VERIFIED`, never `CANONICAL`. This skill applies transformations; it does not verify them.

## Activation Conditions
This skill MUST be activated when:
- The routing skill emits `routing_target: "candidate_symbolic_transformation"` with `task_class: "transformation"` and `sub_class` matching `candidate_A` through `candidate_G` or `candidate_unspecified`.
- A human explicitly requests a transformation at a named level (e.g., "apply level B transformations" or "simplify using algebraic identities").
- A downstream task (e.g., integration) requires a transformed expression as input.
- The adapter or raw object's `allowed_transformations` authorizes a specific transformation level.

This skill MUST NOT be activated for:
- Expressions already labelled `VERIFIED` or `CANONICAL` (transformations of verified expressions require explicit re-transformation authorization).
- Expressions where the requested transformation level exceeds what is authorized by `allowed_transformations`.
- Verification of a transformation (that belongs to `exact_and_bounded_symbolic_verification`).

## Required Inputs
1. **Source expression** (mandatory): A normalized child expression (from `child_expressions.json`) or parent expression (from `normalized_parent.json`) that is the target of the transformation.
2. **Routing decision** (mandatory): The `routing_decision.json` that authorized this transformation, explicitly stating the authorized transformation level.
3. **Transformation constraints** (mandatory): From the raw object's `transformation_constraints`:
   - `allowed_transformations`: Which levels (A–G) or specific rules are permitted.
   - `forbidden_transformations`: Which levels or rules are forbidden.
   - `regression_targets`: Expressions that must be preserved or satisfied by the transformation.
4. **Adapter configuration** (optional): Additional transformation rules, identities, or conventions provided by the adapter.
5. **Semantic definitions** (mandatory for levels C–G): Definitions of symbols, operators, and operators provided by the human or adapter. Without these, levels C–G cannot be applied.
6. **Prior transformation record** (optional): If this is an incremental transformation, the prior state to build upon.

## Required Output Directory
```
skills/candidate_symbolic_transformation/output/{transformation_id}/
```
Where `{transformation_id}` is a deterministic identifier based on source expression SHA + transformation level + rules applied.

## Required Output Artifacts

### 1. candidate_transformation.json (always produced)
```json
{
  "transformation_id": "string",
  "source_expression_id": "string (child_id or parent_id of input)",
  "source_expression_sha256": "string",
  "transformation_level": "A | B | C | D | E | F | G",
  "authorized_level": "string (the level explicitly authorized by the routing decision)",
  "level_check": "PASS | FAIL (did authorized_level >= transformation_level?)",
  "transformed_expression": "string (canonical serialization)",
  "transformed_expression_sha256": "string",
  "status": "CANDIDATE_TRANSFORMED",
  "rules_applied": [
    {
      "rule_id": "string",
      "rule_name": "string",
      "rule_level": "A | B | C | D | E | F | G",
      "rule_description": "string",
      "rule_source": "builtin | adapter | human_defined",
      "rule_source_reference": "string (adapter name, human escalation ID, or builtin reference)",
      "applied_to_subexpression": "string (which part of source was transformed)",
      "input_subexpression_sha256": "string",
      "output_subexpression_sha256": "string",
      "reversible": true | false
    }
  ],
  "regression_check": {
    "targets_checked": ["string (target_ids)"],
    "all_preserved": true | false,
    "violations": [
      {
        "target_id": "string",
        "violation_description": "string"
      }
    ]
  },
  "transformation_timestamp": "string (ISO 8601)",
  "transformation_agent": "string"
}
```

### 2. rule_application_trace.json (always produced)
A detailed trace of every rule application:
```json
{
  "transformation_id": "string",
  "trace": [
    {
      "step": "integer",
      "rule_id": "string",
      "before_expression_sha256": "string",
      "after_expression_sha256": "string",
      "match_location": "string (AST path)", 
      "substitution_detail": "string",
      "side_conditions_checked": ["string"],
      "side_conditions_passed": true | false,
      "warnings": ["string"]
    }
  ]
}
```

### 3. level_boundary_audit.json (always produced)
Proof that no higher-level transformation was silently applied:
```json
{
  "transformation_id": "string",
  "authorized_level": "A | B | C | D | E | F | G",
  "maximum_applied_level": "A | B | C | D | E | F | G",
  "level_violation": true | false,
  "violating_rules": [
    {
      "rule_id": "string",
      "rule_level": "string (the violating level)",
      "authorized_level": "string"
    }
  ]
}
```

### 4. transformation_report.md (always produced)
Human-readable Markdown report summarizing:
- Source expression identity and SHA.
- Authorized level and actual maximum applied level.
- Every rule applied with its level, description, and source.
- Before/after term counts and structure metrics.
- Regression check results.
- Explicit statement: "This output is CANDIDATE_TRANSFORMED; it has NOT been verified."
- List of what verification steps are recommended.

### 5. transformation_regression_check.json (conditional)
Produced if regression targets were specified in the raw object. Detailed comparison of each regression target against the transformed expression.

## Transformation Levels

### Level A — Syntax-Preserving
Operations that change only the representation, not the mathematical value:
- Renaming free symbols (with recorded mapping).
- Renaming dummy indices (with collision detection).
- Reordering commutative terms or factors.
- Changing notation (e.g., partial derivatives ∂_a → D_a notation with recorded mapping).
- Converting between equivalent serialization formats.
- **Constraint**: The mathematical object is unchanged; only its syntactic representation changes.

### Level B — Exact Algebraic
Operations that are mathematically exact identities on the algebraic structure:
- Arithmetic simplification (e.g., `2*x + 3*x` → `5*x`, `a*(b + c)` → `a*b + a*c`).
- Rational function normalization.
- Polynomial expansion, factorization (exact, not approximate).
- Commutator/anticommutator algebra with known commutation relations.
- Index symmetrization/antisymmetrization with declared symmetry properties.
- **Constraint**: The identity is provable within the algebraic theory of the expression, using only the declared algebraic properties of the operators.

### Level C — Scientific-Definition Identities
Operations that use the scientific definitions of symbols:
- Substituting the definition of a symbol (e.g., `F_{ab} = ∂_a A_b - ∂_b A_a`).
- Applying the definition of a physical constant in terms of fundamental constants.
- Expanding a defined composite operator into its constituents.
- **Constraint**: The definition must be explicitly provided by the human or adapter. The definition is used only in the forward direction (definition → expansion), never reversed unless explicitly authorized.
- **Blocker**: This level CANNOT be applied without semantic definitions from the human.

### Level D — Differential / Product-Rule Identities
Operations that use differential calculus identities:
- Leibniz/product rule: `∂_a(f * g) = (∂_a f) * g + f * (∂_a g)`.
- Chain rule for composed functions.
- Commutation of partial derivatives: `∂_a ∂_b = ∂_b ∂_a` (requires smoothness assumption).
- Covariant derivative expansions (requires connection definition).
- Lie derivative identities.
- **Constraint**: Requires smoothness/differentiability assumptions to be declared.

### Level E — Integration / IBP Identities
Operations that use integration or integration-by-parts:
- Integration by parts: `∫ f * ∂g = boundary - ∫ ∂f * g`.
- Discarding total derivative terms in integrals (requires boundary conditions).
- Changing integration variables (requires Jacobian).
- **Constraint**: Requires boundary conditions or compact support assumptions to be declared. All discarded boundary terms must be explicitly listed.

### Level F — Integrated Cancellation
Operations that cancel terms after integration:
- Cancelling pairs of terms that are shown to be equal after integration.
- Summing integrated sub-expressions and simplifying.
- Combining integration results from different sectors.
- **Constraint**: Requires Level E to have been applied first and verified. Cancellation must be exact (not approximate).

### Level G — Closure / Canonicalization
Operations that produce a closed-form result:
- Recognizing pattern matches against known integral formulas or special functions.
- Applying closure relations (e.g., completeness of basis functions).
- Summing infinite series to closed form.
- Reducing the expression to a "simplest" form according to the adapter's canonicalization rules.
- **Constraint**: This is the highest level. Applying Level G without having applied and verified lower levels is a level violation.

## Allowed Operations
- Apply any rule at or below the **explicitly authorized** transformation level.
- Record every rule applied with its level, source, and effect.
- Check that no rule exceeds the authorized level.
- Apply rules from the adapter if the adapter's rules are at the authorized level or below.
- Apply rules from human-provided semantic definitions.
- Check regression targets: verify that the transformation does not violate known regression identities.
- Label output as `CANDIDATE_TRANSFORMED`.
- Request human input for missing semantic definitions (via escalation).
- Produce detailed trace of every rule application.

## Forbidden Operations
- **Applying a rule at a level HIGHER than the explicitly authorized level** — even if it would produce a correct simplification.
- **Silent level escalation**: Level A authorization must not silently permit Level B operations.
- **Labelling output as VERIFIED or CANONICAL** — the output is `CANDIDATE_TRANSFORMED` only.
- **Applying rules from the adapter if the adapter's rules exceed the authorized level** — the rule must be skipped, not downgraded.
- **Applying definitions in reverse** (e.g., recognizing a pattern as a definition and collapsing it) unless the reverse direction is separately authorized.
- **Discarding boundary terms in IBP without explicitly listing them** — all discarded surface/boundary terms must be itemized.
- **Applying integration cancellation (Level F) without prior Level E completion and verification.**
- **Applying closure patterns (Level G) without lower-level verification.**
- **Modifying the source expression in place** — always produce a new transformation artifact.
- **Claiming that the transformation is correct** — correctness is the domain of `exact_and_bounded_symbolic_verification`.

## Semantic Blockers
The following conditions MUST block transformation and require escalation:
1. **Insufficient authorization**: The routing decision's `authorized_level` is below the minimum level needed for any meaningful transformation, and the human has not specified a higher level.
2. **Missing semantic definitions** (Levels C and above): A rule requires a definition that has not been provided by the human or adapter.
3. **Missing boundary conditions** (Level E and above): IBP requires boundary/surface terms to be specified.
4. **Missing smoothness assumptions** (Level D and above): Differential identities require declared differentiability.
5. **Missing commutation relations** (Level B and above, for noncommutative operators): Algebraic transformations on noncommutative objects require commutation relation definitions.
6. **Regression target violation**: A rule would produce a transformation that violates a known regression target, and no alternative rule at the same level avoids the violation.
7. **Irreversible rule without authorization**: A rule is marked `reversible: false` and the human has not explicitly authorized an irreversible step.
8. **Circular transformation**: The rule would produce an expression identical to a prior state in the transformation chain (infinite loop detection).

## Task Lifecycle
1. **RECEIVE**: Accept the source expression and routing decision.
2. **EXTRACT_AUTHORIZATION**: Parse the routing decision to determine the `authorized_level`.
3. **LOAD_RULES**: Load all available rules at or below the authorized level (builtin + adapter + human-defined).
4. **LOAD_DEFINITIONS**: Load all semantic definitions required by the loaded rules. Escalate if any are missing.
5. **LOAD_ASSUMPTIONS**: Load all assumptions (smoothness, boundary conditions, commutation relations) required by the loaded rules. Escalate if any are missing.
6. **VALIDATE_LEVEL**: Confirm that `authorized_level` is at least the minimum needed for an applicable rule. If not, escalate.
7. **MATCH_RULES**: For each applicable rule, attempt to match it against sub-expressions of the source. Record matches.
8. **SELECT_RULES**: Select which matched rules to apply. Strategy may be: apply all, apply greedily for simplification, or ask human to choose.
9. **APPLY_RULES**: Apply each selected rule in sequence, recording the before/after state, the matched location, side conditions, and warnings.
10. **CHECK_LEVEL_BOUNDARY**: After all rules are applied, verify that no rule at a level higher than `authorized_level` was applied.
11. **CHECK_REGRESSION**: Compare the transformed expression against all regression targets.
12. **DECIDE**: If level boundary is violated → HALT and record the violation. If regression targets are violated → HALT and escalate. If all checks pass → produce output.
13. **LABEL**: Set `status: "CANDIDATE_TRANSFORMED"` for all output.
14. **WRITE**: Produce all output artifacts.
15. **LOG**: Append to the repo-level transformation registry.

## Relation / Claim Types
This skill produces exactly ONE type of claim:
- `CANDIDATE_TRANSFORMED`: An expression has been transformed by applying rules at level X, and the transformation has been recorded with full traceability. The transformation has NOT been verified.

This skill does NOT produce:
- `VERIFIED` (that requires `exact_and_bounded_symbolic_verification`).
- `CANONICAL` (that requires `provenance_claim_and_canonical_state` with verification + human gate + integration).
- `NORMALIZED_PARENT` (that requires `generic_expression_normalization_and_decomposition`).
- `RAW_INGESTED` (that requires `generic_raw_expression_ingestion`).

## Artifact Contract
- `candidate_transformation.json` MUST have `status: "CANDIDATE_TRANSFORMED"`.
- `level_boundary_audit.json` MUST have `level_violation: false` for the output to be valid.
- `candidate_transformation.json` MUST have `level_check: "PASS"`.
- Every rule in `rules_applied` MUST have all required fields.
- `rule_application_trace.json` MUST contain a trace entry for every rule application, with SHA-256 before and after.
- `transformation_report.md` MUST contain the explicit statement: "This output is CANDIDATE_TRANSFORMED; it has NOT been verified."
- All timestamps MUST be ISO 8601 UTC.

## Downstream Eligibility
A transformed expression is eligible for verification ONLY if:
1. `candidate_transformation.json` exists with `status: "CANDIDATE_TRANSFORMED"`.
2. `level_boundary_audit.json` shows `level_violation: false`.
3. `regression_check.all_preserved` is `true` (or violations have been waived by the human).
4. The `authorized_level` is correctly recorded and matches the routing decision.
5. The transformation has not been superseded by a later transformation of the same source.

## Human Escalation Behavior
- Missing semantic definitions (Level C+) are escalated via `human_scientist_semantic_escalation`.
- Missing boundary conditions (Level E+) are escalated.
- Missing smoothness assumptions (Level D+) are escalated.
- When a transformation would violate a regression target, the human is presented with: the specific rule that causes the violation, the regression target that is violated, the alternative rules at the same level (if any), and the option to waive the regression target or choose a different rule.
- If the human authorizes a transformation at a higher level than previously specified, the routing decision must be updated (by re-routing through `scientific_symbolic_repo_entry`) before the higher-level rules are applied.
- If the human authorizes an irreversible rule, the authorization is recorded as a `HUMAN_AUTHORIZED_IRREVERSIBLE` event with the specific rule and rationale.

## Interaction with Other Skills
- **Receives from**: `scientific_symbolic_repo_entry` (routing decision), `generic_expression_normalization_and_decomposition` (normalized children/parent as source).
- **Escalates to**: `human_scientist_semantic_escalation` (missing definitions, assumptions, regression violations).
- **Feeds into**: `exact_and_bounded_symbolic_verification` (the transformed expression is the subject of verification).
- **Feeds into**: `generic_expression_normalization_and_decomposition` (if the transformed expression needs re-normalization before verification).
- **Referenced by**: `provenance_claim_and_canonical_state` (transformations are steps in the derivation lineage).
- **Referenced by**: `verified_provenance_to_latex_pdf` (transformation rules appear in `transformation_registry.tex`).

## Error Handling
- **No rules match at authorized level**: Halt. Record `transformation_result: NO_MATCHING_RULES`. This is a valid outcome — not all expressions can be transformed at every level.
- **Level boundary violation**: Halt. Do not produce any output labelled as valid. Record the violation in `level_boundary_audit.json` with `level_violation: true` and escape.
- **Rule application error**: If a rule cannot be applied (e.g., pattern mismatch due to structural assumptions), skip that rule and continue with others. Record the skip in `rule_application_trace.json` as a warning.
- **Regression check failure**: Halt. Record the violation. Escalate to human if no alternative rules avoid the violation.
- **Infinite loop detected**: Halt. Record the cycle. This is a CRITICAL error — the rule selection logic is defective or the expression structure has a pathological property.
- **Transformation is identity**: Record the transformation (with zero rules applied), mark `status: CANDIDATE_TRANSFORMED` with `transformation_result: IDENTITY`. This is a valid outcome — the expression was already in the requested form.
