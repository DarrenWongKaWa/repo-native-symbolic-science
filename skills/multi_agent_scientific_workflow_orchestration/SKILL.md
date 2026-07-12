# Multi-Agent Scientific Workflow Orchestration

## Skill identity

- **Skill**: `multi_agent_scientific_workflow_orchestration`
- **Version**: 1.0.0
- **Role**: Main controller for autonomous multi-agent scientific workflows
- **Authority**: Model-neutral repository governance
- **Implementation**: SLOOP_ORCH_002

## Purpose

Enable one human-facing controller agent to coordinate isolated scientific subagents (planner, executor, independent verifier, repair, integration, and reporting) through frozen repository-native contracts, without the controller replacing independent verification.

## Core principle

```
one human-facing controller session != one context performing every role
```

The controller routes, schedules, and adjudicates. It must not replace independent verification.

## Required isolation

```
executor_context != verifier_context
integration_executor_context != integration_verifier_context
report_writer_context != report_verifier_context
```

Only explicit task contracts and frozen repo-native artifacts may cross role boundaries.

## Orchestration sequence

### 1. Load repository authority

Read in order:

1. `AGENTS.md`
2. `REPO_POLICY.md` (if present)
3. Discover applicable skills from `skills/` directory
4. Load skill registry and capability inventory

### 2. Classify request and construct orchestration request

Convert the natural-language request into a structured `orchestration_request.json` conforming to `schemas/orchestration_request.schema.json`.

Required fields:

- `request_id`: unique immutable identifier
- `human_scientific_goal`: natural-language statement
- `source_files`: explicit paths (SHAs frozen later)
- `requested_output`: description of output
- `scientific_adapter`: domain mapping
- `known_definitions`: authoritative definitions with SHAs
- `known_assumptions`: explicit assumptions with sources
- `allowed_operations`: enumerated allowed symbolic operations
- `forbidden_operations`: enumerated forbidden operations (disjoint from allowed)
- `human_gate_policy`: which decisions require human gates
- `verification_policy`: requirement for independent verifier
- `reporting_policy`: report generation and verification rules
- `resource_constraints`: max subagents, timeout, memory
- `preferred_backends`: backends in priority order

`scientific_invention_forbidden` must be `true` unless the human has explicitly authorized scientific invention.

### 3. Run semantic completeness audit

Before planning or execution, validate:

- All referenced definitions exist and have SHAs
- All scientific objects (indices, tensors, fields) are declared
- All assumptions are explicit
- No circular dependencies exist
- Backend capabilities match requirements

If any of the following are missing, stop and escalate to a human gate (`BLOCKED_HUMAN_INFORMATION`):

- missing scientific definitions
- ambiguous index roles
- undeclared symmetry assumptions
- undeclared boundary conditions
- undeclared integration-by-parts intent
- undeclared boundary-term removal
- undeclared limit ordering

### 4. Construct dependency DAG

Materialize a dependency DAG for the workflow:

1. Identify all required subagent tasks
2. Map dependencies between tasks
3. Create dependency gate records (`dependency_gate.schema.json`)
4. Identify safe parallel lanes
5. Mark integration points

### 5. Materialize subagent task contracts

For each task, create a frozen task contract conforming to `schemas/subagent_task_contract.schema.json`:

- `task_id`: immutable unique identifier
- `objective`: human-readable description
- `authorized_inputs`: frozen paths with SHA-256 hashes
- `required_outputs`: artifact paths that must be materialized
- `dependency_gate_ids`: gates that must pass before launch
- `allowed_actions`: explicit permitted actions
- `forbidden_actions`: explicit prohibited actions
- `claim_boundary`: what this task may and may not claim

### 6. Create role-isolated subagents

For each eligible task:

1. Validate dependency gate (all upstream tasks terminal, contract-valid, SHA-valid, human decisions materialized)
2. Create a role assignment record (`subagent_role_assignment.schema.json`)
3. Launch an isolated subagent context with the frozen task contract
4. Record a handoff (`subagent_handoff.schema.json`)
5. Log the dispatch event

**A chat message alone is never a valid handoff.** Every handoff must be a persisted JSON record.

### 7. Wait for and validate subagent results

When a subagent completes:

1. Validate the result envelope (`subagent_result_envelope.schema.json`)
2. Verify all required outputs exist on disk
3. Verify all output SHA-256 hashes match the manifest
4. Verify no temporary or partial files are present in place of required outputs
5. Validate any self-reported validation results
6. Check claims stay within the assigned claim boundary

