#!/usr/bin/env python3
"""
validate_verifier_independence.py -- Validate verifier independence from executor.

Ensures the verifier subagent operates independently: different IDs,
separate output directories (not nested inside each other), and the
verifier's authorized input paths do not include executor scratch/tmp
directories.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import json
import os
import sys


FORBIDDEN_INPUT_TOKENS = (".tmp", "scratch", "mutable")


def _is_subdirectory(parent, child):
    try:
        parent_real = os.path.realpath(parent)
        child_real = os.path.realpath(child)
        rel = os.path.relpath(child_real, parent_real)
        if rel.startswith(".."):
            return False
        if rel == ".":
            return True
        return True
    except Exception:
        return False


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
    parser.add_argument("--verifier-inputs", required=True,
                        help="Comma-separated paths the verifier is authorized to read.")
    args = parser.parse_args()

    validator_name = "validate_verifier_independence"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    executor_id = args.executor_id.strip()
    verifier_id = args.verifier_id.strip()
    executor_out = os.path.abspath(args.executor_output_dir.strip())
    verifier_out = os.path.abspath(args.verifier_output_dir.strip())
    verifier_inputs = [p.strip() for p in args.verifier_inputs.split(",") if p.strip()]

    if not executor_id or not verifier_id:
        errors.append("empty_agent_id")
    if executor_id == verifier_id:
        errors.append("executor_id == verifier_id")

    if executor_out == verifier_out:
        errors.append("executor_output_dir == verifier_output_dir")

    if _is_subdirectory(verifier_out, executor_out):
        errors.append("verifier_output_dir is subdirectory of executor_output_dir")
    if _is_subdirectory(executor_out, verifier_out):
        errors.append("executor_output_dir is subdirectory of verifier_output_dir")

    forbidden_matches = []
    for inp in verifier_inputs:
        inp_lower = inp.lower()
        if any(token in inp_lower for token in FORBIDDEN_INPUT_TOKENS):
            forbidden_matches.append(inp)

    if forbidden_matches:
        errors.append(f"forbidden_tokens_in_verifier_inputs:{forbidden_matches}")

    result["details"] = {
        "executor_id": executor_id,
        "verifier_id": verifier_id,
        "executor_output_dir": executor_out,
        "verifier_output_dir": verifier_out,
        "verifier_input_count": len(verifier_inputs),
        "ids_separated": executor_id != verifier_id,
        "dirs_separated": executor_out != verifier_out,
        "nested_dirs": _is_subdirectory(verifier_out, executor_out) or _is_subdirectory(executor_out, verifier_out),
        "forbidden_inputs_detected": forbidden_matches,
        "errors": errors,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    result["evidence"] = (
        f"Verifier independent: distinct IDs, distinct output dirs (not nested), "
        f"no forbidden input paths detected among {len(verifier_inputs)} authorized inputs"
    )
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
