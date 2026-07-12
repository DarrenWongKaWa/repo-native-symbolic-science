from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orch_registry import CLAIM_LEVEL_RANK, OrchRegistry

logger = logging.getLogger(__name__)


VALID_VALIDATION_STAGES = frozenset({
    "pre_execute",
    "post_execute",
    "pre_verify",
    "post_verify",
    "pre_integration",
})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _compute_sha256_text(text: str) -> str:
    """Compute the SHA-256 digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ControllerValidationResult:
    """Structured validation result from the controller.

    Encapsulates the outcome of a dispatch, validation stage, or workflow
    run. Fail-closed by default: ``passed`` is ``False`` and
    ``final_exit_status`` is ``1`` until positive evidence is recorded.
    """

    def __init__(self) -> None:
        self.task_id: str | None = None
        self.workflow_state: str | None = None
        self.requested_role: str | None = None
        self.selected_adapter: str | None = None
        self.selected_validators: list[str] = []
        self.required_inputs: list[str] = []
        self.resolved_inputs: list[str] = []
        self.checks_expected: int = 0
        self.checks_executed: int = 0
        self.checks_passed: int = 0
        self.checks_failed: int = 0
        self.artifacts_consumed: list[dict[str, str]] = []
        self.transition_attempted: dict[str, str] | None = None
        self.transition_result: dict[str, Any] | None = None
        self.blocking_findings: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: bool = False
        self.final_exit_status: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "task_id": self.task_id,
            "workflow_state": self.workflow_state,
            "requested_role": self.requested_role,
            "selected_adapter": self.selected_adapter,
            "selected_validators": self.selected_validators,
            "required_inputs": self.required_inputs,
            "resolved_inputs": self.resolved_inputs,
            "checks_expected": self.checks_expected,
            "checks_executed": self.checks_executed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "artifacts_consumed": self.artifacts_consumed,
            "transition_attempted": self.transition_attempted,
            "transition_result": self.transition_result,
            "blocking_findings": self.blocking_findings,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
            "final_exit_status": self.final_exit_status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ControllerValidationResult:
        """Deserialize from a dict."""
        result = cls()
        result.task_id = d.get("task_id")
        result.workflow_state = d.get("workflow_state")
        result.requested_role = d.get("requested_role")
        result.selected_adapter = d.get("selected_adapter")
        result.selected_validators = d.get("selected_validators", [])
        result.required_inputs = d.get("required_inputs", [])
        result.resolved_inputs = d.get("resolved_inputs", [])
        result.checks_expected = d.get("checks_expected", 0)
        result.checks_executed = d.get("checks_executed", 0)
        result.checks_passed = d.get("checks_passed", 0)
        result.checks_failed = d.get("checks_failed", 0)
        result.artifacts_consumed = d.get("artifacts_consumed", [])
        result.transition_attempted = d.get("transition_attempted")
        result.transition_result = d.get("transition_result")
        result.blocking_findings = d.get("blocking_findings", [])
        result.errors = d.get("errors", [])
        result.warnings = d.get("warnings", [])
        result.passed = d.get("passed", False)
        result.final_exit_status = d.get("final_exit_status", 1)
        return result

    def add_blocker(self, finding: str) -> None:
        """Add a blocking finding.

        Automatically sets ``passed`` to ``False`` and
        ``final_exit_status`` to ``1``.
        """
        self.blocking_findings.append(finding)
        self.passed = False
        self.final_exit_status = 1

    def add_error(self, error: str) -> None:
        """Add an error. Errors are always blocking."""
        self.errors.append(error)
        self.add_blocker(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning. Warnings do not block."""
        self.warnings.append(warning)

    @property
    def all_checks_executed(self) -> bool:
        """Whether all expected checks have been executed."""
        return self.checks_executed >= self.checks_expected

    @property
    def has_blockers(self) -> bool:
        """Whether any blocking findings exist."""
        return len(self.blocking_findings) > 0

    def award_pass(self) -> None:
        """Award a PASS verdict.

        Requires positive evidence: checks_executed > 0,
        checks_passed == checks_executed, and no blockers.
        """
        if (
            self.checks_executed > 0
            and self.checks_passed == self.checks_executed
            and not self.has_blockers
        ):
            self.passed = True
            self.final_exit_status = 0
        else:
            self.passed = False
            self.final_exit_status = 1


