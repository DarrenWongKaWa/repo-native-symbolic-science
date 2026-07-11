# Verified Provenance to LaTeX / PDF

## Purpose
Map eligible evidence (verified, integrated, or canonical artifacts) into **traceable TeX** and (with later-authorized compilation) **PDF outputs**. Every equation, table, and conclusion must map back to its source task, source artifact, SHA-256, verification record, claim type, assumptions, scope, human decision dependency, caveats, and canonical/candidate status. This skill does NOT promote artifacts to canonical status — it only presents them.

## Activation Conditions
This skill MUST be activated when:
- The routing skill emits `routing_target: "verified_provenance_to_latex_pdf"` with `task_class: "reporting"`.
- A human requests generation of LaTeX, PDF, or publication-ready output from the provenance tree.
- A checkpoint, branch, or canonical state needs to be rendered into human-readable form.
- A derivation DAG needs to be visualized as a TeX document.
- A paper section (abstract, results, appendix) needs to be generated with full traceability.

This skill MUST NOT be activated for:
- Artifacts that have not passed verification (CANDIDATE_TRANSFORMED without VERIFIED status).
- Expressions that have not been normalized or ingested.
- Generating output without explicit provenance mapping.
- Modifying symbolic artifacts (this skill is read-only with respect to the provenance tree).

## Required Inputs
1. **Checkpoint reference or artifact selection** (mandatory): Which checkpoint, branch, or set of artifacts to render. Must reference existing lifecycle events.
2. **Routing decision** (mandatory): The `routing_decision.json` that authorized this report generation.
3. **Output format specification** (mandatory): Whether to generate only TeX, or TeX + PDF (if compilation is authorized).
4. **Style specification** (optional): LaTeX document class, bibliography style, figure placement preferences.
5. **Audience specification** (optional): Whether the output is for internal audit, colleague review, or publication submission.
6. **Lifecycle state** (mandatory): The current provenance tree, canonical registry, and lifecycle audit log to verify that only eligible artifacts are presented.

## Required Output Directory
```
skills/verified_provenance_to_latex_pdf/output/{report_id}/
```
Where `{report_id}` is based on the checkpoint or artifact selection + timestamp.

## Required Output Structure

### publication/ subdirectory (always produced)
```
publication/
  main.tex                          # Main LaTeX document
  main.pdf                          # Compiled PDF (conditional — only with later-authorized compilation)
  bibliography.bib                  # Bibliography entries for all referenced sources
  build.log                         # Compilation log (conditional)
  figures/                          # Any generated figures or diagrams
```

### generated/ subdirectory (always produced — embedded into main.tex)
```
generated/
  provenance_manifest.json          # Complete mapping of every TeX element to its source
  latex_evidence_mapping.json       # Bidirectional TeX label to source artifact mapping
  symbol_convention_table.tex       # Table of all symbols, indices, domains, and conventions
  source_equation_map.tex           # Map of equation numbers in output to source equations in raw objects
  derivation_dag.tex                # Derivation DAG diagram or table
  raw_architecture.tex              # Raw expression structure overview
  sector_decomposition.tex          # Sector decomposition table
  transformation_registry.tex       # All transformations applied, with levels and rules
  verification_summary.tex          # Summary of all verification results
  human_decision_summary.tex        # Summary of all human gate decisions
  caveat_and_residual_registry.tex  # All caveats, unresolved issues, and residual terms
  final_expression.tex              # The final expression(s) in LaTeX form
  stage_to_script_correspondence.tex # Mapping of derivation stages to scripts/tasks
  claim_boundary.tex                # Explicit boundary of what is claimed vs what is assumed
```

## Required Output Artifact Details

