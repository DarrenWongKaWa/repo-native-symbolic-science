#!/usr/bin/env python3
"""
validate_output_contract_completion.py -- Validate task output contract completion.

Checks that a task contract's required outputs all exist in the output
directory, that no temporary/partial files remain, that all JSON files
parse correctly, and that a result_envelope.json (if present) validates
against the subagent_result_envelope schema.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


TEMPORARY_SUFFIXES = (".tmp", ".partial", ".in_progress")
TEMPORARY_PREFIXES = (".",)


def _is_temporary(filename):
    if any(filename.endswith(suf) for suf in TEMPORARY_SUFFIXES):
        return True
    if filename.endswith("~"):
        return True
    if filename.endswith(".swp"):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-path", required=True,
                        help="Path to task contract JSON.")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory to check.")
    args = parser.parse_args()

    validator_name = "validate_output_contract_completion"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    contract_path = args.contract_path
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.exists(contract_path):
        result["evidence"] = f"Contract not found: {contract_path}"
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(contract_path) as f:
            contract = json.load(f)
    except Exception as e:
        result["evidence"] = f"Contract unparseable: {e}"
        print(json.dumps(result))
        sys.exit(1)

    required_outputs = contract.get("required_outputs", [])
    if not required_outputs:
        errors.append("contract_has_no_required_outputs")

    if not os.path.isdir(output_dir):
        result["evidence"] = f"Output directory not found: {output_dir}"
        result["details"] = {"output_dir": output_dir}
        print(json.dumps(result))
        sys.exit(1)

    for rel in required_outputs:
        full = os.path.join(output_dir, rel)
        if not os.path.exists(full):
            errors.append(f"missing_required_output:{rel}")
            continue
        if os.path.getsize(full) == 0:
            errors.append(f"empty_required_output:{rel}")

    temp_files = []
    json_parse_errors = []
    if os.path.isdir(output_dir):
        for entry in os.listdir(output_dir):
            full = os.path.join(output_dir, entry)
            if os.path.isfile(full) and _is_temporary(entry):
                temp_files.append(entry)
            if os.path.isfile(full) and entry.endswith(".json"):
                try:
                    with open(full) as f:
                        json.load(f)
                except Exception as e:
                    json_parse_errors.append(f"{entry}:{e}")

    if temp_files:
        errors.append(f"temporary_files_present:{temp_files}")
    if json_parse_errors:
        errors.append(f"json_parse_errors:{json_parse_errors}")

    result_envelope_path = os.path.join(output_dir, "result_envelope.json")
    envelope_valid = None
    if os.path.exists(result_envelope_path):
        try:
            with open(result_envelope_path) as f:
                envelope = json.load(f)
            required_env_fields = {
                "task_id", "subagent_id", "role", "completion_status",
                "produced_artifacts", "output_sha_manifest", "validation_results",
                "claims", "caveats", "blockers", "resource_usage",
                "started_at", "completed_at"
            }
            env_missing = required_env_fields - set(envelope.keys())
            if env_missing:
                errors.append(f"result_envelope_missing_fields:{sorted(env_missing)}")
                envelope_valid = False
            else:
                envelope_valid = True
        except Exception as e:
            errors.append(f"result_envelope_unparseable:{e}")
            envelope_valid = False

    result["details"] = {
        "contract_path": os.path.abspath(contract_path),
        "output_dir": output_dir,
        "num_required_outputs": len(required_outputs),
        "temp_files_found": temp_files,
        "json_parse_errors_count": len(json_parse_errors),
        "result_envelope_valid": envelope_valid,
        "errors": errors,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"All {len(required_outputs)} required output(s) present; "
        f"no temporary files; all JSON parseable"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
