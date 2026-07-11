# Skill Cookbook

This document describes every public skill in the Repo-Native Symbolic Science framework. Natural-language automatic routing through `scientific_symbolic_repo_entry` is recommended for most users. Explicit skill naming is available for advanced control.

---

## scientific_symbolic_repo_entry

- **Skill name**: `scientific_symbolic_repo_entry`
- **Scientific intention**: Route human natural-language requests into one of six task classes: ingestion, transformation, verification, human-decision, integration, or reporting.
- **Activation conditions**: Any natural-language request referencing symbolic expressions, derivations, simplifications, verifications, or reporting. Also activated for ambiguous requests that require classification.
- **Required inputs**: Natural-language request text; context snapshot (working directory, open files, recent git history, active branch).
- **Generated outputs**: `routing_decision.json`, `clarification_request.md` (conditional), `routing_audit_log.json`.
- **Allowed operations**: Parse and classify requests; detect ambiguity; generate clarification requests; log routing decisions; hand off to target skills.
- **Forbidden operations**: Performing symbolic manipulation directly; producing symbolic output, TeX, or PDF; best-effort routing without resolution of missing information; interpreting scientific meaning from symbol names; adding missing information by guesswork.
- **Human gates**: Automatically escalates when information is missing via `clarification_request.md`.
- **Typical next skill**: Any of the five downstream skill classes (ingestion, transformation, verification, human-decision, integration, reporting).
- **Copy-paste user request**:
  > Use the Repo-Native Symbolic Science workflow for this project. Read `AGENTS.md` and `REPO_POLICY.md` first. Ingest the raw expression as immutable input, audit its scientific semantics, and tell me what definitions or assumptions are missing.

---

## generic_raw_expression_ingestion

- **Skill name**: `generic_raw_expression_ingestion`
- **Scientific intention**: Freeze raw expression bytes with SHA-256 hashing and audit expression structure without performing any simplification or transformation.
- **Activation conditions**: A raw expression file, string, or path is provided and must be frozen as an immutable input artifact.
- **Required inputs**: Raw expression bytes or file path; expression language (e.g., sympy, latex, mathematica); optional scientific adapter configuration.
- **Generated outputs**: `raw_object.json` (with SHA-256), `symbol_inventory.json`, `index_audit.json`, `structure_audit.json`, `ingestion_report.md`.
- **Allowed operations**: Hash raw bytes; extract and inventory symbols, indices, operators, and functions; record expression structure; freeze as `RAW_INGESTED`.
- **Forbidden operations**: Performing any simplification, expansion, or algebraic manipulation; reinterpreting symbol semantics; adding or removing terms; converting between expression languages that introduce semantic loss.
- **Human gates**: Escalates when symbols lack definitions, index roles are ambiguous, or expression structure is underspecified.
- **Typical next skill**: `human_scientist_semantic_escalation` (if gaps found) or `generic_expression_normalization_and_decomposition` (if all semantics declared).
- **Copy-paste user request**:
  > Ingest the raw expression from `input/raw_expression.txt`. Treat the original bytes as immutable. Inventory all symbols, indices, operators, denominators, special functions, and structure. Do not simplify, expand, or transform anything.

---

## human_scientist_semantic_escalation

- **Skill name**: `human_scientist_semantic_escalation`
- **Scientific intention**: The only mechanism for requesting human semantic input when definitions, assumptions, index roles, or authorizations are missing.
- **Activation conditions**: Any downstream skill detects missing scientific definitions, ambiguous index roles, underdetermined assumptions, or unauthorized operations.
- **Required inputs**: The incomplete artifact or task state; the specific gap identified; the list of entities requiring definition.
- **Generated outputs**: `human_information_request.md`, `escalation_record.json`, `missing_semantics_registry.json`, `resolved_semantics_registry.json`, `blocked_claims.json`, `allowed_continuation.json`, `human_decision_record.json`, `escalation_audit_log.json`.
- **Allowed operations**: Formulate structured questions; distinguish "not found" from "does not exist"; record human decisions; gate all unresolved definitions as BLOCKED.
- **Forbidden operations**: Inventing definitions; inferring from notation alone; reinterpreting "not found" as "nonexistent"; authorizing IBP, limit reordering, or canonical promotion.
- **Human gates**: This skill IS the human gate mechanism. Every output requires human response.
- **Typical next skill**: Returns to the skill that triggered the escalation.
- **Copy-paste user request**:
  > Audit whether all symbols in the raw expression have authoritative definitions. If definitions such as h1, h2, or h3 are missing, do not infer them from notation. Materialize a human information request specifying exactly what definitions, signs, prefactors, index orientations, and source evidence are required.

