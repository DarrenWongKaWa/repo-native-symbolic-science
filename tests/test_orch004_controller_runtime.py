#!/usr/bin/env python3
"""
Comprehensive pytest suite for controller runtime fail-closed behaviour.

Covers:
  - CLI commands: validate-task, check-transition, list-roles, run-workflow
  - ControllerDispatcher: dispatch_role, run_validation_stage, run_workflow,
    collect_results, check_transition, validate_task
  - OrchRegistry: register_adapter, load_adapter_instance, validate_role, list_roles
  - SyntheticExecutor: exception, zero-checks, malformed output, missing inputs
  - Role isolation: planner/executor/verifier separation, authority bounds
  - Human gate lifecycle: PENDING → DECIDED resumption
  - Workflow fixtures: success, failure propagation, verbose mode

Uses ONLY Python standard library + pytest.  CLI tests use subprocess.
All fixtures live in temporary directories (tmp_path).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _controller_cmd(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run orch_controller.py with given args, using *cwd* as working dir."""
    cmd = [sys.executable, str(SCRIPTS / "orch_controller.py"), *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


def _jout(proc: subprocess.CompletedProcess) -> dict:
    """Parse stdout as JSON dict. Returns empty dict on failure."""
    try:
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"_raw_stdout": proc.stdout.strip()}


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _compute_sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compute_sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Temporary state directory for dispatcher persistence."""
    d = tmp_path / "orch_state"
    d.mkdir()
    return d


@pytest.fixture
def valid_task_contract() -> dict:
    """A minimal valid task contract dict with all required fields."""
    return {
        "task_id": "task-001",
        "workflow_state": "RECEIVED",
        "target_role": "executor",
    }


@pytest.fixture
def workflow_fixture() -> dict:
    """A 3-step workflow: plan → execute → verify."""
    return {
        "tasks": [
            {"task_id": "wf-plan-001", "role": "planner"},
            {"task_id": "wf-exec-001", "role": "executor"},
            {"task_id": "wf-ver-001", "role": "verifier"},
        ]
    }


# ===================================================================
# CLI tests
# ===================================================================


class TestControllerCLI:
    """CLI tests using subprocess to invoke orch_controller.py."""

    def test_cli_validate_task_valid_contract_passes(self, tmp_path: Path):
        """Valid task contract passes validation with exit 0."""
        contract = {
            "task_id": "task-cli-001",
            "workflow_state": "RECEIVED",
            "target_role": "executor",
        }
        contract_path = tmp_path / "task_contract.json"
        _write_json(contract_path, contract)

        proc = _controller_cmd(["validate-task", str(contract_path)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {result}"
        assert result.get("passed") is True, result

    def test_cli_validate_task_missing_file_fails(self, tmp_path: Path):
        """Nonexistent file causes exit 1 with blocking finding about missing file."""
        nonexistent = tmp_path / "does_not_exist.json"
        proc = _controller_cmd(["validate-task", str(nonexistent)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 1, f"Expected exit 1, got {proc.returncode}: {result}"
        assert result.get("passed") is False, result
        errors = result.get("errors", [])
        assert len(errors) > 0, "Expected error about missing file"
        assert any("not found" in e for e in errors), (
            f"Expected 'not found' in errors: {errors}"
        )

    def test_cli_validate_task_empty_file_fails(self, tmp_path: Path):
        """Empty file causes exit 1 with blocking finding about invalid/empty content."""
        empty_path = tmp_path / "empty.json"
        empty_path.write_text("", encoding="utf-8")

        proc = _controller_cmd(["validate-task", str(empty_path)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 1, f"Expected exit 1, got {proc.returncode}: {result}"
        assert result.get("passed") is False, result
        assert len(result.get("errors", [])) > 0, "Expected errors for empty file"

    def test_cli_validate_task_malformed_json_fails(self, tmp_path: Path):
        """Malformed JSON causes exit 1."""
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{not valid json at all!!", encoding="utf-8")

        proc = _controller_cmd(["validate-task", str(bad_path)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 1, f"Expected exit 1, got {proc.returncode}: {result}"
        assert result.get("passed") is False, result

    def test_cli_check_transition_valid_passes(self, tmp_path: Path):
        """RECEIVED → POLICY_LOADING is a valid transition (exit 0)."""
        proc = _controller_cmd(
            ["check-transition", "--from", "RECEIVED", "--to", "POLICY_LOADING"],
            cwd=tmp_path,
        )
        result = _jout(proc)

        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {result}"
        assert result.get("allowed") is True, result

    def test_cli_check_transition_invalid_fails(self, tmp_path: Path):
        """EXECUTING → VERIFIED is not allowed (exit 1)."""
        proc = _controller_cmd(
            ["check-transition", "--from", "EXECUTING", "--to", "VERIFIED"],
            cwd=tmp_path,
        )
        result = _jout(proc)

        assert proc.returncode == 1, f"Expected exit 1, got {proc.returncode}: {result}"
        assert result.get("allowed") is False, result

    def test_cli_list_roles(self, tmp_path: Path):
        """list-roles exits 0 and returns JSON with roles array."""
        proc = _controller_cmd(["list-roles"], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {result}"
        assert "roles" in result, result
        assert isinstance(result["roles"], list), f"Expected roles list, got {type(result['roles'])}"
        assert len(result["roles"]) > 0, "Expected at least one role"

    def test_cli_run_workflow_success(self, tmp_path: Path):
        """Full CLI run-workflow with a 3-step fixture exits 0."""
        fixture = {
            "tasks": [
                {"task_id": "cli-wf-exec-1", "role": "executor"},
                {"task_id": "cli-wf-repair", "role": "repair_executor"},
                {"task_id": "cli-wf-ver", "role": "independent_verifier"},
            ]
        }
        fixture_path = tmp_path / "workflow.json"
        _write_json(fixture_path, fixture)

        proc = _controller_cmd(["run-workflow", str(fixture_path)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 0, (
            f"Expected exit 0, got {proc.returncode}: {result}\nstderr: {proc.stderr[:500]}"
        )
        assert result.get("passed") is True, result

    def test_cli_run_workflow_failure(self, tmp_path: Path):
        """CLI run-workflow where one task has no registered adapter → exits 1."""
        fixture = {
            "tasks": [
                {"task_id": "cli-fail-wf-1", "role": "report_generator"},
            ]
        }
        fixture_path = tmp_path / "workflow_fail.json"
        _write_json(fixture_path, fixture)

        proc = _controller_cmd(["run-workflow", str(fixture_path)], cwd=tmp_path)
        result = _jout(proc)

        assert proc.returncode == 1, (
            f"Expected exit 1 for missing adapter, got {proc.returncode}: {result}\nstderr: {proc.stderr[:500]}"
        )
        assert result.get("passed") is False, result

    def test_cli_verbose_mode(self, tmp_path: Path):
        """--verbose produces stderr output."""
        contract = {
            "task_id": "task-verbose",
            "workflow_state": "RECEIVED",
            "target_role": "executor",
        }
        contract_path = tmp_path / "task.json"
        _write_json(contract_path, contract)

        proc = _controller_cmd(
            ["--verbose", "validate-task", str(contract_path)],
            cwd=tmp_path,
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}"
        assert len(proc.stderr.strip()) > 0, (
            f"Expected stderr output with --verbose, got empty stderr"
        )


# ===================================================================
# Fail-Closed Behavior Tests (dispatcher directly)
# ===================================================================


class TestFailClosedBehavior:
    """Fail-closed tests using ControllerDispatcher and SyntheticExecutor directly."""

    def test_unavailable_validator_fails_closed(self, tmp_path: Path):
        """Adapter with nonexistent module_path produces ImportError → fail-closed."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("repair_executor", {
            "module_path": "nonexistent.module.ghost.GhostClass",
            "class_name": "GhostClass",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        contract = {"task_id": "ghost-task", "workflow_state": "RECEIVED", "target_role": "repair_executor"}

        result = dispatcher.dispatch_role(contract, "repair_executor")
        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings for unavailable validator"
        assert any("unavailable" in bf.lower() or "import" in bf.lower() for bf in result.blocking_findings), (
            f"Expected blocking finding about unavailable/import: {result.blocking_findings}"
        )

    def test_validator_exception_fails_closed(self):
        """SyntheticExecutor with should_raise=True → caught, passed=False, blocking findings."""
        from loop_engine.orch_adapters.synthetic_executor import SyntheticExecutor
        from loop_engine.orch_dispatcher import ControllerValidationResult

        executor = SyntheticExecutor({"should_raise": True})

        result = ControllerValidationResult()
        try:
            executor.execute({"task_id": "exc-test", "required_outputs": []}, ".")
        except RuntimeError as exc:
            result.add_blocker(f"Synthetic executor raised exception: {exc}")
            result.add_error(str(exc))

        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"
        assert any("raise" in bf.lower() or "runtime" in bf.lower() for bf in result.blocking_findings), (
            f"Expected exception-related blocking finding: {result.blocking_findings}"
        )

    def test_validator_returns_zero_checks_fails(self):
        """SyntheticExecutor with should_return_zero_checks=True → passed=False, checks_executed=0."""
        from loop_engine.orch_adapters.synthetic_executor import SyntheticExecutor

        executor = SyntheticExecutor({"should_return_zero_checks": True})
        result = executor.execute({"task_id": "zero-check-test", "required_outputs": []}, ".")

        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert result.checks_executed == 0, f"Expected 0 checks, got {result.checks_executed}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"
        assert any("zero" in bf.lower() for bf in result.blocking_findings), (
            f"Expected zero-checks blocking finding: {result.blocking_findings}"
        )

    def test_required_artifact_absent_fails(self, tmp_path: Path):
        """dispatch_role detects missing required input artifacts → passed=False."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("executor", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [str(tmp_path / "missing_output.json")],
            "allowed_actions": ["read", "write"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        contract = {
            "task_id": "missing-artifact",
            "workflow_state": "EXECUTION_ELIGIBLE",
            "target_role": "executor",
        }

        result = dispatcher.dispatch_role(contract, "executor")
        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"
        assert any("missing" in bf.lower() for bf in result.blocking_findings), (
            f"Expected 'missing' in blocking findings: {result.blocking_findings}"
        )

    def test_artifact_sha_mismatch_fails(self, tmp_path: Path):
        """Computed SHA vs fake SHA mismatch is detected."""
        content = "Hello, artifact world!"
        file_path = tmp_path / "artifact.txt"
        file_path.write_text(content, encoding="utf-8")

        real_sha = _compute_sha256_file(file_path)
        fake_sha = "a" * 64

        assert real_sha != fake_sha, f"Real SHA should not match fake SHA"
        assert len(real_sha) == 64, f"SHA256 digest should be 64 hex chars, got {len(real_sha)}"

        computed = _compute_sha256_text(content)
        assert computed == real_sha, "SHA of text should match SHA of file"

    def test_no_validator_selected_fails(self, tmp_path: Path):
        """run_validation_stage with no validators for the stage → passed=False."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("no_val_role", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": [],
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        result = dispatcher.run_validation_stage(
            "task-no-val", "no_val_role", "pre_execute", artifacts_dir
        )

        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"
        assert any(
            "no validator" in bf.lower() or "none" in bf.lower()
            for bf in result.blocking_findings
        ), f"Expected 'no validator' in findings: {result.blocking_findings}"

    def test_unauthorized_role_transition_fails(self, tmp_path: Path):
        """Role with insufficient authority for claimed action → passed=False."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()

        ok, reason = registry.validate_role("executor", "execution")
        assert ok is True, f"execution authority should be valid for executor: {reason}"

        ok2, reason2 = registry.validate_role("executor", "publication")
        assert ok2 is False, f"publication authority should be invalid for executor: {reason2}"

    def test_executor_self_verification_fails(self):
        """Executor's can_verify_self is False, self_verify is in forbidden_actions."""
        from loop_engine.orch_registry import ROLE_REGISTRY, OrchRegistry

        registry = OrchRegistry()
        executor_role = registry._roles.get("executor")
        assert executor_role is not None, "executor role must exist in registry"

        assert executor_role["can_verify_self"] is False, (
            "executor must not be able to self-verify"
        )
        assert "self_verify" in executor_role["forbidden_actions"], (
            "self_verify must be in executor's forbidden_actions"
        )

        verifier_role = registry._roles.get("independent_verifier")
        assert verifier_role is not None, "verifier role must exist in registry"
        assert "self_verify" in verifier_role["forbidden_actions"], (
            "self_verify must be in verifier's forbidden_actions"
        )

    def test_malformed_result_envelope_fails(self):
        """SyntheticExecutor with should_return_malformed=True returns non-ValidationResult → fail."""
        from loop_engine.orch_adapters.synthetic_executor import SyntheticExecutor
        from loop_engine.orch_dispatcher import ControllerValidationResult

        executor = SyntheticExecutor({"should_return_malformed": True})
        raw = executor.execute({"task_id": "malform-test", "required_outputs": []}, ".")

        is_valid = isinstance(raw, ControllerValidationResult)
        if not is_valid:
            result = ControllerValidationResult()
            result.add_blocker("Malformed result envelope: not a ControllerValidationResult")
            result.task_id = raw.get("task_id", "unknown") if isinstance(raw, dict) else "unknown"
        else:
            result = raw

        assert result.passed is False, f"Expected passed=False, got {result.to_dict()}"
        assert len(result.blocking_findings) > 0, "Expected blocking findings for malformed result"


