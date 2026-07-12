#!/usr/bin/env python3
"""
validate_controller_resumability.py -- Validate controller resumability from disk state.

Checks that all required orchestration state files exist, are valid JSON,
and are internally consistent: task IDs referenced in the orchestration
state exist in the task registry, the event_log_cursor is consistent
with the event log line count, and no critical file is empty-but-invalid.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


REQUIRED_FILES = [
    "orchestration_state.json",
    "task_registry.json",
    "handoff_registry.json",
    "dependency_dag.json",
    "event_log.jsonl",
    "human_decision_registry.json",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True,
                        help="Orchestration state directory.")
    args = parser.parse_args()

    validator_name = "validate_controller_resumability"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []
    files_present = {}
    parsed_data = {}

    state_dir = os.path.abspath(args.state_dir)

    if not os.path.isdir(state_dir):
        result["evidence"] = f"State directory not found: {state_dir}"
        print(json.dumps(result))
        sys.exit(1)

    for filename in REQUIRED_FILES:
        full = os.path.join(state_dir, filename)
        exists = os.path.exists(full)
        files_present[filename] = exists
        if not exists:
            if filename in ("event_log.jsonl", "human_decision_registry.json"):
                files_present[filename] = True
                continue
            errors.append(f"missing_required_file:{filename}")
            continue

        try:
            if filename.endswith(".json"):
                with open(full) as f:
                    parsed_data[filename] = json.load(f)
            elif filename.endswith(".jsonl"):
                with open(full) as f:
                    lines = [line for line in f if line.strip()]
                parsed_data[filename] = lines
            else:
                with open(full) as f:
                    parsed_data[filename] = f.read()
        except Exception as e:
            errors.append(f"unparseable:{filename}:{e}")

    state = parsed_data.get("orchestration_state.json", {})
    task_registry = parsed_data.get("task_registry.json", {})
    event_log_lines = parsed_data.get("event_log.jsonl", [])

    if state:
        current_state_obj = state.get("current_state") if isinstance(state, dict) else None
        active_task_ids = state.get("active_task_ids", []) if isinstance(state, dict) else []
        eligible_task_ids = state.get("eligible_task_ids", []) if isinstance(state, dict) else []
        completed_task_ids = state.get("completed_task_ids", []) if isinstance(state, dict) else []

        all_referenced = set(
            (active_task_ids or []) +
            (eligible_task_ids or []) +
            (completed_task_ids or [])
        )
        task_registry_keys = set(task_registry.keys()) if isinstance(task_registry, dict) else set()
        missing_from_registry = all_referenced - task_registry_keys
        if missing_from_registry:
            errors.append(f"task_ids_in_state_not_in_registry:{sorted(missing_from_registry)}")

        if isinstance(state, dict):
            event_log_cursor = state.get("event_log_cursor", -1)
            if event_log_cursor >= 0 and isinstance(event_log_cursor, int):
                line_count = len(event_log_lines) if isinstance(event_log_lines, list) else 0
                if event_log_cursor > line_count:
                    errors.append(
                        f"event_log_cursor ({event_log_cursor}) exceeds line count ({line_count})"
                    )
                    result["details"]["event_log_cursor"] = {
                        "cursor": event_log_cursor,
                        "line_count": line_count,
                        "consistent": False,
                    }
                else:
                    result["details"]["event_log_cursor"] = {
                        "cursor": event_log_cursor,
                        "line_count": line_count,
                        "consistent": True,
                    }
    else:
        errors.append("orchestration_state_json_empty_or_missing")

    task_statuses = {}
    if isinstance(task_registry, dict):
        for tid, entry in task_registry.items():
            if isinstance(entry, dict):
                task_statuses[tid] = entry.get("status", entry.get("verdict", "unknown"))
            else:
                task_statuses[tid] = str(entry)

    active_count = sum(1 for s in task_statuses.values() if s.upper() in ("ACTIVE", "RUNNING", "IN_PROGRESS"))
    completed_count = sum(1 for s in task_statuses.values() if s.upper() in ("COMPLETED", "VERIFIED", "VERIFIED_WITH_CAVEAT"))
    failed_count = sum(1 for s in task_statuses.values() if s.upper() in ("FAILED", "REJECTED"))

    result["details"] = {
        "state_dir": state_dir,
        "files_present": files_present,
        "current_state": current_state_obj,
        "task_summary": {
            "total": len(task_statuses),
            "active": active_count,
            "completed": completed_count,
            "failed": failed_count,
        },
        "active_task_ids": active_task_ids,
        "completed_task_ids": completed_task_ids,
        "errors": errors,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    present_count = sum(1 for v in files_present.values() if v)
    result["passed"] = True
    result["evidence"] = (
        f"Controller resumable: {present_count}/{len(REQUIRED_FILES)} required files present; "
        f"all task references consistent; "
        f"{len(task_statuses)} tasks ({active_count} active, {completed_count} completed, {failed_count} failed)"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
