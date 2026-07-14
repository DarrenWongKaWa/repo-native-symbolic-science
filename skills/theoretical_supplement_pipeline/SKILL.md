# Theoretical Supplement Pipeline

## Purpose

`theoretical_supplement_pipeline` is the default user-facing orchestration facade for assembling a provenance-traceable supplement package and renderer dispatch from authenticated, pre-authored artifacts through one configured workflow.

This skill is:

- a user-facing orchestration facade;
- a dependency resolver;
- a stage planner;
- a validator coordinator;
- a resumable pipeline controller.

This skill is not:

- a mathematical derivation engine;
- a physical interpretation engine;
- a PDF renderer;
- a replacement for any existing internal supplement skill.

## Public Promise

Assemble a human-readable narrative package, provenance records, and renderer dispatch from supplied artifacts whose configured structural and provenance checks pass. This is not mathematical verification, complete TeX generation, or PDF compilation.

## Activation Conditions

Activate this skill when:

- a user asks for a complete theoretical supplement;
- a user asks for a one-command supplement workflow;
- a user provides a `theoretical_supplement_request` and wants the full pipeline planned, validated, resumed, or executed;
- a user asks whether final TeX/PDF rendering is authorized.

Do not activate this skill for direct symbolic simplification, equation editing, physical interpretation creation, standalone renderer use, or canonical promotion.

## Minimal Request Format

The default user request should provide a single request file:

```json
{
  "request_id": "example_theoretical_supplement",
  "source_manifest": "path/to/source_artifact_manifest.json",
  "output_directory": "output/example_theoretical_supplement",
  "audience": "theoretical_physicist",
  "output_formats": ["latex", "pdf"],
  "pipeline_mode": "full",
  "require_term_level_interpretation": true,
  "require_long_expression_reconstruction": true,
  "require_independent_readability_review": true
}
```

Users should not need to manually invoke internal skills for the default workflow.

## Dependency Graph

```text
SOURCE_AUTHENTICATION
  -> DERIVATION_GRAPH
  -> DERIVATION_NARRATIVE
  -> PHYSICAL_INTERPRETATION
  -> LONG_EXPRESSION_PRESENTATION
  -> EQUATION_EVIDENCE_MAPPING
  -> SUPPLEMENT_ASSEMBLY
  -> HANDOFF_VALIDATION
  -> PROVENANCE_RENDERING
  -> READABILITY_AUDIT
  -> FINALIZATION
```

`PHYSICAL_INTERPRETATION` and `LONG_EXPRESSION_PRESENTATION` may be planned as parallel-eligible after the derivation graph and narrative prerequisites are valid. The facade records that eligibility but does not collapse the skills into one implementation.

## Stage Eligibility Rules

- `SOURCE_AUTHENTICATION` requires a readable source manifest and SHA-valid source artifacts.
- `DERIVATION_GRAPH` requires authenticated source artifacts and a valid derivation graph artifact.
- `DERIVATION_NARRATIVE` requires a validated derivation graph.
- `PHYSICAL_INTERPRETATION` requires traceable target expressions and physical interpretation artifacts when requested.
- `LONG_EXPRESSION_PRESENTATION` requires complete long-expression artifacts and omission ledgers when reconstruction is requested.
- `EQUATION_EVIDENCE_MAPPING` requires derivation steps and evidence mapping artifacts.
- `SUPPLEMENT_ASSEMBLY` requires all mandatory upstream native artifacts.
- `HANDOFF_VALIDATION` requires a complete `reporting_handoff_package.json`.
- `PROVENANCE_RENDERING` requires a validated handoff package whose `rendering_authority` is `verified_provenance_to_latex_pdf`.
- `READABILITY_AUDIT` requires assembled supplement artifacts and a complete 13-check audit.
- `FINALIZATION` requires all mandatory stages to pass or reuse SHA-valid prior outputs.

## Renderer Authorization Gate

The facade must enforce:

```text
No validated reporting_handoff_package.json
-> no final TeX/PDF rendering
```

The facade must reject this shortcut:

```text
read scientific files
-> handwrite main.tex
-> compile PDF
```

`verified_provenance_to_latex_pdf` remains the sole rendering authority. The facade may create a renderer dispatch package only after handoff validation passes.

## Native Artifact Requirements

The pipeline records the following proof artifacts in the selected output directory:

```text
pipeline_plan.json
pipeline_state.json
pipeline_event_log.jsonl
skill_execution_manifest.json
missing_prerequisites.json
final_result.json
```

Each internal skill entry in `skill_execution_manifest.json` records:

- skill name;
- `SKILL.md` path;
- activation decision;
- input artifacts;
- output artifacts;
- validators executed;
- validation results;
- start and finish timestamps;
- artifact SHA-256 values;
- status: `PASS`, `FAIL`, `SKIPPED_VALID_EXISTING`, or `BLOCKED`.

A skill is not considered executed merely because its name appears in the plan.

## Resume Behavior

Resume mode must:

- load `pipeline_state.json`;
- reuse only prior stage outputs whose current SHA-256 matches the recorded SHA-256;
- rerun stale or invalid generated stages when possible;
- never accept partial artifacts as complete;
- never silently skip a required stage;
- preserve the first blocking failure.

## Fail-Closed Behavior

Examples:

```text
missing derivation graph
-> BLOCKED_AT_DERIVATION_GRAPH

derivation graph contains a gap
-> BLOCKED_BY_DERIVATION_GAP

missing term-level interpretation
-> BLOCKED_AT_PHYSICAL_INTERPRETATION

handoff validation fails
-> BLOCKED_AT_HANDOFF_VALIDATION

renderer invoked without eligible handoff
-> RENDERER_AUTHORIZATION_DENIED
```

## Final Result Envelope

The final result envelope must include:

- `request_id`;
- overall status;
- final verdict;
- blocking status and blocking stage, if any;
- output directory;
- plan path;
- state path;
- event log path;
- skill execution manifest path;
- rendered or renderer-dispatch artifacts;
- artifact SHA summary.

## Non-Actions

The facade must not:

- perform symbolic simplification;
- invent derivation steps;
- invent physical interpretations;
- edit equations;
- promote claims;
- replace existing validators;
- duplicate the PDF renderer;
- duplicate scientific implementation;
- hard-code a scientific document independently of the existing assembler contract;
- make the renderer responsible for missing narrative content.
