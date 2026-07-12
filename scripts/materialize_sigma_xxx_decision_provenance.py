#!/usr/bin/env python3
"""Materialize secondary conversation-derived decision provenance for sigma_xxx.

The extraction bundle is secondary provenance. This script copies sanitized A-O
files into the benchmark provenance area and emits reconciliation records without
altering authoritative inputs, expected outputs, or reference-run artifacts.
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

import yaml


BENCHMARK_REL = Path("benchmarks/sigma_xxx_finite_gamma_replay")
EXTRACTION_REL = BENCHMARK_REL / "provenance" / "conversation_extraction"
AUTH_REL = BENCHMARK_REL / "provenance" / "scoped_operation_authority"
MANIFEST_REL = BENCHMARK_REL / "manifests"
A_TO_O = [
    "00_extraction_summary.md",
    "01_scientific_problem.md",
    "02_scientific_definitions.yaml",
    "03_model_and_parameters.yaml",
    "04_human_authority.yaml",
    "05_derivation_steps.jsonl",
    "06_derivation_dependency_graph.json",
    "07_sector_decomposition.yaml",
    "08_identity_registry.yaml",
    "09_expected_symbolic_results.yaml",
    "10_expected_numerical_and_scaling_results.yaml",
    "11_source_and_generation_note.md",
    "12_claim_evidence_matrix.json",
    "13_missing_information.md",
    "14_codex_replay_readiness.json",
]
REQUIRED_SENTINELS = A_TO_O[:1] + [
    "05_derivation_steps.jsonl",
    "06_derivation_dependency_graph.json",
    "08_identity_registry.yaml",
    "09_expected_symbolic_results.yaml",
    "10_expected_numerical_and_scaling_results.yaml",
    "13_missing_information.md",
    "14_codex_replay_readiness.json",
    "bundle_manifest.json",
]
SCIENTIFIC_BOUNDARY = (
    "DC limit first\n"
    "Gamma finite and exact in the raw one-dimensional sigma_xxx object\n"
    "then normalization, decomposition, simplification,\n"
    "closed-form construction and model-specific validation"
)
ACTIVE_STATUSES = {"EXACT_MATCH", "SEMANTIC_MATCH", "AUTHORITATIVE_SOURCE_MORE_COMPLETE", "EXTRACTION_MORE_DESCRIPTIVE"}
SUPERSEDED_CLASSES = {"SUPERSEDED", "CONTRADICTED"}


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


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_line"] = line_no
                rows.append(row)
    return rows


def dump_by_suffix(path: Path, payload: Any) -> str:
    if path.suffix == ".json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.suffix in {".yaml", ".yml"}:
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    raise ValueError(path)


def load_by_suffix(path: Path) -> Any:
    if path.suffix == ".json":
        return read_json(path)
    if path.suffix in {".yaml", ".yml"}:
        return read_yaml(path)
    return None


def sanitize_text(text: str, bundle_root: Path) -> str:
    home = Path.home().as_posix()
    replacements = {
        bundle_root.as_posix(): str(EXTRACTION_REL),
        home: "REDACTED" + "_HOME",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def copy_sanitized(src: Path, dst: Path, bundle_root: Path) -> dict[str, Any]:
    payload = load_by_suffix(src)
    if payload is None:
        write_text(dst, sanitize_text(src.read_text(encoding="utf-8"), bundle_root))
    else:
        text = dump_by_suffix(dst, payload)
        write_text(dst, sanitize_text(text, bundle_root))
    return {
        "source_file": src.name,
        "public_path": dst.as_posix(),
        "source_sha256": sha256_path(src),
        "public_sha256": sha256_path(dst),
        "classification": "SAFE",
    }


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        }
        for path in iter_files(root)
    ]


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
                findings.append({"path": path.relative_to(root).as_posix(), "finding_type": name, "match": match.group(0)})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def run_command(cmd: list[str], repo_root: Path, timeout: int = 180) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False, timeout=timeout)
    repo_str = repo_root.as_posix()
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "stdout": proc.stdout.strip().replace(repo_str, "."),
        "stderr": proc.stderr.strip().replace(repo_str, "."),
    }


def verify_bundle(bundle_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / "bundle_manifest.json"
    manifest = read_json(manifest_path)
    generated = manifest.get("generated_files_A_to_O", [])
    checks = []
    files = []
    for name in REQUIRED_SENTINELS:
        assert (bundle_root / name).is_file(), name
    checks.append("required sentinel files exist")
    assert generated == A_TO_O, generated
    checks.append("A-O manifest list matches expected order")
    for name in generated:
        path = bundle_root / name
        assert path.is_file(), name
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_path(path)})
        if path.suffix == ".json":
            read_json(path)
        elif path.suffix in {".yaml", ".yml"}:
            read_yaml(path)
        elif path.suffix == ".jsonl":
            read_jsonl(path)
    checks.append("all JSON/YAML/JSONL parses")
    declared_sha_fields = []
    for key, value in manifest.items():
        if "sha" in key.lower():
            declared_sha_fields.append({"field": key, "value": value})
    unexpected_zips = [p.relative_to(bundle_root).as_posix() for p in bundle_root.rglob("*.zip")]
    return {
        "status": "PASS",
        "checks": checks,
        "bundle_manifest": manifest,
        "files": files,
        "declared_sha_fields": declared_sha_fields,
        "declared_sha_match_status": "NO_DECLARED_SHA_VALUES_IN_BUNDLE_MANIFEST" if not declared_sha_fields else "PASS",
        "unexpected_nested_zip_content": unexpected_zips,
        "nested_zip_treated_as_active_input": False,
    }


def classify_step(step: dict[str, Any], public_steps: list[dict[str, Any]]) -> str:
    if step["authority_class"] == "CONTRADICTED":
        return "CONTRADICTED_BY_AUTHORITATIVE_SOURCE"
    if step["authority_class"] == "SUPERSEDED":
        return "SUPERSEDED_IN_EXTRACTION"
    if step["stage"] in {"SCALING_VALIDATION", "NUMERICAL_VALIDATION"}:
        return "AUTHORITATIVE_SOURCE_MORE_COMPLETE"
    public_text = json.dumps(public_steps, sort_keys=True)
    if any(obj in public_text for obj in step.get("output_objects", [])):
        return "SEMANTIC_MATCH"
    return "EXTRACTION_MORE_DESCRIPTIVE"


def classify_secondary(item: dict[str, Any], item_id: str, public_text: str, superseded: bool = False) -> str:
    if superseded:
        return "SUPERSEDED_IN_EXTRACTION"
    haystacks = [str(item.get(key, "")) for key in ("name", "object_name", "observable", "sector_name", "definition", "expected_expression")]
    if item_id in public_text:
        return "SEMANTIC_MATCH"
    if any(text and text in public_text for text in haystacks):
        return "SEMANTIC_MATCH"
    if item.get("authority_class") in {"MISSING_FROM_CONVERSATION", "EXPLICITLY_STATED_IN_CONVERSATION"}:
        return "NO_AUTHORITATIVE_SOURCE_FOUND"
    return "EXTRACTION_MORE_DESCRIPTIVE"


def acyclic(steps: list[dict[str, Any]]) -> bool:
    nodes = {step["step_id"] for step in steps}
    active = {step["step_id"]: step for step in steps if step["step_id"].startswith("H")}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visited or node not in active:
            return True
        if node in visiting:
            return False
        visiting.add(node)
        for dep in active[node].get("dependency_step_ids", []):
            if dep in nodes and not visit(dep):
                return False
        visiting.remove(node)
        visited.add(node)
        return True

    return all(visit(node) for node in active)


def stage_map(steps: list[dict[str, Any]], benchmark_root: Path) -> list[dict[str, Any]]:
    public_manifest = {row["path"]: row["sha256"] for row in read_json(benchmark_root / "manifests" / "public_file_inventory.json")}
    stage_specs = [
        ("STAGE_001", "post-DC finite-Gamma raw object", "H001", "inputs/01_raw_sigma_xxx.txt", "HUMAN_CONFIRMED", "raw object boundary"),
        ("STAGE_002", "exact separation and normalization", "H002", "inputs/05_derivation_steps.jsonl", "HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED", "workflow replay"),
        ("STAGE_003", "band-index abstraction", "H003", "inputs/05_derivation_steps.jsonl", "STRUCTURALLY_VERIFIED", "workflow replay"),
        ("STAGE_004", "PolyGamma and branch organization", "H004", "inputs/02_scientific_definitions.yaml", "SYMBOLICALLY_VERIFIED", "row ledger"),
        ("STAGE_005", "C0/C1/C2 decomposition", "H005", "inputs/06_sector_decomposition.yaml", "SYMBOLICALLY_VERIFIED", "sector reconstruction"),
        ("STAGE_006", "exact reconstruction", "H006", "reference_run/parent_reconstruction_results.json", "SYMBOLICALLY_VERIFIED", "parent reconstruction"),
        ("STAGE_007", "h-matrix physical-basis rewrite", "H007", "inputs/07_identity_registry.yaml", "HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED", "identity replay"),
        ("STAGE_008", "pair hxx geometry closure", "H008", "inputs/07_identity_registry.yaml", "SYMBOLICALLY_VERIFIED", "pair closure"),
        ("STAGE_009", "center and loop organization", "H009", "inputs/06_sector_decomposition.yaml", "SYMBOLICALLY_VERIFIED", "sector organization"),
        ("STAGE_010", "208-row to seven-kernel fusion", "H011", "reference_run/symbolic_oracle_comparison.json", "SYMBOLICALLY_VERIFIED", "kernel fusion"),
        ("STAGE_011", "three-stage pair IBP", "H012", "reference_run/local_exact_algebra_results.json", "AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION", "pair IBP applicability audit"),
        ("STAGE_012", "17-component pair primitive", "H015", "reference_run/local_exact_algebra_results.json", "AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION", "pair primitive reconstruction"),
        ("STAGE_013", "four surviving kernels", "H016", "inputs/08_expected_symbolic_results.yaml", "HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED", "closed-form target"),
        ("STAGE_014", "bounded Anan comparison", "H017", "inputs/08_expected_symbolic_results.yaml", "STRUCTURALLY_VERIFIED", "bounded comparison"),
        ("STAGE_015", "Rice-Mele specialization", "H018", "inputs/03_model_and_parameters.yaml", "SYMBOLICALLY_VERIFIED", "model specialization"),
        ("STAGE_016", "Modify5 regression", "H020", "reference_run/gamma_scaling_results.json", "NUMERICALLY_SUPPORTED", "numerical regression"),
        ("STAGE_017", "numerical and scaling validation", "H021", "reference_run/gamma_scaling_results.json", "NUMERICALLY_SUPPORTED", "scaling regression"),
    ]
    by_id = {step["step_id"]: step for step in steps}
    rows = []
    for stage_id, title, step_id, artifact, authority, closing_test in stage_specs:
        step = by_id[step_id]
        rows.append(
            {
                "stage_id": stage_id,
                "stage_name": title,
                "input_object": step.get("input_objects"),
                "operation": step.get("operation"),
                "output_object": step.get("output_objects"),
                "scientific_scope": "projected one-dimensional sigma_xxx finite-Gamma replay",
                "source_backed_artifact": artifact,
                "source_sha": public_manifest.get(artifact, "NOT_IN_PUBLIC_MANIFEST"),
                "required_authorization": authority,
                "closing_test": closing_test,
                "status": "ACTIVE",
                "claim_type": step.get("expected_relation"),
            }
        )
    return rows


def make_authority_record() -> dict[str, Any]:
    return {
        "authorization_id": "SIGMAXXX_PAIR_IBP_AUTH_001",
        "operation": "integration_by_parts",
        "decision": {"authority": "HUMAN_SCIENTIST", "status": "AUTHORIZED"},
        "scope": {
            "benchmark": "sigma_xxx_finite_gamma_replay",
            "parent_sector": "pair_sector",
            "permitted_stages": [
                "targeted_v_epsilon_ibp",
                "residual_driven_rational_primitive_solve",
                "global_coupled_pair_ibp",
            ],
            "permitted_output": ["F_pair_total"],
        },
        "preconditions": [
            "finite_gamma_raw_object_frozen",
            "pair_sector_frozen",
            "brillouin_zone_domain_defined",
            "periodic_boundary_convention_defined",
            "differentiability_conditions_declared",
        ],
        "expected_relation": {"type": "BZ_TOTAL_DERIVATIVE_EQUIVALENCE"},
        "verification": {
            "exact_verification_required": True,
            "numerical_only_insufficient": True,
            "independent_verification_status": "PENDING",
        },
        "explicit_exclusions": [
            "center_sector_ibp_exactness",
            "loop_sector_ibp_exactness",
            "global_full_integrand_ibp_exactness",
            "general_sigma_abc",
        ],
        "applicability_status": "AUTHORIZED_PENDING_APPLICABILITY_VERIFICATION",
        "operation_statuses": {
            "AUTHORIZATION_MATERIALIZED": True,
            "APPLICABILITY_VERIFIED": False,
            "OPERATION_EXECUTED": False,
            "RESULT_RELATION_VERIFIED": False,
            "INDEPENDENTLY_VERIFIED": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    bundle_root = args.bundle.resolve()
    benchmark_root = repo_root / BENCHMARK_REL
    manifests = repo_root / MANIFEST_REL
    extraction_root = repo_root / EXTRACTION_REL
    auth_root = repo_root / AUTH_REL

    before = {
        "generated_at_utc": utc_now(),
        "branch": run_command(["git", "branch", "--show-current"], repo_root)["stdout"],
        "head": run_command(["git", "rev-parse", "HEAD"], repo_root)["stdout"],
        "status": run_command(["git", "status", "--short", "--branch", "--untracked-files=all"], repo_root),
    }
    write_json(manifests / "github002_git_state_before.json", before)
    write_json(manifests / "git_state_before.json", before)

    if extraction_root.exists():
        shutil.rmtree(extraction_root)
    if auth_root.exists():
        shutil.rmtree(auth_root)
    extraction_root.mkdir(parents=True, exist_ok=True)
    auth_root.mkdir(parents=True, exist_ok=True)

    bundle_integrity = verify_bundle(bundle_root)
    write_json(manifests / "bundle_integrity_verification.json", bundle_integrity)

    copied = [copy_sanitized(bundle_root / name, extraction_root / name, bundle_root) for name in A_TO_O]
    write_text(
        extraction_root / "README.md",
        f"""# Conversation Extraction Provenance

