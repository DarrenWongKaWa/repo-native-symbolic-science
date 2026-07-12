#!/usr/bin/env python3
"""Validate equation_evidence_mapping.json against the schema and claim rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_CLAIM_TYPES = {
    "definition", "literal_equality", "finite_role_preserving_rename",
    "identity_under_assumptions", "pointwise_identity", "projected_identity",
    "integrated_identity", "structural_replay", "exact_reconstruction",
    "numerical_regression", "counterexample", "not_established",
    "verified_candidate", "canonical_result", "historical_result", "rejected_result"
}

VALID_OBJECT_ROLES = {"RESULT", "INTERMEDIATE", "DEFINITION", "EXPLANATORY_NOTATION", "CONJECTURE"}
VALID_CANONICAL = {"CANONICAL", "INTEGRATED", "VERIFIED", "CANDIDATE", "NOT_ESTABLISHED"}
VALID_VERDICTS = {
    "PASS_EXACT_SYMBOLIC", "PASS_EXACT_UNDER_ASSUMPTIONS",
    "PASS_NUMERICAL", "PASS_RECONSTRUCTION", "INCONCLUSIVE",
    "FAIL_COUNTEREXAMPLE", "FAIL_SYMBOLIC", "PENDING", "NOT_VERIFIED"
}
VALID_STEP_IDS = {
    "step_def_R", "step_def_AB", "step_raw_eq", "step_product_rule",
    "step_reorganize", "step_decompose", "step_project",
    "step_integ_A", "step_integ_B", "step_combine",
    "step_limit", "step_numeric", "step_interpret"
}


def validate_evidence_mapping(mapping_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "equation_evidence_mapping.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(mapping_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    claim_type = data.get("claim_type", "")
    if claim_type not in VALID_CLAIM_TYPES:
        errors.append(f"Invalid claim_type '{claim_type}'. Must be one of 16 INTERFACE CONTRACT relation types.")

    obj_role = data.get("object_role", "")
    if obj_role not in VALID_OBJECT_ROLES:
        errors.append(f"Invalid object_role '{obj_role}'.")

    canonical = data.get("canonical_status", "")
    if canonical not in VALID_CANONICAL:
        errors.append(f"Invalid canonical_status '{canonical}'.")

    verdict = data.get("verification_verdict", "")
    if verdict not in VALID_VERDICTS:
        errors.append(f"Invalid verification_verdict '{verdict}'.")

    step_id = data.get("derivation_step_id", "")
    if step_id and step_id not in VALID_STEP_IDS:
        warnings.append(f"Non-INTERFACE-CONTRACT derivation_step_id '{step_id}'.")

    if canonical == "CANONICAL":
        hd = data.get("human_decision", {})
        if hd.get("decision") != "ACCEPTED":
            errors.append("CANONICAL status requires human_decision.decision == ACCEPTED.")

    if claim_type == "pointwise_identity" and "PASS_EXACT" not in verdict:
        warnings.append("pointwise_identity claim without exact verification evidence.")

    if claim_type == "numerical_regression" and "PASS_EXACT" in verdict:
        warnings.append("numerical_regression claim with exact verification evidence; consider upgrading claim_type.")

    if verdict == "PENDING" and canonical != "NOT_ESTABLISHED":
        warnings.append(f"PENDING verification but canonical_status is '{canonical}'.")

    num_evidence = data.get("numerical_evidence", {})
    if num_evidence.get("numerical_agreement_is_not_symbolic_equality") is False:
        errors.append("numerical_agreement_is_not_symbolic_equality must be True.")

    assumptions = data.get("assumption_scope", {})
    if not assumptions.get("assumptions_required"):
        warnings.append("No assumptions_required listed. If truly no assumptions, state this explicitly.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "equation_label": data.get("equation_label", ""),
            "claim_type": claim_type,
            "verification_verdict": verdict,
            "canonical_status": canonical,
            "object_role": obj_role,
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <equation_evidence_mapping.json>")
        sys.exit(2)
    result = validate_evidence_mapping(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
