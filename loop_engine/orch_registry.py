from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

ROLE_REGISTRY: dict[str, dict[str, Any]] = {
    "global_planner": {
        "max_claim": "planning",
        "allowed_actions": [
            "read_inputs",
            "create_plan",
            "decompose_task",
            "map_dependencies",
        ],
        "forbidden_actions": [
            "execute_implementation",
            "verify_results",
            "promote_canonical",
            "self_verify",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "lane_planner": {
        "max_claim": "planning",
        "allowed_actions": [
            "read_inputs",
            "create_lane_plan",
        ],
        "forbidden_actions": [
            "execute_implementation",
            "verify_results",
            "promote_canonical",
            "self_verify",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "executor": {
        "max_claim": "execution",
        "allowed_actions": [
            "read_frozen_inputs",
            "execute_transformations",
            "write_outputs",
            "generate_sha_manifest",
        ],
        "forbidden_actions": [
            "verify_own_output",
            "repair_own_output",
            "promote_canonical",
            "self_verify",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "independent_verifier": {
        "max_claim": "verification",
        "allowed_actions": [
            "read_frozen_executor_artifacts",
            "validate_sha_manifests",
            "recompute_results",
            "issue_verdict",
        ],
        "forbidden_actions": [
            "edit_executor_outputs",
            "repair_executor_outputs",
            "read_executor_scratch",
            "self_verify",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": False,
    },
    "repair_executor": {
        "max_claim": "execution",
        "allowed_actions": [
            "read_rejection_evidence",
            "read_original_artifacts",
            "execute_transformations",
            "write_outputs",
        ],
        "forbidden_actions": [
            "overwrite_original_artifacts",
            "self_verify",
            "promote_canonical",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "human_gate_materializer": {
        "max_claim": "human_gate",
        "allowed_actions": [
            "record_decision",
            "freeze_decision_artifact",
            "update_registry",
        ],
        "forbidden_actions": [
            "make_scientific_decisions",
            "promote_canonical",
            "self_verify",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": False,
    },
    "integration_executor": {
        "max_claim": "integration",
        "allowed_actions": [
            "read_verified_lane_results",
            "combine_results",
            "write_integrated_outputs",
        ],
        "forbidden_actions": [
            "self_verify_integration",
            "promote_canonical",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "integration_verifier": {
        "max_claim": "verification",
        "allowed_actions": [
            "read_integration_outputs",
            "validate_integration",
            "issue_verdict",
        ],
        "forbidden_actions": [
            "edit_integration_outputs",
            "repair_integration",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": False,
    },
    "report_generator": {
        "max_claim": "reporting",
        "allowed_actions": [
            "read_verified_results",
            "generate_report",
        ],
        "forbidden_actions": [
            "self_verify_report",
            "promote_canonical",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "report_verifier": {
        "max_claim": "verification",
        "allowed_actions": [
            "read_report",
            "validate_claims",
            "issue_verdict",
        ],
        "forbidden_actions": [
            "edit_report",
            "rewrite_report",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": False,
    },
    "supplement_writer": {
        "max_claim": "supplement",
        "allowed_actions": [
            "read_verified_results",
            "write_supplement",
        ],
        "forbidden_actions": [
            "self_review_supplement",
            "promote_canonical",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": True,
    },
    "supplement_reviewer": {
        "max_claim": "verification",
        "allowed_actions": [
            "read_supplement",
            "review_supplement",
        ],
        "forbidden_actions": [
            "edit_supplement",
        ],
        "can_verify_self": False,
        "can_repair": False,
        "requires_independent_verifier": False,
    },
}

CLAIM_LEVEL_RANK: dict[str, int] = {
    "planning": 0,
    "execution": 1,
    "verification": 2,
    "human_gate": 3,
    "integration": 4,
    "reporting": 5,
    "supplement": 5,
    "canonical": 6,
    "publication": 7,
}


class OrchRegistry:
    """Role and adapter registry for orchestration controller.

    Manages role definitions, adapter specifications, and validator scripts.
    Supports loading from a JSON registry file or using builtin defaults.
    """

    def __init__(self, registry_path: str | Path | None = None) -> None:
        """Load registry from a JSON file or use builtin defaults.

        Args:
            registry_path: Optional path to a JSON registry file. If not
                provided or the file is missing/invalid, the builtin
                ROLE_REGISTRY is used as the default.
        """
        self._roles: dict[str, dict[str, Any]] = dict(ROLE_REGISTRY)
        self._adapters: dict[str, dict[str, Any]] = {}

        if registry_path is not None:
            self._load_registry_file(Path(registry_path))

    def _load_registry_file(self, path: Path) -> None:
        """Load and merge a JSON registry file into the current roles.

        Entries from the file supplement or override builtin defaults.
        Malformed files are logged and silently skipped (builtin defaults
        remain intact).
        """
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

        if not isinstance(data, dict):
            return

        roles = data.get("roles") if isinstance(data.get("roles"), dict) else data
        for role_name, role_def in roles.items():
            if isinstance(role_def, dict):
                self._roles[role_name] = role_def

    def register_adapter(self, role_name: str, adapter_spec: dict[str, Any]) -> None:
        """Register an adapter for a role.

        Args:
            role_name: The role identifier (e.g. 'executor').
            adapter_spec: A dict with keys:
                - module_path: Python module path
                  (e.g. 'loop_engine.orch_adapters.synthetic_executor')
                - class_name: class name within the module
                - validator_scripts: list of script paths to run as validators
                - required_inputs: list of input file path descriptions
                - allowed_actions: list of permitted actions
                - forbidden_actions: list of disallowed actions
                - claim_authority: string identifying the claim level
        """
        required_keys = {
            "module_path",
            "class_name",
            "validator_scripts",
            "required_inputs",
            "allowed_actions",
            "forbidden_actions",
            "claim_authority",
        }
        missing = required_keys - set(adapter_spec.keys())
        if missing:
            raise ValueError(
                f"Adapter spec for role '{role_name}' is missing required keys: "
                f"{sorted(missing)}"
            )
        self._adapters[role_name] = dict(adapter_spec)

    def get_adapter(self, role_name: str) -> dict[str, Any] | None:
        """Get the adapter spec for a role.

        Args:
            role_name: The role identifier.

        Returns:
            The adapter spec dict, or None if no adapter is registered.
        """
        return self._adapters.get(role_name)

    def get_required_validators(
        self, role_name: str, stage: str
    ) -> list[str]:
        """Get validator scripts required for a role at a given stage.

        Validator stages include: 'pre_execute', 'post_execute',
        'pre_verify', 'post_verify', 'pre_integration'.

        Args:
            role_name: The role identifier.
            stage: The validation stage name.

        Returns:
            A list of validator script paths. If no adapter is registered
            or the stage has no validators, returns an empty list.
        """
        adapter = self.get_adapter(role_name)
        if adapter is None:
            return []
        validators = adapter.get("validator_scripts", [])
        if isinstance(validators, list):
            return validators
        if isinstance(validators, dict):
            return validators.get(stage, [])
        return []

    def load_adapter_instance(self, role_name: str) -> Any:
        """Dynamically import and instantiate the adapter class.

        Enforces fail-closed behavior: if the module or class cannot be
        imported, an ImportError is raised. The caller must handle the
        error to block the pipeline.

        Args:
            role_name: The role identifier.

        Returns:
            An instance of the adapter class.

        Raises:
            ImportError: If the module or class is unavailable.
            ValueError: If no adapter is registered for the role.
        """
        adapter_spec = self.get_adapter(role_name)
        if adapter_spec is None:
            raise ValueError(
                f"No adapter registered for role '{role_name}'. "
                f"Available roles: {sorted(self._adapters.keys())}"
            )

        module_path = adapter_spec["module_path"]
        class_name = adapter_spec["class_name"]

        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ImportError(
                f"Fail-closed: cannot import adapter module '{module_path}' "
                f"for role '{role_name}': {exc}"
            ) from exc

        cls = getattr(module, class_name, None)
        if cls is None:
            raise ImportError(
                f"Fail-closed: module '{module_path}' has no class "
                f"'{class_name}' for role '{role_name}'"
            )

        return cls()

    def list_roles(self) -> list[str]:
        """List all registered role names.

        Returns:
            A sorted list of role name strings.
        """
        return sorted(self._roles.keys())

    def validate_role(
        self, role_name: str, claimed_authority: str
    ) -> tuple[bool, str]:
        """Check if role_name is valid and the claimed authority is within
        bounds.

        Args:
            role_name: The role identifier to validate.
            claimed_authority: The authority level being claimed.

        Returns:
            A tuple of (is_valid, reason).
        """
        role = self._roles.get(role_name)
        if role is None:
            return False, (
                f"Unknown role '{role_name}'. "
                f"Registered roles: {sorted(self._roles.keys())}"
            )

        max_claim = role.get("max_claim", "")
        max_rank = CLAIM_LEVEL_RANK.get(max_claim, -1)
        claimed_rank = CLAIM_LEVEL_RANK.get(claimed_authority, -1)

        if claimed_rank < 0:
            return False, (
                f"Unknown claim authority '{claimed_authority}'. "
                f"Known levels: {sorted(CLAIM_LEVEL_RANK.keys())}"
            )

        if max_rank < 0:
            return False, (
                f"Unknown max claim '{max_claim}' for role '{role_name}'. "
                f"Known levels: {sorted(CLAIM_LEVEL_RANK.keys())}"
            )

        if claimed_rank > max_rank:
            return False, (
                f"Role '{role_name}' can claim at most '{max_claim}' "
                f"(rank {max_rank}), but claimed '{claimed_authority}' "
                f"(rank {claimed_rank})"
            )

        return True, (
            f"Role '{role_name}' authorized to claim '{claimed_authority}'"
        )
