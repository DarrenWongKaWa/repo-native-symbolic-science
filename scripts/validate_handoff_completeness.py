#!/usr/bin/env python3
"""
validate_handoff_completeness.py -- Validate a subagent handoff record.

Checks that a handoff JSON file exists, parses correctly, and satisfies
the subagent_handoff.schema.json requirements.  Includes an age check
for PENDING handoffs older than 24 hours (warning, still passes).

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys
import time


VALID_COMPLETION_STATUSES = {"PENDING", "ACCEPTED", "RUNNING", "COMPLETED", "FAILED",
                              "TIMED_OUT", "REJECTED"}

REQUIRED_FIELDS = [
    "handoff_id",
    "parent_agent",
    "child_agent",
    "task_id",
    "role",
    "authorized_input_paths",
    "authorized_input_shas",
    "forbidden_inputs",
    "required_outputs",
    "output_directory",
    "claim_boundary",
    "deadline_or_timeout",
    "completion_status",
]

PENDING_WARN_SECONDS = 24 * 60 * 60


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-path", required=True,
                        help="Path to handoff JSON file.")
    args = parser.parse_args()

    validator_name = "validate_handoff_completeness"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []
    warnings = []
    handoff_path = args.handoff_path

    if not os.path.exists(handoff_path):
        result["evidence"] = f"Handoff file not found: {handoff_path}"
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(handoff_path) as f:
            handoff = json.load(f)
    except Exception as e:
        result["evidence"] = f"Handoff file unparseable: {e}"
        result["details"] = {"path": handoff_path}
        print(json.dumps(result))
        sys.exit(1)

    for field in REQUIRED_FIELDS:
        if field not in handoff:
            errors.append(f"missing_required_field:{field}")
        elif isinstance(handoff[field], str) and not handoff[field]:
            errors.append(f"empty_required_field:{field}")
        elif isinstance(handoff[field], list) and len(handoff[field]) == 0 and field in ("authorized_input_paths", "required_outputs"):
            errors.append(f"empty_list_field:{field}")

    authorized_input_shas = handoff.get("authorized_input_shas", {})
    if not isinstance(authorized_input_shas, dict) or len(authorized_input_shas) == 0:
        errors.append("authorized_input_shas_is_empty_or_not_dict")

    required_outputs = handoff.get("required_outputs", [])
    if not isinstance(required_outputs, list) or len(required_outputs) == 0:
        errors.append("required_outputs_is_empty_or_not_list")

    completion_status = handoff.get("completion_status", "")
    if completion_status not in VALID_COMPLETION_STATUSES:
        errors.append(f"invalid_completion_status:{completion_status}")

    if completion_status == "PENDING":
        created_at = handoff.get("created_at")
        if created_at:
            try:
                import datetime
                if created_at.endswith("Z"):
                    created_at = created_at[:-1] + "+00:00"
                created_dt = datetime.datetime.fromisoformat(created_at)
                age = time.time() - created_dt.timestamp()
                if age > PENDING_WARN_SECONDS:
                    age_hours = age / 3600
                    warnings.append(
                        f"Handoff PENDING for {age_hours:.1f}h (>24h); still passes"
                    )
            except Exception:
                pass

    result["details"] = {
        "handoff_id": handoff.get("handoff_id"),
        "completion_status": completion_status,
        "num_input_shas": len(authorized_input_shas),
        "num_required_outputs": len(required_outputs),
        "errors": errors,
    }

    if warnings:
        result["details"]["warnings"] = warnings

    if errors:
        result["evidence"] = "; ".join(errors)
        if warnings:
            result["evidence"] += " | WARNINGS: " + "; ".join(warnings)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = f"Handoff {handoff.get('handoff_id')} passes all completeness checks"
    if warnings:
        result["evidence"] += " (with warnings: " + "; ".join(warnings) + ")"
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