### 1. provenance_manifest.json (always produced)
Complete mapping of every TeX element to its provenance source. Schema:
- `report_id`: unique report identifier string.
- `report_timestamp`: ISO 8601 UTC timestamp.
- `source_checkpoint`: the checkpoint this report was built from (or null).
- `source_branch`: the branch this report was built from (or null).
- `eligible_artifacts_included`: array of objects, each containing:
  - `artifact_id`: the provenance artifact identifier.
  - `artifact_type`: RAW_OBJECT, NORMALIZED_PARENT, CHILD_EXPRESSION, CANDIDATE_TRANSFORMED, CLAIM_RELATION, CHECKPOINT.
  - `artifact_status`: current lifecycle status.
  - `latex_labels`: array of LaTeX label strings that reference this artifact.
  - `appears_in`: array of section or equation references where this artifact appears.
- `ineligible_artifacts_excluded`: array of objects, each containing:
  - `artifact_id`: excluded artifact identifier.
  - `exclusion_reason`: why the artifact was excluded (e.g. CANDIDATE_TRANSFORMED without VERIFIED).
- `provenance_tree_sha256`: SHA-256 of the provenance tree at the time of report generation.

### 2. latex_evidence_mapping.json (always produced)
Bidirectional mapping between every LaTeX element and its evidence source. Each mapping entry contains:
- `latex_label`: LaTeX label string (e.g. eq:final_generic_target).
- `latex_element_type`: equation, table, figure, section, or claim_statement.
- `latex_location`: section and line numbers.
- `source_task`: the task ID from routing.
- `source_artifact`: file path and artifact ID.
- `source_sha`: SHA-256 of the source artifact.
- `verification_task`: the verification ID that verified this claim.
- `claim_type`: the verified_relation value.
- `assumptions`: array of assumption strings.
- `scope`: domain string.
- `human_decision_dependency`: human decision event ID (or null).
- `caveats`: array of caveat strings.
- `canonical_or_candidate_status`: CANONICAL, INTEGRATED, VERIFIED, or CANDIDATE_TRANSFORMED.

### 3. symbol_convention_table.tex (always produced)
LaTeX tabular environment listing every symbol that appears in the output:
- Symbol name (LaTeX math mode).
- Index structure (if indexed).
- Index domain and range.
- Summation convention (summed or free).
- Symmetry properties (if known).
- Definition source (artifact reference).
- Human confirmation status.

### 4. source_equation_map.tex (always produced)
Map of equation numbers in the output document to source equations in raw ingested expressions:
- Output equation number.
- Source expression reference (raw_object_id).
- Transformation lineage summary.
- Verification status.
- Any differences between source and output (if the output is a simplified form).

### 5. derivation_dag.tex (always produced)
A diagram or tabular representation of the derivation DAG:
- Nodes: raw objects, normalized parents, children, transformed candidates.
- Edges: transformation rules, normalization steps, decomposition relationships.
- Node labels: artifact IDs, statuses, key metrics (term count, etc.).
- Critical path highlighting: the path from raw input to final result.

### 6. raw_architecture.tex (always produced)
Structural overview of the raw ingested expression:
- Free symbols inventory.
- Indexed symbols with index structures.
- Dummy index summary.
- External index summary.
- Summation convention declaration.
- Known symmetries.
- Adapter-provided metadata summary.

### 7. sector_decomposition.tex (always produced)
Sector decomposition table showing:
- Sector names and descriptions.
- Sub-expression membership.
- Boundary conditions between sectors.
- Adapter-supplied tagging rationale.

### 8. transformation_registry.tex (always produced)
All transformations applied in the derivation, with:
- Transformation ID.
- Rule name and level (A-G).
- Applied to (source sub-expression).
- Before and after SHA-256.
- Authorized level vs actual applied level.
- Reversibility.
- Human authorization status.

### 9. verification_summary.tex (always produced)
Summary of all verification results:
- Verification ID.
- Claimed relation vs verified relation.
- Methods applied and results.
- Numerical agreement flag (with explicit caveat if only numerical).
- Counterexamples found (if any).
- Scope coverage audit.
- Assumption audit.

### 10. human_decision_summary.tex (always produced)
Summary of all human gate decisions:
- Decision event ID and timestamp.
- Which claim was decided upon.
- Decision (PASS, FAIL, WAIVE, OVERRIDE).
- Human rationale.
- Caveats or conditions attached to the decision.

