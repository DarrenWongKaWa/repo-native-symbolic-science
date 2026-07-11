# Provenance Claim and Canonical State

## Purpose
Enforce the **immutable lifecycle** for symbolic artifacts from raw ingestion through canonical promotion. This skill governs role separation (Executor vs Verifier vs Integrator), amendment-based repair (never overwrite), gated progression, integration verification, and canonical promotion. Automatic canonical promotion is FORBIDDEN. No executor may self-verify. No artifact may be promoted to canonical without human gate approval.

## Activation Conditions
This skill MUST be activated when:
- The routing skill emits `routing_target: "provenance_claim_and_canonical_state"` with `task_class: "integration"` or `task_class: "human_decision"` with `sub_class: "promote"`.
- A verified claim needs to pass through the HUMAN_GATE.
- A human explicitly requests checkpoint freezing, branch opening, merging, or superseding.
- An artifact needs its lifecycle state transitioned.
- An amendment to a previous artifact is needed.
- Provenance must be audited or validated.
- The repo state needs to be frozen as a named checkpoint.

This skill MUST NOT be activated for:
- Producing transformations, verifications, or any symbolic computation.
- Performing the actual ingestion (that belongs to `generic_raw_expression_ingestion`).
- Generating LaTeX/PDF output (that belongs to `verified_provenance_to_latex_pdf`).

## Required Inputs
1. **Lifecycle state context** (mandatory): The current state of all relevant artifacts, their statuses, and the lineage graph.
2. **Routing decision** (mandatory): The `routing_decision.json` that authorized this lifecycle operation.
3. **Artifact references** (mandatory): The specific artifacts whose lifecycle is being modified:
   - For promotion: The `claim_relation.json` from verification and all upstream artifacts.
   - For checkpoint freezing: The set of artifacts to include in the checkpoint.
   - For branching: The checkpoint to branch from.
   - For superseding: The artifact to be superseded and the superseding artifact.
4. **Human gate decision** (mandatory for promotion gates): The human's explicit decision record.
5. **Role assertion** (mandatory for all operations): Confirmation of the agent's role (Executor, Verifier, Integrator, Human, Auditor).
6. **Repo-level provenance registry** (mandatory): The current provenance tree.

## Required Output Directory
```
skills/provenance_claim_and_canonical_state/output/{operation_id}/
```
Where `{operation_id}` is determined by the operation type and the artifacts involved.

## Required Output Artifacts

### 1. lifecycle_event.json (always produced)
```json
{
  "event_id": "string",
  "event_type": "HUMAN_GATE_PASS | HUMAN_GATE_FAIL | CHECKPOINT_FREEZE | BRANCH_OPEN | BRANCH_MERGE | SUPERSEDE | AMENDMENT | CANONICAL_PROMOTION | CANONICAL_DEMOTION | INTEGRATION_VERIFY",
  "event_timestamp": "string (ISO 8601)",
  "event_agent": "string",
  "event_agent_role": "EXECUTOR | VERIFIER | INTEGRATOR | HUMAN | AUDITOR",
  "affected_artifacts": [
    {
      "artifact_id": "string",
      "artifact_type": "RAW_OBJECT | NORMALIZED_PARENT | CHILD_EXPRESSION | CANDIDATE_TRANSFORMED | CLAIM_RELATION | CHECKPOINT",
      "previous_status": "string",
      "new_status": "string",
      "transition_valid": true | false
    }
  ],
  "gate_conditions": [
    {
      "condition_id": "string",
      "condition_description": "string",
      "condition_met": true | false,
      "evidence_ref": "string (artifact that satisfies this condition)"
    }
  ],
  "human_decision_ref": "string | null (reference to human decision record)",
  "role_separation_valid": true | false,
  "preconditions_check": "PASS | FAIL",
  "postconditions_check": "PASS | FAIL | NOT_YET_CHECKED",
  "caveats": ["string"]
}
```

### 2. lifecycle_audit_log.json (always produced, append-only)
An append-only log of ALL lifecycle events in the repo. Each entry is a `lifecycle_event.json` object. This file is the single source of truth for artifact state transitions.

