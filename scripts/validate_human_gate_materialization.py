#!/usr/bin/env python3
"""
validate_human_gate_materialization.py -- Validate human gate decision materialization.

Checks that a human gate escalation JSON is valid and that the decision,
once made (DECIDED or FROZEN status), has been properly materialized:
decision artifact exists, decision field is a valid allowed response,
decided_by is non-empty, and resolved_at is set.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-path", required=True,
                        help="Path to human gate escalation JSON.")
    parser.add_argument("--decision-dir", required=True,
                        help="Directory where decision artifacts should be.")
    args = parser.parse_args()

    validator_name = "validate_human_gate_materialization"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    gate_path = args.gate_path
    decision_dir = os.path.abspath(args.decision_dir)

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

    status = gate.get("status", "")
    allowed_responses = gate.get("allowed_responses", [])
    decision_artifact_path = gate.get("decision_artifact_path", "")

    if status in ("DECIDED", "FROZEN"):
        if not decision_artifact_path:
            errors.append("DECIDED/FROZEN but no decision_artifact_path set")
        else:
            resolved_path = decision_artifact_path
            if not os.path.isabs(resolved_path):
                resolved_path = os.path.join(decision_dir, decision_artifact_path)
            if not os.path.exists(resolved_path):
                errors.append(f"decision_artifact_missing:{resolved_path}")
            elif os.path.getsize(resolved_path) == 0:
                errors.append(f"decision_artifact_empty:{resolved_path}")

        decision = gate.get("decision", "")
        if not decision:
            errors.append("DECIDED/FROZEN but decision field is empty")
        elif allowed_responses and decision not in allowed_responses:
            errors.append(f"decision_not_in_allowed_responses:{decision}:allowed:{allowed_responses}")

        decided_by = gate.get("decided_by", "")
        if not decided_by:
            errors.append("DECIDED/FROZEN but decided_by is empty")

        resolved_at = gate.get("resolved_at", "")
        if not resolved_at:
            errors.append("DECIDED/FROZEN but resolved_at is empty")
    elif status == "PENDING":
        pass
    else:
        pass

    result["details"] = {
        "gate_id": gate.get("gate_id"),
        "status": status,
        "decision_present": bool(gate.get("decision")),
        "decision_artifact_exists": (
            os.path.exists(
                decision_artifact_path
                if os.path.isabs(decision_artifact_path)
                else os.path.join(decision_dir, decision_artifact_path)
            )
            if decision_artifact_path else False
        ),
        "errors": errors,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    if status in ("DECIDED", "FROZEN"):
        result["evidence"] = (
            f"Human gate {gate.get('gate_id')} is {status}: "
            f"decision materialized, artifact present, resolved_at set"
        )
    else:
        result["evidence"] = (
            f"Human gate {gate.get('gate_id')} is {status}: "
            f"not yet in a materialized state (no validation required)"
        )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
