# Long Expression Presentation and Omission

## Purpose
Manage the presentation of long mathematical expressions that exceed typical readability thresholds. This skill selects appropriate presentation modes from 9 allowed formats, creates mathematical omission ledgers for abbreviated expressions, and ensures that all omissions are fully reconstructible.

## Activation Conditions
This skill MUST be activated when:
- An expression has `term_count > 10` and requires structured presentation.
- The `theoretical_physics_derivation_narrative` skill requests alternative presentation for readability.
- The `supplementary_material_build_and_audit` skill requires an electronic appendix.
- A derivation step produces a long expression that would read poorly inline.
- The human readability audit flags an expression as requiring better presentation.
- An omission ledger needs to be created or validated.

This skill MUST NOT be activated for:
- Short expressions with `term_count <= 10` (use standard inline LaTeX).
- Creating new mathematical expressions (only presenting existing ones).
- Verifying expression correctness (that belongs to `exact_and_bounded_symbolic_verification`).
- Generating physical interpretations (that belongs to `physical_interpretation_and_limiting_cases`).

## Required Inputs
1. **Target expressions** (mandatory): The long expressions to present, each with:
   - Equation label (from INTERFACE CONTRACT).
   - Full LaTeX source.
   - Complete term list with LaTeX snippets and physical origin annotations.
   - Term count and structural information.
2. **Expression presentation schema** (mandatory): `schemas/expression_presentation.schema.json`.
3. **Mathematical omission ledger schema** (mandatory): `schemas/mathematical_omission_ledger.schema.json`.
4. **Readability thresholds** (mandatory): Configuration specifying when each presentation mode should be applied.
5. **Section contract** (conditional): Required to know which section the expression will appear in.

## Required Outputs

### 1. expression_presentation.json (one per expression)
A presentation specification conforming to `schemas/expression_presentation.schema.json`, selecting one of the 9 presentation modes and populating all required conditional fields.

### 2. omission_ledger.json (conditional — when omission is used)
A mathematically precise ledger conforming to `schemas/mathematical_omission_ledger.schema.json` that records:
- The SHA-256 of the complete expression.
- Which terms are displayed and which are omitted.
- The exact reconstruction rule for recovering the complete expression.

### 3. presentation_recommendation_report.json (always produced)
```json
{
  "report_id": "string",
  "expressions_processed": [
    {
      "equation_label": "string",
      "term_count": "integer",
      "readability_score_before": "number",
      "selected_presentation_mode": "string",
      "readability_score_after": "number",
      "omission_used": "boolean",
      "reconstruction_verified": "boolean | null",
      "page_estimate": "integer",
      "rationale": "string"
    }
  ],
  "summary": {
    "total_expressions": "integer",
    "omission_ledgers_created": "integer",
    "modes_used": ["string"],
    "overall_readability_improvement": "number"
  }
}
```

### 4. reconstructed_expressions_validation.json (conditional — when omission is used)
Validation that the reconstruction rule actually reproduces the complete expression:
```json
{
  "omission_id": "string",
  "equation_label": "string",
  "reconstruction_tested": "boolean",
  "reconstruction_result": "PASS | FAIL",
  "reconstruction_residual": "string",
  "reconstruction_method": "string",
  "reconstruction_sha256": "string",
  "sha256_match": "boolean"
}
```

## Gates

### Gate 1: Term Count Threshold
- Expressions with `term_count <= 10`: use `compact_inline` or `expanded_display` mode.
- Expressions with `10 < term_count <= 30`: consider `term_by_term_numbered` or `grouped_by_physical_origin`.
- Expressions with `term_count > 30`: strongly consider `abbreviated_with_omission_ledger` or `computational_literal_for_reproduction`.

### Gate 2: Presentation Mode Selection
The selection algorithm considers:
- Total term count.
- Structural properties (index symmetries, repetitive patterns).
- Physical interpretability (can terms be grouped by physical origin?).
- Target section (inline narrative vs. appendix).
- Reader pathway requirements (physics-first vs. machine-reproduction).

### Gate 3: Omission Integrity
When terms are omitted:
- The complete expression must be available and SHA-256 hashed.
- The omission pattern must be explicitly stated.
- The reconstruction rule must be testable (when executed, reproduces the complete expression).
- Displayed terms must be identified by their term indices.

### Gate 4: Reconstruction Verification
- Every omission ledger must be tested: apply the reconstruction rule, compute SHA-256 of result, compare with `full_expression_sha256`.
- If reconstruction fails, the omission ledger is invalid and must be corrected.

### Gate 5: Readability Score
- Every presented expression must receive a `human_readability_score` (0-10).
- Score >= 7: No action needed.
- Score 4-6: Consider alternative presentation mode.
- Score < 4: Mandatory alternative presentation.

## Forbidden Operations
- **Omitting terms without a reconstruction rule** — every omission must be explicitly reconstructible.
- **Omitting structurally unique terms** — only terms that can be regenerated by a rule may be omitted.
- **Using "..." ellipsis without specification** — the pattern must be mathematically precise.
- **Omitting signs or coefficients** — all signs and coefficients must be preserved or reconstructible.
- **Presenting different terms to different reader personas** — the same expression must be used, just presented differently.
- **Truncation without ledger** — truncating an expression without creating a corresponding omission ledger entry.
- **Inconsistent term numbering** — term indices must be consistent between the presentation and the omission ledger.

## Output Directory
```
skills/long_expression_presentation_and_omission/output/{presentation_id}/
```

## The 9 Presentation Modes

