#!/usr/bin/env python3
"""
validate_input_sha_freezing.py -- Validate frozen input SHA manifests.

Checks that an input SHA manifest JSON is present, valid, and that its
files map is non-empty.  With --check-files, it also verifies that every
referenced file exists on disk and its SHA-256 matches the manifest.

This script:
- uses Python standard library only
- never modifies any artifact
- never runs git commands
"""

import argparse
import hashlib
import json
import os
import sys


REQUIRED_FIELDS = {"generated_at", "files"}


def _sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", required=True,
                        help="Path to input SHA manifest JSON.")
    parser.add_argument("--check-files", action="store_true",
                        help="Also verify actual file SHAs on disk.")
    args = parser.parse_args()

    validator_name = "validate_input_sha_freezing"
    result = {"validator": validator_name, "passed": False, "evidence": "", "details": {}}
    errors = []

    manifest_path = args.manifest_path
    if not os.path.exists(manifest_path):
        result["evidence"] = f"Manifest not found: {manifest_path}"
        print(json.dumps(result))
        sys.exit(1)

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        result["evidence"] = f"Manifest unparseable: {e}"
        result["details"] = {"path": manifest_path}
        print(json.dumps(result))
        sys.exit(1)

    missing_fields = REQUIRED_FIELDS - set(manifest.keys())
    if missing_fields:
        errors.append(f"missing_required_fields:{sorted(missing_fields)}")

    files = manifest.get("files", {})
    if not isinstance(files, dict) or len(files) == 0:
        errors.append("files_is_empty_or_not_dict")

    if args.check_files and files:
        manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
        sha_mismatches = []
        missing_files = []
        for rel_path, expected_sha in files.items():
            abs_path = os.path.join(manifest_dir, rel_path)
            if not os.path.exists(abs_path):
                missing_files.append(rel_path)
                continue
            actual_sha = _sha256(abs_path)
            if actual_sha is None:
                errors.append(f"cannot_hash:{rel_path}")
                continue
            if actual_sha != expected_sha:
                sha_mismatches.append(rel_path)

        if missing_files:
            errors.append(f"files_missing_on_disk:{missing_files}")
        if sha_mismatches:
            errors.append(f"sha_mismatches:{sha_mismatches}")

    result["details"] = {
        "manifest_path": os.path.abspath(manifest_path),
        "num_files": len(files),
        "generated_at": manifest.get("generated_at"),
        "check_files_flag": args.check_files,
    }

    if errors:
        result["evidence"] = "; ".join(errors)
        result["details"]["errors"] = errors
        print(json.dumps(result))
        sys.exit(1)

    result["passed"] = True
    files_count = len(files)
    evidence = f"Manifest valid with {files_count} file(s)"
    if args.check_files:
        evidence += f"; {files_count} SHA(s) verified on disk"
    result["evidence"] = evidence
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
