#!/usr/bin/env python3
"""Validate claim lifecycle artifacts against the schema and transition rules."""
import json
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
from claim_decision_engine import (
    VALID_STATES,
    is_valid_transition,
    is_terminal,
    reject_invalid_evidence,
    _AUTHORITY_TIER,
    _ARTIFACT_AUTHORITY_TIER,
    authority_tier_for_artifact_type,
)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def validate_claim_lifecycle(data):
    errors = []
    warnings = []

    if "claim_id" not in data:
        errors.append("missing_claim_id")

    state = data.get("current_state", "")
    if state not in VALID_STATES:
        errors.append(f"invalid_state: {state}")

    history = data.get("state_history", [])
    prev_state = None
    for entry in history:
        frm = entry.get("from_state")
        to = entry.get("to_state")
        if frm and to and not is_valid_transition(frm, to):
            errors.append(f"invalid_transition_in_history: {frm} -> {to} (decision: {entry.get('decision_event_id')})")
        prev_state = to

    if prev_state and prev_state != state:
        errors.append(f"history_final_state_{prev_state}_mismatches_current_state_{state}")

    artifacts = data.get("provenance_artifacts", {}).get("artifact_runs", [])
    for art in artifacts:
        if art.get("artifact_type") not in _ARTIFACT_AUTHORITY_TIER:
            errors.append(f"unknown_artifact_type: {art.get('artifact_type')}")
        sha = art.get("artifact_sha", "")
        if sha and not (len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
            errors.append(f"invalid_sha_for_{art.get('artifact_run_id')}: {sha}")

    authority = data.get("authority_level", "")
    if authority not in _AUTHORITY_TIER:
        errors.append(f"unknown_authority_level: {authority}")

    scope = data.get("scope_classification", "")
    valid_scopes = ["GENERAL_SYMBOLIC_IDENTITY", "MODEL_SPECIFIC_EQUIVALENCE",
                    "LOCAL_EXACT_IDENTITY", "BOUNDARY_APPLICABILITY"]
    if scope not in valid_scopes:
        errors.append(f"unknown_scope_classification: {scope}")

    proj = data.get("projection_context", {})
    if proj.get("is_projection"):
        if proj.get("injectivity_established") is None:
            errors.append("projection_missing_injectivity_field")
        if scope == "GENERAL_SYMBOLIC_IDENTITY" and not proj.get("injectivity_established"):
            errors.append("projection_claims_general_scope_without_injectivity")

    evidence_errors = reject_invalid_evidence(data)
    errors.extend(evidence_errors)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "claim_id": data.get("claim_id", "UNKNOWN"),
        "current_state": state,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_claim_lifecycle.py <claim.json>")
        sys.exit(1)
    data = load_json(sys.argv[1])
    result = validate_claim_lifecycle(data)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
