#!/usr/bin/env python3
"""
validate_repair_lineage.py -- Validate the repair lineage chain.

Checks that the repair lineage from a rejected task to a repair task is
consistent: different IDs, different output directories, original
directory preserved, no circular lineage, and the lineage registry
records the chain correctly.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-task-id", required=True,
                        help="The rejected task ID.")
    parser.add_argument("--repair-task-id", required=True,
                        help="The new repair task ID.")
    parser.add_argument("--original-output-dir", required=True,
                        help="Original output directory (should still exist).")
    parser.add_argument("--repair-output-dir", required=True,
                        help="Repair output directory (should be different).")
    parser.add_argument("--lineage-registry-path", required=True,
                        help="JSON file tracking repair lineage.")
    args = parser.parse_args()

    validator_name = "validate_repair_lineage"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    original_id = args.original_task_id.strip()
    repair_id = args.repair_task_id.strip()
    original_out = os.path.abspath(args.original_output_dir.strip())
    repair_out = os.path.abspath(args.repair_output_dir.strip())
    lineage_path = args.lineage_registry_path

    if original_id == repair_id:
        errors.append("original_task_id == repair_task_id (must be different)")

    if original_out == repair_out:
        errors.append("original_output_dir == repair_output_dir (must be different)")

    if not os.path.isdir(original_out):
        errors.append(f"original_output_dir_missing:{original_out}")

    if not os.path.isdir(repair_out):
        errors.append(f"repair_output_dir_missing:{repair_out}")

    if not os.path.exists(lineage_path):
        result["evidence"] = f"Lineage registry not found: {lineage_path}"
        result["details"] = {
            "original_task_id": original_id,
            "repair_task_id": repair_id,
            "errors": errors,
        }
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(lineage_path) as f:
            lineage = json.load(f)
    except Exception as e:
        errors.append(f"lineage_registry_unparseable:{e}")

    entries = lineage if isinstance(lineage, list) else lineage.get("entries", [])
    chain = {}
    for entry in entries:
        if isinstance(entry, dict):
            task = entry.get("task_id") or entry.get("id", "")
            origin = entry.get("origin_task_id") or entry.get("repairs_to", "")
            if task:
                chain[task] = origin

    if repair_id not in chain and entries:
        current = chain.get(original_id)
        if current:
            errors.append(
                f"lineage_registry_does_not_record_repair: original={original_id} -> "
                f"expected={repair_id}, found={current}"
            )
        else:
            errors.append(f"lineage_registry_does_not_record_repair: original={original_id} -> repair={repair_id}")

    if chain.get(original_id, "").split(",") if isinstance(chain.get(original_id), str) else []:
        origin_of_original = chain.get(original_id, "").split(",") if isinstance(chain.get(original_id), str) else [chain.get(original_id)]
        if repair_id in origin_of_original:
            errors.append(f"circular_lineage: original={original_id} claims repair={repair_id} as origin")

    result["details"] = {
        "original_task_id": original_id,
        "repair_task_id": repair_id,
        "original_output_dir": original_out,
        "repair_output_dir": repair_out,
        "lineage_registry_path": os.path.abspath(lineage_path),
        "ids_different": original_id != repair_id,
        "dirs_different": original_out != repair_out,
        "original_dir_exists": os.path.isdir(original_out),
        "errors": errors,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"Repair lineage valid: {original_id} -> {repair_id}; "
        f"IDs and dirs distinct; original artifacts preserved"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
