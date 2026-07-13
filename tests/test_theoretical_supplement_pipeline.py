import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_theoretical_supplement.py"
EXAMPLE_REQUEST = REPO_ROOT / "examples" / "theoretical_supplement_request.json"
SOURCE_MANIFEST = REPO_ROOT / "fixtures" / "supplement" / "two_sector_response" / "source_artifact_manifest.json"

spec = importlib.util.spec_from_file_location("build_theoretical_supplement", SCRIPT_PATH)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _request(tmp_path: Path, **overrides) -> Path:
    data = json.loads(EXAMPLE_REQUEST.read_text())
    data["output_directory"] = str(tmp_path / "out")
    data.update(overrides)
    path = tmp_path / "request.json"
    _write_json(path, data)
    return path


def _run(request_path: Path, *extra: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--request", str(request_path), *extra],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _copy_fixture_manifest(tmp_path: Path) -> tuple[Path, Path]:
    fixture_copy = tmp_path / "fixture"
    shutil.copytree(REPO_ROOT / "fixtures" / "supplement" / "two_sector_response", fixture_copy)
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    manifest["fixture_root"] = str(fixture_copy)
    manifest_path = tmp_path / "source_manifest.json"
    _write_json(manifest_path, manifest)
    return fixture_copy, manifest_path


def test_valid_request_parsing(tmp_path):
    req = _request(tmp_path)
    data = _load(req)
    assert pipeline.validate_request(data, req) == []


def test_dry_run_dependency_planning(tmp_path):
    req = _request(tmp_path)
    proc = _run(req, "--dry-run")
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["status"] == "DRY_RUN_PASS"
    plan = _load(tmp_path / "out" / "pipeline_plan.json")
    assert plan["stage_order"] == pipeline.STAGE_ORDER


def test_correct_internal_skill_order():
    plan = pipeline.build_plan({"request_id": "r", "pipeline_mode": "full"})
    assert plan["stage_order"] == [
        "SOURCE_AUTHENTICATION",
        "DERIVATION_GRAPH",
        "DERIVATION_NARRATIVE",
        "PHYSICAL_INTERPRETATION",
        "LONG_EXPRESSION_PRESENTATION",
        "EQUATION_EVIDENCE_MAPPING",
        "SUPPLEMENT_ASSEMBLY",
        "HANDOFF_VALIDATION",
        "PROVENANCE_RENDERING",
        "READABILITY_AUDIT",
        "FINALIZATION",
    ]


def test_valid_existing_stage_reuse(tmp_path):
    req = _request(tmp_path)
    assert _run(req).returncode == 0
    proc = _run(req, "--resume")
    assert proc.returncode == 0, proc.stderr
    manifest = _load(tmp_path / "out" / "skill_execution_manifest.json")
    statuses = {entry["stage"]: entry["status"] for entry in manifest["skills"]}
    assert "SKIPPED_VALID_EXISTING" in statuses.values()


def test_stale_stage_rejection_reruns_generated_output(tmp_path):
    req = _request(tmp_path)
    assert _run(req).returncode == 0
    narrative = tmp_path / "out" / "section_narratives.json"
    narrative.write_text(narrative.read_text() + "\n", encoding="utf-8")
    assert _run(req, "--resume").returncode == 0
    state = _load(tmp_path / "out" / "pipeline_state.json")
    assert state["stages"]["DERIVATION_NARRATIVE"]["status"] == "PASS"


def test_missing_derivation_graph_blocking(tmp_path):
    fixture_copy, manifest_path = _copy_fixture_manifest(tmp_path)
    (fixture_copy / "derivation_graph.json").unlink()
    req = _request(tmp_path, source_manifest=str(manifest_path))
    proc = _run(req)
    assert proc.returncode == 1
    result = _load(tmp_path / "out" / "final_result.json")
    assert result["blocking_reason"].startswith("SOURCE_AUTHENTICATION_FAILED")


def test_derivation_gap_blocking(tmp_path):
    fixture_copy, manifest_path = _copy_fixture_manifest(tmp_path)
    graph = _load(fixture_copy / "derivation_graph.json")
    graph["validation"] = {"validation_errors": ["DERIVATION_GAP"]}
    _write_json(fixture_copy / "derivation_graph.json", graph)
    manifest = _load(manifest_path)
    manifest["artifact_shas"]["derivation_graph"] = pipeline.sha256_file(fixture_copy / "derivation_graph.json")
    _write_json(manifest_path, manifest)
    req = _request(tmp_path, source_manifest=str(manifest_path))
    proc = _run(req)
    assert proc.returncode == 1
    result = _load(tmp_path / "out" / "final_result.json")
    assert result["verdict"] == "BLOCKED_BY_DERIVATION_GAP"


def test_missing_interpretation_blocking(tmp_path):
    manifest = _load(SOURCE_MANIFEST)
    manifest["artifacts"].pop("physical_interpretation_mapping")
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    req = _request(tmp_path, source_manifest=str(manifest_path))
    proc = _run(req)
    assert proc.returncode == 1
    assert _load(tmp_path / "out" / "final_result.json")["verdict"] == "BLOCKED_AT_PHYSICAL_INTERPRETATION"


def test_missing_omission_ledger_blocking_when_required(tmp_path):
    manifest = _load(SOURCE_MANIFEST)
    manifest["artifacts"].pop("mathematical_omission_ledger")
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    req = _request(tmp_path, source_manifest=str(manifest_path))
    proc = _run(req)
    assert proc.returncode == 1
    assert "mathematical_omission_ledger" in _load(tmp_path / "out" / "final_result.json")["blocking_reason"]


def test_supplement_assembly_prerequisite_enforcement(tmp_path):
    req = _request(tmp_path)
    proc = _run(req, "--stage", "SUPPLEMENT_ASSEMBLY")
    assert proc.returncode == 0, proc.stderr
    state = _load(tmp_path / "out" / "pipeline_state.json")
    assert state["stages"]["SUPPLEMENT_ASSEMBLY"]["status"] == "PASS"
    assert (tmp_path / "out" / "reporting_handoff_package.json").exists()


def test_direct_render_bypass_denial(tmp_path):
    request = _load(EXAMPLE_REQUEST)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    with pytest.raises(RuntimeError, match="RENDERER_AUTHORIZATION_DENIED"):
        pipeline.build_renderer_dispatch(output_dir, request)


def test_validated_handoff_allows_rendering(tmp_path):
    req = _request(tmp_path)
    proc = _run(req, "--stage", "PROVENANCE_RENDERING")
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "out" / "renderer_dispatch_manifest.json").exists()
    assert (tmp_path / "out" / "publication" / "main.tex").exists()


