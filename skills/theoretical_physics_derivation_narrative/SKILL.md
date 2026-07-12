# Theoretical Physics Derivation Narrative

## Purpose
Construct a coherent, pedagogically sound narrative explanation of a theoretical physics derivation. This skill consumes a derivation graph, derivation steps, and physical interpretation mappings to produce a human-readable narrative that traces the derivation from starting equations through intermediate steps to the final result.

## Activation Conditions
This skill MUST be activated when:
- A supplement request requires a narrative derivation section (SEC_03 through SEC_08).
- The routing skill emits `routing_target: "theoretical_physics_derivation_narrative"`.
- A human scientist requests construction of a derivation narrative.
- A derivation graph exists and needs to be explained in prose.
- The supplementary material build skill requests narrative content.

This skill MUST NOT be activated for:
- Creating derivation steps (that belongs to `candidate_symbolic_transformation`).
- Verifying equations (that belongs to `exact_and_bounded_symbolic_verification`).
- Building the derivation graph (that belongs to `verified_artifact_to_derivation_graph`).
- Generating the final LaTeX document (that belongs to `verified_provenance_to_latex_pdf`).

## Required Inputs
1. **Derivation graph** (mandatory): A valid `derivation_graph.json` conforming to `schemas/derivation_graph.schema.json`.
2. **Derivation steps** (mandatory): Array of `derivation_step` objects for all nodes in the graph.
3. **Equation evidence mappings** (mandatory): `equation_evidence_mapping` objects for all equations.
4. **Expression presentations** (conditional): Required for long expressions; conforms to `schemas/expression_presentation.schema.json`.
5. **Physical interpretation mappings** (conditional): Required for SEC_09 interpretation section; conforms to `schemas/physical_interpretation_mapping.schema.json`.
6. **Section contract** (mandatory): `supplement_section_contract.json` specifying which sections need narrative content.
7. **Reader pathway definitions** (mandatory): To tailor narrative depth for different personas.

## Required Outputs

### 1. derivation_narrative.md (always produced)
A comprehensive Markdown document containing the full derivation narrative organized by section, with:
- Section-level introductions and conclusions.
- Step-by-step explanation of each derivation step.
- Physical motivation before each mathematical operation.
- Commentary on assumptions, caveats, and scope.
- Cross-references to equation labels from the INTERFACE CONTRACT.

### 2. section_narratives.json (always produced)
```json
{
  "narrative_id": "string",
  "graph_id": "string",
  "sections": [
    {
      "section_code": "string (from INTERFACE CONTRACT section profile)",
      "title": "string",
      "narrative_text": "string (Markdown)",
      "equations_referenced": ["string (equation labels)"],
      "reader_pathway_annotations": {
        "physics_first": "string (guidance for physics-first readers)",
        "derivation_checking": "string (guidance for derivation-checking readers)",
        "machine_reproduction": "string (guidance for machine-reproduction readers)"
      },
      "key_points": ["string"],
      "transitions": {
        "from_previous": "string",
        "to_next": "string"
      }
    }
  ],
  "narrative_flow_score": "number (0-10)"
}
```

### 3. narrative_consistency_report.json (always produced)
```json
{
  "consistency_checks": {
    "equation_labels_all_referenced": {"status": "PASS | FAIL", "missing": []},
    "step_narrative_coverage": {"status": "PASS | FAIL", "uncovered_steps": []},
    "assumption_documentation": {"status": "PASS | FAIL", "undocumented": []},
    "cross_reference_integrity": {"status": "PASS | FAIL", "broken_refs": []},
    "physical_interpretation_coverage": {"status": "PASS | FAIL", "uninterpreted": []},
    "reader_pathway_coverage": {"status": "PASS | FAIL", "gaps": []}
  },
  "overall_consistent": true
}
```

## Gates

### Gate 1: Graph Completeness
- The derivation graph must pass all validation checks.
- All nodes must have corresponding derivation steps with complete information.

### Gate 2: Narrative Coverage
- Every derivation step must be mentioned in the narrative.
- Every equation label must be referenced at least once.
- Every assumption must be explicitly stated before it is used.

### Gate 3: Physical Motivation
- Each mathematical operation must be preceded by a physical motivation.
- Integration by parts must explain what boundary terms are dropped and why.
- Projections must explain what sector is being projected onto and why.

### Gate 4: Reader Accessibility
- The narrative must support all three reader personas with annotations.
- Physics-first readers: emphasis on physical meaning, skim mathematical details.
- Derivation-checking readers: complete step-by-step with all intermediate expressions.
- Machine-reproduction readers: exact inputs, outputs, and computational steps.

### Gate 5: Self-Consistency
- The narrative must not contradict any derivation step.
- Caveats documented in derivation steps must appear in the narrative.
- Status qualifiers (UNVERIFIED, CANDIDATE) must be reflected in the narrative language.

