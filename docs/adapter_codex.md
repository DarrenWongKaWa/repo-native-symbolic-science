# Codex Adapter for Multi-Agent Scientific Workflow Orchestration

## Adapter Identity
- **Adapter**: `codex_adapter`
- **Version**: 1.0.0
- **Environment**: Codex
- **Purpose**: Thin adapter exposing Codex subagent capabilities for the model-neutral orchestration layer

## Scope

This adapter explains how to use Codex-specific mechanisms to implement the generic orchestration contracts. It must produce repository-native artifacts compatible with the model-neutral schemas in `schemas/`.

This adapter does NOT define scientific governance. Scientific authority remains in `AGENTS.md`, `REPO_POLICY.md`, schemas, skills, task templates, and validators.

## Discovery

To discover the orchestration skill in Codex:

1. Load `skills/multi_agent_scientific_workflow_orchestration/SKILL.md`
2. Load `AGENTS.md` for repository rules
3. Discover applicable skills from `skills/` directory
4. Load schema registry from `schemas/`

## Creating Isolated Subagents

Codex supports subagent creation via the Task tool or equivalent agent dispatch primitives.

For each orchestrated task:

1. **Create a task contract** conforming to `schemas/subagent_task_contract.schema.json`
2. **Create a role assignment** conforming to `schemas/subagent_role_assignment.schema.json`
3. **Launch the subagent** using Codex's agent/task infrastructure with:
   - The rendered task template as the prompt
   - The authorized input paths as readable files
   - The output directory as the writable target
   - The forbidden paths as exclusions

### Subagent identifier

Use the `subagent_id` from the role assignment record. Do NOT reuse the same subagent_id for executor and verifier.

### Role isolation

Key separations for Codex:
- `executor_context != verifier_context`: Launch verifier as a completely separate task, not as a continuation
- `integration_executor_context != integration_verifier_context`: Same separation
- `report_writer_context != report_verifier_context`: Same separation

## Supplying Task Contracts

Before launching a subagent, supply:

1. The rendered task template with all `{{PLACEHOLDERS}}` replaced
2. The frozen input SHA manifest
3. Authorized file paths (read-only access)
4. Output directory path (write access)
5. Forbidden paths (blocked access)

## Waiting for Results

In Codex, subagent tasks return results when complete. The controller must:

1. Wait for the subagent to reach a terminal state
2. Validate the result envelope against `schemas/subagent_result_envelope.schema.json`
3. Check all required outputs exist on disk
4. Verify all SHA-256 hashes match
5. Check for partial or temporary files

Do NOT treat a natural-language summary as a valid result envelope.

## Freezing Artifacts

After validating subagent output:

1. Generate the output SHA manifest
2. Record the manifest in `{{STATE_DIR}}/sha_manifests/`
3. Mark the task as completed in the task registry
4. Evaluate downstream dependency gates
5. Log a TASK_COMPLETED or ARTIFACT_FROZEN event

## Launching an Independent Verifier

To verify an executor's work in Codex:

1. Create a NEW task contract for the verifier (new task_id)
2. Create a NEW role assignment (new subagent_id, different from executor)
3. Set authorized inputs to the executor's frozen output artifacts (read-only)
4. Set output directory to a NEW path (separate from executor)
5. Forbid access to executor scratch files and mutable workspace
6. Launch as an isolated subagent
7. Wait for the verifier's result envelope
8. Validate and adjudicate the verdict

## Controller State

In Codex, persist controller state to disk for resumability:

- `{{STATE_DIR}}/orchestration_state.json`
- `{{STATE_DIR}}/task_registry.json`
- `{{STATE_DIR}}/handoff_registry.json`
- `{{STATE_DIR}}/human_decision_registry.json`
- `{{STATE_DIR}}/dependency_dag.json`
- `{{STATE_DIR}}/event_log.jsonl`

These files enable a new controller session in Codex to reconstruct the full orchestration state without relying on conversation memory.

## Human Gates

In Codex, present human gates using the rendered `HUMAN_GATE_RESUME.template.md`:

1. Create the human gate record
2. Present the question via the chat interface
3. Wait for a materialized decision
4. Record the decision in `human_decision_registry.json`
5. Freeze the decision artifact
6. Re-evaluate blocked dependency gates
7. Resume eligible tasks

## Compatibility Target

Same schemas, task identities, claims, artifacts, and verdict semantics as the Claude Code adapter.