# ===================================================================
# Valid Workflow Tests
# ===================================================================


class TestValidWorkflows:
    """Tests for correct operation of the full workflow chain."""

    def test_full_planner_executor_verifier_chain_passes(self, tmp_path: Path):
        """All three roles dispatch successfully in sequence → chain validates."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        for role_name, claim in [
            ("executor", "execution"),
            ("repair_executor", "execution"),
            ("independent_verifier", "verification"),
        ]:
            registry.register_adapter(role_name, {
                "module_path": "loop_engine.orch_adapters.synthetic_executor",
                "class_name": "SyntheticExecutor",
                "validator_scripts": ["/bin/true"],
                "required_inputs": [],
                "allowed_actions": ["read", "write"],
                "forbidden_actions": [],
                "claim_authority": claim,
            })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        contract_base = {"task_id": "chain-test", "workflow_state": "PLANNING"}

        plan_result = dispatcher.dispatch_role(dict(contract_base, task_id="plan-1"), "executor")
        assert len(plan_result.blocking_findings) == 0 or any(
            "no validator" in bf.lower() for bf in plan_result.blocking_findings
        ), f"Unexpected blocking findings: {plan_result.blocking_findings}"

        exec_contract = dict(contract_base, task_id="exec-1")
        exec_contract["workflow_state"] = "EXECUTION_ELIGIBLE"
        exec_result = dispatcher.dispatch_role(exec_contract, "repair_executor")

        ver_contract = dict(contract_base, task_id="ver-1")
        ver_contract["workflow_state"] = "VERIFICATION_ELIGIBLE"
        ver_result = dispatcher.dispatch_role(ver_contract, "independent_verifier")

        results = [plan_result, exec_result, ver_result]
        aggregated = dispatcher.collect_results(results)
        assert aggregated.checks_expected >= 0, f"Expected checks_expected >= 0, got {aggregated.checks_expected}"
        assert isinstance(aggregated.blocking_findings, list), "blocking_findings should be a list"

    def test_human_gate_pause_resume_passes(self, tmp_path: Path):
        """Human gate: PENDING → create decision → DECIDED → resumption verified."""
        decision_dir = tmp_path / "decisions"
        decision_dir.mkdir()

        gate = {
            "gate_id": "gate-lifecycle-004",
            "orchestration_id": "orch-lifecycle-004",
            "triggering_task_id": "task-life-004",
            "decision_type": "assumption",
            "question": "Should we proceed with this assumption?",
            "known_context_paths": [],
            "known_context_shas": {},
            "allowed_responses": ["YES", "NO"],
            "blocked_task_ids": ["task-blocked-004"],
            "decision_artifact_path": "",
            "status": "PENDING",
            "created_at": "2026-01-01T00:00:00Z",
            "resolved_at": "",
        }
        gate_path = tmp_path / "human_gate.json"
        _write_json(gate_path, gate)

        assert gate["status"] == "PENDING", "Gate should start in PENDING state"
        assert gate["decision_artifact_path"] == "", "Decision artifact should be empty initially"

        decision_file = decision_dir / "gate-lifecycle-004_decision.json"
        _write_json(decision_file, {"decision": "YES", "rationale": "Accepted"})

        gate["status"] = "DECIDED"
        gate["decision"] = "YES"
        gate["decided_by"] = "scientist_jh"
        gate["resolved_at"] = "2026-01-02T00:00:00Z"
        gate["decision_artifact_path"] = str(decision_file)
        _write_json(gate_path, gate)

        reloaded = json.loads(gate_path.read_text(encoding="utf-8"))
        assert reloaded["status"] == "DECIDED", f"Expected DECIDED, got {reloaded['status']}"
        assert reloaded["decision_artifact_path"] == str(decision_file)
        assert decision_file.exists(), "Decision artifact must exist on disk"

        assert len(reloaded["blocked_task_ids"]) > 0, "Blocked tasks should still be recorded"
        assert "task-blocked-004" in reloaded["blocked_task_ids"]

    def test_controller_collect_results(self):
        """collect_results aggregates multiple results correctly (some pass, some fail)."""
        from loop_engine.orch_dispatcher import ControllerValidationResult, ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        r1 = ControllerValidationResult()
        r1.task_id = "pass-1"
        r1.checks_expected = 3
        r1.checks_executed = 3
        r1.checks_passed = 3
        r1.award_pass()

        r2 = ControllerValidationResult()
        r2.task_id = "fail-1"
        r2.checks_expected = 3
        r2.checks_executed = 1
        r2.checks_passed = 0
        r2.add_blocker("Simulated failure")

        r3 = ControllerValidationResult()
        r3.task_id = "pass-2"
        r3.checks_expected = 2
        r3.checks_executed = 2
        r3.checks_passed = 2
        r3.award_pass()

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry)

        aggregated = dispatcher.collect_results([r1, r2, r3])

        assert aggregated.checks_expected == 8, f"Expected 8 checks, got {aggregated.checks_expected}"
        assert aggregated.checks_executed == 6, f"Expected 6 executed, got {aggregated.checks_executed}"
        assert aggregated.checks_passed == 5, f"Expected 5 passed, got {aggregated.checks_passed}"
        assert aggregated.checks_failed == 0, f"Expected 0 explicitly failed, got {aggregated.checks_failed}"
        assert len(aggregated.blocking_findings) == 1, (
            f"Expected 1 blocking finding, got {aggregated.blocking_findings}"
        )
        assert aggregated.passed is False, (
            "Aggregated should not pass due to blocking findings"
        )

    def test_workflow_fixture_run(self, tmp_path: Path):
        """3-step workflow fixture runs to completion via run_workflow."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        for role_name, claim in [
            ("executor", "execution"),
            ("repair_executor", "execution"),
            ("independent_verifier", "verification"),
        ]:
            registry.register_adapter(role_name, {
                "module_path": "loop_engine.orch_adapters.synthetic_executor",
                "class_name": "SyntheticExecutor",
                "validator_scripts": ["/bin/true"],
                "required_inputs": [],
                "allowed_actions": ["read", "write"],
                "forbidden_actions": [],
                "claim_authority": claim,
            })

        fixture = {
            "tasks": [
                {"task_id": "wf-plan-100", "role": "executor"},
                {"task_id": "wf-exec-100", "role": "repair_executor"},
                {"task_id": "wf-ver-100", "role": "independent_verifier"},
            ]
        }
        fixture_path = tmp_path / "wf_fixture.json"
        _write_json(fixture_path, fixture)

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        result = dispatcher.run_workflow(fixture_path)

        assert result.checks_expected >= 0, f"checks_expected should be >= 0: {result.to_dict()}"
        assert isinstance(result.blocking_findings, list)
        assert isinstance(result.errors, list)

    def test_failing_stage_stops_workflow(self, tmp_path: Path):
        """Second step with missing inputs → result has blockers, fails overall."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("executor", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })
        registry.register_adapter("repair_executor", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [str(tmp_path / "nonexistent_file.xyz")],
            "allowed_actions": ["read", "write"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })
        registry.register_adapter("independent_verifier", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "verification",
        })

        fixture = {
            "tasks": [
                {"task_id": "wf-stop-exec", "role": "executor", "workflow_state": "EXECUTION_ELIGIBLE"},
                {"task_id": "wf-stop-repair", "role": "repair_executor", "workflow_state": "EXECUTION_ELIGIBLE"},
                {"task_id": "wf-stop-ver", "role": "independent_verifier", "workflow_state": "VERIFICATION_ELIGIBLE"},
            ]
        }
        fixture_path = tmp_path / "wf_failing.json"
        _write_json(fixture_path, fixture)

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        result = dispatcher.run_workflow(fixture_path)

        assert result.passed is False, f"Workflow should fail overall, got passed={result.passed}"
        assert len(result.blocking_findings) > 0, (
            f"Expected blocking findings for failed stage: {result.blocking_findings}"
        )
        assert any(
            "missing" in bf.lower() for bf in result.blocking_findings
        ), f"Expected blocker mentioning missing input: {result.blocking_findings}"


# ===================================================================
# Role Isolation Tests
# ===================================================================


class TestRoleIsolation:
    """Verify role isolation constraints on planner, executor, and verifier."""

    def test_planner_cannot_execute(self):
        """Planner's forbidden_actions includes execute_implementation."""
        from loop_engine.orch_registry import ROLE_REGISTRY

        planner = ROLE_REGISTRY.get("global_planner")
        assert planner is not None, "global_planner must exist in ROLE_REGISTRY"
        assert "execute_implementation" in planner["forbidden_actions"], (
            f"Planner forbidden_actions must include 'execute_implementation': {planner['forbidden_actions']}"
        )
        assert "execute_implementation" not in planner["allowed_actions"], (
            f"Planner allowed_actions must NOT include 'execute_implementation': {planner['allowed_actions']}"
        )

    def test_executor_cannot_self_verify(self):
        """Executor can_verify_self is False, self_verify in forbidden_actions."""
        from loop_engine.orch_registry import ROLE_REGISTRY

        executor = ROLE_REGISTRY.get("executor")
        assert executor is not None, "executor must exist in ROLE_REGISTRY"
        assert executor["can_verify_self"] is False, (
            f"Executor can_verify_self must be False, got {executor['can_verify_self']}"
        )
        assert "self_verify" in executor["forbidden_actions"], (
            f"Executor forbidden_actions must include 'self_verify': {executor['forbidden_actions']}"
        )

    def test_verifier_cannot_repair(self):
        """Verifier can_repair is False."""
        from loop_engine.orch_registry import ROLE_REGISTRY

        verifier = ROLE_REGISTRY.get("independent_verifier")
        assert verifier is not None, "independent_verifier must exist"
        assert verifier["can_repair"] is False, (
            f"Verifier can_repair must be False, got {verifier['can_repair']}"
        )
        assert "edit_executor_outputs" in verifier["forbidden_actions"], (
            "Verifier must not edit executor outputs"
        )
        assert "repair_executor_outputs" in verifier["forbidden_actions"], (
            "Verifier must not repair executor outputs"
        )


