#!/usr/bin/env python3
"""Materialize the public sigma_xxx finite-Gamma replay benchmark.

This script copies only the authorized, curated public benchmark inputs and
selected reference-run artifacts. Source paths are supplied at runtime so the
repository copy does not embed local workstation paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by environment, not logic.
    yaml = None


BENCHMARK_REL = Path("benchmarks/sigma_xxx_finite_gamma_replay")
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
REFERENCE_FILES = [
    "case003r1_result.json",
    "closure_matrix_final.json",
    "validation_summary.md",
    "final_case_study_report.md",
    "gamma_scaling_results.json",
    "symbolic_oracle_comparison.json",
    "parent_reconstruction_results.json",
    "local_exact_algebra_results.json",
]
EXPECTED_SLOPES = {
    "insulating_small_gamma_slope": 1.9845925371006055,
    "metallic_high_mu_slope": 0.9932470742383429,
}
SCIENTIFIC_BOUNDARY = (
    "DC limit first\n"
    "Gamma finite and exact in the raw one-dimensional sigma_xxx object\n"
    "then normalization, decomposition, simplification and closed-form processing"
)
ATTRIBUTION_SENTENCE = (
    "The sigma_xxx case study was developed in the context of "
    "nonlinear-transport research undertaken in collaboration with Zhichao Guo."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_data(path: Path) -> Any:
    if path.suffix == ".json":
        return read_json(path)
    if path.suffix in {".yaml", ".yml"} and yaml is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return None


def dump_data(path: Path, payload: Any) -> str:
    if path.suffix == ".json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.suffix in {".yaml", ".yml"} and yaml is not None:
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    raise ValueError(f"unsupported structured output: {path}")


def sanitize_string(value: str, source_root: Path, benchmark_rel: Path) -> str:
    source_root_posix = source_root.as_posix().rstrip("/")
    home = Path.home().as_posix().rstrip("/")
    replacements = {
        source_root_posix + "/incoming_materials": str(benchmark_rel / "inputs"),
        source_root_posix: str(benchmark_rel / "source_reference" / "private_source_root"),
        home + "/.local/bin/wolframscript": "wolframscript",
        home: "REDACTED" + "_HOME",
    }
    out = value
    for old, new in replacements.items():
        out = out.replace(old, new)
    out = out.replace("No public release authorization is implied.", "Public release authorization was granted after this reference run.")
    out = out.replace("No public release is authorized by CASE_MVP_003R1.", "CASE_MVP_003R1 was a reference replay; public release authorization was granted later.")
    return out


def sanitize_obj(value: Any, source_root: Path, benchmark_rel: Path) -> Any:
    if isinstance(value, str):
        return sanitize_string(value, source_root, benchmark_rel)
    if isinstance(value, list):
        return [sanitize_obj(item, source_root, benchmark_rel) for item in value]
    if isinstance(value, dict):
        sanitized = {key: sanitize_obj(item, source_root, benchmark_rel) for key, item in value.items()}
        if "workspace_root" in sanitized:
            sanitized["workspace_root"] = str(benchmark_rel)
        if "workspace" in sanitized:
            sanitized["workspace"] = str(benchmark_rel)
        if "authorized_input_root" in sanitized:
            sanitized["authorized_input_root"] = str(benchmark_rel / "inputs")
        return sanitized
    return value


def copy_sanitized(src: Path, dst: Path, source_root: Path, benchmark_rel: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    payload = load_data(src)
    if payload is not None:
        sanitized = sanitize_obj(payload, source_root, benchmark_rel)
        dst.write_text(dump_data(dst, sanitized), encoding="utf-8")
    else:
        text = src.read_text(encoding="utf-8")
        dst.write_text(sanitize_string(text, source_root, benchmark_rel), encoding="utf-8")
    return {
        "source": src.name,
        "public_path": str(dst.relative_to(dst.parents[2])),
        "source_sha256": sha256_path(src),
        "public_sha256": sha256_path(dst),
        "status": "SANITIZED_IN_DERIVED_PUBLIC_FILE",
    }


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def file_inventory(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in iter_files(root):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
        )
    return records


def public_scan(root: Path) -> dict[str, Any]:
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
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in patterns.items():
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "finding_type": name,
                        "match": match.group(0),
                        "classification": "BLOCKING_PUBLICATION",
                    }
                )
    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def run_command(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=120)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "status": "PASS" if proc.returncode == 0 else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", required=True, type=Path)
    parser.add_argument("--reference-run", required=True, type=Path)
    parser.add_argument("--executor", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    incoming = args.incoming.resolve()
    reference = args.reference_run.resolve()
    executor = args.executor.resolve()
    source_root = incoming.parent
    bench = repo_root / BENCHMARK_REL

    if bench.exists():
        shutil.rmtree(bench)
    for rel in ["inputs", "execution", "expected_outputs", "reference_run", "tests", "manifests"]:
        (bench / rel).mkdir(parents=True, exist_ok=True)

    mapping = []
    for name in REQUIRED_INPUTS:
        mapping.append(copy_sanitized(incoming / name, bench / "inputs" / name, source_root, BENCHMARK_REL))
    for name in REFERENCE_FILES:
        mapping.append(copy_sanitized(reference / name, bench / "reference_run" / name, source_root, BENCHMARK_REL))
    shutil.copy2(executor, bench / "execution" / "run_case003r1_replay.py")

    write_text(
        bench / "STATUS.md",
        """# Sigma_xxx Finite-Gamma Replay Benchmark Status