class ControllerDispatcher:
    """Generic model-neutral multi-agent orchestration controller dispatcher.

    Enforces role isolation, authority bounds, and fail-closed behaviour
    across all dispatch, validation, and workflow operations.
    """

    def __init__(
        self,
        registry: OrchRegistry | None = None,
        state_dir: str | Path | None = None,
    ) -> None:
        """Initialize with an OrchRegistry instance.

        Args:
            registry: An OrchRegistry instance. If None, a default
                registry with builtin roles is created.
            state_dir: Optional directory for persisting dispatch state.
        """
        self.registry = registry if registry is not None else OrchRegistry()
        self.state_dir = Path(state_dir) if state_dir else Path(".loop/orch_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Task contract loading and validation
    # ------------------------------------------------------------------

    def load_task_contract(
        self, contract_path: str | Path
    ) -> tuple[dict[str, Any], list[str]]:
        """Load and validate a task contract JSON file.

        Args:
            contract_path: Path to the task contract JSON file.

        Returns:
            A tuple of (contract_dict, errors_list). If contract_dict is
            empty, errors_list describes what went wrong.
        """
        path = Path(contract_path)
        errors: list[str] = []

        if not path.exists():
            errors.append(f"Task contract file not found: {path}")
            return {}, errors

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in task contract '{path}': {exc}")
            return {}, errors

        if not isinstance(data, dict):
            errors.append(f"Task contract root must be a JSON object, got {type(data).__name__}")
            return {}, errors

        required_keys = {"task_id", "workflow_state", "target_role"}
        missing = required_keys - set(data.keys())
        for key in sorted(missing):
            errors.append(f"Task contract missing required key: '{key}'")

        return data, errors

    def validate_task(self, contract_path: str | Path) -> ControllerValidationResult:
        """Run pre-dispatch validation on a task contract.

        Args:
            contract_path: Path to the task contract JSON file.

        Returns:
            A ControllerValidationResult with validation outcome.
        """
        result = ControllerValidationResult()
        path = Path(contract_path)

        contract, load_errors = self.load_task_contract(contract_path)

        result.task_id = contract.get("task_id")
        result.workflow_state = contract.get("workflow_state")

        if load_errors:
            for err in load_errors:
                result.add_error(err)
            return result

        role_name = contract.get("target_role", "")
        if not role_name:
            result.add_error("Task contract has no 'target_role'")
            return result

        result.requested_role = role_name

        role_def = self.registry._roles.get(role_name, {})
        max_claim = role_def.get("max_claim", role_name)
        role_ok, role_reason = self.registry.validate_role(role_name, max_claim)
        if not role_ok:
            result.add_error(f"Role validation failed: {role_reason}")
            return result

        adapter = self.registry.get_adapter(role_name)
        if adapter is None:
            result.add_warning(
                f"No adapter registered for role '{role_name}'; "
                f"dispatch will fail if adapter is required"
            )
        else:
            result.selected_adapter = adapter.get("class_name", "")
            result.selected_validators = adapter.get("validator_scripts", [])
            result.required_inputs = adapter.get("required_inputs", [])

        result.checks_expected = 1
        result.checks_executed = 1
        result.checks_passed = 1
        result.award_pass()
        return result

    # ------------------------------------------------------------------
    # Role dispatch
    # ------------------------------------------------------------------

    def dispatch_role(
        self,
        contract: dict[str, Any],
        role_name: str,
        adapter_config: dict[str, Any] | None = None,
    ) -> ControllerValidationResult:
        """Dispatch a task to a specific role's adapter.

        Enforces role isolation, authority, and transition rules.

        Args:
            contract: The task contract dict.
            role_name: The role to dispatch to.
            adapter_config: Optional override adapter configuration.

        Returns:
            A ControllerValidationResult with the dispatch outcome.
        """
        result = ControllerValidationResult()
        result.task_id = contract.get("task_id")
        result.workflow_state = contract.get("workflow_state")
        result.requested_role = role_name

        # --- 7. Role authorization check ---
        claimed = (contract.get("claim_boundary") or {}).get("max_claim_level", "execution")
        role_ok, role_reason = self.registry.validate_role(role_name, claimed)
        if not role_ok:
            result.add_blocker(f"Role unauthorized: {role_reason}")
            return result

        # --- Resolve adapter ---
        adapter = self.registry.get_adapter(role_name)
        if adapter is None and adapter_config is None:
            result.add_blocker(
                f"No adapter registered for role '{role_name}'"
            )
            return result

        if adapter_config is not None:
            adapter = adapter_config

        if adapter is None:
            result.add_blocker(f"Adapter resolution failed for role '{role_name}'")
            return result

        result.selected_adapter = adapter.get("class_name", "")
        result.selected_validators = adapter.get("validator_scripts", [])
        result.required_inputs = adapter.get("required_inputs", [])

        # --- 1. Check selected adapter is importable ---
        try:
            self.registry.load_adapter_instance(role_name)
        except (ImportError, ValueError) as exc:
            result.add_blocker(
                f"Declared validator unavailable: {exc}"
            )
            return result

        # --- 2. Check required input artifacts exist ---
        missing_inputs: list[str] = []
        for req in result.required_inputs:
            req_path = Path(req)
            if not req_path.exists():
                missing_inputs.append(req)
        if missing_inputs:
            result.add_blocker(
                f"Required input artifacts missing: {missing_inputs}"
            )

        # --- 3. Check required files are not empty ---
        empty_inputs: list[str] = []
        for req in result.required_inputs:
            req_path = Path(req)
            if req_path.exists() and req_path.stat().st_size == 0:
                empty_inputs.append(req)
        if empty_inputs:
            result.add_blocker(f"Required files are empty: {empty_inputs}")

        # --- 5. Check validators for required stages ---
        role_def = self.registry._roles.get(role_name, {})
        role_needs_verification = role_def.get("requires_independent_verifier", False)
        adapter_has_validators = (
            bool(adapter.get("validator_scripts")) or
            bool(adapter.get("required_validators_pre_execute")) or
            bool(adapter.get("required_validators_post_execute")) or
            bool(adapter.get("required_validators_pre_verify")) or
            bool(adapter.get("required_validators_post_verify"))
        )
        if not result.selected_validators and role_needs_verification and adapter_has_validators:
            result.add_blocker(
                f"No validator selected for role '{role_name}'; "
                "at least one validator script is required"
            )

        # --- 9. Check for partial artifact consumption ---
        resolved_inputs: list[str] = []
        for req in result.required_inputs:
            if Path(req).exists():
                resolved_inputs.append(req)
        result.resolved_inputs = resolved_inputs

        if len(resolved_inputs) < len(result.required_inputs):
            result.add_blocker(
                "Partial artifact consumption: not all required inputs "
                "are resolvable"
            )

        # --- Calculate check metrics ---
        result.checks_expected = len(result.required_inputs) + 1
        result.checks_executed = len(resolved_inputs)
        result.checks_passed = len(resolved_inputs)
        result.checks_failed = 0

        if result.has_blockers:
            result.checks_failed = result.checks_expected - result.checks_executed

        return result

    # ------------------------------------------------------------------
    # Validation stage execution
    # ------------------------------------------------------------------

    def run_validation_stage(
        self,
        task_id: str,
        role_name: str,
        stage: str,
        artifacts_dir: str | Path,
    ) -> ControllerValidationResult:
        """Run validator scripts for a given validation stage.

        Each validator script is invoked as a subprocess. If any validator
        fails (nonzero exit code), the stage fails. Collects all results.

        Args:
            task_id: The task identifier.
            role_name: The role owning the validators.
            stage: One of the defined validation stages.
            artifacts_dir: Directory containing artifacts to validate.

        Returns:
            A ControllerValidationResult aggregating all validator outcomes.
        """
        result = ControllerValidationResult()
        result.task_id = task_id
        result.requested_role = role_name
        result.workflow_state = stage

        if stage not in VALID_VALIDATION_STAGES:
            result.add_blocker(
                f"Unknown validation stage '{stage}'. "
                f"Valid stages: {sorted(VALID_VALIDATION_STAGES)}"
            )
            return result

        scripts = self.registry.get_required_validators(role_name, stage)
        result.selected_validators = scripts

        if not scripts:
            result.add_blocker(
                f"No validator scripts registered for role '{role_name}' "
                f"at stage '{stage}'"
            )
            return result

        artifacts_path = Path(artifacts_dir)

        # --- Compute SHA for artifacts ---
        if artifacts_path.exists():
            for entry in sorted(artifacts_path.glob("**/*")):
                if entry.is_file():
                    sha = _compute_sha256(entry)
                    result.artifacts_consumed.append({
                        "path": str(entry),
                        "sha256": sha,
                    })

        result.checks_expected = len(scripts)
        result.checks_executed = 0
        result.checks_passed = 0
        result.checks_failed = 0

        for script_path in scripts:
            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(artifacts_path) if artifacts_path.exists() else None,
                )
                result.checks_executed += 1
                if proc.returncode == 0:
                    result.checks_passed += 1
                else:
                    result.checks_failed += 1
                    result.add_blocker(
                        f"Validator script '{script_path}' failed with exit "
                        f"code {proc.returncode}: {proc.stderr.strip()[:500]}"
                    )
            except subprocess.TimeoutExpired:
                result.checks_executed += 1
                result.checks_failed += 1
                result.add_blocker(
                    f"Validator script '{script_path}' timed out"
                )
            except FileNotFoundError:
                result.add_blocker(
                    f"Validator script not found: {script_path}"
                )
            except OSError as exc:
                result.add_blocker(
                    f"Validator script '{script_path}' OS error: {exc}"
                )

        # --- 6. Zero checks executed = blocker ---
        if result.checks_executed == 0 and not result.has_blockers:
            result.add_blocker(
                f"Validator stage '{stage}' executed zero checks: "
                f"no validator scripts ran successfully"
            )

        if not result.has_blockers and result.checks_executed > 0:
            result.award_pass()

        return result

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    def run_workflow(
        self, workflow_fixture_path: str | Path
    ) -> ControllerValidationResult:
        """Run a synthetic workflow fixture.

        The fixture is a JSON file defining a sequence of tasks. Each
        task specifies a role, action, and inputs. Tasks are dispatched
        sequentially and results are aggregated.

        Args:
            workflow_fixture_path: Path to the workflow fixture JSON file.

        Returns:
            A ControllerValidationResult aggregating all task outcomes.
        """
        result = ControllerValidationResult()
        fixture_path = Path(workflow_fixture_path)

        if not fixture_path.exists():
            result.add_error(f"Workflow fixture not found: {fixture_path}")
            return result

        try:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.add_error(f"Invalid JSON in workflow fixture: {exc}")
            return result

        if not isinstance(fixture, dict):
            result.add_error("Workflow fixture root must be a JSON object")
            return result

        raw_tasks = fixture.get("tasks") or fixture.get("stages")
        if raw_tasks is None:
            raw_tasks = []
        if not isinstance(raw_tasks, list) or len(raw_tasks) == 0:
            result.add_error("Workflow fixture contains no 'tasks' or 'stages' array")
            return result

        tasks: list[dict] = []
        for entry in raw_tasks:
            if isinstance(entry, dict):
                task_contract = entry.get("task_contract", entry)
                task_contract["task_id"] = task_contract.get("task_id", entry.get("stage_id", ""))
                task_contract["role"] = task_contract.get("role", entry.get("role", ""))
                tasks.append(task_contract)

        task_results: list[ControllerValidationResult] = []

        for idx, task_def in enumerate(tasks):
            if not isinstance(task_def, dict):
                result.add_warning(
                    f"Workflow task at index {idx} is not a dict; skipping"
                )
                continue

            task_id = task_def.get("task_id", f"wf_task_{idx}")
            role_name = task_def.get("role", "")
            if not role_name:
                result.add_blocker(
                    f"Workflow task {task_id} has no 'role' field"
                )
                continue

            task_result = self.dispatch_role(task_def, role_name)
            task_results.append(task_result)

            if task_result.has_blockers:
                result.add_blocker(
                    f"Workflow task '{task_id}' (role '{role_name}') failed: "
                    f"{task_result.blocking_findings}"
                )

        aggregated = self.collect_results(task_results)
        result.checks_expected = aggregated.checks_expected
        result.checks_executed = aggregated.checks_executed
        result.checks_passed = aggregated.checks_passed
        result.checks_failed = aggregated.checks_failed
        result.blocking_findings = aggregated.blocking_findings
        result.errors = aggregated.errors
        result.warnings = aggregated.warnings
        result.selected_adapter = aggregated.selected_adapter
        result.selected_validators = aggregated.selected_validators
        result.required_inputs = aggregated.required_inputs
        result.resolved_inputs = aggregated.resolved_inputs
        result.artifacts_consumed = aggregated.artifacts_consumed

        if not result.has_blockers and result.checks_executed > 0:
            result.award_pass()

        return result

    # ------------------------------------------------------------------
    # Result collection and aggregation
    # ------------------------------------------------------------------

    def collect_results(
        self, task_results: list[ControllerValidationResult]
    ) -> ControllerValidationResult:
        """Aggregate multiple ControllerValidationResults into a summary.

        Args:
            task_results: A list of individual task results.

        Returns:
            A single ControllerValidationResult with aggregated metrics.
        """
        aggregated = ControllerValidationResult()

        if not task_results:
            return aggregated

        all_checks_expected = sum(r.checks_expected for r in task_results)
        all_checks_executed = sum(r.checks_executed for r in task_results)
        all_checks_passed = sum(r.checks_passed for r in task_results)
        all_checks_failed = sum(r.checks_failed for r in task_results)

        aggregated.checks_expected = all_checks_expected
        aggregated.checks_executed = all_checks_executed
        aggregated.checks_passed = all_checks_passed
        aggregated.checks_failed = all_checks_failed

        for task_result in task_results:
            aggregated.blocking_findings.extend(task_result.blocking_findings)
            aggregated.errors.extend(task_result.errors)
            aggregated.warnings.extend(task_result.warnings)
            aggregated.artifacts_consumed.extend(task_result.artifacts_consumed)

            if task_result.requested_role:
                aggregated.selected_validators.extend(
                    task_result.selected_validators
                )
                aggregated.required_inputs.extend(
                    task_result.required_inputs
                )
                aggregated.resolved_inputs.extend(
                    task_result.resolved_inputs
                )

        first = task_results[0]
        aggregated.task_id = first.task_id or "aggregated"
        aggregated.workflow_state = first.workflow_state
        aggregated.requested_role = first.requested_role
        aggregated.selected_adapter = first.selected_adapter

        if not aggregated.has_blockers and aggregated.checks_executed > 0:
            aggregated.award_pass()

        return aggregated

    # ------------------------------------------------------------------
    # State transition validation
    # ------------------------------------------------------------------

    def check_transition(
        self,
        from_state: str,
        to_state: str,
        evidence: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Check if a state transition is valid.

        Uses internal transition rules to validate that moving from
        ``from_state`` to ``to_state`` is permitted.

        Args:
            from_state: The originating state.
            to_state: The target state.
            evidence: Optional evidence dict supporting the transition.

        Returns:
            A tuple of (allowed: bool, reason: str).
        """
        # --- Same-state is always allowed ---
        if from_state == to_state:
            return True, "No transition needed (same state)"

        valid_transitions: dict[str, set[str]] = {
            "RECEIVED": {"POLICY_LOADING", "FAILED"},
            "POLICY_LOADING": {"INTENT_ROUTING", "SEMANTIC_AUDIT", "FAILED"},
            "INTENT_ROUTING": {"SEMANTIC_AUDIT", "PLANNING", "FAILED"},
            "SEMANTIC_AUDIT": {"PLANNING", "BLOCKED_HUMAN_INFORMATION", "FAILED"},
            "PLANNING": {"PLAN_READY", "FAILED"},
            "PLAN_READY": {"EXECUTION_ELIGIBLE", "FAILED"},
            "EXECUTION_ELIGIBLE": {"EXECUTING", "FAILED"},
            "EXECUTING": {
                "EXECUTION_COMPLETE", "REJECTED", "REPAIR_REQUIRED", "FAILED",
            },
            "EXECUTION_COMPLETE": {"VERIFICATION_ELIGIBLE", "FAILED"},
            "VERIFICATION_ELIGIBLE": {"VERIFYING", "FAILED"},
            "VERIFYING": {
                "VERIFIED", "VERIFIED_WITH_CAVEAT", "REJECTED",
                "REPAIR_REQUIRED", "FAILED",
            },
            "VERIFIED": {
                "INTEGRATION_ELIGIBLE", "REPORTING", "COMPLETED", "FAILED",
            },
            "VERIFIED_WITH_CAVEAT": {
                "INTEGRATION_ELIGIBLE", "REPORTING", "COMPLETED",
                "HUMAN_GATE_REQUIRED", "FAILED",
            },
            "REJECTED": {"REPAIR_REQUIRED", "HUMAN_GATE_REQUIRED", "FAILED"},
            "REPAIR_REQUIRED": {"EXECUTING", "FAILED"},
            "HUMAN_GATE_REQUIRED": {
                "PLANNING", "EXECUTING", "INTEGRATION_ELIGIBLE", "FAILED",
            },
            "INTEGRATION_ELIGIBLE": {"INTEGRATING", "FAILED"},
            "INTEGRATING": {"VERIFIED", "VERIFIED_WITH_CAVEAT", "FAILED"},
            "REPORTING": {"COMPLETED", "FAILED"},
            "COMPLETED": set(),
            "FAILED": {"REPAIR_REQUIRED", "RECEIVED", "HUMAN_GATE_REQUIRED"},
            "PAUSED": {"RECEIVED", "PLANNING", "EXECUTING", "VERIFYING"},
        }

        allowed_targets = valid_transitions.get(from_state)
        if allowed_targets is None:
            return False, (
                f"Unknown from_state '{from_state}'"
            )

        if to_state not in allowed_targets:
            return False, (
                f"Transition from '{from_state}' to '{to_state}' is not "
                f"allowed. Allowed targets: {sorted(allowed_targets)}"
            )

        return True, (
            f"Transition from '{from_state}' to '{to_state}' is allowed"
        )
