# Orchestration Recovery

## Recovery Identity
- **Recovery ID**: `{{RECOVERY_ID}}`
- **Orchestration ID**: `{{ORCHESTRATION_ID}}`
- **Failure Class**: `{{FAILURE_CLASS}}`
- **Failed Task ID**: `{{FAILED_TASK_ID}}`
- **Last Valid State**: `{{LAST_VALID_STATE}}`

## Recovery Objective

Reconstruct the orchestration state from repository-native artifacts and resume from the next eligible task.

## Authoritative Recovery Sources

The following repo-native files are the source of truth. Do NOT rely on conversation memory.

| File | Purpose |
|------|---------|
| `{{STATE_DIR}}/orchestration_state.json` | Current orchestration state |
| `{{STATE_DIR}}/task_registry.json` | All tasks and their statuses |
| `{{STATE_DIR}}/handoff_registry.json` | All handoffs |
| `{{STATE_DIR}}/artifact_contracts/` | Task artifact contracts |
| `{{STATE_DIR}}/sha_manifests/` | Frozen SHA manifests |
| `{{STATE_DIR}}/human_decision_registry.json` | Human decisions |
| `{{STATE_DIR}}/dependency_dag.json` | Task dependency DAG |
| `{{STATE_DIR}}/event_log.jsonl` | Append-only event log |

## Recovery Algorithm

### Step 1: Load State

```
python3 scripts/recover_orchestration_state.py \
  --state-dir "{{STATE_DIR}}" \
  --orchestration-id "{{ORCHESTRATION_ID}}"
```

### Step 2: Identify Completed Tasks

From `task_registry.json`, identify:
- `completed_task_ids`: tasks with terminal status (COMPLETED, VERIFIED)
- `active_task_ids`: tasks that may still be running
- `failed_task_ids`: tasks with FAILED or TIMED_OUT status

### Step 3: Check Active Tasks

For each active task:
1. Check if a heartbeat file exists and is recent
2. If timed out, create a recovery record (`orchestration_recovery.schema.json`)
3. Mark the task as TIMED_OUT or FAILED

### Step 4: Identify Blockers

From `orchestration_state.json`, identify all blockers:
- Missing human decisions → create/resume human gates
- Failed dependency gates → re-evaluate
- Failed tasks → check for recovery records

### Step 5: Identify Missing Human Decisions

From `human_decision_registry.json`:
- List all gates with status PENDING or PRESENTED
- Present each to the human
- Block dependent tasks

### Step 6: Identify Eligible Tasks

For each pending task:
1. Load its dependency gate
2. Re-evaluate against current state
3. If ELIGIBLE, add to `eligible_task_ids`

### Step 7: Resume

1. Update `orchestration_state.json` with current state
2. Log a RECOVERY_COMPLETED event
3. Resume with the next eligible task

## Failure Classes

| Class | Meaning | Recovery Action |
|-------|---------|-----------------|
| `SUBTASK_TIMEOUT` | Subagent exceeded time limit | Create recovery record, retry or escalate |
| `SUBTASK_CRASH` | Subagent terminated unexpectedly | Check partial artifacts, retry |
| `OUTPUT_VALIDATION_FAILURE` | Output failed contract validation | Block downstream, require repair |
| `SHA_MISMATCH` | Manifest SHA does not match file | Treat as OUTPUT_VALIDATION_FAILURE |
| `PARTIAL_ARTIFACT` | Temporary or incomplete file detected | Clear partial, retry |
| `CONTRACT_VIOLATION` | Subagent exceeded contract bounds | Block, require human review |
| `VERIFIER_REJECTION` | Independent verifier rejected | Follow repair lineage |
| `ENVIRONMENT_LOSS` | Controller session terminated | Full recovery from disk |
| `DEPENDENCY_STALL` | Upstream task stalled indefinitely | Timeout and escalate |
| `HUMAN_GATE_EXPIRY` | Human did not respond | Apply default response or escalate |
| `PARALLELISM_CONFLICT` | Unsafe parallelism detected | Serialize conflicting tasks |

## Preserved Artifacts

The following artifacts are valid and preserved:

{{#each PRESERVED_ARTIFACTS}}
- `{{path}}` (SHA: `{{sha256}}`)
{{/each}}

## Invalid or Partial Artifacts

The following must be cleaned or regenerated:

{{#each INVALID_ARTIFACTS}}
- `{{path}}`: {{issue}}
{{/each}}

## Retry/Repair Task

New task ID for retry: `{{RETRY_TASK_ID}}`

## Irreversible Actions

The following actions must NOT be automatically repeated:

{{#each IRREVERSIBLE_ACTIONS}}
- {{this}}
{{/each}}

## Resume Preconditions

Before resuming, verify:

{{#each RESUME_PRECONDITIONS}}
- [ ] {{this}}
{{/each}}

## Recovery Validation

```
python3 scripts/validate_controller_resumability.py \
  --state-dir "{{STATE_DIR}}" \
  --orchestration-id "{{ORCHESTRATION_ID}}"
```

## Recovery Status

Current recovery status: `{{RECOVERY_STATUS}}`

Transition to READY_FOR_RETRY when all preconditions are met.
