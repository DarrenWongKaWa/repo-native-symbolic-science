#!/usr/bin/env python3
"""Validate scientific_adapter.json files against the schema."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

def validate(adapter_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "scientific_adapter.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(adapter_path) as f:
        data = json.load(f)

    errors = []

    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if "symbol_dictionary" in data and not isinstance(data["symbol_dictionary"], dict):
        errors.append("symbol_dictionary must be an object")
    if "index_role_dictionary" in data and not isinstance(data["index_role_dictionary"], dict):
        errors.append("index_role_dictionary must be an object")
    if "required_human_gates" in data and not isinstance(data["required_human_gates"], list):
        errors.append("required_human_gates must be a list")

    generic_hardcoding_banned = [
        "DC limit before Gamma expansion",
        "finite exact Gamma during DC",
    ]
    for field in ["canonicalization_policy"]:
        pass

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": [],
        "adapter_has_gates": len(data.get("required_human_gates", [])) > 0
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_scientific_adapter.py <adapter.json>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
