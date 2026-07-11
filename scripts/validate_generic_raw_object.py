#!/usr/bin/env python3
"""Validate generic_raw_object.json files against the schema."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

def validate(raw_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "generic_raw_object.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(raw_path) as f:
        data = json.load(f)

    errors = []

    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if data.get("current_status") not in ("RAW_UNVERIFIED", "RAW_INGESTED") and data.get("current_status") is not None:
        pass

    sha = data.get("source_sha256", "")
    if sha and len(sha) != 64:
        errors.append(f"Invalid source_sha256 length: {len(sha)}")

    valid_statuses = schema["properties"]["current_status"]["enum"]
    if data.get("current_status") not in valid_statuses:
        errors.append(f"Invalid current_status: {data.get('current_status')}")

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": [],
        "object_id": data.get("object_id", "UNKNOWN")
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_generic_raw_object.py <raw_object.json>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
