#!/usr/bin/env python3
"""Orchestration Controller CLI — validates, dispatches, and runs workflows.

Subcommands:
    validate-task <contract_path>   Validate a task contract JSON file.
    check-transition --from X --to Y  Check state transition validity.
    list-roles                      List all registered roles.
    run-workflow <fixture_path>     Run a workflow fixture JSON file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from loop_engine.orch_dispatcher import ControllerDispatcher
from loop_engine.orch_registry import OrchRegistry


def _register_synthetic_adapters(registry: OrchRegistry) -> None:
    _always_exists = sys.executable
    registry.register_adapter("global_planner", {
        "module_path": "loop_engine.orch_adapters.synthetic_planner",
        "class_name": "SyntheticPlanner",
        "validator_scripts": [],
        "required_inputs": [],
        "allowed_actions": ["read_inputs", "create_plan", "decompose_task", "map_dependencies"],
        "forbidden_actions": ["execute_implementation", "verify_results", "promote_canonical", "self_verify"],
        "claim_authority": "planning",
    })
    registry.register_adapter("lane_planner", {
        "module_path": "loop_engine.orch_adapters.synthetic_planner",
        "class_name": "SyntheticPlanner",
        "validator_scripts": [],
        "required_inputs": [],
        "allowed_actions": ["read_inputs", "create_lane_plan"],
        "forbidden_actions": ["execute_implementation", "verify_results", "promote_canonical", "self_verify"],
        "claim_authority": "planning",
    })
    registry.register_adapter("executor", {
        "module_path": "loop_engine.orch_adapters.synthetic_executor",
        "class_name": "SyntheticExecutor",
        "validator_scripts": ["/bin/true"],
        "required_inputs": [_always_exists],
        "allowed_actions": ["read_frozen_inputs", "execute_transformations", "write_outputs"],
        "forbidden_actions": ["verify_own_output", "self_verify"],
        "claim_authority": "execution",
    })
    registry.register_adapter("repair_executor", {
        "module_path": "loop_engine.orch_adapters.synthetic_executor",
        "class_name": "SyntheticExecutor",
        "validator_scripts": ["/bin/true"],
        "required_inputs": [_always_exists],
        "allowed_actions": ["read_rejection_evidence", "execute_transformations", "write_outputs"],
        "forbidden_actions": ["self_verify"],
        "claim_authority": "execution",
    })
    registry.register_adapter("independent_verifier", {
        "module_path": "loop_engine.orch_adapters.synthetic_executor",
        "class_name": "SyntheticExecutor",
        "validator_scripts": ["/bin/true"],
        "required_inputs": [_always_exists],
        "allowed_actions": ["read_frozen_executor_artifacts", "validate_sha_manifests", "issue_verdict"],
        "forbidden_actions": ["edit_executor_outputs", "self_verify"],
        "claim_authority": "verification",
    })
    registry.register_adapter("human_gate_materializer", {
        "module_path": "loop_engine.orch_adapters.synthetic_executor",
        "class_name": "SyntheticExecutor",
        "validator_scripts": ["/bin/true"],
        "required_inputs": [_always_exists],
        "allowed_actions": ["record_decision", "freeze_decision_artifact"],
        "forbidden_actions": ["make_scientific_decisions"],
        "claim_authority": "human_gate",
    })
    registry.register_adapter("integration_executor", {
        "module_path": "loop_engine.orch_adapters.synthetic_executor",
        "class_name": "SyntheticExecutor",
        "validator_scripts": ["/bin/true"],
        "required_inputs": [_always_exists],
        "allowed_actions": ["read_verified_lane_results", "combine_results", "write_integrated_outputs"],
        "forbidden_actions": ["self_verify_integration"],
        "claim_authority": "integration",
    })


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestration Controller CLI",
    )
    parser.add_argument("--verbose", action="store_true", help="Print extra info to stderr")
    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("validate-task", help="Validate a task contract JSON file")
    p.add_argument("contract_path", help="Path to the task contract JSON file")

    p = subparsers.add_parser("check-transition", help="Check if a state transition is valid")
    p.add_argument("--from", dest="from_state", required=True, help="Originating state")
    p.add_argument("--to", dest="to_state", required=True, help="Target state")

    subparsers.add_parser("list-roles", help="List all registered roles")

    p = subparsers.add_parser("run-workflow", help="Run a workflow fixture")
    p.add_argument("fixture_path", help="Path to the workflow fixture JSON file")

    args = parser.parse_args()

    verbose = args.verbose
    registry = OrchRegistry()
    _register_synthetic_adapters(registry)
    dispatcher = ControllerDispatcher(registry=registry)

    if args.command == "validate-task":
        result = dispatcher.validate_task(args.contract_path)
        output = result.to_dict()
        if verbose:
            print(json.dumps(output, indent=2), file=sys.stderr)
        print(json.dumps({"passed": result.passed, "blocking_findings": result.blocking_findings, "errors": result.errors}))
        sys.exit(0 if result.passed else 1)

    elif args.command == "check-transition":
        allowed, reason = dispatcher.check_transition(args.from_state, args.to_state)
        output = {"allowed": allowed, "reason": reason, "from": args.from_state, "to": args.to_state}
        if verbose:
            print(json.dumps(output, indent=2), file=sys.stderr)
        print(json.dumps(output))
        sys.exit(0 if allowed else 1)

    elif args.command == "list-roles":
        roles = registry.list_roles()
        output = {"roles": roles}
        if verbose:
            print(json.dumps(output, indent=2), file=sys.stderr)
        print(json.dumps(output))
        sys.exit(0)

    elif args.command == "run-workflow":
        result = dispatcher.run_workflow(args.fixture_path)
        output = result.to_dict()
        if verbose:
            print(json.dumps(output, indent=2), file=sys.stderr)
        print(json.dumps({"passed": result.passed, "blocking_findings": result.blocking_findings, "errors": result.errors}))
        sys.exit(0 if result.passed else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
