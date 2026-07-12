#!/usr/bin/env python3
"""
validate_dependency_eligibility.py -- Validate dependency gate eligibility.

Evaluates whether a downstream task is eligible given upstream task
completions, artifact existence, SHA manifest validity, and human
decision resolution.  Reads a dependency gate JSON and a task registry
to determine ELIGIBLE or BLOCKED status.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


TERMINAL_VERDICTS = {"COMPLETED", "VERIFIED", "VERIFIED_WITH_CAVEAT", "FAILED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-path", required=True,
                        help="Path to dependency gate JSON.")
    parser.add_argument("--task-registry-path", required=True,
                        help="Path to task registry JSON (maps task_id -> status).")
    parser.add_argument("--state-dir", required=True,
                        help="State directory for SHA manifests and human decisions.")
    args = parser.parse_args()

    validator_name = "validate_dependency_eligibility"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []
    failing_conditions = []

    gate_path = args.gate_path
    task_registry_path = args.task_registry_path
    state_dir = os.path.abspath(args.state_dir)

    if not os.path.exists(gate_path):
        result["evidence"] = f"Gate file not found: {gate_path}"
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(gate_path) as f:
            gate = json.load(f)
    except Exception as e:
        result["evidence"] = f"Gate unparseable: {e}"
        print(json.dumps(result))
        sys.exit(1)

    if not os.path.exists(task_registry_path):
        result["evidence"] = f"Task registry not found: {task_registry_path}"
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(task_registry_path) as f:
            task_registry = json.load(f)
    except Exception as e:
        result["evidence"] = f"Task registry unparseable: {e}"
        print(json.dumps(result))
        sys.exit(1)

    all_upstream_terminal = True
    required_task_ids = gate.get("required_task_ids", [])
    upstream_states = {}
    for tid in required_task_ids:
        status = task_registry.get(tid)
        upstream_states[tid] = status
        if status not in TERMINAL_VERDICTS:
            all_upstream_terminal = False
            failing_conditions.append(f"task_{tid}_not_terminal:{status}")

    if not required_task_ids:
        errors.append("gate_has_no_required_task_ids")
        all_upstream_terminal = False

    all_artifacts_frozen = True
    required_artifacts = gate.get("required_artifacts", [])
    for art_path in required_artifacts:
        if not os.path.exists(art_path):
            all_artifacts_frozen = False
            failing_conditions.append(f"artifact_missing:{art_path}")

    if not required_artifacts:
        errors.append("gate_has_no_required_artifacts")
        all_artifacts_frozen = False

    all_shas_valid = True
    required_sha_manifests = gate.get("required_sha_manifests", [])
    for sha_path in required_sha_manifests:
        resolved = sha_path if os.path.isabs(sha_path) else os.path.join(state_dir, sha_path)
        if not os.path.exists(resolved):
            all_shas_valid = False
            failing_conditions.append(f"sha_manifest_missing:{sha_path}")
            continue
        try:
            with open(resolved) as f:
                sha_data = json.load(f)
            if not isinstance(sha_data.get("files"), dict) or len(sha_data["files"]) == 0:
                all_shas_valid = False
                failing_conditions.append(f"sha_manifest_empty_or_invalid:{sha_path}")
        except Exception:
            all_shas_valid = False
            failing_conditions.append(f"sha_manifest_unparseable:{sha_path}")

    all_human_decisions_materialized = True
    human_decision_ids = gate.get("human_decision_ids", [])
    human_registry_path = os.path.join(state_dir, "human_decision_registry.json")

    if human_decision_ids:
        if os.path.exists(human_registry_path):
            try:
                with open(human_registry_path) as f:
                    human_registry = json.load(f)
                for h_id in human_decision_ids:
                    h_entry = human_registry.get(h_id, {})
                    h_status = h_entry.get("status") if isinstance(h_entry, dict) else h_entry
                    if h_status not in ("DECIDED", "FROZEN"):
                        all_human_decisions_materialized = False
                        failing_conditions.append(f"human_decision_not_resolved:{h_id}:{h_status}")
            except Exception:
                all_human_decisions_materialized = False
                failing_conditions.append("human_decision_registry_unparseable")
        else:
            all_human_decisions_materialized = False
            failing_conditions.append("human_decision_registry_missing")

    eligibility_status = "ELIGIBLE" if not failing_conditions and not errors else "BLOCKED"

    result["details"] = {
        "gate_id": gate.get("gate_id"),
        "consumer_task_id": gate.get("consumer_task_id"),
        "all_upstream_terminal": all_upstream_terminal,
        "all_artifacts_frozen": all_artifacts_frozen,
        "all_shas_valid": all_shas_valid,
        "all_human_decisions_materialized": all_human_decisions_materialized,
        "failing_conditions": failing_conditions,
        "upstream_task_states": upstream_states,
        "eligibility_status": eligibility_status,
        "errors": errors,
    }

    if errors or failing_conditions:
        all_reasons = errors + failing_conditions
        result["evidence"] = f"BLOCKED: " + "; ".join(all_reasons)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"ELIGIBLE: all {len(required_task_ids)} upstream task(s) terminal, "
        f"all {len(required_artifacts)} artifact(s) frozen, "
        f"all {len(required_sha_manifests)} SHA manifest(s) valid, "
        f"all {len(human_decision_ids)} human decision(s) materialized"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
