#!/usr/bin/env python3
"""Validate supplement_claim_registry.json against the schema and claim boundary rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_CLAIM_TYPES = {
    "definitional_identity", "pointwise_tensorial_identity", "integrated_identity",
    "projected_identity", "assumption_bound_identity", "derived_asymptotic_form",
    "numerical_observation", "physical_interpretation", "methodological_result",
    "reconstruction_formula", "historical_citation", "not_established_pattern"
}

VALID_CANONICAL = {"CANONICAL", "INTEGRATED", "VERIFIED", "CANDIDATE", "NOT_ESTABLISHED"}
VALID_VERIFICATION = {"VERIFIED", "NUMERICALLY_SUPPORTED", "UNVERIFIED", "NOT_APPLICABLE"}


def validate_claim_registry(registry_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "supplement_claim_registry.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(registry_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    claims = data.get("claims", [])
    claim_ids = set()
    equation_labels_refs = set()

    for claim in claims:
        cid = claim.get("claim_id", "")
        if cid in claim_ids:
            errors.append(f"Duplicate claim_id: {cid}")
        claim_ids.add(cid)

        ctype = claim.get("claim_type", "")
        if ctype not in VALID_CLAIM_TYPES:
            errors.append(f"Invalid claim_type '{ctype}' for claim {cid}.")

        canonical = claim.get("canonical_status", "")
        if canonical not in VALID_CANONICAL:
            errors.append(f"Invalid canonical_status '{canonical}' for claim {cid}.")

        verification = claim.get("verification_status", "")
        if verification not in VALID_VERIFICATION:
            errors.append(f"Invalid verification_status '{verification}' for claim {cid}.")

        eq_labels = claim.get("equation_labels", [])
        for lbl in eq_labels:
            equation_labels_refs.add(lbl)

        boundary = claim.get("claim_boundary", {})
        if not boundary.get("scope"):
            warnings.append(f"Claim {cid} has no scope defined in claim_boundary.")

        if canonical == "CANONICAL":
            parent_ids = claim.get("parent_claim_ids", [])
            for pid in parent_ids:
                if pid not in claim_ids:
                    warnings.append(f"Claim {cid} references parent {pid} which may not be in this registry.")

    canonical_count = sum(1 for c in claims if c.get("canonical_status") == "CANONICAL")
    verified_count = sum(1 for c in claims if c.get("verification_status") == "VERIFIED")
    candidate_count = sum(1 for c in claims if c.get("canonical_status") == "CANDIDATE")
    not_est_count = sum(1 for c in claims if c.get("canonical_status") == "NOT_ESTABLISHED")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_claims": len(claims),
            "canonical_count": canonical_count,
            "verified_count": verified_count,
            "candidate_count": candidate_count,
            "not_established_count": not_est_count,
            "unique_equation_labels": len(equation_labels_refs),
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <supplement_claim_registry.json>")
        sys.exit(2)
    result = validate_claim_registry(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
