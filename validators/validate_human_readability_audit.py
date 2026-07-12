#!/usr/bin/env python3
"""Validate human_readability_audit.json against the schema and completeness rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

REQUIRED_CHECK_TYPES = [
    "equation_numbering_consistency",
    "cross_reference_validity",
    "notation_defined_before_use",
    "index_convention_clarity",
    "term_grouping_readability",
    "abbreviation_expansion_present",
    "figure_table_label_consistency",
    "derivation_step_narrative_flow",
    "physical_interpretation_accessibility",
    "limiting_case_explicitness",
    "mathematical_omission_transparency",
    "reproduction_instruction_completeness",
    "reader_pathway_signposting",
]

VALID_VERDICTS = {"PASS", "PASS_WITH_MINOR", "FAIL_WITH_REQUIRED_FIX", "NOT_APPLICABLE"}
VALID_SEVERITY = {"CRITICAL", "MAJOR", "MINOR", "COSMETIC"}
VALID_READINESS = {"READY", "READY_WITH_MINOR_REVISIONS", "REVISION_REQUIRED", "NOT_READY"}


def validate_readability_audit(audit_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "human_readability_audit.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(audit_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    checks = data.get("checks", [])
    present_types = {c.get("check_type", "") for c in checks}

    for ct in REQUIRED_CHECK_TYPES:
        if ct not in present_types:
            errors.append(f"Missing required check_type: {ct}")

    for ct in present_types:
        if ct not in REQUIRED_CHECK_TYPES:
            errors.append(f"Unknown check_type: {ct}")

    if len(checks) != 13:
        errors.append(f"Expected exactly 13 checks, got {len(checks)}.")

    critical_count = 0
    major_count = 0
    for check in checks:
        verdict = check.get("verdict", "")
        if verdict not in VALID_VERDICTS:
            errors.append(f"Invalid verdict '{verdict}' for check '{check.get('check_type')}'.")

        severity = check.get("severity", "")
        if severity not in VALID_SEVERITY:
            errors.append(f"Invalid severity '{severity}' for check '{check.get('check_type')}'.")

        if severity == "CRITICAL":
            critical_count += 1
        elif severity == "MAJOR":
            major_count += 1

        if verdict == "FAIL_WITH_REQUIRED_FIX" and not check.get("recommendation"):
            warnings.append(f"Check '{check.get('check_type')}' FAIL_WITH_REQUIRED_FIX but has no recommendation.")

    overall = data.get("overall_verdict", {})
    readiness = overall.get("publication_readiness", "")
    if readiness not in VALID_READINESS:
        errors.append(f"Invalid publication_readiness '{readiness}'.")

    score = overall.get("readability_score", 0)
    if score < 0 or score > 10:
        errors.append(f"readability_score {score} out of range [0, 10].")
    elif score < 4 and readiness == "READY":
        warnings.append(f"readability_score is {score} but publication_readiness is READY. Review this discrepancy.")

    if critical_count > 0 and readiness == "READY":
        errors.append(f"Cannot be READY with {critical_count} CRITICAL issues.")

    pathway = data.get("reader_pathway_assessment", {})
    for persona in ["physics_first", "derivation_checking", "machine_reproduction"]:
        pa = pathway.get(persona, {})
        acc = pa.get("accessibility_score", -1)
        if acc < 0 or acc > 10:
            warnings.append(f"Missing or out-of-range accessibility_score for {persona}.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "audit_id": data.get("audit_id", ""),
            "total_checks": len(checks),
            "critical_issues": critical_count,
            "major_issues": major_count,
            "publication_readiness": readiness,
            "readability_score": score,
            "missing_check_types": [ct for ct in REQUIRED_CHECK_TYPES if ct not in present_types],
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <human_readability_audit.json>")
        sys.exit(2)
    result = validate_readability_audit(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