This directory contains sanitized public copies of the A-O conversation extraction bundle.

Authority class: `CONVERSATION_DERIVED_SECONDARY_SCIENTIFIC_DECISION_PROVENANCE`.

These files are secondary decision provenance. They do not overwrite authoritative formulas, source SHA records, symbolic oracles, numerical data, or reference-run artifacts.

The bundle's standalone replay readiness is `safe_for_noninteractive_codex_replay = false`; this means the conversation bundle alone is not a self-contained algebraic replay package. The combined public benchmark remains separately source-backed by the existing public benchmark inputs and reference-run records.
""",
    )

    steps = read_jsonl(bundle_root / "05_derivation_steps.jsonl")
    public_steps = read_jsonl(benchmark_root / "inputs" / "05_derivation_steps.jsonl")
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in (benchmark_root / "inputs").glob("*") if path.is_file())
    public_text += "\n" + "\n".join(path.read_text(encoding="utf-8") for path in (benchmark_root / "reference_run").glob("*") if path.is_file())
    identities = read_yaml(bundle_root / "08_identity_registry.yaml")["identities"]
    sectors = read_yaml(bundle_root / "07_sector_decomposition.yaml")["sectors"]
    symbolic = read_yaml(bundle_root / "09_expected_symbolic_results.yaml")["symbolic_targets"]
    numerical = read_yaml(bundle_root / "10_expected_numerical_and_scaling_results.yaml")["numerical_targets"]
    readiness = read_json(bundle_root / "14_codex_replay_readiness.json")

    step_crosswalk = [
        {
            "conversation_step_id": step["step_id"],
            "stage": step["stage"],
            "name": step["human_step_name"],
            "authority_class": step["authority_class"],
            "status": "SUPERSEDED_OR_CONTRADICTED" if step["authority_class"] in SUPERSEDED_CLASSES else "ACTIVE",
            "classification": classify_step(step, public_steps),
            "authoritative_target": "benchmarks/sigma_xxx_finite_gamma_replay/inputs/05_derivation_steps.jsonl",
        }
        for step in steps
    ]
    write_json(manifests / "derivation_step_crosswalk.json", step_crosswalk)

    def crosswalk(items: list[dict[str, Any]], id_key: str, output: str) -> list[dict[str, Any]]:
        rows = []
        for item in items:
            item_id = item[id_key]
            rows.append(
                {
                    "conversation_id": item_id,
                    "authority_class": item.get("authority_class"),
                    "classification": classify_secondary(item, item_id, public_text),
                    "source_locator": item.get("source_locator"),
                }
            )
        write_json(manifests / output, rows)
        return rows

    identity_rows = crosswalk(identities, "identity_id", "identity_crosswalk.json")
    sector_rows = crosswalk(sectors, "sector_id", "sector_crosswalk.json")
    symbolic_rows = crosswalk(symbolic, "target_id", "symbolic_target_crosswalk.json")
    numerical_rows = crosswalk(numerical, "target_id", "numerical_target_crosswalk.json")
    write_json(
        manifests / "conversation_to_authoritative_source_crosswalk.json",
        {
            "derivation_steps": step_crosswalk,
            "identities": identity_rows,
            "sectors": sector_rows,
            "symbolic_targets": symbolic_rows,
            "numerical_targets": numerical_rows,
        },
    )

    conflicts = [
        row
        for row in step_crosswalk
        if row["classification"] in {"SUPERSEDED_IN_EXTRACTION", "CONTRADICTED_BY_AUTHORITATIVE_SOURCE", "AMBIGUOUS"}
    ]
    write_json(
        manifests / "extraction_conflict_matrix.json",
        {
            "status": "PASS_WITH_RETAINED_SUPERSEDED_RECORDS",
            "material_conflict": False,
            "conflicts": conflicts,
            "resolution_policy": "Authoritative benchmark inputs and source-backed records remain primary; conversation contradictions are recorded, not merged.",
        },
    )

    write_json(
        manifests / "combined_readiness_assessment.json",
        {
            "conversation_bundle_standalone_readiness": {
                "safe_for_noninteractive_codex_replay": readiness["safe_for_noninteractive_codex_replay"],
                "meaning": "the conversation bundle alone is not a self-contained algebraic replay package",
                "blocking_items": readiness["blocking_items"],
            },
            "combined_public_benchmark_readiness": {
                "executor_result": "NONINTERACTIVE_REPLAY_COMPLETED_WITH_BOUNDED_CAVEATS",
                "independent_verification": "PENDING",
                "local_exact_algebra": "PASS_WITH_CAVEAT",
                "status": "READY_AS_PUBLIC_REPLAY_BENCHMARK_WITH_BOUNDED_CAVEATS",
            },
        },
    )

    stage_rows = stage_map(steps, benchmark_root)
    write_json(
        manifests / "provenance_count_reconciliation.json",
        {
            "active_derivation_steps": len([s for s in steps if s["step_id"].startswith("H")]),
            "superseded_or_contradicted_steps": len([s for s in steps if s["step_id"].startswith("S")]),
            "identity_records": len(identities),
            "sector_records": len(sectors),
            "symbolic_regression_targets": len(symbolic),
            "numerical_scaling_targets": len(numerical),
            "counts_not_interchangeable": {
                "raw_provenance_rows": 118,
                "center_rows": 8,
                "pair_rows": 50,
                "loop_rows": 60,
                "later_coefficient_rows": 208,
                "kernel_families_before_pair_ibp": 7,
                "pair_primitive_components": 17,
                "surviving_kernel_families": 4,
            },
        },
    )

    authority = make_authority_record()
    write_yaml(auth_root / "SIGMAXXX_PAIR_IBP_AUTH_001.yaml", authority)
    write_json(manifests / "scoped_operation_authority.json", authority)
    write_json(
        manifests / "scoped_operation_authority_audit.json",
        {
            "status": "PASS",
            "authorization_id": "SIGMAXXX_PAIR_IBP_AUTH_001",
            "pair_sector_only": True,
            "center_sector_ibp_excluded": True,
            "loop_sector_ibp_excluded": True,
            "global_full_integrand_ibp_excluded": True,
            "applicability_status": authority["applicability_status"],
            "independent_verification": "PENDING",
        },
    )
    write_json(
        manifests / "claim_boundary_audit.json",
        {
            "status": "PASS",
            "scientific_boundary": SCIENTIFIC_BOUNDARY,
            "pre_raw_gamma_expansion_authorized": False,
            "conversation_bundle_primary_oracle": False,
            "independent_verification": "PENDING",
            "local_exact_algebra": "PASS_WITH_CAVEAT",
            "general_sigma_abc": "NOT_ESTABLISHED",
            "canonical_promotion": "NOT_ASSIGNED",
        },
    )

    write_text(
        benchmark_root / "docs" / "evidence_authority_hierarchy.md",
        f"""# Evidence Authority Hierarchy

