#!/usr/bin/env python3
"""Validate supplement_section_contract.json against the 14-section profile."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

REQUIRED_SECTION_CODES = [
    "SEC_01_SCOPE", "SEC_02_CONVENTIONS", "SEC_03_STARTING_RESPONSE",
    "SEC_04_DECOMPOSITION", "SEC_05_SECTORS", "SEC_06_IDENTITIES",
    "SEC_07_IBP", "SEC_08_FINAL_RESULT", "SEC_09_INTERPRETATION",
    "SEC_10_LIMITS", "SEC_11_VALIDATION", "SEC_12_EVIDENCE_MAP",
    "SEC_13_ELECTRONIC_APPENDIX", "SEC_14_REPRODUCTION"
]

VALID_SECTION_ROLES = {"scoping", "definitional", "derivation", "result", "validation", "metadata"}

EXPECTED_ROLES = {
    "SEC_01_SCOPE": "scoping",
    "SEC_02_CONVENTIONS": "definitional",
    "SEC_03_STARTING_RESPONSE": "derivation",
    "SEC_04_DECOMPOSITION": "derivation",
    "SEC_05_SECTORS": "derivation",
    "SEC_06_IDENTITIES": "derivation",
    "SEC_07_IBP": "derivation",
    "SEC_08_FINAL_RESULT": "result",
    "SEC_09_INTERPRETATION": "result",
    "SEC_10_LIMITS": "result",
    "SEC_11_VALIDATION": "validation",
    "SEC_12_EVIDENCE_MAP": "metadata",
    "SEC_13_ELECTRONIC_APPENDIX": "metadata",
    "SEC_14_REPRODUCTION": "metadata",
}


def validate_section_contract(contract_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "supplement_section_contract.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(contract_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    sections = data.get("section_contracts", [])
    present_codes = {s.get("section_code", "") for s in sections}

    for code in REQUIRED_SECTION_CODES:
        if code not in present_codes:
            errors.append(f"Missing required section: {code}")

    for code in present_codes:
        if code not in REQUIRED_SECTION_CODES:
            errors.append(f"Unknown section code: {code}")

    for section in sections:
        code = section.get("section_code", "")
        role = section.get("section_role", "")
        if role not in VALID_SECTION_ROLES:
            errors.append(f"Invalid section_role '{role}' for {code}.")

        expected = EXPECTED_ROLES.get(code)
        if expected and role != expected:
            warnings.append(f"Section {code}: role is '{role}' but expected '{expected}'.")

        relevance = section.get("reader_pathway_relevance", {})
        for persona in ["physics_first", "derivation_checking", "machine_reproduction"]:
            val = relevance.get(persona, "")
            if val and val not in {"ESSENTIAL", "RECOMMENDED", "OPTIONAL", "SKIP"}:
                errors.append(f"Section {code}: invalid reader_pathway_relevance '{val}' for {persona}.")

    if len(sections) != 14:
        errors.append(f"Expected exactly 14 sections, got {len(sections)}.")

    role_counts = {role: 0 for role in VALID_SECTION_ROLES}
    for s in sections:
        r = s.get("section_role", "")
        if r in role_counts:
            role_counts[r] += 1

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_sections": len(sections),
            "missing_sections": [c for c in REQUIRED_SECTION_CODES if c not in present_codes],
            "extra_sections": [c for c in present_codes if c not in REQUIRED_SECTION_CODES],
            "role_distribution": role_counts,
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <supplement_section_contract.json>")
        sys.exit(2)
    result = validate_section_contract(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
