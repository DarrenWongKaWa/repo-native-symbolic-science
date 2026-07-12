#!/usr/bin/env python3
"""Validate mathematical_omission_ledger.json against the schema and reconstruction rules."""
import json
import sys
import os
import hashlib

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_OMISSION_PATTERNS = [
    "first_k_displayed", "representative_sample", "structured_ellipsis",
    "typographic_grouping", "block_diagram_replacement", "index_range_notation"
]

VALID_RECONSTRUCTION_RULES = [
    "permutation_symmetry", "index_cyclic_extension", "tensor_symmetry_closure",
    "explicit_term_list", "generating_function_substitution", "computational_regeneration"
]


def validate_omission_ledger(ledger_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "mathematical_omission_ledger.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(ledger_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    pattern = data.get("omission_pattern", "")
    if pattern not in VALID_OMISSION_PATTERNS:
        errors.append(f"Invalid omission_pattern '{pattern}'. Must be one of 6 allowed patterns.")

    rule = data.get("reconstruction_rule", {})
    rule_type = rule.get("rule_type", "")
    if rule_type not in VALID_RECONSTRUCTION_RULES:
        errors.append(f"Invalid reconstruction rule_type '{rule_type}'. Must be one of 6 allowed types.")

    if not rule.get("rule_description"):
        errors.append("reconstruction_rule.rule_description is required.")

    total = data.get("total_term_count", 0)
    displayed = data.get("displayed_term_count", 0)
    omitted = data.get("omitted_term_count", 0)

    if displayed + omitted != total:
        errors.append(f"displayed_term_count ({displayed}) + omitted_term_count ({omitted}) != total_term_count ({total}).")

    if omitted == 0:
        warnings.append("omitted_term_count is 0. Why is an omission ledger needed?")

    if displayed == 0:
        errors.append("displayed_term_count is 0. At least some terms must be displayed.")

    if omitted > 0 and pattern == "first_k_displayed" and displayed == total:
        warnings.append("first_k_displayed pattern but all terms displayed (no omission).")

    full_sha = data.get("full_expression_sha256", "")
    if not full_sha or len(full_sha) != 64:
        errors.append(f"full_expression_sha256 must be a 64-character hex string, got '{full_sha}'.")

    displayed_terms = data.get("displayed_terms", [])
    omitted_terms = data.get("omitted_terms", [])
    if len(displayed_terms) != displayed:
        warnings.append(f"displayed_terms array has {len(displayed_terms)} entries but displayed_term_count is {displayed}.")
    if len(omitted_terms) != omitted:
        warnings.append(f"omitted_terms array has {len(omitted_terms)} entries but omitted_term_count is {omitted}.")

    all_indices = set()
    for term in displayed_terms + omitted_terms:
        idx = term.get("term_index")
        if idx in all_indices:
            errors.append(f"Duplicate term_index {idx} found (term double-counted).")
        all_indices.add(idx)

    validation = data.get("validation", {})
    if omitted > 0 and not validation.get("reconstruction_verified"):
        warnings.append("Omission ledger with omitted terms has not had reconstruction verified.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "omission_id": data.get("omission_id", ""),
            "equation_label": data.get("equation_label", ""),
            "total_terms": total,
            "displayed_terms": displayed,
            "omitted_terms": omitted,
            "omission_pattern": pattern,
            "rule_type": rule_type,
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mathematical_omission_ledger.json>")
        sys.exit(2)
    result = validate_omission_ledger(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
