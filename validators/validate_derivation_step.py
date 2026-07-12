#!/usr/bin/env python3
"""Validate derivation_step.json against the schema and INTERFACE CONTRACT rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_STEP_IDS = {
    "step_def_R", "step_def_AB", "step_raw_eq", "step_product_rule",
    "step_reorganize", "step_decompose", "step_project",
    "step_integ_A", "step_integ_B", "step_combine",
    "step_limit", "step_numeric", "step_interpret"
}

VALID_RELATION_TYPES = {
    "definition", "literal_equality", "finite_role_preserving_rename",
    "identity_under_assumptions", "pointwise_identity", "projected_identity",
    "integrated_identity", "structural_replay", "exact_reconstruction",
    "numerical_regression", "counterexample", "not_established",
    "verified_candidate", "canonical_result", "historical_result", "rejected_result"
}

VALID_CANONICAL_STATUS = {"CANONICAL", "INTEGRATED", "VERIFIED", "CANDIDATE", "NOT_ESTABLISHED"}
VALID_VERIFICATION_STATUS = {"VERIFIED", "NUMERICALLY_SUPPORTED", "UNVERIFIED", "NOT_APPLICABLE"}
VALID_SCOPE = {"pointwise", "integrated", "not_applicable"}

REQUIRED_FIELDS = [
    "step_id", "step_label", "source_object_id", "target_object_id",
    "relation_type", "canonical_status", "verification_status",
    "pointwise_integrated_scope", "index_scope", "expression_scope",
    "assumptions", "derivation_category", "input_equation_label",
    "output_equation_label", "provenance_chain", "executor_role",
    "verifier_role", "symbolic_equality_claimed", "numerical_support_level",
    "caveats", "human_gate_status", "parent_step_ids", "child_step_ids"
]


def validate_derivation_step(step_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "derivation_step.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(step_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    step_id = data.get("step_id", "")
    if step_id and step_id not in VALID_STEP_IDS:
        errors.append(f"Invalid step_id '{step_id}'. Must be from INTERFACE CONTRACT.")

    relation_type = data.get("relation_type", "")
    if relation_type and relation_type not in VALID_RELATION_TYPES:
        errors.append(f"Invalid relation_type '{relation_type}'. Must be one of 16 INTERFACE CONTRACT values.")

    canonical = data.get("canonical_status", "")
    if canonical and canonical not in VALID_CANONICAL_STATUS:
        errors.append(f"Invalid canonical_status '{canonical}'.")

    verification = data.get("verification_status", "")
    if verification and verification not in VALID_VERIFICATION_STATUS:
        errors.append(f"Invalid verification_status '{verification}'.")

    scope = data.get("pointwise_integrated_scope", "")
    if scope and scope not in VALID_SCOPE:
        errors.append(f"Invalid pointwise_integrated_scope '{scope}'.")

    index_scope = data.get("index_scope", {})
    required_index_fields = ["free_indices", "dummy_indices", "index_domains",
                              "summation_conventions", "symmetry_properties", "role_preserving_renames"]
    for field in required_index_fields:
        if field not in index_scope:
            errors.append(f"index_scope missing required field: {field}")

    executor = data.get("executor_role", "")
    verifier = data.get("verifier_role", "")
    if executor and verifier and executor == verifier and verifier != "none":
        errors.append(f"Executor role '{executor}' cannot equal verifier role '{verifier}' (role separation violated).")

    if data.get("symbolic_equality_claimed") and relation_type == "numerical_regression":
        warnings.append("symbolic_equality_claimed is True but relation_type is numerical_regression. Numerical agreement alone is not symbolic equality.")

    symbolic = data.get("symbolic_equality_claimed", False)
    if symbolic and verification == "NUMERICALLY_SUPPORTED" and verification != "VERIFIED":
        warnings.append("symbolic_equality_claimed is True but verification_status is not VERIFIED.")

    if canonical == "CANONICAL" and data.get("human_gate_status") != "PASSED":
        errors.append("CANONICAL status requires human_gate_status == PASSED.")

    if canonical == "CANDIDATE" and verification == "VERIFIED":
        warnings.append("VERIFIED but still CANDIDATE: check if human gate is pending.")

    cat = data.get("derivation_category", "")
    valid_categories = {
        "definition", "algebraic_manipulation", "product_rule", "integration_by_parts",
        "index_renaming", "symmetry_reduction", "projection", "integration",
        "limiting_case", "numerical_evaluation", "physical_interpretation"
    }
    if cat and cat not in valid_categories:
        warnings.append(f"Unknown derivation_category '{cat}'.")

    parent_ids = data.get("parent_step_ids", [])
    child_ids = data.get("child_step_ids", [])
    if step_id in parent_ids:
        errors.append(f"Step references itself in parent_step_ids.")
    if step_id in child_ids:
        errors.append(f"Step references itself in child_step_ids.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "step_id": step_id,
            "relation_type": relation_type,
            "canonical_status": canonical,
            "verification_status": verification,
            "human_gate_status": data.get("human_gate_status", ""),
            "missing_fields": len([f for f in REQUIRED_FIELDS if f not in data]),
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <derivation_step.json>")
        sys.exit(2)
    result = validate_derivation_step(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
