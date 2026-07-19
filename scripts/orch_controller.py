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
    # Gate 3.5: narrow geometric-basis verification capability (math unchanged).
    registry.register_adapter("geometric_basis_verify", {
        "module_path": "loop_engine.orch_adapters.geometric_basis_verify_adapter",
        "class_name": "GeometricBasisVerifyAdapter",
        "validator_scripts": [],
        "required_inputs": [],
        "allowed_actions": ["verify_geometric_basis_claim"],
        "forbidden_actions": ["promote_canonical", "reinterpret_scope",
                              "upgrade_numerical_to_symbolic"],
        "claim_authority": "verification",
    })
    # Fusion Stage 1: GENERAL symbolic identity judge (arbitrary caller expression).
    # Same verification authority + fail-closed governance; forbidden from self-verifying
    # or accepting any proposer's self-scored result as evidence.
    registry.register_adapter("symbolic_identity_verify", {
        "module_path": "loop_engine.orch_adapters.symbolic_identity_verify_adapter",
        "class_name": "SymbolicIdentityVerifyAdapter",
        "validator_scripts": [],
        "required_inputs": [],
        "allowed_actions": ["adjudicate_symbolic_identity_claim"],
        "forbidden_actions": ["promote_canonical", "reinterpret_scope",
                              "upgrade_numerical_to_symbolic", "self_verify",
                              "accept_proposer_self_score"],
        "claim_authority": "verification",
    })
    # Fusion Stage 2: the PROPOSER organ. Emits UNVERIFIED candidate claims only; it may
    # never verify, score, promote, or execute generated code. proposal authority.
    registry.register_adapter("propose_equation_candidates", {
        "module_path": "loop_engine.orch_adapters.propose_equation_candidates_adapter",
        "class_name": "ProposeEquationCandidatesAdapter",
        "validator_scripts": [],
        "required_inputs": [],
        "allowed_actions": ["propose_candidate_claims"],
        "forbidden_actions": ["verify_results", "self_verify", "promote_canonical",
                              "score_candidates", "execute_generated_code"],
        "claim_authority": "proposal",
    })


def route_geometric_basis_verify(registry: OrchRegistry, raw: str) -> tuple[dict, int]:
    """Pure routing seam: raw JSON request -> (response payload, exit code).

    Shared verbatim by the production CLI and by the Gate-4 test harness so both
    exercise the IDENTICAL ORCH routing (capability lookup, real importlib adapter
    load, verbatim exit-code propagation). ORCH does NOT reinterpret scope, average
    oracles, upgrade evidence, or wrap a conflict as success. This function contains
    no fault-injection path; a test harness injects faults only by monkeypatching the
    vendored verifier in its OWN process before calling this — the capability is never
    exposed to a normal caller of the registry or the CLI."""
    try:
        req = json.loads(raw)
    except Exception as exc:
        return {"orch_error": "INVALID_JSON_REQUEST", "detail": str(exc)[:120]}, 1
    op = req.get("operation")
    if registry.get_adapter(op) is None:
        return {"orch_error": "CAPABILITY_NOT_REGISTERED", "operation": op,
                "attempted_registry": "loop_engine.orch_registry"}, 1
    try:
        adapter = registry.load_adapter_instance(op)   # real importlib load path
    except Exception as exc:
        return {"orch_error": "ADAPTER_LOAD_FAILED", "operation": op, "detail": str(exc)[:160]}, 1
    try:
        result, exit_code = adapter.run(req)
    except Exception as exc:
        # Emit the contract error taxonomy at the boundary, not a library class name:
        # AdapterError carries .code; a jsonschema ValidationError maps to the contract code.
        code = getattr(exc, "code", None)
        if code is None:
            code = "SCHEMA_VALIDATION_FAILED" if exc.__class__.__name__ == "ValidationError" \
                   else exc.__class__.__name__
        return {"orch_error": code, "operation": op}, 1
    return result, exit_code