## Forbidden Operations
- **Claiming unverified steps are verified** — the narrative language must reflect the verification status.
- **Omitting assumptions** — every assumption required by a step must be stated.
- **Adding physical interpretations without evidence** — interpretations must come from `physical_interpretation_mapping`.
- **Reordering steps** — the narrative must follow the graph's topological order.
- **Inventing intermediate equations** — only equations from the derivation steps may appear.
- **Hiding caveats** — all caveats from derivation steps must be surfaced.
- **Using different notation** — all notation must match the INTERFACE CONTRACT and derivation steps exactly.

## Output Directory
```
skills/theoretical_physics_derivation_narrative/output/{narrative_id}/
```

## Interaction with Other Skills
- **Receives from**: `verified_artifact_to_derivation_graph` (derivation graph), `physical_interpretation_and_limiting_cases` (interpretations), `long_expression_presentation_and_omission` (expression presentations).
- **Feeds into**: `supplementary_material_build_and_audit` (narrative content for supplement sections).
- **Consumes**: `derivation_graph.schema.json`, `derivation_step.schema.json`, `physical_interpretation_mapping.schema.json`, `expression_presentation.schema.json`.
- **Produces**: `derivation_narrative.md`, `section_narratives.json`, `narrative_consistency_report.json`.

## Failure Behavior
- **DERIVATION_GAP**: If the derivation graph has structural gaps that prevent a coherent narrative, produce the best narrative possible but flag the gap with explicit language: "At this point, the derivation requires a step that has not been formally established..."
- **Incomplete step information**: If a derivation step lacks `input_equation_label` or `output_equation_label`, flag it and provide the narrative without that detail, noting the omission.
- **Contradictory evidence**: If two derivation steps make contradictory claims about the same equation, halt and escalate. Do not produce a narrative that is internally inconsistent.
- **Missing physical interpretation**: If an important equation has no physical interpretation mapping, note this in the narrative ("The physical significance of this term requires further investigation") but do not block.
- **Presentation exceeds readability threshold**: If an expression has `human_readability_score < 3`, request the `long_expression_presentation_and_omission` skill to provide an alternative presentation.

## Narrative Style Guidelines

### Physics-First Tone
- Begin each section with the physical question being addressed.
- State the answer before showing the derivation.
- Use phrases like "physically, this term represents..."
- Keep mathematical detail in expandable/collapsible blocks or separate subsections.

### Derivation-Checking Tone
- State each operation explicitly: "We apply the product rule to..."
- Show the exact input and output of every transformation.
- Document index manipulations explicitly.
- Note every place where an assumption is invoked.

### Machine-Reproduction Tone
- Provide exact input expressions in computer-readable form.
- Specify all parameter values, index ranges, and summation conventions.
- Note computational complexity (term count, operation count).
- Reference the exact artifact SHA-256 for each expression.

## Section Narrative Mapping
Each section in the 14-section profile receives specific narrative treatment:

- **SEC_01_SCOPE**: Broad motivation, what question is being answered, what is and is not covered.
- **SEC_02_CONVENTIONS**: All notation definitions, index conventions, summation rules. No derivations.
- **SEC_03_STARTING_RESPONSE**: The starting expression, its physical origin, and why this form is chosen.
- **SEC_04_DECOMPOSITION**: How the expression is decomposed, what each component represents physically.
- **SEC_05_SECTORS**: Description of each sector, the physical meaning of the decomposition.
- **SEC_06_IDENTITIES**: Each identity used, why it holds, and under what assumptions.
- **SEC_07_IBP**: Integration by parts steps, boundary conditions, justification for dropping boundary terms.
- **SEC_08_FINAL_RESULT**: The final simplified expression, comparison with known results.
- **SEC_09_INTERPRETATION**: Term-by-term physical interpretation of the final result.
- **SEC_10_LIMITS**: Limiting cases, benchmark comparisons, known special cases recovered.
- **SEC_11_VALIDATION**: How the result has been validated (symbolic, numerical, reconstruction).
- **SEC_12_EVIDENCE_MAP**: Tabular mapping from equations to verification evidence.
- **SEC_13_ELECTRONIC_APPENDIX**: Long expressions, omission ledgers, computational code.
- **SEC_14_REPRODUCTION**: Exact steps to reproduce the entire derivation computationally.

## Transitions Between Sections
Each section narrative must include:
- A brief recap of where the derivation stands at the start of the section.
- A forward pointer to what the next section will accomplish.
- Explicit cross-references when a result from a previous section is used.

## Human Escalation Behavior
- **Contradictory steps**: If the derivation graph contains nodes with contradictory claims, escalate for human resolution. Do not narrate contradictions as if they are both true.
- **Missing physical insight**: If a derivation step performs a non-obvious mathematical operation without physical motivation, flag it and suggest the human provide the physical rationale.
- **Incomplete derivation**: If the graph does not reach a final result (no leaf node), produce what exists but flag the incomplete status prominently.