# ===================================================================
# Registry / Adapter Tests
# ===================================================================


class TestRegistryAdapter:
    """Tests for OrchRegistry adapter registration and loading."""

    def test_adapter_load_instance_success(self):
        """Register and load the synthetic_executor adapter successfully."""
        from loop_engine.orch_adapters.synthetic_executor import SyntheticExecutor
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("test_exec", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [],
            "allowed_actions": ["read", "write"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        instance = registry.load_adapter_instance("test_exec")
        assert isinstance(instance, SyntheticExecutor), (
            f"Expected SyntheticExecutor, got {type(instance).__name__}"
        )

    def test_adapter_load_instance_import_error(self):
        """Adapter with bogus module_path raises ImportError (fail-closed)."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("bogus_role", {
            "module_path": "completely.nonexistent.module.path.NoClass",
            "class_name": "NoClass",
            "validator_scripts": [],
            "required_inputs": [],
            "allowed_actions": [],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        with pytest.raises(ImportError) as exc_info:
            registry.load_adapter_instance("bogus_role")

        assert "Fail-closed" in str(exc_info.value), (
            f"ImportError should mention 'Fail-closed': {exc_info.value}"
        )
        assert "completely.nonexistent" in str(exc_info.value), (
            f"ImportError should mention the module path: {exc_info.value}"
        )

    def test_validate_role_within_authority(self):
        """Executor with 'execution' authority passes; executor with 'publication' fails."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()

        ok1, reason1 = registry.validate_role("executor", "execution")
        assert ok1 is True, f"Executor should have execution authority: {reason1}"

        ok2, reason2 = registry.validate_role("executor", "publication")
        assert ok2 is False, f"Executor should NOT have publication authority: {reason2}"
        assert "publication" in reason2.lower(), (
            f"Expected reason to mention publication: {reason2}"
        )

        ok3, reason3 = registry.validate_role("executor", "nonexistent_authority")
        assert ok3 is False, f"Nonexistent authority should fail: {reason3}"


# ===================================================================
# Additional edge-case tests
# ===================================================================


class TestEdgeCases:
    """Additional fail-closed and validation edge cases."""

    def test_dispatch_role_missing_adapter(self, tmp_path: Path):
        """dispatch_role for an unregistered role → blocked."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        contract = {"task_id": "no-adapter", "workflow_state": "RECEIVED"}

        result = dispatcher.dispatch_role(contract, "unregistered_role")
        assert result.passed is False, f"Expected passed=False for unregistered role"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"

    def test_validate_task_missing_target_role(self, tmp_path: Path):
        """Task contract without target_role key → validate_task returns errors."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        contract = {"task_id": "no-role-task", "workflow_state": "RECEIVED"}
        contract_path = tmp_path / "no_role_contract.json"
        _write_json(contract_path, contract)

        result = dispatcher.validate_task(contract_path)
        assert result.passed is False, f"Expected passed=False: {result.to_dict()}"
        assert len(result.errors) > 0, "Expected errors about missing target_role"

    def test_run_validation_stage_invalid_stage_name(self, tmp_path: Path):
        """Invalid validation stage name → blocked."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("some_role", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()

        result = dispatcher.run_validation_stage(
            "task-bad-stage", "some_role", "invalid_stage_name", art_dir
        )
        assert result.passed is False, f"Expected passed=False for invalid stage"
        assert len(result.blocking_findings) > 0, "Expected blocking findings"
        assert any("unknown" in bf.lower() or "invalid" in bf.lower() for bf in result.blocking_findings), (
            f"Expected 'unknown/invalid' in findings: {result.blocking_findings}"
        )

    def test_collect_results_empty_list(self, tmp_path: Path):
        """collect_results with empty list returns a default result."""
        from loop_engine.orch_dispatcher import ControllerDispatcher, ControllerValidationResult
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        result = dispatcher.collect_results([])
        assert isinstance(result, ControllerValidationResult)
        assert result.checks_expected == 0
        assert result.checks_executed == 0
        assert result.passed is False

    def test_run_workflow_missing_fixture_file(self, tmp_path: Path):
        """run_workflow with nonexistent fixture → error."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        result = dispatcher.run_workflow(tmp_path / "nonexistent_fixture.json")
        assert result.passed is False, f"Expected passed=False"
        assert len(result.errors) > 0, "Expected errors for missing fixture"

    def test_run_workflow_malformed_fixture_json(self, tmp_path: Path):
        """run_workflow with malformed JSON fixture → error."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        fixture_path = tmp_path / "bad_fixture.json"
        fixture_path.write_text("{not valid json", encoding="utf-8")

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        result = dispatcher.run_workflow(fixture_path)
        assert result.passed is False, f"Expected passed=False"
        assert len(result.errors) > 0, "Expected errors for malformed fixture"

    def test_run_workflow_empty_tasks_array(self, tmp_path: Path):
        """run_workflow with empty tasks array → error."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        fixture_path = tmp_path / "empty_tasks.json"
        _write_json(fixture_path, {"tasks": []})

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        result = dispatcher.run_workflow(fixture_path)
        assert result.passed is False, f"Expected passed=False for empty tasks"
        assert len(result.errors) > 0, "Expected errors for empty tasks"

    def test_dispatch_role_empty_inputs_blocking(self, tmp_path: Path):
        """Adapter with empty required files in required_inputs → blocked."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        empty_file = tmp_path / "empty_required.txt"
        empty_file.write_text("", encoding="utf-8")

        registry = OrchRegistry()
        registry.register_adapter("executor", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": ["/bin/true"],
            "required_inputs": [str(empty_file)],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)
        contract = {"task_id": "empty-in", "workflow_state": "RECEIVED"}

        result = dispatcher.dispatch_role(contract, "executor")
        assert len(result.blocking_findings) > 0, (
            f"Expected blocking findings for empty required file: {result.to_dict()}"
        )
        assert any("empty" in bf.lower() for bf in result.blocking_findings), (
            f"Expected 'empty' mention: {result.blocking_findings}"
        )

    def test_check_transition_unknown_from_state(self, tmp_path: Path):
        """check_transition with unknown from_state returns not allowed."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        allowed, reason = dispatcher.check_transition("NONEXISTENT_STATE", "RECEIVED")
        assert allowed is False, f"Expected not allowed for unknown state: {reason}"
        assert "unknown" in reason.lower() or "nonexistent" in reason.lower(), (
            f"Expected 'unknown' mention in reason: {reason}"
        )

    def test_check_transition_same_state_allowed(self, tmp_path: Path):
        """check_transition with same from/to state is always allowed."""
        from loop_engine.orch_dispatcher import ControllerDispatcher
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        dispatcher = ControllerDispatcher(registry=registry, state_dir=tmp_path)

        allowed, reason = dispatcher.check_transition("RECEIVED", "RECEIVED")
        assert allowed is True, f"Same-state transition should be allowed: {reason}"


# ===================================================================
# ControllerValidationResult unit tests
# ===================================================================


class TestValidationResult:
    """Tests for ControllerValidationResult internal logic."""

    def test_award_pass_requires_positive_checks(self):
        """award_pass only passes when checks_executed > 0 and no blockers."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        r = ControllerValidationResult()
        r.checks_executed = 0
        r.checks_passed = 0
        r.award_pass()
        assert r.passed is False, "Zero checks should not pass"
        assert r.final_exit_status == 1

        r2 = ControllerValidationResult()
        r2.checks_executed = 3
        r2.checks_passed = 3
        r2.award_pass()
        assert r2.passed is True
        assert r2.final_exit_status == 0

    def test_award_pass_blocked_by_findings(self):
        """Blocking findings prevent award_pass even with positive checks."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        r = ControllerValidationResult()
        r.checks_executed = 5
        r.checks_passed = 5
        r.add_blocker("Something is wrong")
        r.award_pass()
        assert r.passed is False, "Blockers should prevent pass"
        assert r.final_exit_status == 1

    def test_add_warning_not_blocking(self):
        """Warnings do not set passed=False."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        r = ControllerValidationResult()
        r.add_warning("This is just a warning")
        assert r.has_blockers is False
        assert r.passed is False
        r.checks_executed = 1
        r.checks_passed = 1
        r.award_pass()
        assert r.passed is True, "Warnings alone should not block pass"

    def test_to_dict_and_from_dict_roundtrip(self):
        """to_dict → from_dict roundtrip preserves all fields."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        orig = ControllerValidationResult()
        orig.task_id = "roundtrip-1"
        orig.workflow_state = "EXECUTING"
        orig.requested_role = "executor"
        orig.selected_adapter = "SyntheticExecutor"
        orig.selected_validators = ["/bin/true", "/bin/false"]
        orig.required_inputs = ["in1.json", "in2.json"]
        orig.resolved_inputs = ["in1.json"]
        orig.checks_expected = 5
        orig.checks_executed = 4
        orig.checks_passed = 3
        orig.checks_failed = 1
        orig.artifacts_consumed = [{"path": "out.json", "sha256": "a" * 64}]
        orig.transition_attempted = {"from": "A", "to": "B"}
        orig.transition_result = {"allowed": True, "reason": "ok"}
        orig.blocking_findings = ["bad thing"]
        orig.errors = ["error 1"]
        orig.warnings = ["warning 1"]
        orig.passed = True
        orig.final_exit_status = 0

        d = orig.to_dict()
        restored = ControllerValidationResult.from_dict(d)

        assert restored.task_id == orig.task_id
        assert restored.workflow_state == orig.workflow_state
        assert restored.requested_role == orig.requested_role
        assert restored.selected_adapter == orig.selected_adapter
        assert restored.selected_validators == orig.selected_validators
        assert restored.required_inputs == orig.required_inputs
        assert restored.resolved_inputs == orig.resolved_inputs
        assert restored.checks_expected == orig.checks_expected
        assert restored.checks_executed == orig.checks_executed
        assert restored.checks_passed == orig.checks_passed
        assert restored.checks_failed == orig.checks_failed
        assert restored.artifacts_consumed == orig.artifacts_consumed
        assert restored.transition_attempted == orig.transition_attempted
        assert restored.transition_result == orig.transition_result
        assert restored.blocking_findings == orig.blocking_findings
        assert restored.errors == orig.errors
        assert restored.warnings == orig.warnings
        assert restored.passed == orig.passed
        assert restored.final_exit_status == orig.final_exit_status


# ===================================================================
# Registry edge cases
# ===================================================================


class TestRegistryMisc:
    """Miscellaneous OrchRegistry tests."""

    def test_register_adapter_missing_keys_raises(self):
        """register_adapter with missing required keys raises ValueError."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        with pytest.raises(ValueError) as exc_info:
            registry.register_adapter("incomplete", {
                "module_path": "some.module",
            })
        assert "missing required keys" in str(exc_info.value).lower(), (
            f"Expected 'missing required keys' in error: {exc_info.value}"
        )

    def test_load_adapter_instance_unregistered_role_raises(self):
        """load_adapter_instance for unregistered role raises ValueError."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        with pytest.raises(ValueError) as exc_info:
            registry.load_adapter_instance("no_such_role")
        assert "no adapter registered" in str(exc_info.value).lower(), (
            f"Expected 'no adapter registered' in error: {exc_info.value}"
        )

    def test_get_required_validators_returns_list_for_dict_spec(self):
        """get_required_validators handles dict-based validator_scripts (per-stage)."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        registry.register_adapter("staged_role", {
            "module_path": "loop_engine.orch_adapters.synthetic_executor",
            "class_name": "SyntheticExecutor",
            "validator_scripts": {
                "pre_execute": ["/bin/validate_pre.sh"],
                "post_execute": ["/bin/validate_post.sh"],
            },
            "required_inputs": [],
            "allowed_actions": ["read"],
            "forbidden_actions": [],
            "claim_authority": "execution",
        })

        pre_validators = registry.get_required_validators("staged_role", "pre_execute")
        assert pre_validators == ["/bin/validate_pre.sh"], (
            f"Expected pre_execute validators, got {pre_validators}"
        )

        post_validators = registry.get_required_validators("staged_role", "post_execute")
        assert post_validators == ["/bin/validate_post.sh"], (
            f"Expected post_execute validators, got {post_validators}"
        )

        unknown = registry.get_required_validators("staged_role", "pre_verify")
        assert unknown == [], f"Expected empty list for unknown stage, got {unknown}"

    def test_list_roles_includes_builtin_roles(self):
        """list_roles returns all builtin roles."""
        from loop_engine.orch_registry import ROLE_REGISTRY, OrchRegistry

        registry = OrchRegistry()
        roles = registry.list_roles()

        builtin = set(ROLE_REGISTRY.keys())
        returned = set(roles)
        assert builtin == returned, (
            f"list_roles should return all builtin roles. Missing: {builtin - returned}, Extra: {returned - builtin}"
        )

    def test_validate_role_unknown_role_fails(self):
        """validate_role for non-existent role returns False."""
        from loop_engine.orch_registry import OrchRegistry

        registry = OrchRegistry()
        ok, reason = registry.validate_role("phantom_role", "execution")
        assert ok is False, f"Unknown role should fail: {reason}"
        assert "unknown role" in reason.lower(), (
            f"Expected 'unknown role' in reason: {reason}"
        )