### 3. checkpoint_manifest.json (conditional — produced for CHECKPOINT_FREEZE events)
```json
{
  "checkpoint_id": "string",
  "checkpoint_name": "string (human-readable name)",
  "checkpoint_description": "string",
  "checkpoint_timestamp": "string (ISO 8601)",
  "frozen_artifacts": [
    {
      "artifact_id": "string",
      "artifact_type": "string",
      "artifact_sha256": "string",
      "artifact_status_at_freeze": "string",
      "artifact_file_path": "string"
    }
  ],
  "parent_checkpoint": "string | null (previous checkpoint this builds on)",
  "derivation_branch": "string",
  "ready_for_branch": true | false
}
```

### 4. branch_manifest.json (conditional — produced for BRANCH_OPEN events)
```json
{
  "branch_id": "string",
  "branch_name": "string",
  "source_checkpoint_id": "string",
  "branch_purpose": "string",
  "branch_created_timestamp": "string (ISO 8601)",
  "branch_status": "ACTIVE | MERGED | ABANDONED",
  "inherited_artifacts": ["string (artifact_ids)"],
  "branch_specific_artifacts": ["string (initially empty)"]
}
```

### 5. canonical_registry.json (always maintained)
A registry of all artifacts that CURRENTLY hold CANONICAL status:
```json
{
  "canonical_entries": [
    {
      "artifact_id": "string",
      "artifact_type": "string",
      "canonical_since": "string (ISO 8601)",
      "canonical_until": "string | null (null if still canonical)",
      "promotion_event_id": "string",
      "superseded_by": "string | null",
      "claim_summary": "string"
    }
  ]
}
```

### 6. amendment_record.json (conditional — produced for AMENDMENT events)
```json
{
  "amendment_id": "string",
  "original_artifact_id": "string (the artifact being amended, NOT modified)",
  "amended_artifact_id": "string (the NEW artifact with the amendment)",
  "amendment_reason": "string",
  "amendment_type": "CORRECTION | CLARIFICATION | EXTENSION | RESTRICTION",
  "what_changed": "string",
  "what_unchanged": "string",
  "downstream_impact": ["string (artifacts that need re-evaluation)"],
  "original_preserved": true
}
```

## Lifecycle States (The Immutable Pipeline)
The full lifecycle of a symbolic artifact from creation to canonical status:

```
PLAN → EXECUTE → VERIFY → HUMAN GATE → INTEGRATE → INTEGRATION VERIFY → CANONICAL PROMOTION
```

### Stage Details

#### 1. PLAN
- **Artifact status**: Not yet materialized.
- **Gate condition**: A routing decision has classified the task and authorized execution.
- **Role**: Planner (human or agent).
- **Output**: Routing decision, task specification.

#### 2. EXECUTE
- **Artifact status**: `RAW_INGESTED`, `NORMALIZED_PARENT`, `CANDIDATE_TRANSFORMED` (depending on the task).
- **Gate condition**: Execution completed successfully with all required output artifacts.
- **Role**: Executor (agent).
- **Output**: The executable artifact (e.g., `candidate_transformation.json`).
- **Forbidden**: Self-verification. The Executor MUST NOT claim the output is verified.

#### 3. VERIFY
- **Artifact status**: `CLAIM_RELATION` established.
- **Gate condition**: Verification completed by a DIFFERENT agent from the Executor.
- **Role**: Verifier (agent, separate from Executor).
- **Output**: `claim_relation.json`, verification report.
- **Forbidden**: Executor verification. If the same agent both executes and verifies, the gate is FAILED.

#### 4. HUMAN GATE
- **Artifact status**: `HUMAN_GATE_PASSED` or `HUMAN_GATE_FAILED`.
- **Gate condition**: Human scientist reviews the verification report, claim relation, and transformation trace, and explicitly approves or rejects.
- **Role**: Human (scientist). Only the human may pass this gate.
- **Required evidence**: `claim_relation.json` with `symbolic_equality_claimed: true`, full provenance chain, all counterexample search results, scope audit.
- **Forbidden**: Chat-only promotion. The human's decision must be formally recorded (not just "looks good" in a chat message).

#### 5. INTEGRATE
- **Artifact status**: `INTEGRATED`.
- **Gate condition**: The verified, human-approved artifact is frozen into the provenance tree, linked to its dependencies, and registered for downstream use.
- **Role**: Integrator (agent or human).
- **Output**: `lifecycle_event.json` with `event_type: INTEGRATION_VERIFY`.
- **Required**: All upstream dependencies must be integrated or explicitly waived. The artifact must not conflict with existing canonical entries.

