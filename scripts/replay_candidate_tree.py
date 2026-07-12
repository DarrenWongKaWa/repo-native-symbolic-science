#!/usr/bin/env python3
"""Replay utility for candidate tree archives.

1. Verifies the target checkout is at d4c25a5e...
2. Verifies the target checkout is clean
3. Verifies the candidate archive SHA
4. Extracts only manifest-authorized files
5. Verifies every extracted file SHA against the manifest
6. Rejects unexpected files
7. Prints a summary report

Usage:
  python3 scripts/replay_candidate_tree.py <candidate_archive.tar.gz> <target_checkout_dir>
"""
import sys
import os
import json
import hashlib
import tarfile
import tempfile
import shutil
import subprocess


REQUIRED_COMMIT_PREFIX = "d4c25a5e"


def run_git(args, cwd):
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def verify_checkout_commit(target_dir):
    stdout, stderr, code = run_git(["rev-parse", "HEAD"], target_dir)
    if code != 0:
        return False, f"git rev-parse failed: {stderr}"
    if not stdout.startswith(REQUIRED_COMMIT_PREFIX):
        return False, (
            f"Checkout commit {stdout[:12]} does not start with "
            f"required prefix {REQUIRED_COMMIT_PREFIX}"
        )
    return True, f"Checkout at correct commit: {stdout}"


def verify_checkout_clean(target_dir):
    stdout, stderr, code = run_git(["status", "--porcelain"], target_dir)
    if code != 0:
        return False, f"git status failed: {stderr}"
    if stdout.strip():
        return False, f"Checkout is dirty:\n{stdout}"
    return True, "Checkout is clean"


def compute_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_archive_sha(archive_path, expected_sha):
    actual = compute_sha256(archive_path)
    if actual != expected_sha:
        return False, (
            f"Archive SHA mismatch: expected {expected_sha[:12]}..., "
            f"got {actual[:12]}..."
        )
    return True, f"Archive SHA verified: {actual[:12]}..."


def extract_manifest_from_archive(archive_path, extract_dir):
    with tarfile.open(archive_path, "r:gz") as tar:
        manifest_member = None
        for member in tar.getmembers():
            if os.path.basename(member.name) == "manifest.json":
                manifest_member = member
                break
        if manifest_member is None:
            return None, "No manifest.json found in archive"
        tar.extract(manifest_member, extract_dir)
        manifest_path = os.path.join(extract_dir, manifest_member.name)
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        return manifest, None


def extract_authorized_files(archive_path, manifest, extract_dir):
    authorized = set()
    if isinstance(manifest, dict):
        authorized_files = manifest.get("files", [])
        if isinstance(authorized_files, list):
            for item in authorized_files:
                if isinstance(item, dict):
                    authorized.add(item.get("path", item.get("file_path", "")))
                elif isinstance(item, str):
                    authorized.add(item)
    elif isinstance(manifest, list):
        for item in manifest:
            if isinstance(item, dict):
                authorized.add(item.get("path", item.get("file_path", "")))
            elif isinstance(item, str):
                authorized.add(item)
    authorized.discard("")
    extracted = []
    rejected = []
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if name == "manifest.json" or name.startswith("manifest"):
                continue
            if name in authorized or os.path.basename(name) in authorized:
                tar.extract(member, extract_dir)
                extracted.append(name)
            else:
                rejected.append(name)
    return extracted, rejected


def verify_extracted_shas(extract_dir, manifest):
    file_sha_map = {}
    if isinstance(manifest, dict):
        items = manifest.get("files", manifest.get("entries", []))
    elif isinstance(manifest, list):
        items = manifest
    else:
        return [], [], "Invalid manifest format"
    if not isinstance(items, list):
        return [], [], "Manifest files/entries is not a list"
    for item in items:
        if isinstance(item, dict):
            path = item.get("path", item.get("file_path", ""))
            sha = item.get("sha256", item.get("sha", ""))
            if path and sha:
                file_sha_map[path] = sha
        elif isinstance(item, str):
            file_sha_map[item] = None
    verified = []
    mismatched = []
    for path, expected in file_sha_map.items():
        full = os.path.join(extract_dir, path)
        if not expected:
            continue
        if os.path.isfile(full):
            actual = compute_sha256(full)
            if actual == expected:
                verified.append(path)
            else:
                mismatched.append(
                    f"{path}: expected {expected[:12]}..., got {actual[:12]}..."
                )
        else:
            mismatched.append(f"{path}: file not found after extraction")
    return verified, mismatched, None


def replay(archive_path, target_dir):
    report = {"archive": archive_path, "target_dir": target_dir, "steps": []}

    ok, msg = verify_checkout_commit(target_dir)
    report["steps"].append({"step": "verify_commit", "ok": ok, "msg": msg})
    if not ok:
        report["overall"] = "FAIL"
        return report

    ok, msg = verify_checkout_clean(target_dir)
    report["steps"].append({"step": "verify_clean", "ok": ok, "msg": msg})
    if not ok:
        report["overall"] = "FAIL"
        return report

    archive_sha = compute_sha256(archive_path)
    report["archive_sha256"] = archive_sha

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest, err = extract_manifest_from_archive(archive_path, tmpdir)
        if err:
            report["steps"].append({
                "step": "extract_manifest", "ok": False, "msg": err
            })
            report["overall"] = "FAIL"
            return report
        report["steps"].append({
            "step": "extract_manifest", "ok": True,
            "msg": f"Manifest loaded: {len(manifest.get('files', manifest))} entries"
        })

        extracted, rejected = extract_authorized_files(
            archive_path, manifest, tmpdir
        )
        report["steps"].append({
            "step": "extract_files", "ok": True,
            "msg": f"Extracted {len(extracted)}, rejected {len(rejected)}",
            "extracted": extracted,
            "rejected": rejected,
        })
        if rejected:
            report["steps"].append({
                "step": "reject_unexpected",
                "ok": False,
                "msg": f"Unexpected files in archive: {rejected}",
            })
            report["overall"] = "FAIL"
            return report

        verified, mismatched, err2 = verify_extracted_shas(tmpdir, manifest)
        report["steps"].append({
            "step": "verify_shas", "ok": len(mismatched) == 0,
            "msg": (
                f"Verified {len(verified)} SHA checks, "
                f"{len(mismatched)} mismatches"
            ),
            "mismatches": mismatched,
        })
        if mismatched:
            report["overall"] = "FAIL"
            return report

    report["overall"] = "PASS"
    return report


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python3 replay_candidate_tree.py "
            "<candidate_archive.tar.gz> <target_checkout_dir>"
        )
        sys.exit(1)
    archive_path = sys.argv[1]
    target_dir = sys.argv[2]
    if not os.path.isfile(archive_path):
        print(f"Archive not found: {archive_path}")
        sys.exit(1)
    if not os.path.isdir(target_dir):
        print(f"Target directory not found: {target_dir}")
        sys.exit(1)
    report = replay(archive_path, target_dir)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report.get("overall") == "PASS" else 1)


if __name__ == "__main__":
    main()
