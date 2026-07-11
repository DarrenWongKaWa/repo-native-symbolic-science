# Human Scientist Semantic Escalation

## Purpose
When scientific meaning is missing, ambiguous, or underspecified, this skill creates **structured human information requests** instead of guessing. It is the ONLY mechanism by which the system may request semantic input from the human scientist. Every semantic gap must be precisely characterized, traced to the specific blocked claim, and presented with clear evidence of what was searched and why it was not found. This skill never infers, guesses, or completes missing information.

## Activation Conditions
This skill MUST be activated when:
- Any downstream skill (ingestion, normalization, transformation, verification, integration) encounters a scientific semantic gap that it cannot resolve automatically.
- The routing skill (`scientific_symbolic_repo_entry`) emits `routing_target: "human_scientist_semantic_escalation"` with `task_class: "human_decision"` and `sub_class: "semantic_define"`.
- A downstream skill detects: missing index domain, undefined symbol semantics, ambiguous summation convention, unknown symmetry property, missing boundary condition, underspecified operator definition, or any other scientifically meaningful gap.
- The system needs to ask the human about matrix-element definitions, bra/ket orientation, external-index roles, Taylor prefactors, source operator signs, or source authority (the h1/h2/h3 regression cases).
- A verification task discovers that a claim depends on an assumption that the human has not explicitly stated.

This skill MUST NOT be activated for:
- Syntactic issues (e.g., unparseable expression — this is handled by the ingestion skill).
- Purely operational issues (e.g., missing file, toolchain failure).
- Requests that can be automatically resolved by consulting the adapter or repo-level conventions.
- Requests where the missing information can be inferred from a prior human declaration already recorded in the provenance system.

## Required Inputs
1. **Caller context** (mandatory): The full context from the downstream skill that triggered the escalation, including:
   - `caller_skill`: Which skill raised the escalation.
   - `caller_task_id`: The task that is blocked.
   - `blocked_claim`: What claim or operation is blocked.
   - `gap_description`: What is missing.
   - `search_attempts`: What the caller searched or attempted before escalating.
   - `partial_results`: Any partial work that was completed before the block.
2. **Raw object reference** (mandatory if applicable): The `raw_object_id` or `child_id` of the expression being processed.
3. **Provenance context** (mandatory): The current state of the provenance tree up to the blocking point.
4. **Adapter configuration** (if available): What conventions the adapter does and does not provide.
5. **Repo-level semantic registry** (if available): Previously resolved semantic questions that may be relevant.

## Required Output Directory
```
skills/human_scientist_semantic_escalation/output/{escalation_id}/
```
Where `{escalation_id}` is a unique identifier (UUID or SHA-based) for this escalation event.

## Required Output Artifacts

