from __future__ import annotations

from typing import Any


class SyntheticExecutor:
    """Synthetic executor adapter for testing fail-closed behavior."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.should_fail = self.config.get("should_fail", False)
        self.should_raise = self.config.get("should_raise", False)
        self.should_return_zero_checks = self.config.get(
            "should_return_zero_checks", False
        )
        self.should_return_malformed = self.config.get(
            "should_return_malformed", False
        )
        self.missing_inputs: list[str] = self.config.get("missing_inputs", [])

    def execute(
        self,
        task_contract: dict[str, Any],
        inputs_dir: str,
    ) -> Any:
        """Execute the task. Returns a ControllerValidationResult-like dict."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        result = ControllerValidationResult()
        result.task_id = task_contract.get("task_id", "unknown")
        result.requested_role = "executor"
        result.selected_adapter = "synthetic_executor"
        result.required_inputs = task_contract.get("required_outputs", [])

        if self.should_raise:
            raise RuntimeError("Synthetic executor: simulated runtime exception")

        if self.should_fail:
            result.add_blocker("Synthetic executor: configured to fail")
            return result

        if self.missing_inputs:
            for inp in self.missing_inputs:
                result.add_blocker(f"Required input not found: {inp}")
            return result

        if self.should_return_zero_checks:
            result.checks_expected = 5
            result.checks_executed = 0
            result.checks_passed = 0
            result.checks_failed = 0
            result.add_blocker("Synthetic executor: zero checks executed")
            return result

        if self.should_return_malformed:
            return {"task_id": "malformed", "this_is_broken": True}

        result.checks_expected = 3
        result.checks_executed = 3
        result.checks_passed = 3
        result.checks_failed = 0
        result.resolved_inputs = list(result.required_inputs)
        result.transition_attempted = {
            "from_state": "EXECUTION_ELIGIBLE",
            "to_state": "EXECUTION_COMPLETE",
        }
        result.transition_result = {
            "allowed": True,
            "reason": "Synthetic executor completed",
        }
        result.award_pass()
        return result

    def validate_outputs(self, output_dir: str) -> dict[str, Any]:
        """Validate executor outputs. Returns a dict with validation results."""
        if self.should_raise:
            raise RuntimeError(
                "Synthetic executor validation: simulated runtime exception"
            )
        return {
            "passed": not self.should_fail,
            "checks": 3,
            "errors": [] if not self.should_fail else ["synthetic failure"],
        }