### 11. caveat_and_residual_registry.tex (always produced)
Registry of all caveats and residual (unresolved) issues:
- Unverified assumptions that were used.
- Scope gaps that could not be tested.
- Numerical-only evidence flagged as supporting.
- Human-waived semantic gaps.
- Residual terms that were not fully simplified.
- Known limitations of the derivation.

### 12. final_expression.tex (always produced)
The final expression(s) in LaTeX math format:
- Canonical expressions with CANONICAL status.
- Verified expressions with VERIFIED status (clearly labelled as "verified, awaiting canonical promotion").
- Candidate expressions (if explicitly requested, clearly labelled as "CANDIDATE — NOT VERIFIED").
- Each expression annotated with its provenance reference (as a LaTeX margin note or footnote).

### 13. stage_to_script_correspondence.tex (always produced)
Mapping of each derivation stage to the script or task that produced it:
- Stage name (PLAN, EXECUTE, VERIFY, etc.).
- Task / script identifier.
- Input artifact references.
- Output artifact references.
- Runtime / timestamp metadata.

### 14. claim_boundary.tex (always produced)
Explicit boundary statement of what is claimed vs what is assumed:
- "We claim that expression X equals expression Y under assumptions Z."
- "We do NOT claim that this holds beyond scope W."
- "The following results rely on unverified assumption A."
- "The following results have been verified only numerically."
- "The following steps are CANDIDATE_TRANSFORMED and have NOT been independently verified."

## Presentation Rules — Forbidden Representations

The following presentations are STRICTLY FORBIDDEN in all output files:

1. **Candidate as verified**: A `CANDIDATE_TRANSFORMED` artifact MUST NOT be presented with any language suggesting it has been verified. It must be clearly labelled as CANDIDATE.

2. **Verified candidate as canonical**: A `VERIFIED` (but not CANONICAL) artifact MUST NOT be presented as if it has canonical authority. It must be labelled as "verified, pending canonical promotion" or equivalent.

3. **Projection relation as global equality**: A `projected_identity` MUST NOT be presented as if it holds for all values. The projection basis must be explicitly stated, and the limitation must be clear.

4. **Pointwise identity as integrated cancellation**: A `pointwise_identity` (which holds at every point) and an `integrated_identity` (which holds only after integration) are fundamentally different and MUST NOT be conflated. If an identity holds only after integration (e.g., up to surface terms), this must be explicitly stated.

5. **Historical result as current truth without temporal qualification**: A `SUPERSEDED` canonical artifact MUST NOT be presented as if it is still canonical. If referenced for historical context, it must be accompanied by a "superseded by [new artifact]" statement.

6. **Numerical evidence as symbolic proof**: Any result supported only by numerical sampling MUST be explicitly labelled as "numerical evidence only — not a symbolic proof."

7. **Assumption-dependent identity without stating assumptions**: An `identity_under_assumptions` MUST have all assumptions stated inline or in a footnote. The assumption list must be complete.

8. **Unverified transformation as verified**: A transformation that has not been independently verified MUST NOT appear in a "verified results" section.

## Allowed Operations
- Read (never modify) all provenance artifacts, lifecycle events, and canonical registry.
- Generate LaTeX source files from eligible artifacts.
- Generate mapping files (JSON) that trace every LaTeX element to its source.
- Assemble a complete `main.tex` that imports all generated TeX files.
- Generate a `bibliography.bib` with all referenced sources.
- Generate `build.log` tracking the TeX generation process.
- Filter artifacts by eligibility: only VERIFIED, INTEGRATED, or CANONICAL artifacts may appear as "results." CANDIDATE_TRANSFORMED artifacts may appear only if explicitly requested and clearly labelled.
- Flag missing or incomplete evidence in `caveat_and_residual_registry.tex`.
- Present status labels consistently and accurately.
- Structural formatting and layout decisions for the TeX document.
- Request human authorization before attempting PDF compilation.

