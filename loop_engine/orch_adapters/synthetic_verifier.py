from __future__ import annotations

from typing import Any


class SyntheticVerifier:
    """Synthetic independent verifier adapter."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.verdict = self.config.get("verdict", "VERIFIED")
        self.should_raise = self.config.get("should_raise", False)
        self.should_return_zero_checks = self.config.get(
            "should_return_zero_checks", False
        )
        self.verifier_id = self.config.get("verifier_id", "synth-verifier-1")
        self.executor_id = self.config.get("executor_id", "synth-executor-1")

    def verify(
        self,
        executor_artifacts_dir: str,
        task_contract: dict[str, Any],
    ) -> Any:
        """Independently verify executor artifacts."""
        from loop_engine.orch_dispatcher import ControllerValidationResult

        result = ControllerValidationResult()
        result.task_id = f"verify-{task_contract.get('task_id', 'unknown')}"
        result.requested_role = "independent_verifier"
        result.selected_adapter = "synthetic_verifier"

        if self.should_raise:
            raise RuntimeError("Synthetic verifier: simulated runtime exception")

        if self.should_return_zero_checks:
            result.checks_expected = 5
            result.checks_executed = 0
            result.checks_passed = 0
            result.add_blocker("Synthetic verifier: zero checks executed")
            return result

        result.checks_expected = 3
        result.checks_executed = 3

        if self.verdict == "VERIFIED":
            result.checks_passed = 3
            result.checks_failed = 0
            result.award_pass()
        elif self.verdict == "VERIFIED_WITH_CAVEAT":
            result.checks_passed = 3
            result.checks_failed = 0
            result.add_warning("Caveat: assumption not independently verifiable")
            result.award_pass()
        elif self.verdict == "REJECTED":
            result.checks_passed = 0
            result.checks_failed = 3
            result.add_blocker("Synthetic verifier: executor output rejected")

        result.transition_attempted = {
            "from_state": "VERIFICATION_ELIGIBLE",
            "to_state": self.verdict,
        }
        result.transition_result = {
            "allowed": True,
            "reason": f"Verdict: {self.verdict}",
        }
        return result
