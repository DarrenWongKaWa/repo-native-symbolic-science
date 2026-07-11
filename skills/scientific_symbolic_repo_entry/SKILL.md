# Scientific Symbolic Repo Entry

## Purpose
Route human natural-language requests into one of exactly six task classes: **ingestion**, **transformation**, **verification**, **human-decision**, **integration**, or **reporting**. This skill is the sole entry point for all human-to-agent scientific interaction. It must parse, disambiguate, classify, and route the request without performing any downstream scientific work itself.

## Activation Conditions
This skill MUST be activated for ANY human natural-language request that refers to or implies:
- A symbolic expression, tensor, operator, integrand, Lagrangian, Hamiltonian, action, or equation of motion.
- A derivation, simplification, expansion, contraction, substitution, integration-by-parts, or algebraic manipulation of such an expression.
- A request involving generic_target, SLOOP, trace, index contraction, dummy-index manipulation, or tensor algebra.
- Verification, validation, auditing, or review of a symbolic result.
- Canonical state promotion, checkpoint freezing, or provenance claims.
- Generating reports, LaTeX, PDFs, or publication artifacts from symbolic results.
- Any file path that resides within or is referenced by a `.claude/skills/` directory within this repo.

This skill MUST also be activated when the human request is ambiguous and requires classification before any downstream action.

## Required Inputs
1. **Natural-language request text** (mandatory): The raw human utterance.
2. **Context snapshot** (mandatory when available): The current working directory, open files, recent git history (last 10 commits), and active branch name.
3. **Available artifact manifest** (optional but strongly recommended): A listing of all existing task artifacts, checkpoints, and provenance records currently known to the repo.
4. **Adapter configuration** (optional): Any project-specific routing rules or adapter-supplied sector definitions.
5. **Human identity / role assertion** (optional): Whether the human claims the role of scientist, reviewer, integrator, or observer.

## Required Output Directory
```
skills/scientific_symbolic_repo_entry/output/
```
This skill produces a routing decision file and, when the request is underspecified, a clarification request. It does NOT produce symbolic output.

## Required Output Artifacts
1. **routing_decision.json** — Always produced. Contains:
   - `request_id`: SHA-256 of the normalized request text + timestamp.
   - `request_text`: Quoted original request.
   - `task_class`: One of `ingestion`, `transformation`, `verification`, `human_decision`, `integration`, `reporting`.
   - `sub_class`: Finer-grained classification (see Routing Classes below).
   - `confidence`: 0.0–1.0 assessment of classification certainty.
   - `ambiguous_flags`: List of terms or phrases that caused ambiguity.
   - `missing_information`: List of information gaps that blocked a definitive classification.
   - `routing_target`: The skill name that should be activated next.
   - `routing_rationale`: Narrative justification for the chosen route.

2. **clarification_request.md** (conditional) — Produced ONLY when `missing_information` is non-empty and `confidence` < 0.9. Contains human-readable questions the human must answer before routing can proceed.

3. **routing_audit_log.json** — Append-only log of every routing decision ever made by this skill.

## Allowed Operations
- Parse the human request text for explicit task-class keywords (e.g., "ingest," "transform," "verify," "integrate," "report," "promote," "freeze," "audit").
- Compare the request against the schema of each of the six task classes.
- Detect ambiguity markers: vague nouns, missing object referents, underspecified scope, conflicting verbs, missing file paths.
- Generate a `clarification_request.md` when information is insufficient.
- Log every routing decision immutably in `routing_audit_log.json`.
- Delegate to the routed skill by emitting a structured handoff (routing_decision.json).
- Detect when the human is requesting an action for which NO skill exists and flag it as `unroutable`.
- Consult the `.claude/skills/sigma-symbolic-normal-form/SKILL.md` for repo-specific routing constraints.