def test_partial_artifact_rejection(tmp_path):
    handoff = tmp_path / "reporting_handoff_package.json"
    handoff.write_text("{}", encoding="utf-8")
    ok, errors = pipeline.validate_handoff(handoff)
    assert not ok
    assert "producer_authority_not_SUPP" in errors


def test_resume_from_last_valid_stage(tmp_path):
    req = _request(tmp_path)
    assert _run(req, "--stage", "SUPPLEMENT_ASSEMBLY").returncode == 0
    assert _run(req, "--resume").returncode == 0
    result = _load(tmp_path / "out" / "final_result.json")
    assert result["status"] == "PASS"


def test_sha_mismatch_rejection(tmp_path):
    fixture_copy, manifest_path = _copy_fixture_manifest(tmp_path)
    source = fixture_copy / "source_artifacts" / "starting_expression.txt"
    source.write_text(source.read_text() + "\nchanged\n", encoding="utf-8")
    req = _request(tmp_path, source_manifest=str(manifest_path))
    proc = _run(req)
    assert proc.returncode == 1
    assert "sha_mismatch" in _load(tmp_path / "out" / "final_result.json")["blocking_reason"]


def test_final_result_envelope_generation(tmp_path):
    req = _request(tmp_path)
    assert _run(req).returncode == 0
    result = _load(tmp_path / "out" / "final_result.json")
    assert result["status"] == "PASS"
    assert result["skill_execution_manifest_path"]
    assert result["main_tex"].endswith("publication/main.tex")


def test_no_project_specific_logic_in_facade():
    text = SCRIPT_PATH.read_text()
    assert "sigma_xxx" not in text
    assert "sigma_abc" not in text


def test_public_fixture_end_to_end_execution(tmp_path):
    req = _request(tmp_path)
    proc = _run(req)
    assert proc.returncode == 0, proc.stderr
    manifest = _load(tmp_path / "out" / "skill_execution_manifest.json")
    assert {entry["status"] for entry in manifest["skills"]} <= {"PASS", "SKIPPED_VALID_EXISTING"}


def test_private_path_safety(tmp_path):
    req = _request(tmp_path, source_manifest="/" + "Users" + "/example/private/source_artifact_manifest.json")
    proc = _run(req)
    assert proc.returncode == 1
    result = _load(tmp_path / "out" / "final_result.json")
    assert "private or local absolute path" in result["blocking_reason"]


def test_deterministic_two_run_pipeline_planning(tmp_path):
    req1 = _request(tmp_path / "r1")
    req2 = _request(tmp_path / "r2")
    assert _run(req1, "--dry-run").returncode == 0
    assert _run(req2, "--dry-run").returncode == 0
    plan1 = _load(tmp_path / "r1" / "out" / "pipeline_plan.json")
    plan2 = _load(tmp_path / "r2" / "out" / "pipeline_plan.json")
    plan1["request_id"] = "normalized"
    plan2["request_id"] = "normalized"
    assert plan1 == plan2