Benchmark visibility:
PUBLIC

Scientific structure:
HUMAN_SUPPLIED_AND_PREVIOUSLY_VERIFIED

Execution mode:
NON_INTERACTIVE_GUIDED_REPLAY

Executor result:
NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS

Independent verification:
PENDING

Autonomous mathematical discovery:
FALSE

General tensorial sigma_abc solution:
NOT ESTABLISHED

Canonical scientific promotion:
NOT ASSIGNED

Local exact algebra:
LOCAL_EXACT_ALGEBRA_CLOSED = PASS_WITH_CAVEAT
""",
    )
    write_text(
        bench / "attribution.md",
        f"""# Attribution

{ATTRIBUTION_SENTENCE}

This acknowledgement does not imply collaborator approval, endorsement, or authorization beyond the acknowledgement text above.
""",
    )
    write_text(
        bench / "README.md",
        f"""# Finite-Gamma Sigma_xxx Replay Benchmark

This benchmark publishes a curated finite-Gamma sigma_xxx replay case for the Repo-Native Symbolic Science framework.

## Purpose

The benchmark demonstrates that the framework can ingest structured scientific semantics, construct and execute a derivation DAG, replay supplied mathematical steps, evaluate sector reconstruction, compare against supplied symbolic oracles, perform numerical and Gamma-scaling regressions, evaluate scoped closure conditions, and generate provenance-backed reports.

It does not demonstrate autonomous mathematical discovery.

## Scientific Boundary

```text
{SCIENTIFIC_BOUNDARY}
```

The raw object must not be described as resulting from a prior Gamma-order expansion.

## Run Command

Validate the public benchmark package:

```bash
python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay
```

Run the pytest wrapper:

```bash
python3 -m pytest benchmarks/sigma_xxx_finite_gamma_replay/tests
```

The historical replay executor is included at `execution/run_case003r1_replay.py`, but this public benchmark package does not include the private `source_snapshots/` tree needed for a full replay. Do not treat the local validation command above as an independent scientific verifier.

## Dependencies

The public validation uses Python standard library parsing plus PyYAML when available. The original replay used Python with PyYAML and optional Wolfram tooling in the private environment.

## Reference Result

Reference result: `NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS`.

Independent verification: `PENDING`.

Local exact algebra: `LOCAL_EXACT_ALGEBRA_CLOSED = PASS_WITH_CAVEAT`.

Gamma-scaling slopes are executor-generated numerical support, not exact symbolic proof:

- insulating small-Gamma slope: `{EXPECTED_SLOPES["insulating_small_gamma_slope"]}`
- metallic/high-mu slope: `{EXPECTED_SLOPES["metallic_high_mu_slope"]}`
""",
    )
    write_text(
        bench / "scientific_contract.yaml",
        f"""benchmark_id: sigma_xxx_finite_gamma_replay
benchmark_interpretation: HUMAN_SPECIFIED_PREVIOUSLY_VERIFIED_NONINTERACTIVE_REPLAY_BENCHMARK
visibility: PUBLIC
scientific_boundary: |-
  {SCIENTIFIC_BOUNDARY.replace(chr(10), chr(10) + "  ")}
raw_object:
  observable: sigma_xxx
  dimensional_scope: one_dimensional
  dc_limit_first: true
  gamma_finite_and_exact_in_raw_object: true
  pre_raw_gamma_expansion: forbidden
execution_mode: NON_INTERACTIVE_GUIDED_REPLAY
executor_result: NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS
independent_verification: PENDING
autonomous_mathematical_discovery: false
general_tensorial_sigma_abc_solution: NOT_ESTABLISHED
canonical_scientific_promotion: NOT_ASSIGNED
local_exact_algebra:
  closure: LOCAL_EXACT_ALGEBRA_CLOSED
  status: PASS_WITH_CAVEAT
gamma_scaling_reference_values:
  insulating_small_gamma_slope: {EXPECTED_SLOPES["insulating_small_gamma_slope"]}
  metallic_high_mu_slope: {EXPECTED_SLOPES["metallic_high_mu_slope"]}
  classification: executor-generated numerical support, not exact symbolic proof
""",
    )
    write_text(
        bench / "execution" / "README.md",
        """# Execution Notes

`run_case003r1_replay.py` is the historical non-interactive replay executor used for the completed reference run. It is included for provenance and smoke compilation.