## Forbidden Operations
- **Promoting artifact status** — this skill is READ-ONLY. It must not change any lifecycle status, canonical registry, or provenance record.
- **Presenting an ineligible artifact as if it were eligible** — see Presentation Rules above.
- **Generating PDF without later-authorized compilation** — TeX generation and PDF compilation are separate steps. The skill may generate TeX freely, but PDF compilation requires explicit authorization (which may be granted after the human reviews the TeX).
- **Claiming `compilation_ready` without verifying the toolchain** — the skill must not assert that the TeX will compile if it has not tested the compilation with a verified LaTeX toolchain.
- **Omitting caveats or limitations** — all known caveats from the verification and human decision records must be included.
- **Presenting a superseded artifact as current** — superseded artifacts must be clearly marked.
- **Adding unsourced claims** — every equation, table, and conclusion must either trace to a provenance artifact or be explicitly labelled as "generated structure" (e.g., section headings, explanatory text that is not a scientific claim).
- **Modifying symbolic expressions** — the TeX representation must be a faithful rendering of the stored expression. No simplification, reordering, or prettification that changes the mathematical content is permitted.

## Semantic Blockers
The following conditions MUST block TeX generation and require escalation:
1. **No eligible artifacts**: The selected checkpoint or branch contains no VERIFIED, INTEGRATED, or CANONICAL artifacts. There is nothing to present.
2. **Incomplete provenance**: An artifact that should be included has a broken provenance chain (missing parent, missing raw object reference).
3. **Conflicting canonical entries**: The canonical registry contains two entries that make contradictory claims, and neither is superseded.
4. **Missing verification for a claimed result**: An artifact is labelled VERIFIED but no `claim_relation.json` can be found.
5. **Corrupted artifact**: An artifact's SHA-256 does not match its stored content.
6. **Unresolved semantic escalation**: A semantic gap that affects a result being presented is still PENDING.
7. **Missing convention table**: Symbol conventions are unknown for symbols that appear in the output, and the human has not provided them.
8. **Circular reference in derivation DAG**: The provenance tree has a cycle, making it impossible to establish a linear derivation order for presentation.

## Task Lifecycle
1. **RECEIVE**: Accept the checkpoint/artifact selection and routing decision.
2. **LOAD_STATE**: Load the provenance tree, lifecycle audit log, canonical registry, and all referenced artifacts.
3. **VALIDATE_ELIGIBILITY**: For each artifact in scope, determine if it is eligible for presentation:
   - CANONICAL: Eligible for "final results."
   - INTEGRATED / VERIFIED: Eligible for "verified results (pending canonical)."
   - CANDIDATE_TRANSFORMED: Eligible only if explicitly requested, with clear label.
   - RAW_INGESTED / NORMALIZED_PARENT: Eligible for "source material" or "architecture" sections, not for "results."
   - SUPERSEDED: Eligible only for historical context, with clear marking.
4. **CHECK_BLOCKERS**: Verify that no semantic blockers exist.
5. **BUILD_MANIFEST**: Create `provenance_manifest.json` listing all included and excluded artifacts.
6. **GENERATE_TEX_FILES**: Generate all 14 generated TeX files plus `symbol_convention_table.tex` through `claim_boundary.tex`.
7. **BUILD_MAPPING**: Create `latex_evidence_mapping.json` tracing every TeX label to its source.
8. **ASSEMBLE_MAIN**: Write `main.tex` that imports all generated files in the correct order.
9. **GENERATE_BIB**: Write `bibliography.bib` with all source references.
10. **VALIDATE_OUTPUT**: Check that all cross-references in the TeX are resolvable. Check that every equation/table has a mapping entry.
11. **REPORT_STATUS**: Record the generation in `build.log`. State whether TeX generation is complete and whether compilation is pending.
12. **PRESENT**: Output the report directory path and a summary of what was generated.

## Compilation Authorization
PDF compilation is a separate, later-authorized step:
- TeX generation produces `.tex` files and a `main.tex` that can (in principle) be compiled.
- Actual compilation (`pdflatex`, `lualatex`, `xelatex`) requires explicit human authorization.
- The human authorizes compilation by setting a flag (e.g., in a routing decision or a file).
- The system MUST verify that a LaTeX toolchain is available before claiming `compilation_ready`.
- `build.log` records the TeX generation details and, separately, any compilation attempts.
- If compilation fails, the build.log records the error. The system MUST NOT silently retry.

