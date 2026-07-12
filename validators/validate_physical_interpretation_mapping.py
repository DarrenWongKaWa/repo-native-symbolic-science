#!/usr/bin/env python3
"""Validate physical_interpretation_mapping.json against the schema and interpretation rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_INTERPRETATION_TYPES = [
    "term_by_term_physical_origin", "tensorial_structure_meaning",
    "parametric_dependence_explanation", "limiting_case_behavior",
    "connection_to_observable"
]

CONDITIONAL_REQUIREMENTS = {
    "term_by_term_physical_origin": ["term_interpretations"],
    "tensorial_structure_meaning": ["tensorial_interpretation"],
    "parametric_dependence_explanation": ["parametric_interpretation"],
    "limiting_case_behavior": ["limiting_cases"],
    "connection_to_observable": ["observable_connection"],
}

VALID_AGREEMENT = {"EXACT", "APPROXIMATE", "QUALITATIVE", "DISAGREES", "NOT_CHECKED"}


def validate_physical_interpretation(interp_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "physical_interpretation_mapping.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(interp_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    itype = data.get("interpretation_type", "")
    if itype not in VALID_INTERPRETATION_TYPES:
        errors.append(f"Invalid interpretation_type '{itype}'. Must be one of 5 allowed types.")

    physical = data.get("physical_meaning", "")
    if not physical or physical.strip() == "":
        errors.append("physical_meaning is empty or missing.")

    required_fields = CONDITIONAL_REQUIREMENTS.get(itype, [])
    for field in required_fields:
        val = data.get(field)
        if val is None or (isinstance(val, (list, str)) and len(val) == 0):
            errors.append(f"interpretation_type '{itype}' requires '{field}', but it is missing or empty.")

    if itype == "term_by_term_physical_origin":
        terms = data.get("term_interpretations", [])
        for term in terms:
            if not term.get("physical_origin"):
                warnings.append(f"term_index {term.get('term_index')} has no physical_origin.")
            if not term.get("physical_significance"):
                warnings.append(f"term_index {term.get('term_index')} has no physical_significance.")

    if itype == "limiting_case_behavior":
        limits = data.get("limiting_cases", [])
        for limit in limits:
            agreement = limit.get("agreement_with_benchmark", "")
            if agreement not in VALID_AGREEMENT:
                errors.append(f"Invalid agreement_with_benchmark '{agreement}' for limit '{limit.get('limit_description')}'.")
            if agreement == "DISAGREES":
                errors.append(f"CRITICAL: Limiting case '{limit.get('limit_description')}' DISAGREES with benchmark '{limit.get('known_benchmark')}'. This requires re-examination.")
            if limit.get("known_benchmark") and agreement == "NOT_CHECKED":
                warnings.append(f"Benchmark '{limit.get('known_benchmark')}' exists but agreement is NOT_CHECKED.")
        if len(limits) == 0:
            errors.append("limiting_case_behavior interpretation requires at least one limiting case.")

    if itype == "tensorial_structure_meaning":
        tensorial = data.get("tensorial_interpretation", {})
        if not tensorial.get("index_structure"):
            errors.append("tensorial_interpretation requires index_structure.")

    if itype == "connection_to_observable":
        obs = data.get("observable_connection", {})
        if not obs.get("observable_name"):
            errors.append("observable_connection requires observable_name.")
        if not obs.get("relationship_to_expression"):
            errors.append("observable_connection requires relationship_to_expression.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "interpretation_id": data.get("interpretation_id", ""),
            "equation_label": data.get("equation_label", ""),
            "interpretation_type": itype,
            "limiting_cases_count": len(data.get("limiting_cases", [])),
            "has_physical_meaning": bool(physical.strip()),
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <physical_interpretation_mapping.json>")
        sys.exit(2)
    result = validate_physical_interpretation(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
