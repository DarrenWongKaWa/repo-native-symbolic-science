#!/usr/bin/env python3
"""
validate_orch_state_transition.py -- Validate orchestration state transitions.

Checks that a proposed state transition (from -> to) is allowed according to
the hardcoded transition rules defined in the SLOOP orchestration spec,
referencing the current orchestration state on disk.

Allowed transitions are checked.  Prohibited transitions are explicitly
rejected with a specific error.  The current_state in the on-disk
orchestration_state.json is cross-checked against --from for consistency.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys

ALLOWED_TRANSITIONS = {
    "RECEIVED":                {"POLICY_LOADING", "INTENT_ROUTING"},
    "POLICY_LOADING":          {"INTENT_ROUTING"},
    "INTENT_ROUTING":          {"SEMANTIC_AUDIT"},
    "SEMANTIC_AUDIT":          {"PLANNING", "BLOCKED_HUMAN_INFORMATION"},
    "BLOCKED_HUMAN_INFORMATION": {"SEMANTIC_AUDIT"},
    "PLANNING":                {"PLAN_READY", "FAILED"},
    "PLAN_READY":              {"EXECUTION_ELIGIBLE", "FAILED"},
    "EXECUTION_ELIGIBLE":      {"EXECUTING", "PAUSED"},
    "EXECUTING":               {"EXECUTION_COMPLETE", "FAILED", "PAUSED"},
    "EXECUTION_COMPLETE":      {"VERIFICATION_ELIGIBLE", "FAILED"},
    "VERIFICATION_ELIGIBLE":   {"VERIFYING", "PAUSED"},
    "VERIFYING":               {"VERIFIED", "VERIFIED_WITH_CAVEAT", "REJECTED", "FAILED", "PAUSED"},
    "REJECTED":                {"REPAIR_REQUIRED", "FAILED"},
    "REPAIR_REQUIRED":         {"EXECUTION_ELIGIBLE", "FAILED"},
    "VERIFIED":                {"INTEGRATION_ELIGIBLE", "REPORTING", "COMPLETED", "FAILED"},
    "VERIFIED_WITH_CAVEAT":    {"HUMAN_GATE_REQUIRED", "INTEGRATION_ELIGIBLE", "FAILED"},
    "HUMAN_GATE_REQUIRED":     {"PLAN_READY", "EXECUTION_ELIGIBLE", "PAUSED", "FAILED"},
    "INTEGRATION_ELIGIBLE":    {"INTEGRATING", "PAUSED"},
    "INTEGRATING":             {"VERIFICATION_ELIGIBLE", "FAILED", "PAUSED"},
    "REPORTING":               {"VERIFICATION_ELIGIBLE", "COMPLETED", "FAILED"},
    "FAILED":                  {"RECEIVED"},
    "PAUSED":                  set(),
}

PROHIBITED_TRANSITIONS = {
    ("EXECUTING", "VERIFIED"),
    ("EXECUTION_COMPLETE", "COMPLETED"),
    ("REJECTED", "VERIFIED"),
    ("HUMAN_GATE_REQUIRED", "EXECUTING"),
    ("RECEIVED", "EXECUTING"),
    ("PLAN_READY", "COMPLETED"),
    ("VERIFYING", "COMPLETED"),
}

TERMINAL_STATES = {"COMPLETED"}


def _is_paused_resume(from_state, to_state, state_data):
    """PAUSED resumes to its previous_state recorded on disk."""
    prev = state_data.get("previous_state")
    if from_state == "PAUSED" and prev and to_state == prev:
        return True
    return False


def _is_fallback_to_failed(from_state, to_state):
    return to_state == "FAILED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", required=True, dest="from_state",
                        help="Previous orchestration state.")
    parser.add_argument("--to", required=True, dest="to_state",
                        help="Proposed next orchestration state.")
    parser.add_argument("--state-dir", required=True,
                        help="Path to orchestration state directory.")
    args = parser.parse_args()

    from_state = args.from_state
    to_state = args.to_state
    state_dir = args.state_dir
    validator_name = "validate_orch_state_transition"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}

    state_path = os.path.join(state_dir, "orchestration_state.json")
    state_data = None
    if os.path.exists(state_path):
        try:
            with open(state_path) as f:
                state_data = json.load(f)
        except Exception as e:
            result["evidence"] = f"orchestration_state.json unparseable: {e}"
            result["details"] = {"from": from_state, "to": to_state}
            print(json.dumps(result))
            sys.exit(1)
    else:
        result["evidence"] = f"orchestration_state.json not found at {state_path}"
        result["details"] = {"from": from_state, "to": to_state}
        print(json.dumps(result))
        sys.exit(1)

    if state_data.get("current_state") != from_state:
        result["evidence"] = (
            f"State file current_state ({state_data.get('current_state')}) "
            f"does not match --from ({from_state})"
        )
        result["details"] = {
            "from": from_state,
            "to": to_state,
            "disk_state": state_data.get("current_state"),
        }
        print(json.dumps(result))
        sys.exit(1)

    # Check prohibited transitions first (explicit block)
    if (from_state, to_state) in PROHIBITED_TRANSITIONS:
        result["evidence"] = (
            f"Transition {from_state} -> {to_state} is explicitly PROHIBITED"
        )
        result["details"] = {
            "from": from_state,
            "to": to_state,
            "prohibited": True,
        }
        print(json.dumps(result))
        sys.exit(1)

    # Any -> FAILED is always allowed
    if _is_fallback_to_failed(from_state, to_state):
        result["passed"] = True
        result["evidence"] = (
            f"Fallback transition {from_state} -> FAILED is allowed (any state may transition to FAILED)"
        )
        result["details"] = {"from": from_state, "to": to_state, "fallback_to_failed": True}
        print(json.dumps(result))
        sys.exit(0)

    # PAUSED resume to previous state
    if _is_paused_resume(from_state, to_state, state_data):
        result["passed"] = True
        result["evidence"] = (
            f"PAUSED resumes to previous state {state_data.get('previous_state')}"
        )
        result["details"] = {
            "from": from_state,
            "to": to_state,
            "paused_resume": True,
            "resumed_to": state_data.get("previous_state"),
        }
        print(json.dumps(result))
        sys.exit(0)

    # Terminal state check
    if from_state in TERMINAL_STATES:
        result["evidence"] = f"State {from_state} is terminal; no outgoing transitions"
        result["details"] = {"from": from_state, "to": to_state, "terminal": True}
        print(json.dumps(result))
        sys.exit(1)

    # PAUSED with no next target
    if from_state == "PAUSED":
        prev = state_data.get("previous_state")
        if prev is None:
            result["evidence"] = (
                "PAUSED with no previous_state recorded; cannot determine resume target"
            )
            result["details"] = {"from": from_state, "to": to_state, "paused_no_previous": True}
            print(json.dumps(result))
            sys.exit(1)
        result["evidence"] = (
            f"PAUSED can only resume to its previous state ({prev}), not {to_state}"
        )
        result["details"] = {
            "from": from_state,
            "to": to_state,
            "paused": True,
            "previous_state": prev,
        }
        print(json.dumps(result))
        sys.exit(1)

    # Check allowed transitions
    allowed_targets = ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state in allowed_targets:
        result["passed"] = True
        result["evidence"] = f"Transition {from_state} -> {to_state} is allowed"
        result["details"] = {"from": from_state, "to": to_state}
        print(json.dumps(result))
        sys.exit(0)

    result["evidence"] = (
        f"Transition {from_state} -> {to_state} is NOT in the allowed set. "
        f"Allowed targets from {from_state}: {sorted(allowed_targets) if allowed_targets else 'none (terminal or PAUSED)'}"
    )
    result["details"] = {
        "from": from_state,
        "to": to_state,
        "allowed_from_current": sorted(allowed_targets) if allowed_targets else [],
    }
    print(json.dumps(result))
    sys.exit(1)


if __name__ == "__main__":
    main()
