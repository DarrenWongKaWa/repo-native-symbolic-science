#!/usr/bin/env python3
"""
Validators for ENGINE_002.
Validates engine requests, capability resolution, execution truth,
normalized results, and cross-engine verification.
"""
import json
import sys
import os
import hashlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_engine_request(request: dict) -> dict:
    """Validate an engine request against its schema and policy rules."""
    errors = []
    warnings = []

    required = [
        "request_id", "source_task_id", "source_artifact", "source_sha",
        "scientific_adapter", "requested_capabilities", "requested_operation_sequence",
        "allowed_operations", "forbidden_operations", "declared_assumptions",
        "expression_scope", "expected_output_type", "requested_claim_type",
        "timeout", "memory_limit", "precision", "determinism_requirement",
        "preferred_backends", "prohibited_backends", "fallback_policy"
    ]
    for field in required:
        if field not in request:
            errors.append(f"missing_required_field: {field}")

    forbidden_ops = set(request.get("forbidden_operations", []))
    allowed_ops = set(request.get("allowed_operations", []))
    requested_ops = {o.get("operation", "") for o in request.get("requested_operation_sequence", [])}

    if forbidden_ops.intersection(requested_ops):
        errors.append("requested_forbidden_operation")

    if not allowed_ops.issuperset(requested_ops):
        warnings.append("some_requested_operations_not_in_allowed_list")

    expected = request.get("expected_output_type")
    claim = request.get("requested_claim_type")
    if expected == "EXACT_SYMBOLIC" and claim in ("numerical_regression", "high_precision_support"):
        warnings.append("exact_symbolic_output_with_numerical_claim_type_mismatch")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "request_id": request.get("request_id", "unknown")
    }


def validate_execution_truth(truth: dict) -> dict:
    """Validate execution truth artifact completeness."""
    errors = []
    required = [
        "request_id", "engine_id", "engine_version", "engine_executable",
        "input_artifacts", "input_shas", "generated_script_sha",
        "exact_command", "started_at", "completed_at", "exit_code",
        "operations_requested", "operations_observed",
        "assumptions_requested", "assumptions_observed",
        "raw_output", "raw_output_sha", "normalized_output", "normalized_output_sha",
        "warnings", "errors", "timeout_state", "memory_state", "partial_result_status"
    ]

    for field in required:
        if field not in truth:
            errors.append(f"missing_execution_truth_field: {field}")

    if truth.get("partial_result_status") == "PARTIAL" and truth.get("result_type") not in ("TIMEOUT", "EXECUTION_FAILED", "PARTIAL"):
        errors.append("partial_result_promoted_to_complete")

    if truth.get("exit_code", -1) == 0 and not truth.get("engine_version"):
        errors.append("success_without_version")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "request_id": truth.get("request_id", "unknown"),
        "engine_id": truth.get("engine_id", "unknown")
    }


def validate_normalized_result(result: dict) -> dict:
    """Validate that normalized result types are not strengthened."""
    errors = []
    warnings = []

    valid_types = [
        "EXACT_SYMBOLIC_RESULT", "EXACT_RECONSTRUCTION_PASS",
        "STRUCTURAL_REPLAY_PASS", "NUMERICAL_REGRESSION_PASS",
        "HIGH_PRECISION_SUPPORT_PASS", "COUNTEREXAMPLE_FOUND",
        "INCONCLUSIVE", "TIMEOUT", "UNSUPPORTED_CAPABILITY",
        "ENGINE_UNAVAILABLE", "EXECUTION_FAILED", "POLICY_VIOLATION",
        "POLICY_CONFIGURATION_ERROR", "UNSUPPORTED_OPERATION",
        "UNAUTHORIZED_OPERATION", "INVALID_EXPRESSION"
    ]

    result_type = result.get("result_type", "")
    if result_type not in valid_types:
        errors.append(f"invalid_result_type: {result_type}")

    if "NUMERICAL" in result_type:
        claim_elig = result.get("claim_eligibility", {})
        if claim_elig.get("eligible_for_exact_symbolic_equality"):
            errors.append("numerical_result_claims_exact_symbolic_equality")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_cross_engine_verification(verification: dict) -> dict:
    """Validate cross-engine verification claim scope."""
    errors = []
    warnings = []

    required = [
        "primary_engine_result", "secondary_engine_results",
        "comparison_method", "shared_assumptions", "expression_translation",
        "translation_loss", "exact_comparison_status",
        "structural_replay_status", "numerical_regression_status",
        "counterexample_status", "claim_scope", "maximum_authorized_claim", "caveats"
    ]
    for field in required:
        if field not in verification:
            errors.append(f"missing_field: {field}")

    if verification.get("translation_loss"):
        claim_scope = verification.get("claim_scope", {})
        if claim_scope.get("exact_cross_engine_verification_eligible"):
            errors.append("lossy_translation_with_exact_verification_claim")

    comparison = verification.get("comparison_method")
    if comparison == "NUMERICAL_REGRESSION":
        claim_scope = verification.get("claim_scope", {})
        if claim_scope.get("symbolic_equality_claim_authorized"):
            errors.append("numerical_comparison_claims_symbolic_equality")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_capability_resolution(selection: dict) -> dict:
    """Validate capability resolution artifact."""
    errors = []
    required = [
        "candidate_backends", "capability_match", "capability_gaps",
        "selected_primary_backend", "selected_supporting_backends",
        "selected_verification_backends", "selection_reason",
        "license_constraints", "availability_evidence", "fallback_path",
        "human_decision_required"
    ]
    for field in required:
        if field not in selection:
            errors.append(f"missing_field: {field}")

    primary = selection.get("selected_primary_backend")
    if primary is None and not selection.get("human_decision_required"):
        warnings = ["no_backend_selected_without_human_decision"]

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def main():
    if len(sys.argv) < 2:
        print("Usage: python validators.py <validator_type> [file.json]")
        return

    vtype = sys.argv[1]
    data = json.load(sys.stdin) if len(sys.argv) < 3 else load_json(sys.argv[2])

    if vtype == "request":
        result = validate_engine_request(data)
    elif vtype == "execution_truth":
        result = validate_execution_truth(data)
    elif vtype == "normalized_result":
        result = validate_normalized_result(data)
    elif vtype == "cross_engine":
        result = validate_cross_engine_verification(data)
    elif vtype == "capability":
        result = validate_capability_resolution(data)
    else:
        result = {"valid": False, "errors": [f"unknown_validator: {vtype}"]}

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("valid") else 1)


if __name__ == "__main__":
    main()
