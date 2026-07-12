#!/usr/bin/env python3
"""
validate_partial_artifact_consumption.py -- Block downstream consumption of partial artifacts.

Scans a directory for temporary/partial files and verifies all required
files are present, non-empty, and parseable (if JSON).  Returns BLOCKED
if any check fails, preventing downstream task eligibility.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


TEMPORARY_PATTERNS = (".tmp", ".partial", ".in_progress", "~", ".swp")


def _is_temporary(filename):
    return any(filename.endswith(pat) for pat in TEMPORARY_PATTERNS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True,
                        help="Directory to scan for partial artifacts.")
    parser.add_argument("--required-files", required=True,
                        help="Comma-separated list of required file names.")
    args = parser.parse_args()

    validator_name = "validate_partial_artifact_consumption"
    result = {"validator": validator_name, "passed": False, "evidence": "BLOCKED", "details": {}}
    errors = []

    artifact_dir = os.path.abspath(args.artifact_dir)
    required_files = [f.strip() for f in args.required_files.split(",") if f.strip()]

    if not required_files:
        errors.append("no_required_files_specified")

    if not os.path.isdir(artifact_dir):
        result["evidence"] = f"Artifact directory not found: {artifact_dir} -> BLOCKED"
        result["details"] = {"artifact_dir": artifact_dir, "errors": ["dir_missing"]}
        print(json.dumps(result))
        sys.exit(1)

    for rel in required_files:
        full = os.path.join(artifact_dir, rel)
        if not os.path.exists(full):
            errors.append(f"missing_required_file:{rel}")
            continue
        if os.path.getsize(full) == 0:
            errors.append(f"empty_required_file:{rel}")

    temp_files = []
    json_errors = []
    for entry in sorted(os.listdir(artifact_dir)):
        full = os.path.join(artifact_dir, entry)
        if os.path.isfile(full) and _is_temporary(entry):
            temp_files.append(entry)
        if os.path.isfile(full) and entry.endswith(".json"):
            try:
                with open(full) as f:
                    json.load(f)
            except Exception as e:
                json_errors.append(f"{entry}:{e}")

    if temp_files:
        errors.append(f"partial_artifacts_detected:{temp_files}")
    if json_errors:
        errors.append(f"json_parse_errors:{json_errors}")

    result["details"] = {
        "artifact_dir": artifact_dir,
        "required_files": required_files,
        "temp_files_detected": temp_files,
        "json_errors": json_errors,
        "errors": errors,
    }

    if errors:
        result["evidence"] = "BLOCKED: " + "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"All {len(required_files)} required file(s) present; "
        f"no partial artifacts detected"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
