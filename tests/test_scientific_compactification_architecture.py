"""Target architecture: proposal, verification, selection, and C0 bridge gates."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.scientific_compactification import core as architecture


REPO = Path(__file__).resolve().parents[1]
CONTROLLER = REPO / "scripts" / "orch_controller.py"


def _contract():
    return {
        "schema_version": "1.0",
        "loop_id": "architecture-test",
        "scientific_contract": {
            "scope": "STRUCTURAL_ONLY",
            "scientific_invention_forbidden": True,
            "definitions": [],
            "index_semantics": [],
            "assumptions": [],
            "authorized_carrier_definitions": ["KernelA"],
            "declared_claim_scope": "STRUCTURAL_ONLY",
            "allowed_operations": ["finite_sum_distributivity"],
            "forbidden_operations": ["integration_by_parts", "canonical_promotion"],
            "preferences": [],
            "stopping_rule": "human_selection_after_independent_zero_residual",
        },
        "current_representation": {
            "representation_id": "C0",
            "format": "wolfram",
            "content_sha256": "a" * 64,
            "status": "RAW_INGESTED",
        },
        "verification_policy": {
            "independent_verifier_required": True,
            "accepted_backends": ["sympy", "mathematica"],
        },
        "selection_policy": {"human_selection_required": True},
    }


def _candidate(contract):
    contract = architecture.build_contract(contract)
    return {
        "candidate_id": "candidate-1",
        "parent_representation_id": contract["current_representation"]["representation_id"],
        "candidate_representation": {
            "representation_id": "candidate-representation-1",
            "format": "wolfram",
            "content_sha256": "b" * 64,
            "status": "CANDIDATE",
        },
        "proposer_id": "external-proposer",
        "carrier_definitions": ["KernelA"],
        "identities_used": ["finite_sum_distributivity"],
        "claimed_scope": "STRUCTURAL_ONLY",
    }


def _human_select_decision(gate):
    artifact = {
        "selection_id": gate["selection_id"],
        "candidate_sha256": gate["candidate_sha256"],
        "verification_sha256": gate["verification_sha256"],
        "decision": "SELECT",
        "decided_by": "human-scientist",
        "authority_role": "human_scientist",
        "rationale": "The verified carrier form is easier to inspect.",
        "target_reached": False,
    }
    return dict(artifact, decision_artifact_sha256=architecture.canonical_sha(artifact))


def _c0_contract(scope):
    contract = _contract()
    parent_claim = {"lhs": "x", "rhs": "x", "symbols": ["x"], "scope": scope}
    contract["current_representation"] = {
        "representation_id": "C0",
        "format": "sympy_identity_claim",
        "content_sha256": architecture.canonical_sha(parent_claim),
        "status": "CURRENT",
        "verifiable_payload": parent_claim,
        "source_claim_id": "seed",
    }
    contract["scientific_contract"]["declared_claim_scope"] = scope
    return contract


def test_pending_structural_evidence_cannot_open_selection_gate():
    contract = architecture.build_contract(_contract())
    candidate = architecture.build_candidate(contract, _candidate(contract))
    pending = architecture.pending_independent_verification(
        contract, candidate, "structural replay is not an independent CAS residual"
    )
    gate = architecture.blocked_selection_gate(contract, candidate, pending)
    node = architecture.build_pending_chain_node(contract, candidate, pending)
    assert pending["verdict"] == "UNKNOWN"
    assert pending["independent"] is False
    assert gate["status"] == "BLOCKED_INDEPENDENT_VERIFICATION"
    assert node["status"] == "PENDING_INDEPENDENT_VERIFICATION"


def test_zero_residual_requires_human_selection_before_next_representation():
    contract = _c0_contract("STRUCTURAL_ONLY")
    result = architecture.bridge_c0_node(contract, {
        "claim_id": "c0-child",
        "claim": {"lhs": "x + x", "rhs": "2*x", "symbols": ["x"], "scope": "STRUCTURAL_ONLY"},
        "parent_claim_id": "seed",
        "residual_verdict": "ZERO",
    }, "c0-proposer")
    candidate = result["candidate"]
    verification = result["verification"]
    gate = result["selection_gate"]
    assert gate["status"] == "HUMAN_SELECTION_REQUIRED"
    selected = architecture.apply_human_selection(contract, candidate, verification, _human_select_decision(gate))
    assert selected["status"] == "HUMAN_SELECTED"
    assert selected["next_representation"]["parent_representation_id"] == "C0"
    assert selected["next_representation"]["status"] == "SELECTED"
    chain = architecture.build_chain_node(contract, candidate, verification, selected)
    assert chain["status"] == "HUMAN_SELECTED"
    assert chain["selection"]["decision_artifact_sha256"] == selected["decision_artifact_sha256"]


def test_proposer_cannot_self_verify_or_use_unauthorized_identity():
    contract = architecture.build_contract(_contract())
    candidate = _candidate(contract)
    candidate["identities_used"] = ["integration_by_parts"]
    with pytest.raises(architecture.ArchitectureError, match="CANDIDATE_IDENTITY_NOT_AUTHORIZED"):
        architecture.build_candidate(contract, candidate)
    candidate = architecture.build_candidate(contract, _candidate(contract))
    verification = {
        "candidate_sha256": candidate["candidate_sha256"],
        "verifier_id": candidate["proposer_id"],
        "backend": "sympy",
        "verdict": "ZERO",
        "verified_scope": "STRUCTURAL_ONLY",
        "residual_evidence": {"residual": "0", "residual_sha256": "c" * 64},
    }
    with pytest.raises(architecture.ArchitectureError, match="EXECUTOR_VERIFIER_ROLE_CONFLICT"):
        architecture.record_verifier_attestation(contract, candidate, verification)
    verification["verifier_id"] = "external-cas"
    verification["verified_scope"] = "BROADER_THAN_CANDIDATE_SCOPE"
    with pytest.raises(architecture.ArchitectureError, match="VERIFIER_SCOPE_MISMATCH"):
        architecture.record_verifier_attestation(contract, candidate, verification)


def test_c0_bridge_preserves_zero_but_still_requires_human_selection():
    contract = _c0_contract("real")
    c0_node = {
        "claim_id": "c0-child",
        "claim": {"lhs": "x + x", "rhs": "2*x", "symbols": ["x"], "scope": "real"},
        "parent_claim_id": "seed",
        "residual_verdict": "ZERO",
    }
    result = architecture.bridge_c0_node(contract, c0_node, "c0-proposer")
    assert result["verification"]["verdict"] == "ZERO"
    assert result["selection_gate"]["status"] == "HUMAN_SELECTION_REQUIRED"


def test_fabricated_c0_zero_is_rechecked_and_cannot_open_selection():
    contract = _c0_contract("real")
    forged = architecture.bridge_c0_node(contract, {
        "claim_id": "forged",
        "claim": {"lhs": "x", "rhs": "x + 1", "symbols": ["x"], "scope": "real"},
        "parent_claim_id": "seed",
        "residual_verdict": "ZERO",
        "residual": {"sha256": "0" * 64},
    }, "c0-proposer")
    assert forged["verification"]["verdict"] == "NONZERO"
    assert forged["selection_gate"]["status"] == "BLOCKED_INDEPENDENT_VERIFICATION"


def test_sympy_current_representation_payload_must_match_its_declared_hash():
    contract = _c0_contract("real")
    contract["current_representation"]["content_sha256"] = "0" * 64
    with pytest.raises(architecture.ArchitectureError, match="REPRESENTATION_PAYLOAD_HASH_MISMATCH"):
        architecture.build_contract(contract)


def test_unrelated_true_recheck_cannot_select_a_different_candidate_payload():
    contract = _c0_contract("STRUCTURAL_ONLY")
    trusted = architecture.bridge_c0_node(contract, {
        "claim_id": "trusted",
        "parent_claim_id": "seed",
        "claim": {"lhs": "x + x", "rhs": "2*x", "symbols": ["x"], "scope": "STRUCTURAL_ONLY"},
    }, "c0-proposer")
    unrelated_claim = {"lhs": "y + y", "rhs": "2*y", "symbols": ["y"], "scope": "STRUCTURAL_ONLY"}
    unrelated = architecture.build_candidate(contract, {
        "candidate_id": "unrelated",
        "parent_representation_id": "C0",
        "candidate_representation": {
            "representation_id": "unrelated-representation",
            "format": "sympy_identity_claim",
            "content_sha256": architecture.canonical_sha(unrelated_claim),
            "status": "CANDIDATE",
            "verifiable_payload": unrelated_claim,
            "source_claim_id": "unrelated",
        },
        "proposer_id": "c0-proposer",
        "carrier_definitions": [],
        "identities_used": [],
        "claimed_scope": "STRUCTURAL_ONLY",
    })
    forged_verification = dict(trusted["verification"])
    forged_verification["candidate_sha256"] = unrelated["candidate_sha256"]
    forged_verification["verification_sha256"] = architecture.canonical_sha(
        {key: value for key, value in forged_verification.items() if key != "verification_sha256"}
    )
    assert architecture.selection_gate(contract, unrelated, forged_verification)["status"] == "BLOCKED_INDEPENDENT_VERIFICATION"


def test_external_zero_attestation_remains_pending_until_registered_recheck():
    contract = architecture.build_contract(_contract())
    candidate = architecture.build_candidate(contract, _candidate(contract))
    attestation = architecture.record_verifier_attestation(contract, candidate, {
        "candidate_sha256": candidate["candidate_sha256"],
        "verifier_id": "external-cas",
        "backend": "sympy",
        "verdict": "ZERO",
        "verified_scope": "STRUCTURAL_ONLY",
        "residual_evidence": {"residual": "0", "residual_sha256": "c" * 64},
    })
    assert attestation["attested_verdict"] == "ZERO"
    assert attestation["verdict"] == "UNKNOWN"
    assert attestation["independent"] is False
    assert architecture.selection_gate(contract, candidate, attestation)["status"] == "BLOCKED_INDEPENDENT_VERIFICATION"


def test_chain_rejects_forged_selection_status():
    contract = _c0_contract("STRUCTURAL_ONLY")
    result = architecture.bridge_c0_node(contract, {
        "claim_id": "c0-child",
        "claim": {"lhs": "x + x", "rhs": "2*x", "symbols": ["x"], "scope": "STRUCTURAL_ONLY"},
        "parent_claim_id": "seed",
    }, "c0-proposer")
    with pytest.raises(architecture.ArchitectureError, match="CHAIN_SELECTION_GATE_MISMATCH"):
        architecture.build_chain_node(
            contract, result["candidate"], result["verification"], {"status": "HUMAN_SELECTED"}
        )


def test_orch_adapter_routes_target_architecture_contract():
    request = {"operation": "scientific_compactification", "contract_version": "1.0",
               "action": "bootstrap", "contract": _contract()}
    completed = subprocess.run(
        [sys.executable, str(CONTROLLER), "scientific-compactification"],
        input=json.dumps(request), text=True, capture_output=True, cwd=str(REPO),
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "CONTRACT_FROZEN"
    assert result["contract"]["status"] == "CONTRACT_FROZEN"


def test_orch_adapter_preserves_contract_error_taxonomy():
    request = {"operation": "scientific_compactification", "contract_version": "1.0",
               "action": "adjudicate", "contract": _contract()}
    completed = subprocess.run(
        [sys.executable, str(CONTROLLER), "scientific-compactification"],
        input=json.dumps(request), text=True, capture_output=True, cwd=str(REPO),
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["orch_error"] == "REQUEST_ACTION_INPUT_MISSING"


def test_target_architecture_capability_is_orchestrator_only():
    operations = {}
    for profile in ("full", "proposer", "judge"):
        completed = subprocess.run(
            [sys.executable, str(CONTROLLER), "--profile", profile, "list-operations"],
            text=True, capture_output=True, cwd=str(REPO),
        )
        assert completed.returncode == 0, completed.stderr
        operations[profile] = set(json.loads(completed.stdout)["operations"])
    assert "scientific_compactification" in operations["full"]
    assert "scientific_compactification" not in operations["proposer"]
    assert "scientific_compactification" not in operations["judge"]
