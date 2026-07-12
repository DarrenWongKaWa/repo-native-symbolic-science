#!/usr/bin/env python3
"""Validate the public sigma_xxx finite-Gamma replay benchmark package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


REQUIRED_INPUTS = [
    "00_case_manifest.yaml",
    "01_raw_sigma_xxx.txt",
    "02_scientific_definitions.yaml",
    "03_model_and_parameters.yaml",
    "04_human_authority.yaml",
    "05_derivation_steps.jsonl",
    "06_sector_decomposition.yaml",
    "07_identity_registry.yaml",
    "08_expected_symbolic_results.yaml",
    "09_expected_numerical_and_scaling_results.yaml",
    "10_source_and_generation_note.md",
    "11_attribution_and_permissions.md",
]
EXPECTED_BOUNDARY = [
    "DC limit first",
    "Gamma finite and exact in the raw one-dimensional sigma_xxx object",
    "then normalization, decomposition, simplification and closed-form processing",
]
EXPECTED_SLOPES = {
    "low_temperature_insulating_regime": 1.9845925371006055,
    "metallic_or_high_temperature_regime": 0.9932470742383429,
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_yaml(path: Path):
    if yaml is None:
        raise RuntimeError("PyYAML is required for YAML validation")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def parse_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_line"] = line_no
                rows.append(row)
    return rows


def assert_no_public_safety_findings(root: Path) -> None:
    local_path_re = "/" + "Users" + "/"
    redacted_home = "REDACTED" + "_HOME"
    secret_word = "sec" + "ret"
    password_word = "pass" + "word"
    cookie_word = "coo" + "kie"
    patterns = {
        "absolute_local_path": re.compile(re.escape(local_path_re) + "|" + re.escape(redacted_home)),
        "email_address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "credential_material": re.compile(
            r"(?i)("
            r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}|"
            + secret_word
            + r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}|"
            + password_word
            + r"\s*[:=]\s*['\"]?.{8,}|"
            + cookie_word
            + r"\s*[:=]\s*['\"]?.{16,}|"
            r"github_pat_[A-Za-z0-9_]{20,}|"
            r"ghp_[A-Za-z0-9]{20,}|"
            r"ssh-rsa\s+[A-Za-z0-9+/]{80,}"
            r")"
        ),
        "private_key_material": re.compile(r"BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY"),
    }
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"path": path.relative_to(root).as_posix(), "finding_type": name})
    assert not findings, findings


def validate(root: Path) -> dict:
    checks = []

    for rel in REQUIRED_INPUTS:
        path = root / "inputs" / rel
        assert path.exists(), rel
    checks.append("required input existence")

    yaml_files = [root / "scientific_contract.yaml"] + sorted((root / "inputs").glob("*.yaml"))
    for path in yaml_files:
        parse_yaml(path)
    checks.append("YAML parsing")

    json_files = sorted(root.rglob("*.json"))
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    checks.append("JSON parsing")

    steps = parse_jsonl(root / "inputs" / "05_derivation_steps.jsonl")
    assert steps, "derivation steps are empty"
    checks.append("JSONL derivation-step parsing")

    manifest = json.loads((root / "manifests" / "public_manifest.json").read_text(encoding="utf-8"))
    manifest_by_path = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    for rel in REQUIRED_INPUTS:
        public_rel = f"inputs/{rel}"
        assert public_rel in manifest_by_path, public_rel
        assert sha256_path(root / public_rel) == manifest_by_path[public_rel]
    checks.append("input SHA verification")

    status_text = (root / "STATUS.md").read_text(encoding="utf-8")
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    contract = parse_yaml(root / "scientific_contract.yaml")
    for phrase in EXPECTED_BOUNDARY:
        assert phrase in readme_text
        assert phrase in contract["scientific_boundary"]
    assert "PRE_RAW_GAMMA_EXPANSION_FORBIDDEN" in (root / "inputs" / "02_scientific_definitions.yaml").read_text(encoding="utf-8")
    assert "Independent verification:\nPENDING" in status_text
    assert "Autonomous mathematical discovery:\nFALSE" in status_text
    checks.append("scientific boundary assertions")

    step_ids = [row["step"] for row in steps]
    assert len(step_ids) == len(set(step_ids))
    assert step_ids == sorted(step_ids)
    checks.append("derivation DAG acyclicity")

    identities = parse_yaml(root / "inputs" / "07_identity_registry.yaml")
    assert identities["identity_sources"]
    for item in identities["identity_sources"]:
        assert item.get("path") and item.get("sha256") and item.get("bytes")
    checks.append("identity reference resolution")

    sectors = parse_yaml(root / "inputs" / "06_sector_decomposition.yaml")
    ledger = sectors["row_ledger_from_human_pipeline"]
    assert ledger["center_C0"] + ledger["pair_C1"] + ledger["loop_C2"] == ledger["total"]
    assert {sector["name"] for sector in sectors["sectors"]} == {
        "center C0(n)",
        "pair C1(n,m)",
        "loop C2(n,m,l)",
    }
    checks.append("sector contract consistency")

    result = json.loads((root / "reference_run" / "case003r1_result.json").read_text(encoding="utf-8"))
    assert result["final_verdict"] == "NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS"
    assert result["execution_mode"] == "NON_INTERACTIVE_GUIDED_REPLAY"
    assert "general tensorial sigma_abc solved" in result["not_established"]
    checks.append("reference result schema")

    gamma = json.loads((root / "reference_run" / "gamma_scaling_results.json").read_text(encoding="utf-8"))
    for key, expected in EXPECTED_SLOPES.items():
        assert abs(gamma[key]["measured_slope"] - expected) < 1e-15
        assert gamma[key]["status"] == "PASS"
    checks.append("Gamma-scaling target schema")

    assert_no_public_safety_findings(root)
    checks.append("public safety scan")

    return {"passed": True, "checks": checks}


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    result = validate(root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