def route_symbolic_identity_verify(registry: OrchRegistry, raw: str) -> tuple[dict, int]:
    """Pure routing seam for the general symbolic identity judge.

    Same contract as route_geometric_basis_verify: capability lookup -> real importlib
    adapter load -> verbatim exit-code propagation. Emits the contract error taxonomy at
    the boundary (AdapterError.code) rather than a library class name."""
    try:
        req = json.loads(raw)
    except Exception as exc:
        return {"orch_error": "INVALID_JSON_REQUEST", "detail": str(exc)[:120]}, 1
    op = req.get("operation")
    if registry.get_adapter(op) is None:
        return {"orch_error": "CAPABILITY_NOT_REGISTERED", "operation": op,
                "attempted_registry": "loop_engine.orch_registry"}, 1
    try:
        adapter = registry.load_adapter_instance(op)
    except Exception as exc:
        return {"orch_error": "ADAPTER_LOAD_FAILED", "operation": op, "detail": str(exc)[:160]}, 1
    try:
        result, exit_code = adapter.run(req)
    except Exception as exc:
        code = getattr(exc, "code", None) or (
            "SCHEMA_VALIDATION_FAILED" if exc.__class__.__name__ == "ValidationError" else exc.__class__.__name__)
        return {"orch_error": code, "operation": op}, 1
    return result, exit_code


def route_propose_equation_candidates(registry: OrchRegistry, raw: str) -> tuple[dict, int]:
    """Pure routing seam for the proposer organ (same shape as the other seams)."""
    try:
        req = json.loads(raw)
    except Exception as exc:
        return {"orch_error": "INVALID_JSON_REQUEST", "detail": str(exc)[:120]}, 1
    op = req.get("operation")
    if registry.get_adapter(op) is None:
        return {"orch_error": "CAPABILITY_NOT_REGISTERED", "operation": op}, 1
    try:
        adapter = registry.load_adapter_instance(op)
    except Exception as exc:
        return {"orch_error": "ADAPTER_LOAD_FAILED", "operation": op, "detail": str(exc)[:160]}, 1
    try:
        result, exit_code = adapter.run(req)
    except Exception as exc:
        code = getattr(exc, "code", None) or exc.__class__.__name__
        return {"orch_error": code, "operation": op}, 1
    return result, exit_code


def build_registry() -> OrchRegistry:
    """Construct the production registry exactly as the CLI does (no fault adapters)."""
    registry = OrchRegistry()
    _register_synthetic_adapters(registry)
    return registry


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
    subparsers.add_parser("list-operations", help="List registered capability/adapter operations")

    p = subparsers.add_parser("run-workflow", help="Run a workflow fixture")
    p.add_argument("fixture_path", help="Path to the workflow fixture JSON file")

    subparsers.add_parser("geometric-basis-verify",
                          help="Route a geometric_basis_verify request (JSON on stdin) through the registry")
    subparsers.add_parser("symbolic-identity-verify",
                          help="Route a symbolic_identity_verify request (JSON on stdin) through the registry")
    subparsers.add_parser("propose-equation-candidates",
                          help="Route a propose_equation_candidates request (JSON on stdin) through the registry")

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

    elif args.command == "list-operations":
        ops = sorted(registry._adapters.keys())
        print(json.dumps({"operations": ops}))
        sys.exit(0)

    elif args.command == "geometric-basis-verify":
        # CLI request -> shared routing seam -> ORCH registry -> adapter -> ORCH response.
        result, exit_code = route_geometric_basis_verify(registry, sys.stdin.read())
        print(json.dumps(result))
        sys.exit(exit_code)

    elif args.command == "symbolic-identity-verify":
        result, exit_code = route_symbolic_identity_verify(registry, sys.stdin.read())
        print(json.dumps(result))
        sys.exit(exit_code)

    elif args.command == "propose-equation-candidates":
        result, exit_code = route_propose_equation_candidates(registry, sys.stdin.read())
        print(json.dumps(result))
        sys.exit(exit_code)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