---

## generic_expression_normalization_and_decomposition

- **Skill name**: `generic_expression_normalization_and_decomposition`
- **Scientific intention**: Apply deterministic structural normalization and decompose a parent expression into independent child sub-expressions (sectors) while preserving free and dummy index roles, noncommutative multiplication order, and source provenance.
- **Activation conditions**: A raw expression has been ingested and all scientific semantics are declared; normalization or decomposition is requested.
- **Required inputs**: `raw_object.json` from ingestion; declared scientific adapter with index roles and assumptions.
- **Generated outputs**: `normalized_parent.json`, `child_expressions.json`, `parent_reconstruction_test.json`.
- **Allowed operations**: Structural normalization (canonical ordering, term grouping); decomposition into independent sectors; parent-child reconstruction verification.
- **Forbidden operations**: Algebraic transformations (expansion, factorization, substitution); integration by parts; boundary term discard; limit reordering; index role reassignment.
- **Human gates**: Escalates if normalization introduces structural ambiguity or if child independence cannot be verified.
- **Typical next skill**: `candidate_symbolic_transformation`.
- **Copy-paste user request**:
  > Normalize the ingested expression and decompose it into independent child sectors. Preserve free and dummy index roles, noncommutative multiplication order, coefficients, and source provenance. Every child sector must reconstruct the exact parent expression. Term-count agreement alone is not sufficient.

---

## candidate_symbolic_transformation

- **Skill name**: `candidate_symbolic_transformation`
- **Scientific intention**: Search for compact candidate representations using authorized algebraic and scientific-definition identities at declared transformation levels (A–G).
- **Activation conditions**: A normalized and decomposed expression exists; transformation level and allowed operations are declared; all definitions are available.
- **Required inputs**: `normalized_parent.json`, `child_expressions.json`, declared transformation level (A–G), authorized identities from scientific adapter.
- **Generated outputs**: `candidate_transformation.json`, `rule_application_trace.json`, `level_boundary_audit.json`, `transformation_report.md`.
- **Allowed operations**: Exact algebraic identities at authorized levels:
  - **Level A**: Syntax-preserving (rename, reorder commuting terms)
  - **Level B**: Exact algebraic (expand, factor, cancel, together)
  - **Level C**: Scientific-definition identities (substitute declared identities)
  - **Level D**: Differential and product rule identities
  - **Level E**: Integration and IBP (requires explicit authorization)
  - **Level F**: Integrated cancellation (requires boundary assumptions)
  - **Level G**: Closure and canonicalization (requires human gate)
- **Forbidden operations**: Using unauthorized levels; silent IBP; discarding boundary terms; reordering limits; inventing identities; promoting candidate to verified without verification.
- **Human gates**: Required for levels E, F, G; required for any operation that crosses the declared transformation boundary.
- **Typical next skill**: `exact_and_bounded_symbolic_verification`.
- **Copy-paste user request**:
  > Search for a more compact candidate representation using only exact algebra and the scientific identities already authorized in the project adapter. Use only levels A through C. Do not use integration by parts, boundary assumptions, or integrated cancellation. Record every transformation and its claim scope.

---

## exact_and_bounded_symbolic_verification

- **Skill name**: `exact_and_bounded_symbolic_verification`
- **Scientific intention**: Verify relations between expressions. Distinguishes exact symbolic equality, structural replay, high-precision support, and numerical regression as separate claim types.
- **Activation conditions**: A candidate transformation or parent-child relationship requires independent verification against frozen inputs.
- **Required inputs**: Source expression (frozen SHA), target expression, declared assumptions, verification scope (pointwise, projected, or integrated).
- **Generated outputs**: `claim_relation.json`, `verification_report.md`, `numerical_evidence.json`, `subtraction_result.json`, `projection_regression.json`, `scope_assumption_audit.json`.
- **Allowed operations**: Exact subtraction and simplification; structural replay; projection onto declared bases; numerical evaluation with declared precision; high-precision sampling as supporting evidence.
- **Forbidden operations**: Claiming symbolic equality from numerical agreement alone; conflating projection equality with global equality; confusing pointwise derivative with integrated identity; auto-promoting verified to canonical.
- **Human gates**: Required to accept a verification verdict; required to claim anything beyond the verified scope.
- **Typical next skill**: `cross_engine_symbolic_and_numeric_verification` (for cross-engine replay) or `provenance_claim_and_canonical_state` (for lifecycle advancement).
- **Copy-paste user request**:
  > Independently verify the candidate result from frozen inputs. Reconstruct the parent expression, compute exact differences where possible, and use high-precision numerical sampling only as supporting evidence. Keep exact equality, structural replay, and numerical regression as separate claim types.

