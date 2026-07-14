# Supplementary Material Build and Audit

## Purpose
Orchestrate assembly, configured validation, and audit of a theoretical-supplement package from supplied artifacts. This skill coordinates supplement skills, enforces the 14-section profile, runs the configured readability audit, and prepares a structured reporting handoff package. It does not independently derive or mathematically verify scientific content, generate a complete TeX supplement, or compile a PDF.

**TeX/PDF Authority**: Final LaTeX rendering and PDF compilation are the exclusive authority of `verified_provenance_to_latex_pdf`. This skill prepares a structured handoff package consumed by that authority. It does NOT perform standalone TeX compilation or final PDF production.

## Activation Conditions
This skill MUST be activated when:
- A `theoretical_supplement_request` is submitted and all prerequisite skills have completed their work.
- The routing skill emits `routing_target: "supplementary_material_build_and_audit"`.
- All derivation steps, evidence mappings, interpretations, and presentations are ready for assembly.
- A human scientist requests the final supplement build.
- A new version of the supplement needs to be produced after amendments.
- A checkpoint build needs to be rendered.

This skill MUST NOT be activated for:
- Creating derivation content (all derivation work must be complete).
- Performing verification (verification must be complete).
- Editing individual equations by hand (all content comes from upstream skills).
- Partial builds (this skill builds the complete supplement).

## Required Inputs
1. **Theoretical supplement request** (mandatory): Full `theoretical_supplement_request` conforming to `schemas/theoretical_supplement_request.schema.json`.
2. **Derivation graph** (mandatory): Validated `derivation_graph.json` from `verified_artifact_to_derivation_graph`.
3. **Section narratives** (mandatory): `section_narratives.json` from `theoretical_physics_derivation_narrative`.
4. **Expression presentations** (mandatory): All `expression_presentation.json` files from `long_expression_presentation_and_omission`.
5. **Omission ledgers** (conditional): All `omission_ledger.json` files for any abbreviated expressions.
6. **Physical interpretation mappings** (mandatory): All `physical_interpretation_mapping.json` files from `physical_interpretation_and_limiting_cases`.
7. **Equation evidence mappings** (mandatory): All `equation_evidence_mapping.json` files from `equation_level_claim_and_evidence_mapping`.
8. **Supplement claim registry** (mandatory): `supplement_claim_registry.json`.
9. **Reader pathway definitions** (mandatory): `reader_pathway.json`.
10. **Section contract** (mandatory): `supplement_section_contract.json`.
11. **Canonical registry** (mandatory): Current canonical status of all artifacts.

## Required Outputs

### 1. reporting_handoff_package.json (always produced)
A structured handoff package for consumption by `verified_provenance_to_latex_pdf`. This package contains all content needed for final TeX rendering and PDF compilation, but does NOT perform rendering itself.

```json
{
  "handoff_id": "string",
  "supplement_request_id": "string",
  "producer_authority": "SUPP",
  "rendering_authority": "verified_provenance_to_latex_pdf",
  "handoff_timestamp": "string (ISO 8601)",
  "section_contents": [...],
  "equation_registry": [...],
  "artifact_paths_and_shas": [...],
  "derivation_step_ids": [...],
  "assumptions": [...],
  "claim_scopes": [...],
  "omission_ledger_references": [...],
  "reader_pathways": [...],
  "output_format_requested": "LaTeX/PDF"
}
```

### 2. build_manifest.json (always produced)
```json
{
  "build_id": "string",
  "supplement_request_id": "string",
  "build_timestamp": "string (ISO 8601)",
  "input_artifacts": [...],
  "section_status": [...],
  "overall_complete": true,
  "missing_content": [...],
  "warnings": [...]
}
```

### 3. human_readability_audit.json (always produced)
A complete readability audit conforming to `schemas/human_readability_audit.schema.json` with all 13 check types evaluated.

### 5. build_integrity_report.json (always produced)
```json
{
  "integrity_checks": {
    "all_sections_populated": {"status": "PASS | FAIL", "empty_sections": []},
    "all_equations_appear": {"status": "PASS | FAIL", "missing_equations": []},
    "cross_references_resolve": {"status": "PASS | FAIL", "broken_refs": []},
    "figure_table_labels_consistent": {"status": "PASS | FAIL", "issues": []},
    "reader_pathways_covered": {"status": "PASS | FAIL", "gaps": []},
    "no_stale_references": {"status": "PASS | FAIL", "stale_refs": []},
    "canonical_statuses_current": {"status": "PASS | FAIL", "outdated": []},
    "evidence_map_complete": {"status": "PASS | FAIL", "missing": []},
    "omission_ledgers_valid": {"status": "PASS | FAIL", "invalid": []},
    "blocker_5_compliant": {"status": "PASS | FAIL", "issues": []}
  },
  "overall_integral": true,
  "blocking_issues": ["string"],
  "recommended_actions": ["string"]
}
```

