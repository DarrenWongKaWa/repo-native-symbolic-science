# Claude Code Adapter for Multi-Agent Scientific Workflow Orchestration

## Adapter Identity
- **Adapter**: `claude_code_adapter`
- **Version**: 1.0.0
- **Environment**: Claude Code
- **Purpose**: Thin adapter exposing Claude Code subagent capabilities for the model-neutral orchestration layer

## Scope

This adapter explains how to use Claude Code-specific mechanisms to implement the generic orchestration contracts. It must produce repository-native artifacts compatible with the model-neutral schemas in `schemas/`.

This adapter does NOT define scientific governance. Scientific authority remains in `AGENTS.md`, `REPO_POLICY.md`, schemas, skills, task templates, and validators.

## Discovery

To discover the orchestration skill in Claude Code:

1. The orchestration skill loads automatically when orchestration is triggered
2. Load `skills/multi_agent_scientific_workflow_orchestration/SKILL.md`
3. Load `CLAUDE.md` for universal repository rules
4. Load `AGENTS.md` for Superpowers/loop discipline rules
5. Discover applicable skills from `skills/` directory
6. Load the sigma-symbolic-normal-form skill for science-specific rules (`.claude/skills/sigma-symbolic-normal-form/SKILL.md`)

## Creating Isolated Subagents

Claude Code supports subagent creation via:
- The Task tool (`subagent_type: "general"`) for isolated subagent contexts
- Each subagent starts with a fresh context and receives a task prompt
- Results are returned back to the controller

For each orchestrated task:

1. **Create a task contract** conforming to `schemas/subagent_task_contract.schema.json`
2. **Create a role assignment** conforming to `schemas/subagent_role_assignment.schema.json`
3. **Launch the subagent** using the Task tool with:
   - `subagent_type`: appropriate type (e.g., "general")
   - `description`: short task description
   - `prompt`: the rendered task template with all `{{PLACEHOLDERS}}` replaced
   - The subagent will have access to the workspace and can read/write files according to its contract

### Subagent identifier

Each Task tool invocation creates a new isolated subagent session. The controller must assign distinct `subagent_id` values in the role assignment record. Do NOT reuse the same subagent_id for executor and verifier.

### Role isolation

Key separations for Claude Code:
- `executor_context != verifier_context`: Launch verifier as a completely new Task, not a continuation or `task_id` resume
- `integration_executor_context != integration_verifier_context`: Same separation
- `report_writer_context != report_verifier_context`: Same separation

### Context rules for Claude Code

- A fresh Task starts with an empty conversation history — it relies entirely on the prompt and accessible files
- The controller prompt must include all necessary context (file paths, SHAs, instructions)
- No hidden conversation state leaks between executor and verifier

## Supplying Task Contracts

Before launching a subagent via Task tool, supply:

1. The rendered task template with all `{{PLACEHOLDERS}}` replaced
2. The frozen input SHA manifest embedded in the prompt
3. Explicit file paths to read (the subagent can Read authorized files)
4. Output directory path (the subagent can Write to authorized paths)
5. Explicit forbidden paths in the prompt

## Waiting for Results

Claude Code Task tool returns results when the subagent completes. The controller must:

1. Wait for the Task to return its result
2. Parse the result for the result envelope path
3. Read and validate the result envelope against `schemas/subagent_result_envelope.schema.json`
4. Check all required outputs exist on disk
5. Verify all SHA-256 hashes match
6. Check for partial or temporary files

Do NOT treat the Task tool's text response as a valid result envelope. The subagent must materialize `result_envelope.json` on disk.

## Freezing Artifacts

After validating subagent output:

1. Generate the output SHA manifest using: `python3 scripts/generate_sha_manifest.py --dir {{OUTPUT_DIRECTORY}}`
2. Record the manifest in `{{STATE_DIR}}/sha_manifests/`
3. Mark the task as completed in the task registry
4. Evaluate downstream dependency gates
5. Log a TASK_COMPLETED or ARTIFACT_FROZEN event to the event log

## Launching an Independent Verifier

To verify an executor's work in Claude Code:

1. Create a NEW task contract for the verifier (new `task_id`)
2. Create a NEW role assignment (new `subagent_id`, different from executor)
3. Set authorized inputs to the executor's frozen output artifacts (read-only)
4. Set output directory to a NEW path (separate from executor)
5. In the prompt, explicitly forbid reading from executor scratch/tmp directories
6. Launch as a separate Task tool invocation (do NOT use `task_id` resume)
7. Wait for the verifier's result envelope
8. Validate and adjudicate the verdict

### Verifier-specific instructions

The verifier prompt (from `SUBAGENT_VERIFY.template.md`) must include:
- The exact paths to executor's frozen artifacts (read-only)
- The SHA manifests to verify against
- The explicit claim boundary to check
- Instructions to NOT edit or repair executor outputs

## Controller State

In Claude Code, persist controller state to disk for resumability:

- `{{STATE_DIR}}/orchestration_state.json`
- `{{STATE_DIR}}/task_registry.json`
- `{{STATE_DIR}}/handoff_registry.json`
- `{{STATE_DIR}}/human_decision_registry.json`
- `{{STATE_DIR}}/dependency_dag.json`
- `{{STATE_DIR}}/event_log.jsonl`

These files enable a new Claude Code session to reconstruct the full orchestration state without relying on conversation memory. Use `python3 scripts/recover_orchestration_state.py --state-dir {{STATE_DIR}}` to load.

## Human Gates

In Claude Code, present human gates using the rendered `HUMAN_GATE_RESUME.template.md`:

1. Create the human gate record conforming to `schemas/human_gate_escalation.schema.json`
2. Present the question via the chat interface
3. Wait for a materialized decision (a file written by the human or an explicit instruction)
4. Record the decision in `human_decision_registry.json`
5. Freeze the decision artifact with a SHA
6. Re-evaluate blocked dependency gates using: `python3 scripts/validate_dependency_eligibility.py --gate-id {{GATE_ID}}`
7. Resume eligible tasks

## Compatibility Target

Same schemas, task identities, claims, artifacts, and verdict semantics as the Codex adapter.