### 1. compact_inline
- **When**: Expression fits on one line, `term_count <= 10`.
- **Format**: Single LaTeX equation, minimal line breaks.
- **Conditional fields**: None.

### 2. expanded_display
- **When**: Expression is multi-line but all terms displayed, `term_count <= 20`.
- **Format**: LaTeX `align` or `multline` environment, one term per line.
- **Conditional fields**: None.

### 3. term_by_term_numbered
- **When**: Moderate length, terms have clear individual identities, `10 < term_count <= 50`.
- **Format**: Each term on a separate line with a term number label.
- **Conditional fields**: `term_labels` (array, one per term).

### 4. grouped_by_physical_origin
- **When**: Terms naturally group by physical mechanism (e.g., intraband, interband, Fermi surface, Fermi sea).
- **Format**: Groups separated by brackets with group labels.
- **Conditional fields**: `physical_origin_groups` (array of group objects with `group_name`, `physical_origin`, `term_indices`).

### 5. index_structure_tree
- **When**: Expression has complex index structure best understood hierarchically.
- **Format**: Tree diagram showing how indices contract, with leaf nodes as scalar terms.
- **Conditional fields**: `index_tree` (hierarchical object).

### 6. tensor_component_table
- **When**: Expression is a tensor whose components are most informative.
- **Format**: Table with rows for index combinations, columns for contributions.
- **Conditional fields**: `component_table` (tabular structure).

### 7. diagrammatic_accompaniment
- **When**: Expression has natural diagrammatic representation (e.g., Feynman-like).
- **Format**: LaTeX with TikZ or similar diagram alongside the expression.
- **Conditional fields**: `diagram_reference` (path to diagram file).

### 8. abbreviated_with_omission_ledger
- **When**: Expression is too long for full display, `term_count > 30`, has repetitive structure.
- **Format**: Display representative terms with ellipsis or summation notation, plus an omission ledger entry.
- **Conditional fields**: `omission_ledger_ref` (reference to ledger entry).

### 9. computational_literal_for_reproduction
- **When**: Expression is extremely long and primarily useful for machine reproduction.
- **Format**: Copy-pasteable code block (Python/Mathematica/other) with the full expression.
- **Conditional fields**: `computational_code` (the literal code).

## Omission Pattern Selection

### first_k_displayed
Show the first K terms explicitly, then indicate the pattern for the rest.

### representative_sample
Show 1-2 terms from each symmetry class or physical group.

### structured_ellipsis
Use mathematically precise ellipsis notation (e.g., "terms for n=3,...,N follow the pattern...").

### typographic_grouping
Use bracket notation or other typography to indicate grouped repetition.

### block_diagram_replacement
Replace the expression with a diagram that captures its structure.

### index_range_notation
Use summation notation or index range notation to compress repetitive terms.

## Reconstruction Rule Types

### permutation_symmetry
Terms are generated by permuting indices according to a specified symmetry group.

### index_cyclic_extension
Terms follow a cyclic pattern in index values.

### tensor_symmetry_closure
Terms are the symmetry-completion of an explicitly displayed representative term.

### explicit_term_list
All omitted terms are listed in a machine-readable format (not displayed but available).

### generating_function_substitution
Terms are generated by expanding a specified generating function.

### computational_regeneration
Terms are produced by running specified computational code.

## Readability Scoring Rubric
Score 0-10 based on:
1. Can a physicist understand the expression's meaning in under 30 seconds? (0-3 points)
2. Can all index structures be traced unambiguously? (0-2 points)
3. Can the contribution of each physical mechanism be identified? (0-2 points)
4. Can the expression be typed into a computer algebra system without ambiguity? (0-2 points)
5. Is the expression self-contained (no external references needed to understand notation)? (0-1 point)

## Interaction with Other Skills
- **Receives from**: `theoretical_physics_derivation_narrative` (requests for better presentation), `supplementary_material_build_and_audit` (appendix requirements).
- **Feeds into**: `theoretical_physics_derivation_narrative` (improved presentation), `supplementary_material_build_and_audit` (appendix content).
- **Consumes**: `expression_presentation.schema.json`, `mathematical_omission_ledger.schema.json`.
- **Produces**: `expression_presentation.json`, `omission_ledger.json`, presentation reports.

## Failure Behavior
- **DERIVATION_GAP**: If a long expression is needed for a derivation step but the complete expression is not available, flag DERIVATION_GAP. The derivation cannot proceed without the full expression.
- **Reconstruction failure**: If the reconstruction rule does not reproduce the complete expression (SHA-256 mismatch), flag as CRITICAL. The omission ledger is invalid. Either fix the reconstruction rule or display the complete expression.
- **Unreadable expression**: If no presentation mode yields a `human_readability_score >= 4`, provide the best available presentation and flag it for human review with all attempted modes and their scores.
- **Missing physical origin**: If terms cannot be grouped by physical origin because origin information is missing, fall back to term_by_term_numbered and flag the gap.

## Blocker_5 Status
**Blocker_5**: ACTIVE — prevents premature closure of scientific sectors. An expression must not be considered "presented" if its presentation is unreadable or non-reconstructible.

## Human Escalation Behavior
- **Extremely long expressions**: If an expression has `term_count > 200`, present the recommended approach but flag for human review to confirm the presentation strategy.
- **Reconstruction rule too complex**: If the reconstruction rule is itself mathematically complex, flag for human review to ensure the rule is clearer than displaying all terms.
- **Presentation mode disagreement**: If different reader pathways would benefit from different presentation modes, present the conflict and let the human decide.
