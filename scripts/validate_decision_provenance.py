#!/usr/bin/env python3
"""Validate decision provenance artifacts."""
import json
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
from claim_decision_engine import (
    VALID_STATES,
    is_valid_transition,
    check_projection_gate,
    check_local_vs_boundary_gate,
    validate_linear_system_evidence,
)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def validate_decision_event(data):
    errors = []
    warnings = []

    for field in ["decision_event_id", "claim_id", "decision_type", "from_state", "to_state", "timestamp", "authorized_by_role"]:
        if field not in data:
            errors.append(f"missing_field: {field}")

    from_s = data.get("from_state", "")
    to_s = data.get("to_state", "")
    if from_s and to_s:
        if from_s not in VALID_STATES:
            errors.append(f"invalid_from_state: {from_s}")
        if to_s not in VALID_STATES:
            errors.append(f"invalid_to_state: {to_s}")
        if not is_valid_transition(from_s, to_s):
            errors.append(f"invalid_transition: {from_s} -> {to_s}")

    valid_roles = ["executor", "independent_verifier", "integration_executor", "integration_verifier", "human_scientist"]
    if data.get("authorized_by_role") not in valid_roles:
        errors.append(f"invalid_role: {data.get('authorized_by_role')}")

    decision_type = data.get("decision_type")
    valid_types = ["promotion", "invalidation", "supersession", "stale_rejection", "rollback", "block", "unblock"]
    if decision_type not in valid_types:
        errors.append(f"invalid_decision_type: {decision_type}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_verification_result(data):
    errors = []
    for field in ["verification_id", "claim_id", "verification_method", "verdict", "timestamp", "verifier_role"]:
        if field not in data:
            errors.append(f"missing_field: {field}")

    if data.get("verdict") not in ["PASS", "FAIL", "CAVEATED_PASS", "INCONCLUSIVE"]:
        errors.append(f"invalid_verdict: {data.get('verdict')}")

    if data.get("verifier_role") not in ["independent_verifier", "integration_verifier", "human_scientist"]:
        errors.append(f"invalid_verifier_role: {data.get('verifier_role')}")

    if data.get("verifier_role") == "executor":
        errors.append("executor_cannot_be_verifier")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": []}


def validate_artifact_run(data):
    errors = []
    for field in ["artifact_run_id", "artifact_type", "authority_tier", "artifact_sha", "timestamp", "generated_by_role"]:
        if field not in data:
            errors.append(f"missing_field: {field}")

    valid_types = ["executable_replay", "frozen_machine_readable_operand", "structured_result_summary", "human_readable_report", "historical_pass_field"]
    if data.get("artifact_type") not in valid_types:
        errors.append(f"invalid_artifact_type: {data.get('artifact_type')}")

    tier = data.get("authority_tier")
    if not isinstance(tier, int) or tier < 0 or tier > 5:
        errors.append(f"invalid_authority_tier: {tier}")

    sha = data.get("artifact_sha", "")
    if not (len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
        errors.append("invalid_artifact_sha")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": []}


def validate_projection_comparison(data):
    errors = []
    for field in ["projection_id", "source_claim_id", "target_claim_id", "projection_method", "injectivity_established", "authorized_scope"]:
        if field not in data:
            errors.append(f"missing_field: {field}")

    errors.extend(check_projection_gate(data))

    return {"valid": len(errors) == 0, "errors": errors, "warnings": []}


def validate_rollback_decision(data):
    errors = []
    for field in ["rollback_id", "target_checkpoint_id", "invalidated_claim_ids", "timestamp", "authorized_by_role"]:
        if field not in data:
            errors.append(f"missing_field: {field}")

    valid_roles = ["integration_executor", "integration_verifier", "human_scientist"]
    if data.get("authorized_by_role") not in valid_roles:
        errors.append(f"invalid_rollback_role: {data.get('authorized_by_role')}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": []}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python validate_decision_provenance.py <type> <file.json>")
        print("Types: decision_event, verification_result, artifact_run, projection_comparison, rollback_decision, linear_system_evidence")
        sys.exit(1)

    vtype = sys.argv[1]
    data = load_json(sys.argv[2])

    validators = {
        "decision_event": validate_decision_event,
        "verification_result": validate_verification_result,
        "artifact_run": validate_artifact_run,
        "projection_comparison": validate_projection_comparison,
        "rollback_decision": validate_rollback_decision,
        "linear_system_evidence": validate_linear_system_evidence,
    }

    validator = validators.get(vtype)
    if validator is None:
        print(json.dumps({"valid": False, "errors": [f"unknown_type: {vtype}"]}))
        sys.exit(1)

    result = validator(data)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("valid") else 1)