### 6. reproduction_package.zip (conditional — when SEC_14 requires it)
A zip archive containing all scripts, data files, and instructions needed to reproduce the derivation computationally.

### 7. supplement_metadata.json (always produced)
```json
{
  "supplement_id": "string",
  "title": "string",
  "authors": ["string"],
  "date": "string",
  "version": "string",
  "derivation_branch": "string",
  "source_checkpoint_id": "string",
  "sha256_of_build": "string",
  "total_pages": "integer",
  "total_equations": "integer",
  "total_figures": "integer",
  "total_tables": "integer",
  "canonical_results_count": "integer",
  "verified_results_count": "integer"
}
```

## Gates

### Gate 1: Input Completeness
Before building:
- All required input artifacts must be present and valid.
- All upstream skill outputs must pass their own validation gates.
- No artifact with UNVERIFIED status may appear as a result without explicit caveats.

### Gate 2: Section Contract Compliance
- All 14 sections must be present.
- Each section must contain the content specified in its contract.
- Required equations for each section must appear.
- Reader pathway relevance annotations must be present.

### Gate 3: Cross-Reference Integrity
- Every `\ref{}` and `\eqref{}` must resolve to an existing label.
- Every equation label used must be from the INTERFACE CONTRACT.
- Every citation must have a corresponding bibliography entry.

### Gate 4: Readability Audit
- All 13 readability check types must be evaluated.
- No CRITICAL issues may remain unresolved.
- MAJOR issues must have documented justification if not fixed.
- Publication readiness must be assessed.

### Gate 5: Blocker_5 Compliance
- Blocker_5 must remain ACTIVE through the build process.
- No scientific sector may be prematurely closed.
- The build manifest must record Blocker_5 status.
- If Blocker_5 is lifted, the human decision record must be referenced.

### Gate 6: Handoff Package Completeness
- The reporting handoff package must contain all required sections, equations, evidence mappings, and reader pathways.
- All artifact paths and SHAs in the handoff must resolve.
- The handoff must identify `rendering_authority: "verified_provenance_to_latex_pdf"`.

### Gate 7: Reproduction Verification (conditional)
- If SEC_14_REPRODUCTION is required, the reproduction package must be tested.
- A clean environment must be able to execute the reproduction scripts.
- Output must match the supplement's results.

## Forbidden Operations
- **Building with missing content** — if a section is empty and no waiver exists, halt the build.
- **Hand-editing LaTeX output** — all LaTeX must be generated from upstream skill outputs.
- **Silently fixing compilation errors by editing equations** — if an equation causes a compilation error, the source must be fixed by the producing skill.
- **Publishing without readability audit** — the audit must pass before the supplement is considered ready.
- **Skipping sections** — all 14 sections must be present or have an explicit waiver.
- **Building from stale artifacts** — SHA-256 must be verified for every input artifact.
- **Claiming completeness without evidence map** — the evidence map must be present and complete.
- **Promoting canonical status** — this skill does not modify canonical status; it only reports it.

## Output Directory
```
skills/supplementary_material_build_and_audit/output/{build_id}/
```

## Build Process

### Phase 1: Pre-Build Validation
1. Validate all input artifacts against their schemas.
2. Verify SHA-256 of all input artifacts.
3. Check that all required artifacts are present.
4. Verify that all upstream skills completed successfully.
5. Check canonical status consistency across all inputs.

### Phase 2: Section Assembly
For each of the 14 sections, in order:
1. Retrieve the section narrative from `section_narratives.json`.
2. Retrieve all equations that belong to this section.
3. Retrieve expression presentations for any long expressions.
4. Retrieve physical interpretations for SEC_09.
5. Retrieve limiting case analyses for SEC_10.
6. Retrieve evidence mappings for SEC_12.
7. Generate LaTeX content for the section.
8. Populate cross-references to equations, figures, and tables.

### Phase 3: Reporting Handoff
1. Assemble the structured `reporting_handoff_package.json` with all section contents, equation registries, artifact SHAs, derivation step IDs, assumptions, claim scopes, omission ledger references, and reader pathways.
2. Validate that all handoff entries resolve against actual artifacts.
3. Delegate final TeX/PDF rendering to `verified_provenance_to_latex_pdf` by passing the handoff package as input.
4. This skill does NOT perform standalone LaTeX compilation or PDF production.
3. Run bibliography processing.
4. Run LaTeX again for cross-reference resolution.
5. Check for compilation warnings and errors.
6. If compilation fails, diagnose and report — do not silently fix.

### Phase 4: Readability Audit
1. Run all 13 readability checks against the compiled PDF.
2. Generate the `human_readability_audit.json`.
3. If CRITICAL issues found, do not proceed to finalization.
4. Report recommendations to the human.

### Phase 5: Integrity Verification
1. Run all 10 integrity checks.
2. Verify cross-references resolve.
3. Verify all equations from the INTERFACE CONTRACT appear.
4. Verify reader pathways are supported.
5. Check for stale or broken references.

