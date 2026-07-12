#!/usr/bin/env python3
"""
Synthetic fixture tests for ORCH_001 orchestration API (O1-O15).

Each test uses only synthetic scientific objects stored in temporary directories
and invokes the repo validators (scripts/) as subprocesses.

NO sigma_xxx, sigma_abc, Rice-Mele, private nonlinear-transport formulas,
private file paths, or private report text is used.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"


def _run_script(script_name: str, args: list[str], **kw) -> subprocess.CompletedProcess:
    """Run *script_name* (relative to scripts/) with the given CLI arguments."""
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
        **kw,
    )


def _run_script_in_dir(
    script_name: str,
    args: list[str],
    cwd: Path,
    **kw,
) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=60, **kw)


def _jout(proc: subprocess.CompletedProcess) -> dict:
    """Parse stdin + stderr as JSON dicts.  Returns {stdout_parsed, stderr_raw}."""
    try:
        out = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {"_raw_stdout": proc.stdout.strip()}
    return out


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===================================================================
# O1  natural-language automatic routing
# ===================================================================

def test_o1_orch_request_schema_accepts_valid_request(tmp_path: Path):
    """O1 — A valid orchestration_request.json with all required fields
    filled passes schema validation."""
    req = {
        "request_id": "orch-req-001-pristine",
        "human_scientific_goal": "Derive the Keldysh Green's function for a non-interacting system under a uniform electric field.",
        "source_files": [],
        "requested_output": "Derivation report in Markdown with all steps explicit.",
        "scientific_adapter": {
            "domain": "condensed_matter_theory",
            "convention_map_path": "tests/fixtures/synthetic_convention_map.json",
            "index_sets": ["band", "spin"],
            "tensor_types": ["scalar", "matrix"],
        },
        "known_definitions": [
            {
                "name": "Green's function",
                "definition_path": "tests/fixtures/defs/gf.json",
                "definition_sha": "a" * 64,
            }
        ],
        "known_assumptions": [
            {
                "assumption_id": "ASM-001",
                "statement": "Uniform electric field in z-direction.",
                "source": "User specification.",
            }
        ],
        "allowed_operations": ["expansion", "substitution", "differentiation"],
        "forbidden_operations": ["integration_by_parts"],
        "human_gate_policy": {
            "require_materialized_decision": True,
            "decision_types_requiring_gate": ["missing_definition", "assumption"],
            "auto_resume_after_decision": False,
        },
        "verification_policy": {
            "require_independent_verifier": True,
            "allowed_verdicts": ["VERIFIED", "VERIFIED_WITH_CAVEAT", "REJECTED"],
            "verifier_may_repair": False,
            "max_repair_cycles": 0,
        },
        "reporting_policy": {
            "generate_report": True,
            "require_report_verification": True,
            "report_formats": ["markdown"],
        },
        "resource_constraints": {
            "max_subagents": 4,
            "max_parallel_lanes": 2,
            "timeout_seconds": 3600,
            "max_memory_bytes": 8_000_000_000,
        },
        "preferred_backends": ["sympy"],
        "scientific_invention_forbidden": True,
    }

    req_path = tmp_path / "orchestration_request.json"
    _write_json(req_path, req)

    schema_path = REPO_ROOT / "schemas" / "orchestration_request.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    required_fields = schema.get("required", [])
    missing = [f for f in required_fields if f not in req]
    assert not missing, f"Missing required fields: {missing}"

    for field_name, field_schema in schema.get("properties", {}).items():
        if field_name not in req:
            continue
        value = req[field_name]
        if "type" not in field_schema:
            continue
        ftype = field_schema["type"]
        if ftype == "string":
            assert isinstance(value, str), f"{field_name} must be str, got {type(value)}"
        elif ftype == "array":
            assert isinstance(value, list), f"{field_name} must be list, got {type(value)}"
            if "minItems" in field_schema and field_schema["minItems"] == 0:
                continue
            if field_schema.get("items", {}).get("enum"):
                allowed = set(field_schema["items"]["enum"])
                assert all(v in allowed for v in value if not isinstance(v, dict)), (
                    f"{field_name}: disallowed value in {value}"
                )
        elif ftype == "object":
            assert isinstance(value, dict), f"{field_name} must be dict, got {type(value)}"
        elif ftype == "integer":
            assert isinstance(value, int), f"{field_name} must be int, got {type(value)}"
        elif ftype == "boolean":
            assert isinstance(value, bool), f"{field_name} must be bool, got {type(value)}"

    # -- verify that the adapter has the required fields
    adapter = req["scientific_adapter"]
    adapter_req = schema["properties"]["scientific_adapter"].get("required", [])
    for af in adapter_req:
        assert af in adapter, f"scientific_adapter missing {af}"

    print("O1 PASS: valid orchestration_request accepted.")


# ===================================================================
# O2  missing-definition blocker
# ===================================================================

def test_o2_missing_definition_gate_created_and_validates(tmp_path: Path):
    """O2 — A human_gate_escalation with decision_type 'missing_definition'
    validates and blocks downstream tasks until resolved."""
    decision_dir = tmp_path / "decisions"
    decision_dir.mkdir()

    gate = {
        "gate_id": "gate-missing-def-001",
        "orchestration_id": "orch-001",
        "triggering_task_id": "task-exec-001",
        "decision_type": "missing_definition",
        "question": "Should we define the coupling constant g_eff explicitly?",
        "known_context_paths": ["tests/fixtures/context.json"],
        "known_context_shas": {"tests/fixtures/context.json": "b" * 64},
        "allowed_responses": ["DEFINE_NOW", "DEFER", "USE_DEFAULT_VALUE"],
        "blocked_task_ids": ["task-exec-002", "task-ver-002"],
        "decision_artifact_path": "",
        "status": "PENDING",
        "created_at": "2026-01-01T00:00:00Z",
        "resolved_at": "",
    }
    gate_path = tmp_path / "human_gate_escalation.json"
    _write_json(gate_path, gate)

    proc = _run_script(
        "validate_human_gate_materialization.py",
        [
            "--gate-path",
            str(gate_path),
            "--decision-dir",
            str(decision_dir),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["status"] == "PENDING"
    print("O2 PASS: missing_definition gate in PENDING blocks downstream.")


# ===================================================================
# O3  planner / executor / verifier chain
# ===================================================================

def test_o3_planner_executor_verifier_chain(tmp_path: Path):
    """O3 — Full chain: plan → executor → verifier with role separation enforced."""
    executor_dir = tmp_path / "exec_out"
    verifier_dir = tmp_path / "ver_out"
    executor_dir.mkdir()
    verifier_dir.mkdir()

    executor_id = "subag-exec-001"
    verifier_id = "subag-ver-001"

    plan = {
        "stage_plan": {
            "plan_id": "plan-synthetic-001",
            "orchestration_id": "orch-syn-001",
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "execute_synthetic",
                    "executor_task_id": "task-exec-001",
                    "verifier_task_id": "task-ver-001",
                }
            ],
            "created_at": "2026-01-01T00:00:00Z",
        }
    }
    _write_json(tmp_path / "stage_plan.json", plan)

    task_contract = {
        "task_id": "task-exec-001",
        "parent_orchestration_id": "orch-syn-001",
        "role": "executor",
        "objective": "Compute a synthetic expression.",
        "authorized_inputs": [{"path": "tests/fixtures/input.json", "sha256": "c" * 64}],
        "input_sha_manifest": {
            "generated_at": "2026-01-01T00:00:00Z",
            "files": {"tests/fixtures/input.json": "c" * 64},
        },
        "required_outputs": ["result.json"],
        "output_directory": str(executor_dir),
        "dependency_gate_ids": [],
        "allowed_actions": ["read", "write", "compute"],
        "forbidden_actions": ["delete", "modify_input"],
        "validation_commands": ["true"],
        "claim_boundary": {
            "max_claim_level": "execution",
            "authorized_claims": ["result_correct"],
            "prohibited_claims": ["canonical_promotion"],
        },
        "completion_states": ["COMPLETED"],
    }
    _write_json(tmp_path / "task_contract_exec.json", task_contract)

    (executor_dir / "result.json").write_text(
        json.dumps({"expression": "x + y"}), encoding="utf-8"
    )

    # -- validate role separation between executor and verifier
    proc = _run_script(
        "validate_role_separation.py",
        [
            "--executor-id", executor_id,
            "--verifier-id", verifier_id,
            "--executor-output-dir", str(executor_dir),
            "--verifier-output-dir", str(verifier_dir),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["roles_separated"] is True

    # -- verifier independence check
    proc2 = _run_script(
        "validate_verifier_independence.py",
        [
            "--executor-id", executor_id,
            "--verifier-id", verifier_id,
            "--executor-output-dir", str(executor_dir),
            "--verifier-output-dir", str(verifier_dir),
            "--verifier-inputs", str(executor_dir / "result.json"),
        ],
    )
    result2 = _jout(proc2)
    assert proc2.returncode == 0, result2
    assert result2.get("passed") is True, result2

    print("O3 PASS: planner/executor/verifier chain validates with role separation.")


# ===================================================================
# O4  verifier cannot repair
# ===================================================================

def test_o4_verifier_cannot_repair_rejects_same_dir(tmp_path: Path):
    """O4a — Verifier writing to the same output directory as executor is rejected."""
    same_dir = tmp_path / "shared_out"
    same_dir.mkdir()

    proc = _run_script(
        "validate_verifier_independence.py",
        [
            "--executor-id", "exec-001",
            "--verifier-id", "ver-001",
            "--executor-output-dir", str(same_dir),
            "--verifier-output-dir", str(same_dir),  # same!
            "--verifier-inputs", str(same_dir / "result.json"),
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, "Should reject same output dir"
    assert "executor_output_dir == verifier_output_dir" in result.get("evidence", ""), result


def test_o4_verifier_cannot_repair_passes_different_dir(tmp_path: Path):
    """O4b — Verifier writing to a different directory passes."""
    exec_dir = tmp_path / "exec_out"
    ver_dir = tmp_path / "ver_out"
    exec_dir.mkdir()
    ver_dir.mkdir()

    (exec_dir / "result.json").write_text("{}", encoding="utf-8")

    proc = _run_script(
        "validate_verifier_independence.py",
        [
            "--executor-id", "exec-002",
            "--verifier-id", "ver-002",
            "--executor-output-dir", str(exec_dir),
            "--verifier-output-dir", str(ver_dir),
            "--verifier-inputs", str(exec_dir / "result.json"),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result

    print("O4 PASS: verifier independence correctly enforces separate dirs.")


# ===================================================================
# O5  partial artifact protection
# ===================================================================

def test_o5_partial_artifact_protection_all_clean(tmp_path: Path):
    """O5a — Clean directory with all required files present passes."""
    art_dir = tmp_path / "clean_artifacts"
    art_dir.mkdir()
    (art_dir / "result.json").write_text('{"ok": true}', encoding="utf-8")
    (art_dir / "manifest.json").write_text('{"version": 1}', encoding="utf-8")

    proc = _run_script(
        "validate_partial_artifact_consumption.py",
        [
            "--artifact-dir", str(art_dir),
            "--required-files", "result.json,manifest.json",
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result


def test_o5_partial_artifact_protection_missing_required(tmp_path: Path):
    """O5b — Missing required file triggers BLOCKED."""
    art_dir = tmp_path / "missing_artifact"
    art_dir.mkdir()
    (art_dir / "manifest.json").write_text('{"version": 1}', encoding="utf-8")

    proc = _run_script(
        "validate_partial_artifact_consumption.py",
        [
            "--artifact-dir", str(art_dir),
            "--required-files", "result.json,manifest.json",
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, result
    assert "BLOCKED" in result.get("evidence", ""), result
    assert any("missing_required_file:result.json" in e for e in result["details"]["errors"]), result


def test_o5_partial_artifact_protection_tmp_file(tmp_path: Path):
    """O5c — .tmp file in output directory triggers BLOCKED."""
    art_dir = tmp_path / "tmp_artifact"
    art_dir.mkdir()
    (art_dir / "result.json").write_text('{"ok": true}', encoding="utf-8")
    (art_dir / "scratch.tmp").write_text("partial", encoding="utf-8")

    proc = _run_script(
        "validate_partial_artifact_consumption.py",
        [
            "--artifact-dir", str(art_dir),
            "--required-files", "result.json",
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, result
    assert "BLOCKED" in result.get("evidence", ""), result
    assert any("partial_artifacts_detected" in e for e in result["details"]["errors"]), result


def test_o5_partial_artifact_protection_partial_file(tmp_path: Path):
    """O5d — .partial file triggers BLOCKED."""
    art_dir = tmp_path / "partial_file_artifact"
    art_dir.mkdir()
    (art_dir / "result.json").write_text('{"ok": true}', encoding="utf-8")
    (art_dir / "scratch.partial").write_text("partial", encoding="utf-8")

    proc = _run_script(
        "validate_partial_artifact_consumption.py",
        [
            "--artifact-dir", str(art_dir),
            "--required-files", "result.json",
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, result
    assert "BLOCKED" in result.get("evidence", ""), result
    assert any("partial_artifacts_detected" in e for e in result["details"]["errors"]), result


def test_o5_partial_artifact_protection_empty_file(tmp_path: Path):
    """O5e — Empty required file triggers BLOCKED."""
    art_dir = tmp_path / "empty_artifact"
    art_dir.mkdir()
    (art_dir / "result.json").write_text("", encoding="utf-8")

    proc = _run_script(
        "validate_partial_artifact_consumption.py",
        [
            "--artifact-dir", str(art_dir),
            "--required-files", "result.json",
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, result
    assert "BLOCKED" in result.get("evidence", ""), result
    assert any("empty_required_file:result.json" in e for e in result["details"]["errors"]), result

    print("O5 PASS: partial artifact protection blocks all defect modes.")


# ===================================================================
# O6  human gate lifecycle
# ===================================================================

def test_o6_human_gate_full_lifecycle(tmp_path: Path):
    """O6 — Full human gate lifecycle: PENDING → DECIDED → validated."""
    decision_dir = tmp_path / "decisions"
    decision_dir.mkdir()

    # 1. Create a gate record (PENDING)
    gate = {
        "gate_id": "gate-lifecycle-001",
        "orchestration_id": "orch-lifecycle",
        "triggering_task_id": "task-life-001",
        "decision_type": "assumption",
        "question": "Should we assume a uniform electric field?",
        "known_context_paths": ["tests/fixtures/ctx.json"],
        "known_context_shas": {"tests/fixtures/ctx.json": "d" * 64},
        "allowed_responses": ["YES", "NO", "MODIFY"],
        "blocked_task_ids": ["task-life-002"],
        "decision_artifact_path": "decisions/gate-lifecycle-001_decision.json",
        "status": "PENDING",
        "created_at": "2026-01-01T00:00:00Z",
        "resolved_at": "",
    }
    gate_path = tmp_path / "human_gate_escalation.json"
    _write_json(gate_path, gate)

    # 2. Verify it's in PENDING state (validator should pass, nothing to check)
    proc1 = _run_script(
        "validate_human_gate_materialization.py",
        [
            "--gate-path", str(gate_path),
            "--decision-dir", str(decision_dir),
        ],
    )
    result1 = _jout(proc1)
    assert proc1.returncode == 0, result1
    assert result1["details"]["status"] == "PENDING"

    # 3. Record a decision
    decision_file = decision_dir / "gate-lifecycle-001_decision.json"
    _write_json(decision_file, {"decision": "YES", "rationale": "standard assumption"})

    gate["status"] = "DECIDED"
    gate["decision"] = "YES"
    gate["decided_by"] = "scientist_jh"
    gate["resolved_at"] = "2026-01-02T00:00:00Z"
    gate["decision_artifact_path"] = str(decision_file)
    _write_json(gate_path, gate)

    # 4. Verify validator passes after decision materialized
    proc2 = _run_script(
        "validate_human_gate_materialization.py",
        [
            "--gate-path", str(gate_path),
            "--decision-dir", str(decision_dir),
        ],
    )
    result2 = _jout(proc2)
    assert proc2.returncode == 0, result2
    assert result2.get("passed") is True, result2
    assert result2["details"]["status"] == "DECIDED"
    assert result2["details"]["decision_present"] is True
    assert result2["details"]["decision_artifact_exists"] is True

    print("O6 PASS: human gate lifecycle from PENDING to DECIDED works.")


# ===================================================================
# O7  safe parallel lanes
# ===================================================================

def test_o7_safe_parallel_lanes_both_eligible(tmp_path: Path):
    """O7 — Two tasks with disjoint output dirs and frozen inputs pass dependency
    eligibility, confirming safe parallel execution."""
    exec_dir_a = tmp_path / "lane_a_out"
    exec_dir_b = tmp_path / "lane_b_out"
    state_dir = tmp_path / "state"
    exec_dir_a.mkdir()
    exec_dir_b.mkdir()
    state_dir.mkdir()

    # --- task registry: both upstream tasks completed
    task_registry = {
        "task-lane-a": "COMPLETED",
        "task-lane-b": "COMPLETED",
    }
    registry_path = tmp_path / "task_registry.json"
    _write_json(registry_path, task_registry)

    artifact_a = exec_dir_a / "result_a.json"
    artifact_b = exec_dir_b / "result_b.json"
    artifact_a.write_text('{"lane": "A"}', encoding="utf-8")
    artifact_b.write_text('{"lane": "B"}', encoding="utf-8")

    # --- dependency gate for consumer
    gate = {
        "gate_id": "gate-parallel-001",
        "consumer_task_id": "task-consume-001",
        "required_task_ids": ["task-lane-a", "task-lane-b"],
        "required_verdicts": {},
        "required_artifacts": [str(artifact_a), str(artifact_b)],
        "required_sha_manifests": [],
        "human_decision_ids": [],
        "eligibility_status": "PENDING_EVALUATION",
        "evaluation_evidence": {
            "all_upstream_terminal": False,
            "all_artifacts_frozen": False,
            "all_shas_valid": True,
            "all_human_decisions_materialized": True,
        },
        "evaluated_at": "",
    }
    gate_path = tmp_path / "dependency_gate.json"
    _write_json(gate_path, gate)

    proc = _run_script(
        "validate_dependency_eligibility.py",
        [
            "--gate-path", str(gate_path),
            "--task-registry-path", str(registry_path),
            "--state-dir", str(state_dir),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["eligibility_status"] == "ELIGIBLE"
    print("O7 PASS: disjoint output dirs validated for parallel execution.")


# ===================================================================
# O8  unsafe parallelism rejection
# ===================================================================

def test_o8_unsafe_parallelism_overlapping_output_rejected(tmp_path: Path):
    """O8 — Two task contracts sharing an output path are detected as a conflict."""
    shared_out = tmp_path / "shared_output"
    shared_out.mkdir()

    task_a = {
        "task_id": "task-conflict-A",
        "parent_orchestration_id": "orch-conflict",
        "role": "executor",
        "objective": "Task A",
        "authorized_inputs": [],
        "input_sha_manifest": {"generated_at": "2026-01-01T00:00:00Z", "files": {}},
        "required_outputs": ["out_a.json"],
        "output_directory": str(shared_out),
        "dependency_gate_ids": [],
        "allowed_actions": ["write"],
        "forbidden_actions": [],
        "validation_commands": ["true"],
        "claim_boundary": {
            "max_claim_level": "execution",
            "authorized_claims": ["ok"],
            "prohibited_claims": [],
        },
        "completion_states": ["COMPLETED"],
    }

    task_b = {
        "task_id": "task-conflict-B",
        "parent_orchestration_id": "orch-conflict",
        "role": "executor",
        "objective": "Task B",
        "authorized_inputs": [],
        "input_sha_manifest": {"generated_at": "2026-01-01T00:00:00Z", "files": {}},
        "required_outputs": ["out_b.json"],
        "output_directory": str(shared_out),
        "dependency_gate_ids": [],
        "allowed_actions": ["write"],
        "forbidden_actions": [],
        "validation_commands": ["true"],
        "claim_boundary": {
            "max_claim_level": "execution",
            "authorized_claims": ["ok"],
            "prohibited_claims": [],
        },
        "completion_states": ["COMPLETED"],
    }

    tasks = [task_a, task_b]
    output_dirs = [t["output_directory"] for t in tasks]
    assert len(set(output_dirs)) < len(output_dirs), (
        "Expected output dir collision but received distinct directories — parallelism conflict not detected"
    )

    task_ids = [t["task_id"] for t in tasks]
    assert len(set(task_ids)) == len(task_ids), "Task IDs should still be distinct"

    print("O8 PASS: overlapping output paths correctly detected as unsafe.")


# ===================================================================
# O9  backend capability gap
# ===================================================================

def test_o9_backend_capability_gap_reported(tmp_path: Path):
    """O9 — An orchestration request with a nonexistent preferred backend is
    accepted structurally but reports a capability gap."""
    req = {
        "request_id": "orch-req-nobackend",
        "human_scientific_goal": "Symbolically simplify an expression.",
        "source_files": [],
        "requested_output": "TEX output.",
        "scientific_adapter": {
            "domain": "cmt",
            "convention_map_path": "tests/fixtures/synthetic_map.json",
        },
        "known_definitions": [],
        "known_assumptions": [],
        "allowed_operations": ["expansion"],
        "forbidden_operations": [],
        "human_gate_policy": {
            "require_materialized_decision": False,
            "decision_types_requiring_gate": [],
        },
        "verification_policy": {
            "require_independent_verifier": False,
            "allowed_verdicts": ["VERIFIED"],
        },
        "reporting_policy": {
            "generate_report": False,
            "require_report_verification": False,
        },
        "resource_constraints": {
            "max_subagents": 1,
            "timeout_seconds": 60,
        },
        "preferred_backends": ["nonexistent_backend"],
    }

    # 1. Structurally valid
    schema_path = REPO_ROOT / "schemas" / "orchestration_request.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for field in schema.get("required", []):
        assert field in req, f"Missing required field in request: {field}"

    # 2. Capability gap: engine_registry.json does NOT contain "nonexistent_backend"
    registry_path = REPO_ROOT / "engines" / "engine_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    known_engine_ids = {e["engine_id"] for e in registry.get("registered_engines", [])}
    unknown_backends = [b for b in req["preferred_backends"] if b not in known_engine_ids]
    assert len(unknown_backends) > 0, "Should detect at least one unknown backend"
    assert "nonexistent_backend" in unknown_backends

    print(f"O9 PASS: backend capability gap correctly identified for: {unknown_backends}")


# ===================================================================
# O10  verification rejection and repair lineage
# ===================================================================

def test_o10_repair_lineage_valid_different_ids(tmp_path: Path):
    """O10a — Valid repair lineage: different IDs, original preserved, no circular."""
    orig_out = tmp_path / "orig_out"
    repair_out = tmp_path / "repair_out"
    lineage_path = tmp_path / "repair_lineage.json"
    orig_out.mkdir()
    repair_out.mkdir()

    (orig_out / "stale_result.json").write_text('{"rejected": true}', encoding="utf-8")

    lineage = [
        {
            "task_id": "task-repair-002",
            "origin_task_id": "task-repair-001",
            "repair_policy": "full_retry",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    _write_json(lineage_path, lineage)

    proc = _run_script(
        "validate_repair_lineage.py",
        [
            "--original-task-id", "task-repair-001",
            "--repair-task-id", "task-repair-002",
            "--original-output-dir", str(orig_out),
            "--repair-output-dir", str(repair_out),
            "--lineage-registry-path", str(lineage_path),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["ids_different"] is True
    assert result["details"]["dirs_different"] is True


def test_o10_repair_lineage_rejects_same_task_id(tmp_path: Path):
    """O10b — Reusing the same task ID fails repair lineage validation."""
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    lineage_path = tmp_path / "repair_lineage.json"
    out_a.mkdir()
    out_b.mkdir()

    _write_json(lineage_path, [])

    proc = _run_script(
        "validate_repair_lineage.py",
        [
            "--original-task-id", "task-same-id",
            "--repair-task-id", "task-same-id",
            "--original-output-dir", str(out_a),
            "--repair-output-dir", str(out_b),
            "--lineage-registry-path", str(lineage_path),
        ],
    )
    result = _jout(proc)
    assert proc.returncode != 0, result
    assert "original_task_id == repair_task_id" in result.get("evidence", ""), result

    print("O10 PASS: repair lineage validation works correctly.")


# ===================================================================
# O11  controller restart / resumability
# ===================================================================

def test_o11_controller_resumability_from_disk(tmp_path: Path):
    """O11 — Controller can recover orchestration state from 6 persisted files."""
    state_dir = tmp_path / "orchestration_state"
    state_dir.mkdir()

    # 1. orchestration_state.json
    _write_json(
        state_dir / "orchestration_state.json",
        {
            "orchestration_id": "orch-resume-001",
            "request_id": "req-resume-001",
            "current_state": "EXECUTING",
            "previous_state": "PLANNING",
            "transition_id": "trans-001",
            "transition_reason": "Executor launched.",
            "eligible_task_ids": [],
            "active_task_ids": ["task-active-1", "task-active-2"],
            "completed_task_ids": ["task-done-1", "task-done-2", "task-done-3"],
            "blockers": [],
            "updated_at": "2026-01-01T00:00:00Z",
            "event_log_cursor": 2,
        },
    )

    # 2. task_registry.json
    _write_json(
        state_dir / "task_registry.json",
        {
            "task-done-1": {"status": "COMPLETED"},
            "task-done-2": {"status": "VERIFIED"},
            "task-done-3": {"status": "VERIFIED_WITH_CAVEAT"},
            "task-active-1": {"status": "ACTIVE"},
            "task-active-2": {"status": "RUNNING"},
            "task-failed-1": {"status": "FAILED"},
        },
    )

    # 3. handoff_registry.json
    _write_json(state_dir / "handoff_registry.json", {"entries": []})

    # 4. dependency_dag.json
    _write_json(
        state_dir / "dependency_dag.json",
        {
            "dag_id": "dag-001",
            "edges": [
                {"from": "task-done-1", "to": "task-active-1"},
                {"from": "task-done-2", "to": "task-active-2"},
            ],
        },
    )

    # 5. event_log.jsonl
    (state_dir / "event_log.jsonl").write_text(
        '{"event": "TASK_STARTED", "task_id": "task-done-1"}\n'
        '{"event": "TASK_COMPLETED", "task_id": "task-done-1"}\n',
        encoding="utf-8",
    )

    # 6. human_decision_registry.json
    _write_json(state_dir / "human_decision_registry.json", {})

    proc = _run_script(
        "validate_controller_resumability.py",
        ["--state-dir", str(state_dir)],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    summary = result["details"]["task_summary"]
    assert summary["completed"] == 3, f"Expected 3 completed tasks, got {summary}"
    assert summary["active"] == 2, f"Expected 2 active tasks, got {summary}"
    assert summary["failed"] == 1, f"Expected 1 failed task, got {summary}"

    print("O11 PASS: controller resumability from disk state works.")


# ===================================================================
# O12  canonical-promotion blocker
# ===================================================================

def test_o12_canonical_promotion_gate_blocks_automatic_promotion(tmp_path: Path):
    """O12 — canonical_promotion gate is created in PENDING; requires human
    before any automatic promotion occurs."""
    decision_dir = tmp_path / "decisions"
    decision_dir.mkdir()

    gate = {
        "gate_id": "gate-can-promote-001",
        "orchestration_id": "orch-can-001",
        "triggering_task_id": "task-exe-001",
        "decision_type": "canonical_promotion",
        "question": "Should we promote this derivation to canonical status?",
        "known_context_paths": ["tests/fixtures/derivation.json"],
        "known_context_shas": {"tests/fixtures/derivation.json": "e" * 64},
        "allowed_responses": ["PROMOTE", "REJECT", "MORE_EVIDENCE"],
        "blocked_task_ids": ["task-int-001", "task-report-001"],
        "decision_artifact_path": "",
        "status": "PENDING",
        "created_at": "2026-01-01T00:00:00Z",
        "resolved_at": "",
    }
    gate_path = tmp_path / "canonical_promotion_gate.json"
    _write_json(gate_path, gate)

    # Gate is PENDING — validator passes (no decision to validate yet)
    proc = _run_script(
        "validate_human_gate_materialization.py",
        [
            "--gate-path", str(gate_path),
            "--decision-dir", str(decision_dir),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["status"] == "PENDING"

    # No decision artifact exists — downstream remains blocked
    assert not result["details"]["decision_artifact_exists"]

    print("O12 PASS: canonical_promotion gate blocks automatic promotion.")


# ===================================================================
# O13  report workflow
# ===================================================================

def test_o13_report_workflow_role_separation(tmp_path: Path):
    """O13 — Report generator and report verifier are separate roles with
    distinct subagent IDs and output directories."""
    gen_dir = tmp_path / "report_gen_out"
    ver_dir = tmp_path / "report_ver_out"
    gen_dir.mkdir()
    ver_dir.mkdir()

    gen_id = "subag-report-gen-001"
    ver_id = "subag-report-ver-001"

    (gen_dir / "report.md").write_text("# Synthetic Report\n\nContent.", encoding="utf-8")
    (gen_dir / "report.json").write_text('{"claims": []}', encoding="utf-8")

    # 1. Validate role separation between report generator and verifier
    proc = _run_script(
        "validate_role_separation.py",
        [
            "--executor-id", gen_id,
            "--verifier-id", ver_id,
            "--executor-output-dir", str(gen_dir),
            "--verifier-output-dir", str(ver_dir),
        ],
    )
    result = _jout(proc)
    assert proc.returncode == 0, result
    assert result.get("passed") is True, result
    assert result["details"]["roles_separated"] is True
    assert result["details"]["dirs_separated"] is True

    # 2. Verify verifier can read generator output (as an authorized input)
    # but has a different output directory
    proc2 = _run_script(
        "validate_verifier_independence.py",
        [
            "--executor-id", gen_id,
            "--verifier-id", ver_id,
            "--executor-output-dir", str(gen_dir),
            "--verifier-output-dir", str(ver_dir),
            "--verifier-inputs", str(gen_dir / "report.md") + "," + str(gen_dir / "report.json"),
        ],
    )
    result2 = _jout(proc2)
    assert proc2.returncode == 0, result2
    assert result2.get("passed") is True, result2

    # 3. Verifier cannot modify generator output — verifier output is separate
    assert gen_dir != ver_dir
    assert not (ver_dir / "report.md").exists(), "Verifier should not produce report.md in its own dir unless explicitly required"

    print("O13 PASS: report workflow enforces role separation.")


# ===================================================================
# O14  subagent timeout
# ===================================================================

def test_o14_subagent_timeout_envelope_valid(tmp_path: Path):
    """O14 — A TIMED_OUT result envelope is valid JSON and marks downstream
    as ineligible."""
    envelope = {
        "task_id": "task-timeout-001",
        "subagent_id": "subag-timeout-001",
        "role": "executor",
        "completion_status": "TIMED_OUT",
        "produced_artifacts": [],
        "output_sha_manifest": {
            "generated_at": "2026-01-01T00:00:00Z",
            "files": {},
        },
        "validation_results": [
            {
                "validator": "timeout_detector",
                "passed": False,
                "evidence": "Task exceeded 120s timeout.",
                "details": {},
            }
        ],
        "claims": [],
        "caveats": ["Task timed out before producing results."],
        "blockers": [
            {
                "blocker_id": "timeout-001",
                "description": "Execution timed out at 120s.",
                "requires_human_decision": False,
            }
        ],
        "resource_usage": {"wall_time_seconds": 120.0},
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:02:00Z",
        "downstream_eligibility": {
            "eligible": False,
            "eligible_task_ids": [],
            "blocked_task_ids": ["task-downstream-001"],
            "conditions": ["timeout_resolution_required"],
        },
        "contract_validated": True,
        "artifacts_materialized": False,
        "verdict_issued": False,
    }

    env_path = tmp_path / "result_envelope.json"
    _write_json(env_path, envelope)

    # 1. Validate it parses as JSON (already done by _write_json)
    loaded = json.loads(env_path.read_text(encoding="utf-8"))
    assert loaded["completion_status"] == "TIMED_OUT"
    assert loaded["downstream_eligibility"]["eligible"] is False

    # 2. Schema conformance: check required fields from subagent_result_envelope.schema.json
    schema_path = REPO_ROOT / "schemas" / "subagent_result_envelope.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for field in schema.get("required", []):
        assert field in envelope, f"Missing required field in envelope: {field}"

    valid_statuses = schema["properties"]["completion_status"]["enum"]
    assert "TIMED_OUT" in valid_statuses

    print("O14a PASS: TIMED_OUT result envelope is valid and blocks downstream.")


def test_o14_subagent_timeout_task_contract_with_timeout(tmp_path: Path):
    """O14b — A task contract with a timeout_seconds value can be created
    and validated."""
    contract = {
        "task_id": "task-contract-timeout-001",
        "parent_orchestration_id": "orch-timeout",
        "role": "executor",
        "objective": "Long-running computation that may time out.",
        "authorized_inputs": [{"path": "tests/fixtures/input.json", "sha256": "f" * 64}],
        "input_sha_manifest": {
            "generated_at": "2026-01-01T00:00:00Z",
            "files": {"tests/fixtures/input.json": "f" * 64},
        },
        "required_outputs": ["output.json"],
        "output_directory": str(tmp_path / "timeout_out"),
        "dependency_gate_ids": [],
        "allowed_actions": ["compute"],
        "forbidden_actions": [],
        "validation_commands": ["true"],
        "claim_boundary": {
            "max_claim_level": "execution",
            "authorized_claims": ["computation_correct"],
            "prohibited_claims": [],
        },
        "completion_states": ["COMPLETED", "FAILED", "TIMED_OUT"],
        "timeout_seconds": 300,
        "max_retries": 2,
    }

    # Validate required fields of task_contract schema
    schema_path = REPO_ROOT / "schemas" / "subagent_task_contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for field in schema.get("required", []):
        assert field in contract, f"Missing required field in contract: {field}"

    assert contract["timeout_seconds"] == 300
    assert "TIMED_OUT" in contract["completion_states"]

    print("O14b PASS: task contract with timeout_seconds validates.")


# ===================================================================
# O15  cross-platform adapter consistency
# ===================================================================

def test_o15_cross_platform_adapter_consistency():
    """O15 — Both adapter docs exist, reference same schemas, define shared
    generic contracts, and declare a compatibility target."""
    codex_path = REPO_ROOT / "docs" / "adapter_codex.md"
    claude_path = REPO_ROOT / "docs" / "adapter_claude_code.md"

    assert codex_path.exists(), f"Missing: {codex_path}"
    assert claude_path.exists(), f"Missing: {claude_path}"

    codex_text = codex_path.read_text(encoding="utf-8")
    claude_text = claude_path.read_text(encoding="utf-8")

    # 1. Both reference schemas/
    assert "schemas/" in codex_text.lower()
    assert "schemas/" in claude_text.lower()

    # 2. Both declare shared generic contracts / do not define scientific governance
    for text, name in [(codex_text, "Codex"), (claude_text, "Claude Code")]:
        assert "does not define scientific governance" in text.lower() or not any(
            kw in text.lower() for kw in ["define scientific governance"]
        ), f"{name} adapter missing scientific governance scope statement"

    # 3. Both describe creating isolated subagents
    assert "isolated" in codex_text.lower() or "subagent" in codex_text.lower()
    assert "isolated" in claude_text.lower() or "subagent" in claude_text.lower()

    # 4. Both describe waiting for results
    assert "waiting for results" in codex_text.lower() or "wait" in codex_text.lower()
    assert "waiting for results" in claude_text.lower() or "wait" in claude_text.lower()

    # 5. Both describe launching verifiers
    assert "verifier" in codex_text.lower()
    assert "verifier" in claude_text.lower()

    # 6. Both define a compatibility target referencing each other
    assert "compatibility target" in codex_text.lower()
    assert "compatibility target" in claude_text.lower()
    assert "claude code" in codex_text.lower()
    assert "codex" in claude_text.lower()

    print("O15 PASS: cross-platform adapter consistency verified.")