If any check fails, block downstream eligibility. Do not infer completion from process silence or a natural-language summary.

### 8. Freeze artifacts and SHA manifest

On successful validation:

1. Generate output SHA manifest for all produced artifacts
2. Freeze the artifacts (make them immutable)
3. Record the frozen manifest in the dependency DAG
4. Evaluate downstream dependency gates

### 9. Commission independent verification

Create an independent verifier subagent:

- **New subagent identifier** — must differ from the executor identifier
- **Separate output directory** — must not share with the executor
- **Read-only access** to frozen executor artifacts
- **No access** to executor scratch files, hidden reasoning, or mutable workspace
- **May not repair** executor outputs

The verifier receives:
- The executor's frozen artifacts (read-only)
- The task contract
- The output SHA manifest
- Explicit contracts only — no undeclared assumptions

The verifier must emit a verdict in `{VERIFIED, VERIFIED_WITH_CAVEAT, REJECTED}`.

### 10. Adjudicate verifier verdicts

Process the verifier's result envelope without silent repair:

| Verdict | Controller action |
|---------|-------------------|
| `VERIFIED` | Mark task as verified. Unlock downstream eligibility. |
| `VERIFIED_WITH_CAVEAT` | Record caveats. Unlock downstream with caveat flag. May require human gate for publication-level claims. |
| `REJECTED` | Preserve rejected artifacts (immutable). Create new repair task ID. Assign repair executor. Create new verifier task. Record repair lineage. |

### 11. Materialize repair lineage when required

On `REJECTED`:

1. Preserve all rejected artifacts — do not overwrite or delete
2. Create a new `repair_executor` task with a new task ID
3. The repair executor receives:
   - Frozen original artifacts
   - Verifier's rejection evidence
   - Original task contract
   - Explicit repair instructions
4. After repair: new frozen output, new independent verifier
5. Record the full repair lineage: original → rejected → repair → verified

### 12. Handle human gates

When a human decision is required:

1. Create a human gate record (`human_gate_escalation.schema.json`)
2. Present the question with all known context
3. Block all dependent tasks
4. Pause the orchestration or mark `HUMAN_GATE_REQUIRED`
5. Wait for a materialized repo-native decision artifact
6. On receipt: freeze the decision, evaluate dependency gates, resume eligible tasks

Decision types that require human gates:

- `missing_definition`
- `index_role`
- `assumption`
- `symmetry`
- `boundary_condition`
- `integration_by_parts`
- `boundary_term_removal`
- `limit_ordering`
- `transformation_level_promotion`
- `canonical_promotion`
- `publication_claim`
- `software_or_environment_mutation`

**Continuation requires a repo-native human-decision artifact with provenance.** The controller may ask in natural language, but must not resume without a persisted decision artifact.

### 13. Recover state after controller restart

A new controller session must reconstruct from repo-native state:

1. Load `orchestration_state.json` — current state and task registry
2. Load task registry — all tasks, their states, and contracts
3. Load handoff registry — all handoffs and their completion status
4. Load artifact contracts — required and produced artifacts per task
5. Load SHA manifests — frozen input and output hashes
6. Load human-decision registry — resolved and pending gates
7. Load dependency DAG — task relationships and gate evaluations
8. Load event log — replay events to verify state consistency

Recovery algorithm:

1. Identify `completed_task_ids` from the state
2. Identify `active_task_ids` — check if subagents are still running
3. For running tasks: check heartbeat or timeout; if timed out, record recovery
4. For failed tasks: check recovery records; retry or escalate
5. Identify `blockers` — what is preventing progress
6. Identify missing human decisions
7. Identify `eligible_task_ids` — what can run next given completed upstreams
8. Resume from the next eligible task

**The system must not depend on hidden conversation memory.**

### 14. Coordinate integration and reporting

Integration eligibility:

- All required upstream lanes complete and verified
- No partial cross-consumption risk
- No unresolved shared scientific decisions
- Integration-ready contracts exist

Reporting eligibility:

- All results are verified (or verified with caveat, with human gate for caveats)
- Integration is complete (if integration was required)
- Report generator contract is ready
- Report verifier contract is ready

### 15. Return controller summary

A concise evidence-backed summary must include:

- Orchestration ID and current state
- Tasks completed / in progress / failed / blocked
- Verifier verdicts
- Human gates pending
- Downstream recommendation
- Reference to all materialized artifacts

The summary must not claim completion unless all required tasks are verified and all required artifacts exist.

## State machine

### Allowed states