### 1. human_information_request.json (always produced)
Structured JSON describing exactly what is being asked. Contains:
- `escalation_id`: Unique identifier.
- `escalation_timestamp`: ISO 8601.
- `caller_skill`: Which skill raised this.
- `caller_task_id`: The blocked task.
- `blocked_claims`: Array of claims that are blocked.
- `information_gaps`: Array of objects, each describing:
  - `gap_id`: Unique identifier for this specific gap.
  - `what_is_missing`: Precise description of the missing information.
  - `why_required`: Which claim or operation depends on this information.
  - `search_scope`: What was searched (files, registries, adapters, conventions).
  - `search_result`: `absent` (should exist but doesn't) or `not_found` (may exist but search was inconclusive) or `indeterminate` (cannot determine if it exists).
  - `requested_evidence`: Exactly what the human should provide.
  - `format_suggestion`: Suggested format for the human's response.
  - `examples`: Optional concrete examples of acceptable answers.
  - `severity`: `BLOCKER` (nothing can proceed) vs `WARNING` (some nonblocked work can continue).
- `nonblocked_work`: Array of task IDs that may continue independently of this escalation.
- `forbidden_work`: Array of task IDs or operations that remain forbidden until this is resolved.
- `escalation_rationale`: Narrative justification for why this cannot be auto-resolved.

### 2. human_information_request.md (always produced)
Human-readable Markdown version of the request, formatted for direct presentation to the human scientist. Contains:
- A clear, jargon-minimized description of what is needed.
- The specific blocked scientific claim (with context).
- A description of where the system searched.
- An explicit call to action: "Please provide [X] in format [Y]."
- Examples of acceptable responses.
- A note about what work can continue in parallel.
- Permalink references to the structured JSON for machine consumption.

### 3. missing_semantics_registry.json (always produced)
An append-only registry of all semantic gaps that have been escalated. Each entry contains:
- `escalation_id`: Reference to the escalation.
- `gap_id`: The specific gap.
- `status`: `PENDING_HUMAN`, `RESOLVED`, `WAIVED`, `SUPERSEDED`, `CANCELLED`.
- `resolution`: The human's response (if resolved).
- `resolution_timestamp`: When the human responded.
- `resolution_authority`: Who provided the resolution.
- `affected_claims`: Which claims were unblocked by the resolution.

### 4. blocked_claims.json (always produced)
A list of all claims that are currently blocked, cross-referencing:
- `claim_id`: The claim that is blocked.
- `blocking_gaps`: Which `gap_id` entries are blocking this claim.
- `block_type`: `HARD` (cannot proceed at all) vs `SOFT` (can proceed with caveats, but cannot claim VERIFIED).
- `depends_on`: Upstream claims that must be unblocked first.

### 5. allowed_continuation.json (always produced)
A list of tasks that are NOT blocked by this escalation:
- `continuable_task_ids`: Array of task IDs that may proceed.
- `caveats`: Any restrictions on what those tasks may claim until the escalation is resolved.
- `continuation_constraints`: Operations that remain forbidden even in continuable tasks.

### 6. forbidden_inferences.json (always produced)
An explicit list of inferences that the system MUST NOT make in the absence of human input. Each entry contains:
- `inference_description`: What temptation exists.
- `why_forbidden`: Why this inference would be scientifically invalid.
- `consequence_if_made`: What downstream errors this would cause.
- `blocked_by_gap_id`: Which gap prevents this inference.

### 7. requested_evidence_contract.json (always produced)
A formal specification of what evidence the human must provide:
- `evidence_type`: `definition`, `axiom`, `theorem_citation`, `experimental_bound`, `convention_choice`, `negation` (X is NOT true), `domain_restriction`.
- `formal_schema`: The expected structure of the human's response (JSON schema, formula template, or controlled vocabulary).
- `acceptance_criteria`: How the system will determine if the human's response is sufficient.
- `rejection_criteria`: What would make the response insufficient (circular definitions, contradictions with existing knowledge, underspecification).
- `binding_scope`: Which downstream tasks will be bound by the human's answer.

### 8. search_universe_record.json (always produced)
A record of what the system searched before escalating:
- `searched_registries`: List of registries consulted.
- `searched_adapters`: List of adapters consulted.
- `searched_conventions`: List of convention files consulted.
- `searched_prior_escalations`: List of prior escalation records consulted.
- `search_strategy`: How the search was conducted (keyword, structured query, etc.).
- `search_completeness`: `exhaustive` (all known sources searched) vs `heuristic` (best-effort, may have missed sources).
- `unsearched_sources`: Known sources that were NOT searched and the reason (e.g., "computationally prohibitive," "not applicable to this expression class").

## Allowed Operations
- Receive and parse the caller context from the downstream skill.
- Cross-reference the missing information against all available semantic registries, adapters, and prior escalations.
- Determine whether the information is `absent` (should exist in a specific location but doesn't) or `not_found` (might exist but wasn't locatable).
- Formulate precise, answerable questions for the human scientist.
- Generate human-readable Markdown that explains the scientific context of the gap.
- Record all gaps, blocked claims, forbidden inferences, and allowed continuations.
- Update the `missing_semantics_registry.json` with the new escalation.
- Track resolution status of each gap.
- Re-activate the blocked downstream skill when the human resolves all blocking gaps.
- Produce the h1/h2/h3 regression-specific questions about matrix-element definitions, bra/ket orientation, external-index roles, Taylor prefactors, source operator signs, and source authority.

## Forbidden Operations
- **Inferring or guessing** any semantic meaning from symbol names, nearby notation, or common conventions.
- Assuming that `g_{ab}` is a metric tensor, `R_{abcd}` is a Riemann tensor, `T_{ab}` is a stress-energy tensor, etc., based on notation alone.
- Assuming index domains from index positions alone (upper vs lower = contravariant vs covariant is NOT universal).
- Assuming summation convention applies to all repeated indices without explicit declaration.
- Assuming that an operator is linear, Hermitian, symmetric, or has any property not explicitly stated.
- Completing a definition by analogy ("this looks like the standard X, so it probably is X").
- Resolving the escalation automatically by consulting an external source (e.g., a paper, a textbook) without human authorization — only the human may provide semantic authority.
- Suppressing or skipping the escalation because the gap "seems minor" or "probably doesn't matter."
- Modifying the caller's task state directly (this skill only escalates; the caller remains responsible for resuming).

## Semantic Blockers — h1/h2/h3 Regression Special Cases
For the h1/h2/h3 regression scenarios, the following specific information MUST be requested from the human if missing:
1. **Matrix-element definitions**: The bra and ket states must be precisely defined, including normalization, phase conventions, and the Hilbert space they inhabit.
2. **Bra/ket orientation**: Which quantity enters as bra, which as ket, and whether there is an implicit Hermitian conjugate.
3. **External-index roles**: For each external index, whether it is a free index of the matrix element (in which case the expression is a tensor-valued expectation) or a label for the state (in which case the expression is a scalar for specific states).
4. **Taylor prefactors**: The coefficients of Taylor expansions around specific points must be verified against the source — the system must ask for the exact integer or rational prefactor, not infer it from pattern matching.
5. **Source operator signs**: The sign convention of operators (especially Hamiltonians, Lagrangians, and interaction terms) must be explicitly confirmed, as sign errors propagate through all subsequent derivations.
6. **Source authority**: The specific equation number, section, and version of the source document that the expression was extracted from.

## Task Lifecycle
1. **RECEIVE_ESCALATION**: Accept the caller context and blocked-claim information.
2. **INDEX_GAPS**: Assign a unique `gap_id` to each semantic gap. Classify each as `absent`, `not_found`, or `indeterminate`.
3. **SEARCH_UNIVERSE**: Consult all available registries, adapters, conventions, and prior escalations to confirm the gap cannot be auto-resolved. Record the search in `search_universe_record.json`.
4. **CLASSIFY_SEVERITY**: For each gap, determine if it is a BLOCKER (no work can proceed on the dependent claim) or WARNING (work can proceed with caveats).
5. **IDENTIFY_CONTINUATIONS**: Determine which tasks are NOT dependent on the blocked claim and may continue.
6. **IDENTIFY_FORBIDDEN_INFERENCES**: For each gap, list the inferences the system must not make.
7. **FORMULATE_REQUEST**: Write the structured JSON request and the human-readable Markdown request.
8. **WRITE_ARTIFACTS**: Produce all 8 required output files.
9. **WAIT_FOR_HUMAN**: The system pauses and presents the request to the human. No blocked task may proceed.
10. **RECEIVE_RESPONSE**: When the human responds:
    - Validate the response against `acceptance_criteria` from `requested_evidence_contract.json`.
    - If acceptable: Update `missing_semantics_registry.json` with `status: RESOLVED`, record the resolution, and signal the caller that the block is cleared.
    - If unacceptable: Emit a refined escalation explaining why the response was insufficient and what is still needed.
    - If the human waives the gap: Update with `status: WAIVED`, record the waiver rationale, and signal the caller to proceed with caveats.
    - If the human cancels: Update with `status: CANCELLED`, and signal the caller to abort the dependent claim.
11. **CLEANUP**: Once all gaps for an escalation are resolved/waived/cancelled, mark the escalation as CLOSED.

## Relation / Claim Types
This skill does NOT produce scientific claims. It produces meta-claims about the state of knowledge:
- `GAP_IDENTIFIED`: A specific semantic gap has been formally identified.
- `GAP_BLOCKING`: This gap blocks one or more specific claims.
- `GAP_RESOLVED`: The human has provided the missing information.
- `GAP_WAIVED`: The human has declared the gap irrelevant.
- `INFERENCE_FORBIDDEN`: A specific inference path is forbidden until the gap is resolved.
- `CONTINUATION_ALLOWED`: A specific task may proceed despite unresolved gaps.

## Artifact Contract
- All 8 output files MUST be produced for every escalation (no optional files except where explicitly conditional).
- `human_information_request.json` MUST contain at least one `information_gap` with a non-empty `what_is_missing` field.
- `human_information_request.md` MUST be formatted as GitHub-flavored Markdown suitable for direct display to a human.
- `missing_semantics_registry.json` MUST be append-only; existing entries MUST NOT be modified.
- `forbidden_inferences.json` MUST list at least one forbidden inference per `information_gap`.
- `requested_evidence_contract.json` MUST specify `acceptance_criteria` and `rejection_criteria` for each gap.
- All timestamps MUST be ISO 8601 UTC.

## Downstream Eligibility
A blocked task becomes eligible for resumption when:
1. All BLOCKER gaps in its `blocked_claims.json` entry are RESOLVED or WAIVED.
2. The human's resolution passes the `acceptance_criteria` specified in `requested_evidence_contract.json`.
3. The resolution is recorded in `missing_semantics_registry.json` with a valid `resolution_timestamp` and `resolution_authority`.
4. The caller skill receives an explicit UNBLOCK signal (not just "no more gaps" — the signal must be explicit).
5. If any gap was WAIVED, the caller must proceed with `caveat: HUMAN_WAIVED_GAP_{gap_id}` and must not claim certainty for claims that depend on the waived gap.

## Human Escalation Behavior
- When `human_information_request.md` is produced, it MUST be presented to the human via the opencode interface. The system must not silently wait.
- The system MUST clearly indicate which gaps are BLOCKERs and which are WARNINGs.
- The human may respond to gaps individually or in batch.
- The human may respond with: a direct answer, a reference to a document (which the system may then ingest), a request for clarification (triggering a refined escalation), a waiver, or a cancellation.
- If the human does not respond within a configurable period (default: no timeout — scientific decisions should not be rushed), the system may re-present the request once after a significant interval.
- If the human provides information that resolves some but not all gaps, the system updates the registry, clears the resolved gaps, and re-emits the request for the remaining gaps.
- The human's identity and role are recorded for audit. If the human's authority to resolve the gap is questionable (e.g., a student answering a question about a professor's conventions), this is flagged in the resolution record.

## Interaction with Other Skills
- **Receives from**: ALL other skills (ingestion, normalization, transformation, verification, integration, reporting) as the universal escalation target.
- **Feeds into**: The calling skill (via the UNBLOCK signal with resolved context).
- **Referenced by**: `provenance_claim_and_canonical_state` (escalation records are part of the provenance trail).
- **Referenced by**: `verified_provenance_to_latex_pdf` (escalation records appear in `caveat_and_residual_registry.tex`).
- **Reads from**: Repo-level semantic registries, adapter configurations, prior escalation records.
- **Updates**: `missing_semantics_registry.json` (append-only).

## Error Handling
- **Caller context incomplete**: If the caller did not provide enough context for meaningful escalation, request the caller supplement before proceeding.
- **Duplicate escalation**: If a gap with identical description to an existing PENDING gap is escalated, link the new escalation to the existing one rather than creating a duplicate.
- **Human response fails validation**: Reject with specific reasons, re-emit the request with clarification on what was insufficient.
- **Human response contradicts prior resolution**: Flag as a CONTRADICTION, escalate again asking the human to resolve the contradiction.
- **Human cancels a BLOCKER gap**: The dependent claim is aborted. The abort cascades to all downstream tasks that depend on that claim.
- **Human waives a gap that is actually critical**: The system records the waiver but may flag downstream verification results with a `HUMAN_WAIVED_CRITICAL_GAP` caveat.
