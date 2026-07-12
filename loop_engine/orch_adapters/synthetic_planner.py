from __future__ import annotations

from typing import Any


class SyntheticPlanner:
    """Synthetic planner adapter."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create a plan from a request. Returns task contracts."""
        return {
            "tasks": [
                {"task_id": "exec-1", "role": "executor", "depends_on": []},
                {
                    "task_id": "verify-1",
                    "role": "independent_verifier",
                    "depends_on": ["exec-1"],
                },
            ],
            "parallel_lanes": [],
            "integration_points": [],
        }
