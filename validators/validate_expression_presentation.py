#!/usr/bin/env python3
"""Validate expression_presentation.json against the schema and presentation mode rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_MODES = [
    "compact_inline", "expanded_display", "term_by_term_numbered",
    "grouped_by_physical_origin", "index_structure_tree",
    "tensor_component_table", "diagrammatic_accompaniment",
    "abbreviated_with_omission_ledger", "computational_literal_for_reproduction"
]

CONDITIONAL_FIELDS = {
    "term_by_term_numbered": ["term_labels"],
    "grouped_by_physical_origin": ["physical_origin_groups"],
    "index_structure_tree": ["index_tree"],
    "tensor_component_table": ["component_table"],
    "diagrammatic_accompaniment": ["diagram_reference"],
    "abbreviated_with_omission_ledger": ["omission_ledger_ref"],
    "computational_literal_for_reproduction": ["computational_code"],
}

EXPECTED_CONDITIONAL = {
    "term_labels": "term_by_term_numbered",
    "physical_origin_groups": "grouped_by_physical_origin",
    "index_tree": "index_structure_tree",
    "component_table": "tensor_component_table",
    "diagram_reference": "diagrammatic_accompaniment",
    "omission_ledger_ref": "abbreviated_with_omission_ledger",
    "computational_code": "computational_literal_for_reproduction",
}


def validate_expression_presentation(pres_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "expression_presentation.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(pres_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    mode = data.get("presentation_mode", "")
    if mode not in VALID_MODES:
        errors.append(f"Invalid presentation_mode '{mode}'. Must be one of 9 allowed modes.")

    conditional = data.get("conditional_fields", {})
    required_conditional = CONDITIONAL_FIELDS.get(mode, [])

    for field in required_conditional:
        if field not in conditional:
            errors.append(f"Presentation mode '{mode}' requires conditional_field '{field}', but it is missing.")

    for field_name, expected_mode in EXPECTED_CONDITIONAL.items():
        if field_name in conditional and mode != expected_mode:
            warnings.append(f"conditional_field '{field_name}' is present but is only required for mode '{expected_mode}', not '{mode}'.")

    term_count = data.get("term_count", 0)
    if mode == "compact_inline" and term_count > 10:
        warnings.append(f"compact_inline used with term_count={term_count} (>10). Consider expanded_display or other mode.")
    if mode == "expanded_display" and term_count > 20:
        warnings.append(f"expanded_display used with term_count={term_count} (>20). Consider term_by_term_numbered or abbreviated mode.")

    score = data.get("human_readability_score", 0)
    if score < 4:
        warnings.append(f"human_readability_score={score} is below the mandatory-alternative threshold (4).")
    elif score < 7:
        warnings.append(f"human_readability_score={score} is moderate. Consider alternative presentation.")
    elif score > 10:
        errors.append(f"human_readability_score={score} exceeds maximum (10).")

    if mode == "abbreviated_with_omission_ledger":
        ref = conditional.get("omission_ledger_ref", "")
        if not ref:
            errors.append("abbreviated_with_omission_ledger mode requires a valid omission_ledger_ref.")

    latex = data.get("latex_source", "")
    if not latex or latex.strip() == "":
        errors.append("latex_source is empty or missing.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "presentation_id": data.get("presentation_id", ""),
            "equation_label": data.get("equation_label", ""),
            "presentation_mode": mode,
            "term_count": term_count,
            "readability_score": score,
            "conditional_fields_present": list(conditional.keys()),
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <expression_presentation.json>")
        sys.exit(2)
    result = validate_expression_presentation(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
