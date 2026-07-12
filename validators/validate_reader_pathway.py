#!/usr/bin/env python3
"""Validate reader_pathway.json against the schema and 3-persona requirement."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

REQUIRED_PERSONAS = {"physics_first", "derivation_checking", "machine_reproduction"}

VALID_SECTION_CODES = [
    "SEC_01_SCOPE", "SEC_02_CONVENTIONS", "SEC_03_STARTING_RESPONSE",
    "SEC_04_DECOMPOSITION", "SEC_05_SECTORS", "SEC_06_IDENTITIES",
    "SEC_07_IBP", "SEC_08_FINAL_RESULT", "SEC_09_INTERPRETATION",
    "SEC_10_LIMITS", "SEC_11_VALIDATION", "SEC_12_EVIDENCE_MAP",
    "SEC_13_ELECTRONIC_APPENDIX", "SEC_14_REPRODUCTION"
]

VALID_READING_INSTRUCTIONS = {"READ_FULL", "READ_EQUATIONS_ONLY", "READ_SUMMARY", "SKIM", "SKIP", "REFERENCE_ONLY"}


def validate_reader_pathway(pathway_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "reader_pathway.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(pathway_path) as f:
        data = json.load(f)

    errors = []
    warnings = []

    pathways = data.get("pathways", [])
    personas_found = set()

    for pw in pathways:
        persona = pw.get("persona", "")
        if persona not in REQUIRED_PERSONAS:
            errors.append(f"Unknown persona '{persona}'. Must be one of: {REQUIRED_PERSONAS}")
        personas_found.add(persona)

        route = pw.get("route", [])
        if not route:
            errors.append(f"Pathway for {persona} has an empty route.")
            continue

        entry = pw.get("entry_section", "")
        exit_sec = pw.get("exit_section", "")

        first_code = route[0].get("section_code", "") if route else ""
        last_code = route[-1].get("section_code", "") if route else ""

        if entry != first_code:
            warnings.append(f"Persona {persona}: entry_section '{entry}' does not match first route section '{first_code}'.")
        if exit_sec != last_code:
            warnings.append(f"Persona {persona}: exit_section '{exit_sec}' does not match last route section '{last_code}'.")

        for step in route:
            code = step.get("section_code", "")
            if code not in VALID_SECTION_CODES:
                errors.append(f"Persona {persona}: invalid section_code '{code}' in route.")

            instruction = step.get("reading_instruction", "")
            if instruction not in VALID_READING_INSTRUCTIONS:
                errors.append(f"Persona {persona}: invalid reading_instruction '{instruction}' for section {code}.")

        total_time = sum(step.get("expected_time_minutes", 0) for step in route)
        est_time = pw.get("estimated_time_minutes", 0)
        if est_time > 0 and total_time > 0 and abs(est_time - total_time) > est_time * 0.3:
            warnings.append(f"Persona {persona}: estimated_time_minutes ({est_time}) differs from sum of route times ({total_time}).")

    for persona in REQUIRED_PERSONAS:
        if persona not in personas_found:
            errors.append(f"Missing required persona: {persona}")

    if len(pathways) != 3:
        errors.append(f"Expected exactly 3 pathways, got {len(pathways)}.")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "pathway_id": data.get("pathway_id", ""),
            "personas": list(personas_found),
            "missing_personas": list(REQUIRED_PERSONAS - personas_found),
            "total_pathways": len(pathways),
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <reader_pathway.json>")
        sys.exit(2)
    result = validate_reader_pathway(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