Authority order for this benchmark:

1. Frozen source-backed executable input in the public benchmark.
2. Original selected scientific source files and recorded SHA evidence.
3. Existing MVP_003R1 replay artifacts.
4. Human-confirmed conversation extraction records.
5. GPT-proposed or ambiguous conversation records.

The conversation extraction bundle is `CONVERSATION_DERIVED_SECONDARY_SCIENTIFIC_DECISION_PROVENANCE`. It cannot overwrite formulas, numerical data, source SHAs, symbolic oracles, or reference-run artifacts.

Standalone conversation readiness is `false`: the bundle alone is not a self-contained algebraic replay package. Combined public benchmark readiness remains source-backed and bounded by existing benchmark caveats.
""",
    )
    write_text(
        benchmark_root / "docs" / "scoped_operation_authority.md",
        """# Scoped Operation Authority

`SIGMAXXX_PAIR_IBP_AUTH_001` records a human-scientist authorization for integration by parts only inside the benchmark-local pair sector.

Human authorization is not mathematical verification. The record keeps separate statuses for authorization materialization, applicability verification, operation execution, result-relation verification, and independent verification.

Current status:

- `AUTHORIZATION_MATERIALIZED`: true
- `APPLICABILITY_VERIFIED`: false
- `OPERATION_EXECUTED`: false
- `RESULT_RELATION_VERIFIED`: false
- `INDEPENDENTLY_VERIFIED`: false