### Phase 6: Finalization
1. Generate `build_manifest.json`.
2. Generate `supplement_metadata.json`.
3. If required, create the `reproduction_package.zip`.
4. Record the build SHA-256.
5. Mark the build as complete (but NOT canonical — that requires the lifecycle pipeline).

## Section Content Sources

| Section | Primary Content Source |
|---------|----------------------|
| SEC_01_SCOPE | supplement_request.scientific_scope + section_narratives |
| SEC_02_CONVENTIONS | derivation_steps with derivation_category: definition |
| SEC_03_STARTING_RESPONSE | section_narratives + derivation_graph root node |
| SEC_04_DECOMPOSITION | section_narratives + decomposition nodes from derivation_graph |
| SEC_05_SECTORS | section_narratives + equation_evidence_mapping for sector equations |
| SEC_06_IDENTITIES | section_narratives + identity nodes from derivation_graph |
| SEC_07_IBP | section_narratives + integration_by_parts derivation steps |
| SEC_08_FINAL_RESULT | section_narratives + derivation_graph leaf nodes |
| SEC_09_INTERPRETATION | physical_interpretation_mapping + section_narratives |
| SEC_10_LIMITS | limiting_cases_report + section_narratives |
| SEC_11_VALIDATION | equation_evidence_mapping + verification results |
| SEC_12_EVIDENCE_MAP | evidence_matrix.json + section_narratives |
| SEC_13_ELECTRONIC_APPENDIX | expression_presentation + omission_ledgers |
| SEC_14_REPRODUCTION | derivation_steps with computational_literal + reproduction scripts |

## Readability Audit Checks (13)
1. **equation_numbering_consistency**: Are equation numbers sequential and non-conflicting?
2. **cross_reference_validity**: Do all `\ref` and `\eqref` resolve?
3. **notation_defined_before_use**: Is every symbol defined before first use?
4. **index_convention_clarity**: Are summation conventions and index domains clear?
5. **term_grouping_readability**: Are long expressions presented readably?
6. **abbreviation_expansion_present**: Are all abbreviations expanded on first use?
7. **figure_table_label_consistency**: Do figures and tables have consistent, sequential labels?
8. **derivation_step_narrative_flow**: Does the narrative flow logically?
9. **physical_interpretation_accessibility**: Can a physicist understand the physical meaning?
10. **limiting_case_explicitness**: Are limiting cases clearly documented?
11. **mathematical_omission_transparency**: Are all omissions documented with reconstruction rules?
12. **reproduction_instruction_completeness**: Can the derivation be reproduced?
13. **reader_pathway_signposting**: Are pathway annotations present and helpful?

## Interaction with Other Skills
- **Receives from**: ALL other skills (as the top-level integration skill).
- **Feeds into**: `provenance_claim_and_canonical_state` (for build lifecycle events), `verified_provenance_to_latex_pdf` (for final PDF production — if distinct).
- **Consumes**: ALL schemas.
- **Produces**: `reporting_handoff_package.json`, `build_manifest.json`, `human_readability_audit.json`, `build_integrity_report.json`.
- **Delegates TeX/PDF to**: `verified_provenance_to_latex_pdf` (authoritative renderer).

## Failure Behavior
- **DERIVATION_GAP**: If a required section's content is missing (e.g., no physical interpretations available for SEC_09), flag DERIVATION_GAP. The build may proceed with an empty or placeholder section, but the gap must be prominently documented.
- **Handoff failure**: If the reporting handoff package cannot be assembled because required content is missing, report DERIVATION_GAP and do not proceed.
- **Delegation failure**: If `verified_provenance_to_latex_pdf` cannot consume the handoff, report the contract mismatch and request human resolution. Do NOT attempt standalone TeX/PDF rendering.
- **SHA-256 mismatch**: If any input artifact's SHA-256 does not match its expected value, halt. Do not build from tampered or stale artifacts.
- **Canonical status conflict**: If two artifacts claim CANONICAL status for the same claim, halt and escalate.
- **Blocker_5 violation**: If any section would prematurely close a scientific sector, flag it and do not mark that sector as complete.
- **Missing artifact**: If a required artifact is missing entirely, halt and request it. Do not build with a gap unless the human has explicitly waived the requirement.

## Blocker_5 Status
**Blocker_5**: ACTIVE — prevents premature closure of scientific sectors. The build process must not finalize any scientific sector unless all required evidence, verification, and human gates for that sector have been passed. The build manifest must record the Blocker_5 status of each sector.

## Human Escalation Behavior
- **Build readiness**: Before finalizing, present the `build_integrity_report.json` and `human_readability_audit.json` to the human for approval.
- **Section waivers**: If a section cannot be populated, request an explicit human waiver. Document the waiver in the build manifest.
- **Publication decision**: The human makes the final decision on whether the supplement is ready for publication. This skill provides all evidence but does not decide.
- **Post-build amendments**: If the human requests changes after the build, route to the appropriate upstream skill (never hand-edit the supplement). Create a new build with the amended inputs.