## Forbidden Operations
- Performing any symbolic manipulation, simplification, verification, or transformation directly.
- Producing any symbolic output, TeX, or PDF.
- Accepting a semantically underspecified request and routing it to a downstream skill anyway ("best-effort routing").
- Bypassing the lifecycle by routing directly to CANONICAL_PROMOTION or VERIFIED status.
- Accepting a request that conflates ingestion with transformation or transformation with verification without decomposing it into separate sub-requests.
- Interpreting scientific meaning from symbol names (e.g., assuming `sigma` means conductivity without explicit definition).
- Adding missing information by guesswork.
- Routing a request to a skill that the adapter configuration has explicitly forbidden for this repo.

## Semantic Blockers
The following conditions MUST block routing and force a `clarification_request.md`:
1. **Missing object**: The human says "simplify it" or "verify that" without identifying what "it"/"that" refers to.
2. **Missing scope**: The human says "transform the expression" without specifying which transformation level (A–G) or which sub-expression.
3. **Conflicting verbs**: The human says "simplify and verify" in a single request — this must be decomposed into two separate tasks.
4. **Missing source**: The human says "ingest the file" without providing a file path or raw bytes.
5. **Undefined semantics**: The human uses a term like "the conductivity tensor" without linking it to a known symbol in the artifact manifest.
6. **Lifecycle violation**: The human asks to "promote to canonical" without referencing a prior VERIFIED state and HUMAN_GATE approval.
7. **Authority ambiguity**: The human claims an action (e.g., "I approve the gate") but their role in the system is not established.
8. **Referent ambiguity**: The human uses pronouns ("this," "that," "those terms") without disambiguation when multiple candidates exist.

## Task Lifecycle
1. **RECEIVE**: Capture the raw request text, timestamp, and context snapshot.
2. **NORMALIZE**: Strip whitespace, normalize Unicode, expand contractions, detect language.
3. **CLASSIFY**: Match against the six task-class schemas. Assign `task_class` and `sub_class`.
4. **DISAMBIGUATE**: Detect missing information. Populate `ambiguous_flags` and `missing_information`.
5. **BLOCK or ROUTE**:
   - If `missing_information` is non-empty AND `confidence` < 0.9: Emit `clarification_request.md`, write `routing_decision.json` with `routing_target: null`, log, and HALT.
   - If `confidence` >= 0.9: Write `routing_decision.json` with `routing_target` set, log, and HAND OFF to the target skill.
6. **HANDOFF**: The routing decision is written to disk. The caller (or orchestrator) reads `routing_decision.json` and activates the target skill.
7. **AUDIT**: Every decision is appended to `routing_audit_log.json` with a SHA-256 fingerprint of the decision content.

## Relation / Claim Types
This skill does not produce claims. It classifies tasks that MAY produce claims. The routing `sub_class` field identifies what kind of claim the downstream task will be eligible to make:
- `ingestion.new_raw` → downstream eligible for `RAW_INGESTED` status.
- `transformation.candidate` → downstream eligible for `CANDIDATE_TRANSFORMED` status.
- `verification.independent` → downstream eligible for `claim_relation.json` assertions.
- `human_decision.gate` → downstream eligible for `HUMAN_GATE_PASSED` status.
- `integration.freeze` → downstream eligible for checkpoint freezing.
- `reporting.generate` → downstream eligible for `latex_evidence_mapping.json`.

## Artifact Contract
- `routing_decision.json` MUST be valid JSON conforming to the schema described above.
- `routing_decision.json` MUST contain exactly one `task_class`.
- `routing_decision.json` MUST NOT contain any symbolic output.
- `clarification_request.md` MUST be formatted as GitHub-flavored Markdown.
- `routing_audit_log.json` MUST be append-only; existing entries MUST NOT be modified.
- Every entry in `routing_audit_log.json` MUST contain a `sha256` field computed over the canonical JSON serialization of the routing decision at the time it was made.

## Downstream Eligibility
A task routed by this skill is eligible for downstream execution ONLY if:
1. `routing_decision.json` exists and is valid.
2. `routing_target` is non-null.
3. The target skill is installed and its SKILL.md is loadable.
4. No `clarification_request.md` was emitted for this request (or it was subsequently resolved).
5. The routing decision has not been superseded by a later decision with the same `request_id`.
6. The human has not issued a STOP or ABORT directive before the handoff occurred.