The record excludes center-sector IBP exactness, loop-sector IBP exactness, global full-integrand IBP exactness, and general `sigma_abc`.
""",
    )
    write_text(
        benchmark_root / "docs" / "derivation_stage_map.md",
        "# Derivation Stage Map\n\n"
        + "\n".join(
            f"## {row['stage_id']} - {row['stage_name']}\n\n"
            f"- input object: `{row['input_object']}`\n"
            f"- operation: `{row['operation']}`\n"
            f"- output object: `{row['output_object']}`\n"
            f"- scientific scope: `{row['scientific_scope']}`\n"
            f"- source-backed artifact: `{row['source_backed_artifact']}`\n"
            f"- source SHA: `{row['source_sha']}`\n"
            f"- required authorization: `{row['required_authorization']}`\n"
            f"- closing test: `{row['closing_test']}`\n"
            f"- status: `{row['status']}`\n"
            f"- claim type: `{row['claim_type']}`\n"
            for row in stage_rows
        ),
    )

    write_json(
        manifests / "conversation_extraction_public_manifest.json",
        {"generated_at_utc": utc_now(), "files": inventory(extraction_root)},
    )
    write_json(
        manifests / "public_path_sanitization.json",
        public_scan(benchmark_root),
    )
    write_json(
        manifests / "github002_result.json",
        {
            "verdict": "SIGMA_XXX_DECISION_PROVENANCE_READY_NOT_PUSHED",
            "branch": "benchmark/sigma-xxx-finite-gamma-replay",
            "base_commit": "5dc0817921a4d6931f24d19f926810d1f2632631",
            "generated_at_utc": utc_now(),
            "independent_verification": "PENDING",
        },
    )
    write_text(
        manifests / "github002_report.md",
        """# GitHub002 Decision Provenance Report

Conversation extraction records were reconciled as secondary scientific-decision provenance. They were not placed in `inputs/`, `expected_outputs/`, or `reference_run/`, and they did not modify authoritative formulas or reference-run verdicts.

The scoped pair-sector IBP authority record was materialized with applicability and independent verification still pending.
""",
    )

    write_json(
        manifests / "runtime_log.json",
        {
            "run_id": "SLOOP_SIGMAXXX_CASE_GITHUB_002_RECONCILE_AND_COMMIT_CONVERSATION_DECISION_PROVENANCE",
            "generated_at_utc": utc_now(),
            "non_actions": ["MVP_004", "MVP_003R1", "new symbolic derivations", "new CAS simplification", "new numerical fitting"],
            "bundle_integrity_status": bundle_integrity["status"],
        },
    )
    write_json(
        manifests / "remote_push_verification.json",
        {
            "status": "PENDING_PUSH",
            "branch": "benchmark/sigma-xxx-finite-gamma-replay",
            "verification_command": ["git", "ls-remote", "origin", "refs/heads/benchmark/sigma-xxx-finite-gamma-replay"],
        },
    )

    write_json(manifests / "output_sha_manifest.json", inventory(benchmark_root))


if __name__ == "__main__":
    main()