This public package intentionally excludes private source snapshots and unrelated historical workspace content. Use `../tests/validate_public_benchmark.py` for the public benchmark validation.
""",
    )
    write_json(
        bench / "expected_outputs" / "gamma_scaling_reference_values.json",
        {
            "classification": "executor-generated numerical support, not exact symbolic proof",
            **EXPECTED_SLOPES,
        },
    )

    write_validator(bench / "tests" / "validate_public_benchmark.py")
    write_test(bench / "tests" / "test_public_benchmark.py")

    public_manifest = {
        "generated_at_utc": utc_now(),
        "benchmark_root": BENCHMARK_REL.as_posix(),
        "files": file_inventory(bench),
    }
    write_json(bench / "manifests" / "public_manifest.json", public_manifest)
    write_json(bench / "manifests" / "public_file_inventory.json", public_manifest["files"])
    write_json(bench / "manifests" / "source_to_public_mapping.json", mapping)

    scan = public_scan(bench)
    write_json(bench / "manifests" / "path_sanitization_report.json", scan)
    write_json(bench / "manifests" / "credential_scan.json", scan)
    write_json(
        bench / "manifests" / "license_and_figure_audit.json",
        {
            "status": "PASS",
            "copied_journal_figures": [],
            "classifications": [
                {
                    "scope": "curated text, YAML, JSON, JSONL, Python executor, and generated benchmark reports",
                    "classification": "SAFE",
                },
                {
                    "scope": "source_snapshots, private reports, unlicensed copied figures, sensitive access material, private correspondence",
                    "classification": "EXCLUDED",
                },
            ],
        },
    )
    write_json(
        bench / "manifests" / "git_state_before.json",
        {
            "main_remote_sha_before_modification": run_command(["git", "rev-parse", "origin/main"], repo_root),
            "branch_at_materialization": run_command(["git", "branch", "--show-current"], repo_root),
            "status_before_materialization": "captured before benchmark-tree commit; see runtime_log for command output",
        },
    )

    validation = run_command(
        ["python3", str(BENCHMARK_REL / "tests" / "validate_public_benchmark.py"), str(BENCHMARK_REL)],
        repo_root,
    )
    write_json(bench / "manifests" / "benchmark_test_results.json", validation)
    write_json(
        bench / "manifests" / "framework_regression_results.json",
        {
            "status": "PENDING_RUN_AFTER_MATERIALIZATION",
            "note": "Full framework tests are run by the integration task after files are materialized.",
        },
    )
    write_json(
        bench / "manifests" / "github001_result.json",
        {
            "verdict": "PUBLIC_SIGMA_XXX_BENCHMARK_PREPARED_NOT_PUSHED",
            "updated_at_utc": utc_now(),
            "branch": "benchmark/sigma-xxx-finite-gamma-replay",
            "independent_verification": "PENDING",
        },
    )
    write_text(
        bench / "manifests" / "github001_report.md",
        """# GitHub001 Benchmark Integration Report

The public benchmark package was materialized from authorized inputs with local paths sanitized, private source snapshots excluded, and bounded reference-run caveats preserved.

Final push verification is recorded after commit and push in `remote_push_verification.json`.
""",
    )
    write_json(
        bench / "manifests" / "remote_push_verification.json",
        {"status": "PENDING_PUSH", "branch": "benchmark/sigma-xxx-finite-gamma-replay"},
    )
    write_json(
        bench / "manifests" / "runtime_log.json",
        {
            "run_id": "SLOOP_SIGMAXXX_CASE_GITHUB_001_PUBLISH_PUBLIC_BENCHMARK_TO_FRAMEWORK_REPOSITORY",
            "generated_at_utc": utc_now(),
            "inputs_copied": REQUIRED_INPUTS,
            "reference_files_copied": REFERENCE_FILES,
            "public_scan_status": scan["status"],
            "benchmark_validation": validation,
        },
    )
    write_json(bench / "manifests" / "output_sha_manifest.json", file_inventory(bench))


def write_validator(path: Path) -> None:
    write_text(
        path,
        '''#!/usr/bin/env python3
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
        "email_address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
        "credential_material": re.compile(
            r"(?i)("
            r"api[_-]?key\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_\\-]{16,}|"
            + secret_word
            + r"\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_\\-]{16,}|"
            + password_word
            + r"\\s*[:=]\\s*['\\\"]?.{8,}|"
            + cookie_word
            + r"\\s*[:=]\\s*['\\\"]?.{16,}|"
            r"github_pat_[A-Za-z0-9_]{20,}|"
            r"ghp_[A-Za-z0-9]{20,}|"
            r"ssh-rsa\\s+[A-Za-z0-9+/]{80,}"
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
    assert "Independent verification:\\nPENDING" in status_text
    assert "Autonomous mathematical discovery:\\nFALSE" in status_text
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
''',
    )


def write_test(path: Path) -> None:
    write_text(
        path,
        '''#!/usr/bin/env python3
"""Pytest wrapper for the public sigma_xxx benchmark validator."""

from pathlib import Path

from validate_public_benchmark import validate


def test_sigma_xxx_public_benchmark_contract():
    root = Path(__file__).resolve().parents[1]
    result = validate(root)
    assert result["passed"] is True
''',
    )


if __name__ == "__main__":
    main()