## Human Escalation Behavior
- When `clarification_request.md` is emitted, the system MUST present it to the human and WAIT for a response. No downstream skill may be activated until the human responds.
- If the human does not respond within a configurable timeout (default: none — wait indefinitely), the system MAY re-present the clarification request once.
- If the human provides a response that resolves all `missing_information` entries, the classification step is re-run with the augmented context.
- If the human provides a response that does NOT resolve all missing information, the system MUST emit a refined `clarification_request.md` that acknowledges what was resolved and what remains missing.
- If the human explicitly says "proceed anyway" or "override," the system MUST log this as a HUMAN_OVERRIDE event with the specific missing-information items that were waived, and route the task with `override: true` and `waived_gaps: [...]` in the routing decision. Downstream skills MUST check for override flags and adjust their error behavior accordingly (typically: proceed with caveats, do not claim certainty).
- If the human says "cancel" or "abort," the routing is marked as ABORTED in the audit log and no downstream skill is activated.

## Routing Classes

### Ingestion
- `ingestion.new_raw`: A new raw expression file is provided and must be frozen, audited, and held without simplification.
- `ingestion.append`: Additional source material supplements an existing ingested expression.
- `ingestion.reingest`: A previously ingested expression is re-ingested with corrected metadata.

### Transformation
- `transformation.candidate_A` through `transformation.candidate_G`: Request to apply transformations at levels A–G.
- `transformation.candidate_unspecified`: The human wants a transformation but did not specify the level.
- `transformation.decompose`: Request to decompose an expression into child sub-expressions.

### Verification
- `verification.exact`: Request to verify an exact identity.
- `verification.bounded`: Request to verify a relation under declared assumptions.
- `verification.numerical_supporting`: Request for supporting numerical evidence (not proof).
- `verification.regression`: Request to verify that a transformation did not regress known identities.
- `verification.audit`: Request to audit an existing verification report for correctness.

### Human Decision
- `human_decision.gate_approve`: Human approves a verification gate.
- `human_decision.gate_reject`: Human rejects a verification gate.
- `human_decision.scope_clarify`: Human clarifies the scope of a claim.
- `human_decision.semantic_define`: Human provides missing semantic definitions.
- `human_decision.promote`: Human authorizes canonical promotion.
- `human_decision.override`: Human overrides a blocker.

### Integration
- `integration.freeze_checkpoint`: Freeze all current state as a named checkpoint.
- `integration.open_branch`: Open a new derivation branch from a checkpoint.
- `integration.merge`: Merge a branch into mainline.
- `integration.supersede`: Mark a previous result as superseded.

### Reporting
- `reporting.latex_pdf`: Generate traceable LaTeX and PDF output.
- `reporting.manifest`: Generate a provenance manifest without LaTeX.
- `reporting.audit_trail`: Generate a human-readable audit trail.

## Interaction with Other Skills
- This skill is the **parent** of all other skills in the repo. No other skill should be activated directly by a human without first passing through this entry point.
- The orchestrator (or human using opencode) reads `routing_decision.json` and activates the target skill with the routing decision as input context.
- If a downstream skill encounters a semantic gap that it cannot resolve, it MUST escalate back through this skill (by requesting a new `human_decision.semantic_define` route) rather than guessing.
- This skill MUST consult `skills/sigma-symbolic-normal-form/SKILL.md` for any repo-specific constraints on routing.

## Error Handling
- **Unparseable request**: If the request text cannot be parsed at all (e.g., binary data, empty string, only whitespace), classify as `unroutable` with `error: "unparseable_request"`.
- **No matching skill**: If the request is clear but no skill exists for the identified task class, classify as `unroutable` with `error: "no_matching_skill"`.
- **Conflicting with repo rules**: If the sigma-symbolic-normal-form skill forbids the requested action, classify as `unroutable` with `error: "blocked_by_repo_rules"` and cite the specific rule.
- **Internal error**: If the classification logic itself fails, emit an error log entry and HALT without routing.
