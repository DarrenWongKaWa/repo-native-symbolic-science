#!/usr/bin/env python3
"""Validate session_capability_matrix.json files against the schema and policy rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

REQUIRED_ROLES = [
    "global_planner", "lane_planner", "executor",
    "independent_verifier", "human_gate_materializer",
    "integration_executor", "integration_verifier",
    "report_generator", "report_verifier"
]

def validate(matrix_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "session_capability_matrix.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(matrix_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    roles_present = {r["role"] for r in data.get("roles", [])}
    for role in REQUIRED_ROLES:
        if role not in roles_present:
            errors.append(f"Missing required role: {role}")

    if data.get("default_canonical_state_authority") is not False:
        errors.append("default_canonical_state_authority must be false in generic engine")

    executor_role = None
    verifier_role = None
    for r in data.get("roles", []):
        if r["role"] == "executor":
            executor_role = r
        if r["role"] == "independent_verifier":
            verifier_role = r

    if executor_role and verifier_role:
        exec_read = set(executor_role.get("readable_input_classes", []))
        verif_read = set(verifier_role.get("readable_input_classes", []))
        exec_write = set(executor_role.get("writable_paths", []))
        verif_write = set(verifier_role.get("writable_paths", []))

        if exec_write == verif_write:
            errors.append("Executor and verifier must have distinct writable paths (role separation)")

        if verifier_role.get("canonical_state_authority") not in [False, "recommend_only"]:
            errors.append("Verifier canonical_state_authority must be false or 'recommend_only'")

    rule_violations = []
    for r in data.get("roles", []):
        if "rewrite historical reports" not in r.get("forbidden_actions", []):
            rule_violations.append(f"{r['role']}: missing 'rewrite historical reports' in forbidden_actions")
        if "silent claim promotion" not in r.get("forbidden_actions", []):
            rule_violations.append(f"{r['role']}: missing 'silent claim promotion' in forbidden_actions")

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": rule_violations + warnings,
        "roles_present": sorted(roles_present),
        "executor_verifier_separated": executor_role is not None and verifier_role is not None and exec_write != verif_write
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_session_capability_matrix.py <matrix.json>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