```
RECEIVED → POLICY_LOADING → INTENT_ROUTING → SEMANTIC_AUDIT
SEMANTIC_AUDIT → BLOCKED_HUMAN_INFORMATION (if definitions missing)
SEMANTIC_AUDIT → PLANNING (if complete)
PLANNING → PLAN_READY
PLAN_READY → EXECUTION_ELIGIBLE (after dependency gates evaluated)
EXECUTION_ELIGIBLE → EXECUTING
EXECUTING → EXECUTION_COMPLETE
EXECUTION_COMPLETE → VERIFICATION_ELIGIBLE (after artifact validation and SHA freeze)
VERIFICATION_ELIGIBLE → VERIFYING
VERIFYING → VERIFIED
VERIFYING → VERIFIED_WITH_CAVEAT
VERIFYING → REJECTED
REJECTED → REPAIR_REQUIRED
REPAIR_REQUIRED → EXECUTION_ELIGIBLE (new repair task)
VERIFIED → INTEGRATION_ELIGIBLE (if integration required)
VERIFIED_WITH_CAVEAT → HUMAN_GATE_REQUIRED (for publication-level caveats)
VERIFIED_WITH_CAVEAT → INTEGRATION_ELIGIBLE (for non-blocking caveats)
INTEGRATION_ELIGIBLE → INTEGRATING
INTEGRATING → VERIFICATION_ELIGIBLE (integration verification)
VERIFIED → REPORTING (if no integration required)
INTEGRATION verified → REPORTING
REPORTING → VERIFICATION_ELIGIBLE (report verification)
Report verified → COMPLETED
Any state → FAILED (on unrecoverable error)
Any state → PAUSED (on human gate or controller interrupt)
PAUSED → resumes to previous state via recovery
```

### Prohibited transitions

These transitions are deterministically rejected:

```
EXECUTING → VERIFIED                    (no verification occurred)
EXECUTION_COMPLETE → COMPLETED          (no verification occurred)
REJECTED → VERIFIED                     (no repair occurred)
HUMAN_GATE_REQUIRED → EXECUTING         (missing human decision artifact)
RECEIVED → EXECUTING                    (no planning occurred)
PLAN_READY → COMPLETED                  (no execution occurred)
VERIFYING → COMPLETED                   (no verdict issued)
```

## Subagent roles

### Role definitions

Each role defines:

| Field | Description |
|-------|-------------|
| `readable_artifacts` | Paths the subagent may read |
| `writable_paths` | Paths the subagent may write |
| `permitted_tools` | Tools the subagent may use |
| `forbidden_operations` | Operations explicitly forbidden |
| `claim_authority` | Maximum claim level the subagent may assert |
| `human_gate_dependencies` | Human gates that must be resolved |
| `completion_contract` | Required outputs and envelope schema |

### Roles

| Role | Purpose | Max claim | Forbidden |
|------|---------|-----------|-----------|
| `global_planner` | Decompose request into task DAG | Plan-level | Execute, verify, promote |
| `lane_planner` | Plan a single execution lane | Plan-level | Execute, verify, promote |
| `executor` | Materialize authorized artifacts | Execution | Verify own output, promote |
| `independent_verifier` | Independently verify frozen artifacts | Verification | Repair, edit executor output |
| `repair_executor` | Repair rejected artifacts | Execution | Reuse original executor context |
| `human_gate_materializer` | Record and freeze human decisions | Human gate | Make scientific decisions |
| `integration_executor` | Integrate verified lane results | Integration | Self-verify integration |
| `integration_verifier` | Verify integration outputs | Verification | Edit integration outputs |
| `report_generator` | Produce reports from verified results | Report | Self-verify reports |
| `report_verifier` | Verify report accuracy | Verification | Edit reports |
| `supplement_writer` | Write supplementary material | Supplement | Self-review supplements |
| `supplement_reviewer` | Review supplementary material | Review | Edit supplements |

## Parallelism

### Safe parallel execution

Allowed when ALL of:

1. All inputs are frozen (SHA-valid)
2. Output paths are disjoint between concurrent tasks
3. No partial cross-consumption (no task reads another's in-progress output)
4. No unresolved shared scientific decision
5. Integration task waits for all required lanes
6. All dependency gates independently evaluate to ELIGIBLE

### Unsafe parallelism — rejected

Rejected when ANY of:

1. Output paths overlap between concurrent tasks
2. One task produces input for another running task
3. Shared mutable state exists between tasks
4. Scientific decisions affecting both lanes are unresolved
5. Dependency gate evaluation is not deterministic

## Artifact lifecycle

```
upstream completes
→ output contract validates
→ artifacts validated (exist, parse, no partial files)
→ output SHA manifest freezes
→ dependency gate evaluates
→ downstream becomes eligible
```

### Partial artifact protection

Downstream consumption is blocked when:

- upstream task is still running
- required output file is missing
- temporary file (e.g., `.tmp`, `.partial`, `.in_progress`) is present in place of required output
- JSON write is incomplete or invalid (parse fails)
- artifact contract is unsatisfied
- input or output SHA manifest is incomplete
- manifest SHA does not match actual file content
- result envelope is missing or invalid

### Write protocol

```
1. Write to task-scoped temporary paths
2. Validate all outputs (parse, schema, SHA)
3. Atomically promote/rename to final paths
4. Generate and freeze the output SHA manifest
5. Record completion in result envelope
```

## Security and least privilege

No role receives automatically:

- unrestricted shell authority
- unrestricted network access
- credential access
- private-file access
- Git commit or push permission
- canonical-state mutation permission
- scientific transformation permission

Permissions must be explicit in task contracts.

## Task templates

The controller uses these templates to construct subagent prompts:

| Template | For role |
|----------|----------|
| `templates/MULTI_AGENT_CONTROLLER.template.md` | Controller self-instruction |
| `templates/SUBAGENT_PLAN.template.md` | Planner subagent |
| `templates/SUBAGENT_EXECUTE.template.md` | Executor subagent |
| `templates/SUBAGENT_VERIFY.template.md` | Independent verifier |
| `templates/SUBAGENT_REPAIR.template.md` | Repair executor |
| `templates/SUBAGENT_INTEGRATE.template.md` | Integration executor |
| `templates/SUBAGENT_REPORT.template.md` | Report generator |
| `templates/HUMAN_GATE_RESUME.template.md` | Human gate resumption |
| `templates/ORCHESTRATION_RECOVERY.template.md` | Controller recovery |

## Schemas

All contracts conform to schemas in `schemas/`:

| Schema | Purpose |
|--------|---------|
| `orchestration_request.schema.json` | Structured request from natural language |
| `orchestration_state.schema.json` | Persistent orchestration state |
| `subagent_role_assignment.schema.json` | Least-privilege role assignment |
| `subagent_task_contract.schema.json` | Frozen task contract |
| `subagent_handoff.schema.json` | Frozen artifact-based handoff |
| `subagent_result_envelope.schema.json` | Result envelope from subagent |
| `dependency_gate.schema.json` | Dependency gate evaluation |
| `human_gate_escalation.schema.json` | Human decision gate |
| `orchestration_recovery.schema.json` | Failure recovery record |
| `orchestration_event_log.schema.json` | Append-only event log |
| `subagent_creation_policy.schema.json` | Subagent creation policy |

## Validators

The controller runs validators at specific execution points:

| Validator | When |
|-----------|------|
| `orchestration_state_transition_validator` | Every state transition |
| `role_separation_validator` | Before subagent launch |
| `handoff_completeness_validator` | After subagent completion |
| `input_sha_freezing_validator` | Before subagent launch |
| `output_contract_completion_validator` | After subagent completion |
| `partial_artifact_consumption_validator` | Before downstream eligibility |
| `dependency_eligibility_validator` | Before launching any task |
| `human_gate_materialization_validator` | Before resuming from human gate |
| `verifier_independence_validator` | Before verifier launch |
| `repair_lineage_validator` | Before repair executor launch |
| `controller_resumability_validator` | During controller recovery |

All validators return machine-readable results and nonzero exit on failure. Failure policy: fail closed, preserve evidence, log the error, block downstream eligibility.

## Adapters

### Codex and Claude Code

Thin adapter files explain environment-specific mechanics:

- How to discover the orchestration skill
- How to create role-isolated subagents
- How to supply task contracts
- How to wait for results
- How to freeze artifacts
- How to launch an independent verifier

Adapters must produce compatible repo-native contracts. They must not duplicate or override scientific governance.

Model-neutral authorities remain: `AGENTS.md`, `REPO_POLICY.md`, schemas, skills, task templates, and validators.

## Completion boundary

A successful execution may claim only:

- generic orchestration layer implemented
- schemas, templates, validators materialized
- synthetic orchestration fixtures pass
- existing public regression suites pass
- Codex and Claude Code thin adapters materialized
- executor-local sanitization checks pass

It must not claim:

- independent verification complete
- public integration complete
- documentation integration complete
- GitHub main updated
- automatic orchestration works identically in every agent environment
- human scientific gates can be skipped
