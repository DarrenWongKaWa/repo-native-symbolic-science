#!/usr/bin/env python3
"""Validate conversation-derived decision provenance for the sigma_xxx benchmark."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml


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
PERMITTED_PAIR_STAGES = {
    "targeted_v_epsilon_ibp",
    "residual_driven_rational_primitive_solve",
    "global_coupled_pair_ibp",
}
REQUIRED_PRECONDITIONS = {
    "finite_gamma_raw_object_frozen",
    "pair_sector_frozen",
    "brillouin_zone_domain_defined",
    "periodic_boundary_convention_defined",
    "differentiability_conditions_declared",
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_line"] = line_no
                rows.append(row)
    return rows


def assert_acyclic(steps: list[dict]) -> None:
    active = {row["step_id"]: row for row in steps if row["step_id"].startswith("H")}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visited or step_id not in active:
            return
        assert step_id not in visiting, f"cycle at {step_id}"
        visiting.add(step_id)
        for dep in active[step_id].get("dependency_step_ids", []):
            visit(dep)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in active:
        visit(step_id)


def validate_authority_record(record: dict, exact_evidence_basis: str | None = None) -> None:
    assert record["authorization_id"] == "SIGMAXXX_PAIR_IBP_AUTH_001"
    assert record["operation"] == "integration_by_parts"
    assert record["decision"] == {"authority": "HUMAN_SCIENTIST", "status": "AUTHORIZED"}
    assert record["scope"]["benchmark"] == "sigma_xxx_finite_gamma_replay"
    assert record["scope"]["parent_sector"] == "pair_sector"
    assert set(record["scope"]["permitted_stages"]) == PERMITTED_PAIR_STAGES
    assert record["scope"]["permitted_output"] == ["F_pair_total"]
    assert set(record["preconditions"]) >= REQUIRED_PRECONDITIONS
    assert record["expected_relation"]["type"] == "BZ_TOTAL_DERIVATIVE_EQUIVALENCE"
    assert record["verification"]["exact_verification_required"] is True
    assert record["verification"]["numerical_only_insufficient"] is True
    assert record["verification"]["independent_verification_status"] == "PENDING"
    assert "center_sector_ibp_exactness" in record["explicit_exclusions"]
    assert "loop_sector_ibp_exactness" in record["explicit_exclusions"]
    assert "global_full_integrand_ibp_exactness" in record["explicit_exclusions"]
    assert record["operation_statuses"]["AUTHORIZATION_MATERIALIZED"] is True
    assert record["operation_statuses"]["APPLICABILITY_VERIFIED"] is False
    assert record["operation_statuses"]["OPERATION_EXECUTED"] is False
    assert record["operation_statuses"]["RESULT_RELATION_VERIFIED"] is False
    assert record["operation_statuses"]["INDEPENDENTLY_VERIFIED"] is False
    if exact_evidence_basis is not None:
        assert exact_evidence_basis != "NUMERICAL_ONLY", "numerical evidence cannot verify exact IBP"


def _resolve_benchmark_path(root: Path, path_text: str) -> Path:
    prefix = "benchmarks/sigma_xxx_finite_gamma_replay/"
    if path_text.startswith(prefix):
        return root / path_text[len(prefix):]
    return root / path_text


def validate(root: Path) -> dict:
    checks: list[str] = []
    extraction = root / "provenance" / "conversation_extraction"
    manifests = root / "manifests"

    manifest = json.loads((manifests / "conversation_extraction_public_manifest.json").read_text(encoding="utf-8"))
    manifest_by_path = {row["path"]: row["sha256"] for row in manifest["files"]}
    for rel in A_TO_O:
        path = extraction / rel
        assert path.exists(), rel
        assert rel in manifest_by_path, rel
        assert sha256_path(path) == manifest_by_path[rel], rel
    checks.append("conversation extraction manifest integrity")

    for path in sorted(extraction.glob("*.json")) + sorted(manifests.glob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(extraction.glob("*.yaml")) + sorted((root / "provenance" / "scoped_operation_authority").glob("*.yaml")):
        yaml.safe_load(path.read_text(encoding="utf-8"))
    for path in sorted(extraction.glob("*.jsonl")):
        read_jsonl(path)
    checks.append("JSON/YAML/JSONL parsing")

    steps = read_jsonl(extraction / "05_derivation_steps.jsonl")
    assert len([s for s in steps if s["step_id"].startswith("H")]) == 21
    assert len([s for s in steps if s["step_id"].startswith("S")]) == 4
    assert_acyclic(steps)
    checks.append("derivation DAG parsing and acyclicity")

    identities = yaml.safe_load((extraction / "08_identity_registry.yaml").read_text(encoding="utf-8"))["identities"]
    identity_ids = {row["identity_id"] for row in identities}
    used_identity_ids = {identity_id for step in steps for identity_id in step.get("identity_ids", [])}
    assert used_identity_ids <= identity_ids
    checks.append("identity-reference resolution")

    conflict = json.loads((manifests / "extraction_conflict_matrix.json").read_text(encoding="utf-8"))
    crosswalk = json.loads((manifests / "derivation_step_crosswalk.json").read_text(encoding="utf-8"))
    assert conflict["material_conflict"] is False
    assert {row["conversation_step_id"] for row in conflict["conflicts"]} == {"S001", "S002", "S003", "S004"}
    for row in crosswalk:
        if row["conversation_step_id"].startswith("H"):
            assert row["status"] == "ACTIVE", row
        else:
            assert row["status"] == "SUPERSEDED_OR_CONTRADICTED", row
    checks.append("active versus superseded status consistency")

    combined = json.loads((manifests / "combined_readiness_assessment.json").read_text(encoding="utf-8"))
    assert combined["conversation_bundle_standalone_readiness"]["safe_for_noninteractive_codex_replay"] is False
    assert "not a self-contained algebraic replay package" in combined["conversation_bundle_standalone_readiness"]["meaning"]
    assert combined["combined_public_benchmark_readiness"]["independent_verification"] == "PENDING"
    assert combined["combined_public_benchmark_readiness"]["local_exact_algebra"] == "PASS_WITH_CAVEAT"
    checks.append("combined readiness separation")

    source_crosswalk = json.loads((manifests / "conversation_to_authoritative_source_crosswalk.json").read_text(encoding="utf-8"))
    for group in source_crosswalk.values():
        for row in group:
            target = row.get("authoritative_target")
            if target:
                assert _resolve_benchmark_path(root, target).exists(), target
    checks.append("crosswalk target existence")

    authority = json.loads((manifests / "scoped_operation_authority.json").read_text(encoding="utf-8"))
    validate_authority_record(authority)
    audit = json.loads((manifests / "scoped_operation_authority_audit.json").read_text(encoding="utf-8"))
    assert audit["pair_sector_only"] is True
    assert audit["center_sector_ibp_excluded"] is True
    assert audit["loop_sector_ibp_excluded"] is True
    assert audit["independent_verification"] == "PENDING"
    checks.append("scoped authorization schema consistency")
    checks.append("pair-sector scope restriction")
    checks.append("center and loop IBP exclusion")

    claim = json.loads((manifests / "claim_boundary_audit.json").read_text(encoding="utf-8"))
    assert claim["pre_raw_gamma_expansion_authorized"] is False
    assert claim["conversation_bundle_primary_oracle"] is False
    assert claim["independent_verification"] == "PENDING"
    assert claim["local_exact_algebra"] == "PASS_WITH_CAVEAT"
    checks.append("independent-verification pending status")

    public_scan = json.loads((manifests / "public_path_sanitization.json").read_text(encoding="utf-8"))
    assert public_scan["status"] == "PASS", public_scan
    checks.append("public-path scan")

    return {"passed": True, "checks": checks}


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    print(json.dumps(validate(root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
