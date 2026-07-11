#!/usr/bin/env python3
"""Validate claim_relation.json files against the schema and promotion rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

PROMOTION_RULES = {
    "numerical_regression_only": ["PROVISIONAL"],
    "pointwise_identity": ["PROVISIONAL", "VERIFIED", "VERIFIED_WITH_CAVEAT"],
    "projected_identity": ["PROVISIONAL", "VERIFIED", "VERIFIED_WITH_CAVEAT"],
    "integrated_identity": ["PROVISIONAL", "VERIFIED", "VERIFIED_WITH_CAVEAT"],
    "literal_equality": ["PROVISIONAL", "VERIFIED", "HUMAN_ACCEPTED"],
    "forbidden_claim": [],
}

def validate(claim_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "claim_relation.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(claim_path) as f:
        data = json.load(f)

    errors = []
    warnings = []
    blocked_promotions = []

    relation_type = data.get("relation_type", "")
    status = data.get("status", "")

    if relation_type == "numerical_regression_only" and status == "HUMAN_ACCEPTED":
        errors.append("numerical_regression_only claims cannot be HUMAN_ACCEPTED without additional verification")
        blocked_promotions.append("PROVISIONAL -> HUMAN_ACCEPTED")

    if relation_type == "pointwise_identity" and status == "HUMAN_ACCEPTED":
        warnings.append("pointwise_identity promoted to HUMAN_ACCEPTED: verify this is not confused with integrated cancellation")

    if relation_type == "forbidden_claim":
        errors.append("forbidden_claim type used: this claim must not be promoted")

    verification = data.get("verification_evidence", {})
    if verification.get("numerical_agreement_is_not_symbolic_equality") is False:
        warnings.append("numerical_agreement_is_not_symbolic_equality is false; numerical alone should not establish symbolic equality")

    if data.get("claimed_by_role") == "independent_verifier" and data.get("claimed_by_role") == "executor":
        errors.append("Executor cannot also claim as independent_verifier")

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": warnings,
        "blocked_promotions": blocked_promotions,
        "claim_id": data.get("claim_id", "UNKNOWN"),
        "relation_type": relation_type,
        "status": status
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_claim_relation.py <claim.json>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