## Relation / Claim Types
This skill does NOT produce scientific claims. It produces presentation artifacts:
- `TEX_GENERATED`: TeX source files have been generated for the specified checkpoint/branch.
- `MAPPING_COMPLETE`: The TeX-to-provenance mapping has been generated.
- `COMPILATION_READY`: The TeX has passed structural validation but has not been compiled.
- `PDF_COMPILED`: The TeX has been successfully compiled to PDF (with human authorization).
- `COMPILATION_FAILED`: Compilation was attempted and failed.

## Artifact Contract
- Every equation, table, and figure in `main.tex` MUST have a corresponding entry in `latex_evidence_mapping.json`.
- `latex_evidence_mapping.json` MUST contain a mapping entry for every TeX `\label{...}` in the generated files.
- `provenance_manifest.json` MUST list ALL artifacts in scope, both included and excluded, with explicit reasons for exclusion.
- `caveat_and_residual_registry.tex` MUST list all known caveats from all verification and human decision records.
- `claim_boundary.tex` MUST clearly delineate what is claimed vs what is assumed.
- No artifact in `final_expression.tex` may be presented without its status label.
- Status labels must use consistent terminology: "CANONICAL," "VERIFIED (pending canonical promotion)," "CANDIDATE — NOT VERIFIED."
- All timestamps MUST be ISO 8601 UTC.
- `main.tex` MUST compile independently if all `\input{}` and `\include{}` paths are relative to the `publication/` directory.

## Downstream Eligibility
The generated TeX/PDF output is eligible for:
- Human review and audit.
- Sharing with collaborators (with caveats clearly visible).
- Inclusion in a paper (after human author confirms the content).
- Archival alongside the provenance tree.

The generated output is NOT eligible for:
- Submission to a journal without human review (the system does not submit papers).
- Claiming that the system "proved" something (the human is the authority).

## Human Escalation Behavior
- When no eligible artifacts exist: Escalate to human with a report of what artifacts exist and why none are eligible.
- When a LaTeX symbol cannot be rendered: Escalate with the specific symbol and ask the human for LaTeX representation guidance.
- When the derivation DAG has a cycle: Escalate with the cycle description and ask the human to resolve the provenance inconsistency.
- Before PDF compilation: Ask the human "Compile main.tex to PDF?" with a summary of the toolchain available.
- When compilation fails: Present the error log and ask the human whether to: fix the TeX (human provides correction), adjust the template, skip compilation and use TeX only, or abort.
- When an artifact's status is ambiguous: Escalate with the artifact details and ask the human to clarify whether it should be included.

## Interaction with Other Skills
- **Receives from**: `scientific_symbolic_repo_entry` (routing decision).
- **Reads from**: ALL other skills (raw objects, normalized parents, children, candidates, verifications, lifecycle events, canonical registry).
- **Does NOT modify**: Any artifact, lifecycle state, or provenance record.
- **Feeds into**: Human review workflow, paper-writing pipeline (external to this skill set).
- **Escalates to**: `human_scientist_semantic_escalation` (when semantic gaps affect presentation).

## Error Handling
- **Missing artifact file**: Skip that artifact. Record in `caveat_and_residual_registry.tex` as "artifact [ID] not found — excluded from output."
- **Corrupted artifact (SHA mismatch)**: Skip that artifact. Record in caveats as "artifact [ID] failed integrity check — excluded from output."
- **Unsupported LaTeX construct**: The symbolic expression contains a construct with no known LaTeX mapping. Escalate to human with the construct details.
- **Circular import in TeX**: If `main.tex` import structure is circular, this is a generation logic error. Halt and flag for debugging.
- **bibliography.bib missing required fields**: Flag the missing fields. Attempt to generate with available information. Record gaps in build.log.
- **File system full**: Halt. Report the error. Attempt to preserve already-generated files if partial output is useful.