#### 6. INTEGRATION VERIFY
- **Artifact status**: `INTEGRATION_VERIFIED`.
- **Gate condition**: Post-integration checks confirm that the integrated artifact does not break the provenance tree, does not create circular dependencies, and satisfies all regression targets.
- **Role**: Integrator (ideally a different agent from the one who performed INTEGRATE, but minimum: explicit self-audit with recorded checks).
- **Output**: Integration verification report.

#### 7. CANONICAL PROMOTION
- **Artifact status**: `CANONICAL`.
- **Gate condition**: All previous gates passed. Human explicitly authorizes canonical status. The artifact is registered in `canonical_registry.json`.
- **Role**: Human (scientist) authorizes; Integrator (agent) executes the promotion.
- **Forbidden**: Automatic promotion. No agent may promote to CANONICAL without explicit human authorization.
- **Effect**: The artifact is now the "source of truth" for its claim. Future derivations may use it as an assumption. It may be superseded but never modified.

## Allowed Operations
- Record lifecycle events immutably in `lifecycle_audit_log.json`.
- Transition artifact statuses according to the lifecycle pipeline.
- Enforce gate conditions: every transition must have the required preconditions met.
- Enforce role separation: check that Executor != Verifier, and optionally Verifier != Integrator.
- Create checkpoints (freeze all current state with a name).
- Open branches from checkpoints.
- Merge branches (with conflict detection).
- Supersede artifacts (mark old as `SUPERSEDED`, not deleted).
- Create amendments (new artifact that corrects/extends an old one, preserving the original).
- Register canonical entries in `canonical_registry.json`.
- Audit the provenance tree for consistency.
- Reject transitions that violate lifecycle rules.

## Forbidden Operations
- **Automatic canonical promotion** — no agent may promote to CANONICAL without explicit human authorization recorded in a `human_decision` event.
- **Executor self-verification** — if `executor_agent == verifier_agent`, the VERIFY gate is FAILED. No exceptions.
- **Automatic supersession** — an artifact may be superseded only by explicit human instruction or by the creation of a new artifact that the human has declared supersedes it. No automatic "this is newer so it replaces the old one."
- **Overwriting artifacts in place** — repairs, corrections, and updates are amendments (new artifacts), not overwrites.
- **Chat-only promotion** — "looks good" in a chat message is NOT a valid HUMAN_GATE_PASS. The human decision must be a structured record (JSON or Markdown with explicit fields).
- **Skipping gates** — the lifecycle pipeline is linear. You cannot go from EXECUTE directly to INTEGRATE without VERIFY and HUMAN GATE.
- **Modifying canonical entries in place** — canonical entries can be superseded but never modified.
- **Deleting artifacts** — artifacts may be marked `SUPERSEDED` or `ABANDONED` but never deleted.
- **Promoting a candidate to canonical without verification and human gate** — even if the candidate "looks obviously correct."

## Semantic Blockers
The following conditions MUST block lifecycle transitions and require escalation:
1. **Missing verification**: Attempting to pass HUMAN GATE without a valid `claim_relation.json` where `symbolic_equality_claimed: true`.
2. **Executor-Verifier identity**: The Executor and Verifier are the same agent and no human waiver has been granted.
3. **Missing human decision**: Attempting CANONICAL PROMOTION without a `human_decision` event recording explicit approval.
4. **Circular provenance**: The artifact's provenance chain contains a cycle (A depends on B which depends on A).
5. **Conflict with canonical**: The artifact makes a claim that contradicts an existing CANONICAL entry, and no supersession has been authorized.
6. **Incomplete lineage**: The artifact cannot trace its full provenance back to a `RAW_INGESTED` source.
7. **Unresolved escalation**: The artifact has an associated semantic escalation that is still PENDING.
8. **Broken reconstruction**: A parent artifact's children do not reconstruct the parent (violates the normalization acceptance gate).
9. **Role violation**: An agent attempts an operation that its role is not authorized for.
10. **Fork without checkpoint**: Attempting to branch without first freezing a checkpoint.

## Role Definitions and Separation

### Executor
- **Authorized operations**: EXECUTE (produce raw objects, normalized parents, candidate transformations).
- **Forbidden operations**: VERIFY, HUMAN GATE, CANONICAL PROMOTION.
- **Cannot**: Claim `VERIFIED`, `CANONICAL`, or `INTEGRATION_VERIFIED` status.

