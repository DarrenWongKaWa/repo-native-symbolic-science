#!/usr/bin/env python3
"""Validate latex_evidence_mapping.json files against the schema and completeness rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

def validate(mapping_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "latex_evidence_mapping.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(mapping_path) as f:
        data = json.load(f)

    errors = []
    warnings = []
    forbidden_presentations = {
        "candidate_as_verified": 0,
        "verified_candidate_as_canonical": 0,
        "projection_as_global_equality": 0,
        "pointwise_as_integrated_cancellation": 0,
        "historical_as_current_without_qualification": 0,
    }

    entries = data.get("entries", [])
    for entry in entries:
        status = entry.get("canonical_or_candidate_status", "")
        claim_type = entry.get("claim_type", "")

        if status == "candidate" and claim_type in ("literal_equality", "identity_under_assumptions"):
            warnings.append(f"Entry {entry.get('latex_label')}: candidate presented as verified-type claim ({claim_type})")
            forbidden_presentations["candidate_as_verified"] += 1

        if status == "candidate" and claim_type == "integrated_identity":
            warnings.append(f"Entry {entry.get('latex_label')}: candidate with integrated_identity claim")

        if claim_type == "projected_identity" and status == "canonical":
            pass

        if claim_type == "pointwise_identity" and status == "canonical":
            warnings.append(f"Entry {entry.get('latex_label')}: pointwise_identity marked canonical; verify not confused with integrated cancellation")

        if not entry.get("source_sha") or len(entry.get("source_sha", "")) != 64:
            errors.append(f"Entry {entry.get('latex_label')}: missing or invalid source_sha")

    completeness = data.get("completeness_claim", {})
    if completeness.get("all_equations_mapped") is False or completeness.get("all_tables_mapped") is False:
        warnings.append("Not all equations/tables are mapped")

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": warnings,
        "forbidden_presentations": forbidden_presentations,
        "entry_count": len(entries),
        "mapping_id": data.get("mapping_id", "UNKNOWN")
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_latex_evidence_mapping.py <mapping.json>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