---

## provenance_claim_and_canonical_state

- **Skill name**: `provenance_claim_and_canonical_state`
- **Scientific intention**: Manage the immutable lifecycle from PLAN through EXECUTE, VERIFY, HUMAN GATE, INTEGRATE, INTEGRATION VERIFY, and CANONICAL PROMOTION.
- **Activation conditions**: A verification result, human decision, or integration task requires lifecycle advancement or checkpoint freezing.
- **Required inputs**: Verification artifacts, human decision records, integration manifests.
- **Generated outputs**: `checkpoint_manifest.json`, `canonical_state.json`, `provenance_chain.json`, `integration_record.json`.
- **Allowed operations**: Recording lifecycle state transitions; freezing checkpoints; linking artifacts with SHA-256 provenance; managing the canonical promotion workflow.
- **Forbidden operations**: Automatic canonical promotion; skipping HUMAN GATE; modifying frozen artifacts; retroactively altering lifecycle state.
- **Human gates**: Required for canonical promotion; required for checkpoint freezing that crosses a claim boundary.
- **Typical next skill**: `verified_provenance_to_latex_pdf` (for reporting) or opens a new derivation branch.
- **Copy-paste user request**:
  > Record the verified result in provenance. Freeze the current state as a checkpoint. Do not promote to canonical without explicit human authorization.

---

## verified_provenance_to_latex_pdf

- **Skill name**: `verified_provenance_to_latex_pdf`
- **Scientific intention**: Map verified artifacts to traceable TeX and PDF output where every equation and claim maps to its source task, artifact SHA, verifier verdict, assumptions, and human decisions.
- **Activation conditions**: Verified or canonical artifacts exist; a human-readable report is requested.
- **Required inputs**: Verified artifacts (claim_relation.json, verification_report.md, checkpoint_manifest.json); human-authorized compilation scope.
- **Generated outputs**: Generated TeX files (`publication/*.tex`, `generated/*.tex`), `latex_evidence_mapping.json`, PDF (requires human-authorized compilation).
- **Allowed operations**: Generating TeX from verified artifacts; mapping equations to provenance; compiling PDF when authorized.
- **Forbidden operations**: Presenting candidates as verified; presenting numerical evidence as symbolic proof; omitting caveats from reports; compiling PDF without human authorization.
- **Human gates**: Required for PDF compilation; required for publication-ready finalization.
- **Typical next skill**: None (terminal skill).
- **Copy-paste user request**:
  > Generate a human-readable LaTeX report from verified artifacts. Every important equation and claim must map to its source task, artifact, SHA, verifier verdict, assumptions, human decision, caveats, and canonical status.

---

## computational_backend_selection

- **Skill name**: `computational_backend_selection`
- **Scientific intention**: Select computation backends by matching requested capabilities against available engines (SymPy, NumPy/SciPy/mpmath, Mathematica).
- **Activation conditions**: A computation task has been planned and requires backend execution.
- **Required inputs**: Requested capabilities list; expected output type (EXACT_SYMBOLIC, NUMERICAL_SAMPLED, ANY); preferred and prohibited backends; fallback policy.
- **Generated outputs**: `engine_selection.json`, `capability_gap_report.json`.
- **Allowed operations**: Probing available engines; matching capabilities against engine registries; selecting primary, supporting, and verification backends; recording fallback paths.
- **Forbidden operations**: Selecting Mathematica without license evidence; downgrading exact symbolic requirement to numerical without authorization; selecting a backend with unmatched capabilities.
- **Human gates**: Required when no backend matches all capabilities; required when Mathematica is the only matching backend.
- **Typical next skill**: `bounded_computation_backend_execution`.
- **Copy-paste user request**:
  > Determine which computation capabilities this task requires. Prefer an open-source exact backend when sufficient. Use Mathematica only as an optional backend when its additional capabilities are needed and a license is available. Do not replace an exact symbolic requirement with numerical sampling.

