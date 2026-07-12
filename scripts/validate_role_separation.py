#!/usr/bin/env python3
"""
validate_role_separation.py -- Validate executor and verifier role separation.

Ensures that executor and verifier subagents do not share IDs or
output directories.  This is a structural separation check enforced
before any task begins.

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
    parser.add_argument("--executor-id", required=True,
                        help="Executor subagent ID.")
    parser.add_argument("--verifier-id", required=True,
                        help="Verifier subagent ID.")
    parser.add_argument("--executor-output-dir", required=True,
                        help="Executor output directory.")
    parser.add_argument("--verifier-output-dir", required=True,
                        help="Verifier output directory.")
    args = parser.parse_args()

    validator_name = "validate_role_separation"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    executor_id = args.executor_id.strip()
    verifier_id = args.verifier_id.strip()
    executor_out = os.path.abspath(args.executor_output_dir.strip())
    verifier_out = os.path.abspath(args.verifier_output_dir.strip())

    if not executor_id or executor_id.lower() in ("", "null", "none", "placeholder"):
        errors.append("executor_id is empty or placeholder")
    if not verifier_id or verifier_id.lower() in ("", "null", "none", "placeholder"):
        errors.append("verifier_id is empty or placeholder")

    if executor_id == verifier_id:
        errors.append("executor_id == verifier_id (must be different subagents)")

    if executor_out == verifier_out:
        errors.append("executor_output_dir == verifier_output_dir (no shared writable output)")

    if not os.path.exists(executor_out):
        errors.append(f"executor_output_dir does not exist: {executor_out}")
    if not os.path.exists(verifier_out):
        errors.append(f"verifier_output_dir does not exist: {verifier_out}")

    result["details"] = {
        "executor_id": executor_id,
        "verifier_id": verifier_id,
        "executor_output_dir": executor_out,
        "verifier_output_dir": verifier_out,
        "roles_separated": executor_id != verifier_id,
        "dirs_separated": executor_out != verifier_out,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"Roles separated: executor={executor_id}, verifier={verifier_id}, "
        f"distinct output directories confirmed"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