### Verifier
- **Authorized operations**: VERIFY (produce claim relations, verification reports).
- **Forbidden operations**: EXECUTE (for the same artifact), HUMAN GATE, CANONICAL PROMOTION.
- **Cannot**: Produce candidate transformations for the artifact it is verifying.

### Integrator
- **Authorized operations**: INTEGRATE, INTEGRATION VERIFY, CHECKPOINT FREEZE, BRANCH OPEN/MERGE, SUPERSEDE, AMENDMENT.
- **Forbidden operations**: EXECUTE, VERIFY, HUMAN GATE, CANONICAL PROMOTION (promotion requires human authorization).
- **Cannot**: Create or verify symbolic content.

### Human
- **Authorized operations**: HUMAN GATE, CANONICAL PROMOTION authorization, semantic definitions, scope declarations, assumption declarations, override decisions.
- **Forbidden operations**: None (the human has ultimate authority, but the system records all decisions for audit).
- **Required**: All human decisions must be formally recorded.

### Auditor
- **Authorized operations**: Read-only audit of all artifacts, lifecycle events, and provenance.
- **Forbidden operations**: Any modification of artifacts or lifecycle state.
- **Can**: Flag inconsistencies, request human review, recommend supersession.

## Task Lifecycle
1. **RECEIVE**: Accept the lifecycle operation request and artifact references.
2. **VALIDATE_ROLE**: Confirm the requesting agent's role is authorized for the requested operation.
3. **LOAD_STATE**: Load the current lifecycle state of all affected artifacts from `lifecycle_audit_log.json`.
4. **CHECK_PRECONDITIONS**: Verify all gate conditions for the requested transition are met.
5. **CHECK_ROLE_SEPARATION**: For VERIFY gate: confirm `Executor != Verifier`.
6. **CHECK_PROVENANCE**: Verify the provenance chain is complete and acyclic.
7. **CHECK_CANONICAL_CONFLICTS**: For CANONICAL PROMOTION: verify no conflicts with existing canonical entries.
8. **DECIDE**:
   - If all checks pass → execute the transition.
   - If any check fails → HALT and record the failure. Escalate if the failure is resolvable by human action.
9. **EXECUTE_TRANSITION**: Update artifact statuses, record the lifecycle event, update `lifecycle_audit_log.json`.
10. **POSTCONDITIONS**: Verify that the transition did not introduce inconsistencies.
11. **UPDATE_REGISTRIES**: Update `canonical_registry.json`, `checkpoint_manifest.json`, or `branch_manifest.json` as needed.
12. **LOG**: Append the event to `lifecycle_audit_log.json`.

## Checkpoint Protocol
A checkpoint freezes the state of all specified artifacts at a moment in time:
1. A checkpoint is identified by `checkpoint_id` and has a human-readable `checkpoint_name`.
2. All artifacts in the checkpoint are recorded with their `sha256` and `status_at_freeze`.
3. Checkpoints are immutable — once frozen, they cannot be modified.
4. A checkpoint serves as the basis for opening a branch.
5. The `parent_checkpoint` field creates a chain of checkpoints (a checkpoint lineage).
6. Checkpoints are referenced by downstream skills (e.g., `verified_provenance_to_latex_pdf` can generate output from a checkpoint).

## Branch Protocol
A branch is an isolated derivation workspace:
1. Every branch is rooted at a checkpoint.
2. A branch inherits all artifacts from its source checkpoint.
3. A branch may create its own artifacts without affecting the mainline.
4. A branch may be MERGED into the mainline (or into another branch) after verification and human gate.
5. A branch merge must detect conflicts with the target branch's current state.
6. A branch may be ABANDONED (marked as inactive but not deleted).

## Amendment Protocol
Amendments are the mechanism for repairing or extending artifacts without overwriting:
1. An amendment creates a NEW artifact (new `artifact_id`), never modifying the original.
2. The original artifact is preserved with its original `sha256` and status.
3. The amendment record (`amendment_record.json`) links the original and amended artifacts.
4. The amendment specifies what changed and what remains unchanged.
5. Downstream artifacts that depended on the original may need re-evaluation.
6. If the original was CANONICAL, the amended artifact must go through the full lifecycle (VERIFY → HUMAN GATE → ... → CANONICAL PROMOTION) to also become CANONICAL.