---

## bounded_computation_backend_execution

- **Skill name**: `bounded_computation_backend_execution`
- **Scientific intention**: Execute bounded computation on selected backends with full execution truth recording (22 required fields).
- **Activation conditions**: A backend has been selected; an authorized computation request exists; all scientific definitions are available.
- **Required inputs**: Engine selection result; computation request with operations, assumptions, expression, timeout, and memory limit; input artifact SHAs.
- **Generated outputs**: `execution_truth.json`, `engine_output.json`, `execution_report.md`.
- **Allowed operations**: Running bounded computation on authorized backends; recording execution truth with all 22 required fields; detecting and reporting warnings, errors, timeouts, and memory limits.
- **Forbidden operations**: Running computation beyond declared timeout or memory bounds; silently modifying input; normalizing output in a way that changes mathematical meaning; executing without recording execution truth.
- **Human gates**: Required for Mathematica execution if license not previously confirmed; required when execution warnings indicate potential semantic issues.
- **Typical next skill**: `exact_and_bounded_symbolic_verification` or `cross_engine_symbolic_and_numeric_verification`.
- **Copy-paste user request**:
  > Run the authorized computation on the selected backend. Record complete execution truth including the exact command, all inputs and their SHA-256 hashes, the generated script SHA, start and completion times, exit code, operations observed, assumptions observed, raw and normalized output with SHAs, all warnings and errors, and timeout and memory state.

---

## cross_engine_symbolic_and_numeric_verification

- **Skill name**: `cross_engine_symbolic_and_numeric_verification`
- **Scientific intention**: Independently replay results on verification backends and compare exact, structural, high-precision, and numerical evidence across engines.
- **Activation conditions**: A primary backend has produced a result; cross-engine verification is needed.
- **Required inputs**: Primary backend result with execution truth; verification backend selection; translation mapping between engine expression languages.
- **Generated outputs**: `cross_engine_verification.json`, `cross_engine_report.md`, `translation_loss_record.json`.
- **Allowed operations**: Replaying computation on verification backends; comparing exact symbolic results; comparing structural properties; comparing high-precision numerical values; recording translation loss.
- **Forbidden operations**: Treating cross-engine numerical agreement as cross-engine symbolic equality; ignoring translation loss; comparing results from incompatible expression languages without recorded translation.
- **Human gates**: Required when translation loss is detected; required when backends disagree on a claim that crosses the claim boundary.
- **Typical next skill**: `provenance_claim_and_canonical_state`.
- **Copy-paste user request**:
  > Replay the verified result on a second backend. Compare exact symbolic equality, structural replay fidelity, and high-precision numerical values independently. Record any translation loss between engine representations. Keep exact and numerical evidence separate.

---

## Natural-Language Automatic Routing (Recommended)

For most users, explicit skill selection is unnecessary. The agent reads the repository skills and routes natural-language requests automatically. Example requests and their automatic routing:

| User says | Routed to |
|-----------|-----------|
| "Ingest this file and freeze it" | `scientific_symbolic_repo_entry` → `generic_raw_expression_ingestion` |
| "What definitions am I missing?" | `scientific_symbolic_repo_entry` → `human_scientist_semantic_escalation` |
| "Normalize and split this expression" | `scientific_symbolic_repo_entry` → `generic_expression_normalization_and_decomposition` |
| "Find a simpler form" | `scientific_symbolic_repo_entry` → `candidate_symbolic_transformation` |
| "Is this result correct?" | `scientific_symbolic_repo_entry` → `exact_and_bounded_symbolic_verification` |
| "Generate a PDF report" | `scientific_symbolic_repo_entry` → `verified_provenance_to_latex_pdf` |
| "Which backend should I use?" | `scientific_symbolic_repo_entry` → `computational_backend_selection` |
| "Run this on SymPy" | `scientific_symbolic_repo_entry` → `computational_backend_selection` → `bounded_computation_backend_execution` |
| "Check on a second engine" | `scientific_symbolic_repo_entry` → `cross_engine_symbolic_and_numeric_verification` |

## Explicit Skill Invocation (Advanced)

For advanced users who prefer explicit control, each skill can be invoked directly by name. The agent reads the skill's `SKILL.md` and follows its activation conditions. Explicit invocation bypasses the safety checks in `scientific_symbolic_repo_entry` and is not recommended for routine use.