## Supersession Protocol
Supersession is how canonical artifacts are replaced:
1. A superseding artifact must have passed through the full lifecycle and achieved CANONICAL status.
2. The superseded artifact's `canonical_until` is set to the timestamp of the superseding artifact's promotion.
3. The superseded artifact remains in the provenance tree — it is not deleted.
4. The supersession is recorded as a lifecycle event.

## Relation / Claim Types
This skill produces administrative claims about artifact state:
- `LIFECYCLE_TRANSITION`: Artifact X transitioned from status A to status B.
- `HUMAN_GATE_PASSED`: The human has approved the transition of a verified claim.
- `HUMAN_GATE_FAILED`: The human has rejected the transition.
- `CANONICAL`: The artifact is the current source of truth for its claim.
- `SUPERSEDED`: The artifact was previously canonical but has been replaced.
- `AMENDED`: A new artifact amends this one.
- `CHECKPOINT_FROZEN`: A named checkpoint has been created.
- `BRANCH_OPENED/MERGED/ABANDONED`: Branch lifecycle events.

## Artifact Contract
- `lifecycle_audit_log.json` MUST be append-only. Existing entries MUST NOT be modified.
- Every lifecycle transition MUST be recorded as a separate event with a unique `event_id`.
- `canonical_registry.json` MUST contain exactly one entry per currently canonical artifact.
- `checkpoint_manifest.json` MUST list all frozen artifacts with their SHA-256.
- `amendment_record.json` MUST preserve the original artifact reference — the original MUST still exist.
- All timestamps MUST be ISO 8601 UTC.
- `role_separation_valid` MUST be `true` for VERIFY and CANONICAL PROMOTION events (unless a HUMAN_OVERRIDE with explicit waiver is recorded).

## Downstream Eligibility
An artifact with CANONICAL status is eligible for:
- Use as an assumption in future derivations (Level C transformations).
- Inclusion in LaTeX/PDF output as a "final result."
- Citation in the provenance manifest as a source of truth.
- Use as a regression target for future transformations.

An artifact with INTEGRATED status but NOT canonical may be used as:
- Input for further verification.
- An intermediate result in the derivation DAG.
- Supporting material in reports (with INTEGRATED status label).

## Human Escalation Behavior
- **Gate rejection**: If the human rejects at HUMAN GATE, the system records HUMAN_GATE_FAILED with the human's reason. The artifact stays at VERIFIED (or lower) status. The human may: request a different transformation approach (branch), revise assumptions, or abandon the claim.
- **Gate approval**: If the human approves, the system records HUMAN_GATE_PASSED and proceeds to INTEGRATE.
- **Role conflict**: If Executor == Verifier and no separate verifier is available, the human may either: provide a separate verifier, act as the verifier themselves (HUMAN_AS_VERIFIER override), or waive the role separation requirement with reduced confidence (recorded as a caveat).
- **Canonical conflict**: If a new claim conflicts with an existing CANONICAL entry, the system presents both to the human: the existing canonical entry, the new claim, the nature of the conflict, and asks the human to resolve (supersede old, reject new, or clarify scope to show they don't actually conflict).
- **Timeout**: There is no timeout on human decisions for canonical promotion. Scientific correctness is not time-sensitive.

## Interaction with Other Skills
- **Receives from**: ALL other skills (as the central lifecycle authority).
- **Feeds into**: `verified_provenance_to_latex_pdf` (only CANONICAL and INTEGRATED artifacts may appear in final output).
- **Referenced by**: ALL other skills (for current status of artifacts).
- **Maintains**: `lifecycle_audit_log.json` (the single source of truth for all artifact states).
- **Escalates to**: `human_scientist_semantic_escalation` (when human decision is needed).

## Error Handling
- **Transition preconditions not met**: Reject the transition. Record the failed attempt in the audit log. Return the list of unmet preconditions.
- **Duplicate event_id**: Reject the event. This indicates a logic error or replay attempt.
- **Artifact not found**: Reject the transition. The referenced artifact does not exist in the provenance tree.
- **Provenance cycle detected**: Halt. Flag the cycle. This is a CRITICAL error — the provenance tree is corrupted. Escalate to human immediately.
- **Canonical registry inconsistency**: If `canonical_registry.json` contains entries that don't match `lifecycle_audit_log.json`, halt and flag for audit.
- **Immutable file modified**: If `lifecycle_audit_log.json` has been modified (SHA mismatch since last read), halt. This indicates external tampering.
