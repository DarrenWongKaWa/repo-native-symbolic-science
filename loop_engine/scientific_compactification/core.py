"""Target-architecture contracts for scientific compactification.

This module deliberately separates five facts that are often conflated:

* a human scientific contract A_i;
* a current immutable representation C_i;
* an untrusted proposal C~_(i+1);
* an independent verifier verdict for the declared residual; and
* a human selection decision that alone authorizes C_(i+1) as the next node.

It is an orchestration data model, not a symbolic engine.  A verifier backend
must supply the residual evidence; this layer fails closed on UNKNOWN and never
promotes a representation automatically.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


SCHEMA_VERSION = "1.0"
VERDICTS = {"ZERO", "NONZERO", "UNKNOWN"}


class ArchitectureError(ValueError):
    """A contract violation that must block downstream selection."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_sha(value: Any) -> str:
    """Hash JSON data deterministically for provenance edges."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _require_object(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ArchitectureError(label + "_MALFORMED")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArchitectureError(label + "_MALFORMED")
    return value


def _require_sha(value: Any, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ArchitectureError(label + "_MALFORMED")
    return value


def _require_string_list(value: Any, label: str, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ArchitectureError(label + "_MALFORMED")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ArchitectureError(label + "_MALFORMED")
    return list(value)


def validate_representation(representation: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an immutable representation reference C_i or C_(i+1)."""
    representation = _require_object(representation, "REPRESENTATION")
    _require_nonempty_string(representation.get("representation_id"), "REPRESENTATION_ID")
    _require_nonempty_string(representation.get("format"), "REPRESENTATION_FORMAT")
    _require_sha(representation.get("content_sha256"), "REPRESENTATION_CONTENT_SHA256")
    status = representation.get("status")
    if status not in {"CURRENT", "SELECTED", "RAW_INGESTED", "CANDIDATE"}:
        raise ArchitectureError("REPRESENTATION_STATUS_MALFORMED")
    parent = representation.get("parent_representation_id")
    if parent is not None:
        _require_nonempty_string(parent, "REPRESENTATION_PARENT_ID")
    if representation["format"] == "sympy_identity_claim":
        payload = _require_object(representation.get("verifiable_payload"), "REPRESENTATION_VERIFIABLE_PAYLOAD")
        if representation["content_sha256"] != canonical_sha(payload):
            raise ArchitectureError("REPRESENTATION_PAYLOAD_HASH_MISMATCH")
        _require_nonempty_string(representation.get("source_claim_id"), "REPRESENTATION_SOURCE_CLAIM_ID")
    return dict(representation)


def build_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Freeze A_i and C_i without inferring any scientific semantics."""
    contract = _require_object(contract, "CONTRACT")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ArchitectureError("CONTRACT_VERSION_UNSUPPORTED")
    loop_id = _require_nonempty_string(contract.get("loop_id"), "LOOP_ID")
    scientific = _require_object(contract.get("scientific_contract"), "SCIENTIFIC_CONTRACT")
    scope = scientific.get("scope")
    if scope not in {"STRUCTURAL_ONLY", "DECLARED_SCIENTIFIC_SCOPE"}:
        raise ArchitectureError("SCIENTIFIC_SCOPE_MALFORMED")
    if scientific.get("scientific_invention_forbidden") is not True:
        raise ArchitectureError("SCIENTIFIC_INVENTION_MUST_BE_FORBIDDEN")
    allowed = _require_string_list(scientific.get("allowed_operations"), "ALLOWED_OPERATIONS", False)
    forbidden = _require_string_list(scientific.get("forbidden_operations"), "FORBIDDEN_OPERATIONS", False)
    if set(allowed) & set(forbidden):
        raise ArchitectureError("OPERATION_AUTHORIZATION_OVERLAP")
    for field in ("definitions", "index_semantics", "assumptions", "preferences"):
        _require_string_list(scientific.get(field, []), "SCIENTIFIC_" + field.upper())
    _require_string_list(scientific.get("authorized_carrier_definitions", []),
                         "AUTHORIZED_CARRIER_DEFINITIONS")
    _require_nonempty_string(scientific.get("declared_claim_scope"), "DECLARED_CLAIM_SCOPE")
    _require_nonempty_string(scientific.get("stopping_rule"), "STOPPING_RULE")
    current = validate_representation(contract.get("current_representation"))
    if current["status"] not in {"CURRENT", "RAW_INGESTED"}:
        raise ArchitectureError("CURRENT_REPRESENTATION_STATUS_INVALID")
    verification = _require_object(contract.get("verification_policy"), "VERIFICATION_POLICY")
    if verification.get("independent_verifier_required") is not True:
        raise ArchitectureError("INDEPENDENT_VERIFIER_REQUIRED")
    _require_string_list(verification.get("accepted_backends"), "ACCEPTED_BACKENDS", False)
    selection = _require_object(contract.get("selection_policy"), "SELECTION_POLICY")
    if selection.get("human_selection_required") is not True:
        raise ArchitectureError("HUMAN_SELECTION_REQUIRED")
    out = {
        "schema_version": SCHEMA_VERSION,
        "loop_id": loop_id,
        "scientific_contract": dict(scientific),
        "current_representation": current,
        "verification_policy": dict(verification),
        "selection_policy": dict(selection),
        "status": "CONTRACT_FROZEN",
    }
    out["contract_sha256"] = canonical_sha(out)
    return out


def build_candidate(contract: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Freeze a proposal without treating it as verified or selected."""
    contract = build_contract(contract)
    candidate = _require_object(candidate, "CANDIDATE")
    _require_nonempty_string(candidate.get("candidate_id"), "CANDIDATE_ID")
    if candidate.get("parent_representation_id") != contract["current_representation"]["representation_id"]:
        raise ArchitectureError("CANDIDATE_PARENT_MISMATCH")
    representation = validate_representation(candidate.get("candidate_representation"))
    if representation["status"] != "CANDIDATE":
        raise ArchitectureError("CANDIDATE_REPRESENTATION_STATUS_INVALID")
    _require_nonempty_string(candidate.get("proposer_id"), "PROPOSER_ID")
    _require_string_list(candidate.get("carrier_definitions", []), "CARRIER_DEFINITIONS")
    authorized_carriers = set(contract["scientific_contract"].get("authorized_carrier_definitions", []))
    if any(carrier not in authorized_carriers for carrier in candidate.get("carrier_definitions", [])):
        raise ArchitectureError("CANDIDATE_CARRIER_NOT_AUTHORIZED")
    identities = _require_string_list(candidate.get("identities_used", []), "IDENTITIES_USED")
    allowed = set(contract["scientific_contract"]["allowed_operations"])
    if any(identity not in allowed for identity in identities):
        raise ArchitectureError("CANDIDATE_IDENTITY_NOT_AUTHORIZED")
    claimed_scope = _require_nonempty_string(candidate.get("claimed_scope"), "CANDIDATE_SCOPE")
    if claimed_scope != contract["scientific_contract"]["declared_claim_scope"]:
        raise ArchitectureError("CANDIDATE_SCOPE_MISMATCH")
    out = {
        "candidate_id": candidate["candidate_id"],
        "parent_representation_id": candidate["parent_representation_id"],
        "candidate_representation": representation,
        "proposer_id": candidate["proposer_id"],
        "carrier_definitions": list(candidate.get("carrier_definitions", [])),
        "identities_used": identities,
        "claimed_scope": claimed_scope,
        "proposal_status": "PROPOSAL_ONLY",
        "contract_sha256": contract["contract_sha256"],
    }
    out["candidate_sha256"] = canonical_sha(out)
    return out


def record_verifier_attestation(contract: Dict[str, Any], candidate: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
    """Record external verifier output without upgrading it to independent proof.

    A JSON payload from a named CAS process is provenance, not rechecked proof.
    It remains pending until a registered, role-isolated rechecker validates the
    immutable verifier artifact.  The only bundled trusted recheck is the C0
    SymPy bridge below.
    """
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    verification = _require_object(verification, "VERIFICATION")
    if verification.get("candidate_sha256") != candidate["candidate_sha256"]:
        raise ArchitectureError("VERIFICATION_CANDIDATE_MISMATCH")
    verifier_id = _require_nonempty_string(verification.get("verifier_id"), "VERIFIER_ID")
    if verifier_id == candidate["proposer_id"]:
        raise ArchitectureError("EXECUTOR_VERIFIER_ROLE_CONFLICT")
    backend = _require_nonempty_string(verification.get("backend"), "VERIFIER_BACKEND")
    if backend not in contract["verification_policy"]["accepted_backends"]:
        raise ArchitectureError("VERIFIER_BACKEND_NOT_AUTHORIZED")
    verdict = verification.get("verdict")
    if verdict not in VERDICTS:
        raise ArchitectureError("VERIFIER_VERDICT_MALFORMED")
    verified_scope = _require_nonempty_string(verification.get("verified_scope"), "VERIFIED_SCOPE")
    if verified_scope != candidate["claimed_scope"]:
        raise ArchitectureError("VERIFIER_SCOPE_MISMATCH")
    evidence = _require_object(verification.get("residual_evidence"), "RESIDUAL_EVIDENCE")
    if verdict == "ZERO":
        _require_sha(evidence.get("residual_sha256"), "RESIDUAL_SHA256")
        if evidence.get("residual") != "0":
            raise ArchitectureError("ZERO_VERDICT_WITHOUT_ZERO_RESIDUAL")
    elif verdict == "NONZERO":
        _require_nonempty_string(evidence.get("counterexample_or_residual"), "NONZERO_EVIDENCE")
    else:
        _require_nonempty_string(evidence.get("reason"), "UNKNOWN_EVIDENCE")
    out = {
        "candidate_sha256": candidate["candidate_sha256"],
        "verifier_id": verifier_id,
        "backend": backend,
        "attested_verdict": verdict,
        "verdict": "UNKNOWN",
        "verified_scope": verified_scope,
        "residual_evidence": dict(evidence),
        "independent": False,
        "status": "PENDING_EXTERNAL_RECHECK",
        "contract_sha256": contract["contract_sha256"],
    }
    out["verification_sha256"] = canonical_sha(out)
    return out


def _stable_c0_recheck(claim: Dict[str, Any]):
    """Run C0's exact checker and remove wall-clock noise from its binding hash."""
    from loop_engine.orch_adapters.compactification_loop import core as c0_core
    record = c0_core.python_verify(claim)
    stable_record = {key: value for key, value in record.items() if key != "seconds"}
    return record, stable_record


def _stable_c0_edge_recheck(parent_claim: Dict[str, Any], candidate_claim: Dict[str, Any]):
    """Recheck a C_i -> C_(i+1) edge, not merely the proposed endpoint."""
    from loop_engine.orch_adapters.compactification_loop import core as c0_core
    parent_record, stable_parent = _stable_c0_recheck(parent_claim)
    residual = c0_core.construct_residual(parent_claim, candidate_claim)
    residual_record = c0_core.python_verify(residual)
    stable_residual = {key: value for key, value in residual_record.items() if key != "seconds"}
    return parent_record, stable_parent, residual, residual_record, stable_residual


def _selection_eligible_verification(contract: Dict[str, Any], candidate: Dict[str, Any], verification: Dict[str, Any]) -> bool:
    """Return true only for a bundled or future registered trusted recheck."""
    if not (
            isinstance(verification, dict)
            and verification.get("candidate_sha256") == candidate["candidate_sha256"]
            and verification.get("contract_sha256") == contract["contract_sha256"]
            and verification.get("verified_scope") == candidate["claimed_scope"]
            and verification.get("backend") in contract["verification_policy"]["accepted_backends"]
            and verification.get("verifier_id") != candidate["proposer_id"]
            and verification.get("verdict") == "ZERO"
            and verification.get("independent") is True
            and verification.get("status") == "VERIFIED_BY_RECHECK"
            and verification.get("recheck_kind") == "c0_sympy_identity"
            and isinstance(verification.get("verification_sha256"), str)
            and verification["verification_sha256"] == canonical_sha(
                {key: value for key, value in verification.items() if key != "verification_sha256"}
            )):
        return False
    try:
        recheck_claim = _require_object(verification.get("recheck_claim"), "RECHECK_CLAIM")
        parent_claim = _require_object(contract["current_representation"].get("verifiable_payload"),
                                       "RECHECK_PARENT_CLAIM")
        if candidate["candidate_representation"].get("format") != "sympy_identity_claim":
            return False
        if candidate["candidate_representation"].get("content_sha256") != canonical_sha(recheck_claim):
            return False
        if recheck_claim.get("scope") != candidate["claimed_scope"]:
            return False
        if verification.get("parent_claim_id") != contract["current_representation"].get("source_claim_id"):
            return False
        fresh_parent, stable_parent, residual, fresh, stable_fresh = _stable_c0_edge_recheck(
            parent_claim, recheck_claim
        )
    except Exception:
        return False
    expected_sha = canonical_sha({
        "parent_claim": parent_claim,
        "candidate_claim": recheck_claim,
        "parent_recheck": stable_parent,
        "edge_residual": residual,
        "residual_recheck": stable_fresh,
    })
    evidence = verification.get("residual_evidence") or {}
    return (
        fresh_parent.get("verdict") == "ZERO"
        and fresh.get("verdict") == "ZERO"
        and evidence.get("residual") == "0"
        and evidence.get("residual_sha256") == expected_sha
        and verification.get("recheck_record_sha256") == canonical_sha({
            "parent": stable_parent, "residual": stable_fresh
        })
    )


def selection_gate(contract: Dict[str, Any], candidate: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
    """Create the human-only selection gate after an independent verdict."""
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    if not _selection_eligible_verification(contract, candidate, verification):
        status = "BLOCKED_INDEPENDENT_VERIFICATION"
        question = "No scientific selection is eligible until an independent ZERO residual verdict exists."
    else:
        status = "HUMAN_SELECTION_REQUIRED"
        question = (
            "Select or reject this verified candidate as the next representation. "
            "Selection is a human compactness-and-meaning decision, not an automatic promotion."
        )
    out = {
        "selection_id": "select-" + candidate["candidate_sha256"][:16],
        "candidate_sha256": candidate["candidate_sha256"],
        "verification_sha256": verification["verification_sha256"],
        "status": status,
        "question": question,
        "allowed_decisions": ["SELECT", "REJECT"] if status == "HUMAN_SELECTION_REQUIRED" else [],
        "target_reached": False,
        "contract_sha256": contract["contract_sha256"],
    }
    out["selection_sha256"] = canonical_sha(out)
    return out


def pending_independent_verification(contract: Dict[str, Any], candidate: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Record structural or executor-local evidence without upgrading it.

    This is the required state for a raw workflow that can replay a candidate's
    components but does not yet have a role-isolated CAS residual result.
    """
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    _require_nonempty_string(reason, "PENDING_VERIFICATION_REASON")
    out = {
        "candidate_sha256": candidate["candidate_sha256"],
        "verifier_id": None,
        "backend": None,
        "verdict": "UNKNOWN",
        "verified_scope": candidate["claimed_scope"],
        "residual_evidence": {"reason": reason},
        "independent": False,
        "status": "PENDING_INDEPENDENT_VERIFICATION",
        "contract_sha256": contract["contract_sha256"],
    }
    out["verification_sha256"] = canonical_sha(out)
    return out


def blocked_selection_gate(contract: Dict[str, Any], candidate: Dict[str, Any], pending_verification: Dict[str, Any]) -> Dict[str, Any]:
    """Represent the no-selection state without pretending UNKNOWN was verified."""
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    if pending_verification.get("status") != "PENDING_INDEPENDENT_VERIFICATION":
        raise ArchitectureError("PENDING_VERIFICATION_STATUS_MALFORMED")
    if pending_verification.get("candidate_sha256") != candidate["candidate_sha256"]:
        raise ArchitectureError("PENDING_VERIFICATION_CANDIDATE_MISMATCH")
    if pending_verification.get("contract_sha256") != contract["contract_sha256"]:
        raise ArchitectureError("PENDING_VERIFICATION_CONTRACT_MISMATCH")
    if pending_verification.get("verified_scope") != candidate["claimed_scope"]:
        raise ArchitectureError("PENDING_VERIFICATION_SCOPE_MISMATCH")
    if pending_verification.get("verification_sha256") != canonical_sha(
            {key: value for key, value in pending_verification.items() if key != "verification_sha256"}):
        raise ArchitectureError("PENDING_VERIFICATION_HASH_MISMATCH")
    out = {
        "selection_id": "select-" + candidate["candidate_sha256"][:16],
        "candidate_sha256": candidate["candidate_sha256"],
        "verification_sha256": pending_verification.get("verification_sha256"),
        "status": "BLOCKED_INDEPENDENT_VERIFICATION",
        "question": "Independent residual verification is required before human selection.",
        "allowed_decisions": [],
        "target_reached": False,
        "contract_sha256": contract["contract_sha256"],
    }
    out["selection_sha256"] = canonical_sha(out)
    return out


def build_pending_chain_node(contract: Dict[str, Any], candidate: Dict[str, Any], pending_verification: Dict[str, Any], parent_node_sha256: str = None) -> Dict[str, Any]:
    """Hash-link an unselected proposal while preserving its blocked state."""
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    gate = blocked_selection_gate(contract, candidate, pending_verification)
    node = {
        "node_kind": "SCIENTIFIC_COMPACTIFICATION_STEP",
        "parent_node_sha256": parent_node_sha256,
        "contract_sha256": contract["contract_sha256"],
        "current_representation_id": contract["current_representation"]["representation_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "verification_sha256": pending_verification["verification_sha256"],
        "selection": gate,
        "status": "PENDING_INDEPENDENT_VERIFICATION",
    }
    node["node_sha256"] = canonical_sha(node)
    return node


def apply_human_selection(contract: Dict[str, Any], candidate: Dict[str, Any], verification: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    """Materialize C_(i+1) only from a human SELECT decision."""
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    gate = selection_gate(contract, candidate, verification)
    decision = _require_object(decision, "HUMAN_SELECTION")
    if gate["status"] != "HUMAN_SELECTION_REQUIRED":
        raise ArchitectureError("SELECTION_NOT_ELIGIBLE")
    if decision.get("selection_id") != gate["selection_id"]:
        raise ArchitectureError("SELECTION_GATE_MISMATCH")
    selected_by = _require_nonempty_string(decision.get("decided_by"), "SELECTION_DECIDED_BY")
    if decision.get("authority_role") != "human_scientist":
        raise ArchitectureError("SELECTION_HUMAN_AUTHORITY_REQUIRED")
    if selected_by in {candidate["proposer_id"], verification.get("verifier_id")}:
        raise ArchitectureError("SELECTION_ROLE_CONFLICT")
    _require_nonempty_string(decision.get("rationale"), "SELECTION_RATIONALE")
    action = decision.get("decision")
    if action not in {"SELECT", "REJECT"}:
        raise ArchitectureError("SELECTION_DECISION_MALFORMED")
    artifact = {
        "selection_id": gate["selection_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "verification_sha256": verification["verification_sha256"],
        "decision": action,
        "decided_by": selected_by,
        "authority_role": decision["authority_role"],
        "rationale": decision["rationale"],
        "target_reached": bool(decision.get("target_reached", False)),
    }
    provided_sha = _require_sha(decision.get("decision_artifact_sha256"), "SELECTION_DECISION_SHA")
    if provided_sha != canonical_sha(artifact):
        raise ArchitectureError("SELECTION_DECISION_HASH_MISMATCH")
    if action == "REJECT":
        out = {
            "status": "HUMAN_REJECTED",
            "selection_gate": gate,
            "decision_artifact": artifact,
            "decision_artifact_sha256": provided_sha,
            "next_representation": None,
            "target_reached": False,
        }
        out["selection_result_sha256"] = canonical_sha(out)
        return out
    next_representation = dict(candidate["candidate_representation"])
    next_representation.update({
        "representation_id": "C-next-" + candidate["candidate_sha256"][:16],
        "parent_representation_id": contract["current_representation"]["representation_id"],
        "status": "SELECTED",
    })
    out = {
        "status": "HUMAN_SELECTED",
        "selection_gate": gate,
        "decision_artifact": artifact,
        "decision_artifact_sha256": provided_sha,
        "next_representation": next_representation,
        "target_reached": artifact["target_reached"],
    }
    out["selection_result_sha256"] = canonical_sha(out)
    return out


def _validated_selection_for_chain(gate: Dict[str, Any], selection: Dict[str, Any]) -> Dict[str, Any]:
    """Accept only the generated gate or a hash-bound human decision result."""
    if selection is None:
        return gate
    selection = _require_object(selection, "CHAIN_SELECTION")
    if selection == gate:
        return gate
    if selection.get("status") not in {"HUMAN_SELECTED", "HUMAN_REJECTED"}:
        raise ArchitectureError("CHAIN_SELECTION_STATUS_MALFORMED")
    if selection.get("selection_gate") != gate:
        raise ArchitectureError("CHAIN_SELECTION_GATE_MISMATCH")
    if selection.get("selection_result_sha256") != canonical_sha(
            {key: value for key, value in selection.items() if key != "selection_result_sha256"}):
        raise ArchitectureError("CHAIN_SELECTION_HASH_MISMATCH")
    artifact = _require_object(selection.get("decision_artifact"), "CHAIN_DECISION_ARTIFACT")
    if selection.get("decision_artifact_sha256") != canonical_sha(artifact):
        raise ArchitectureError("CHAIN_DECISION_HASH_MISMATCH")
    if artifact.get("selection_id") != gate["selection_id"]:
        raise ArchitectureError("CHAIN_DECISION_GATE_MISMATCH")
    if artifact.get("authority_role") != "human_scientist":
        raise ArchitectureError("CHAIN_DECISION_HUMAN_AUTHORITY_REQUIRED")
    return selection


def build_chain_node(contract: Dict[str, Any], candidate: Dict[str, Any], verification: Dict[str, Any], selection: Dict[str, Any] = None, parent_node_sha256: str = None) -> Dict[str, Any]:
    """Produce a proof-carrying edge for one compactification iteration."""
    contract = build_contract(contract)
    candidate = build_candidate(contract, candidate)
    gate = selection_gate(contract, candidate, verification)
    selection = _validated_selection_for_chain(gate, selection)
    node = {
        "node_kind": "SCIENTIFIC_COMPACTIFICATION_STEP",
        "parent_node_sha256": parent_node_sha256,
        "contract_sha256": contract["contract_sha256"],
        "current_representation_id": contract["current_representation"]["representation_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "verification_sha256": verification["verification_sha256"],
        "selection": selection,
        "status": selection.get("status", "UNSELECTED"),
    }
    node["node_sha256"] = canonical_sha(node)
    return node


def bridge_c0_node(contract: Dict[str, Any], c0_node: Dict[str, Any], proposer_id: str) -> Dict[str, Any]:
    """Convert a C0 residual node into the target architecture's artifacts.

    The bridge does not trust a supplied C0 verdict or residual hash. It reruns
    C0's strict SymPy verifier on the supplied claim and binds the fresh record
    into this architecture before a selection gate can open.
    """
    contract = build_contract(contract)
    c0_node = _require_object(c0_node, "C0_NODE")
    claim = _require_object(c0_node.get("claim"), "C0_CLAIM")
    current = contract["current_representation"]
    if current.get("format") != "sympy_identity_claim":
        raise ArchitectureError("C0_PARENT_REPRESENTATION_FORMAT_INVALID")
    if c0_node.get("parent_claim_id") != current.get("source_claim_id"):
        raise ArchitectureError("C0_PARENT_CLAIM_MISMATCH")
    claim_sha = canonical_sha(claim)
    candidate = {
        "candidate_id": c0_node.get("claim_id") or "c0-" + claim_sha[:12],
        "parent_representation_id": contract["current_representation"]["representation_id"],
        "candidate_representation": {
            "representation_id": "candidate-" + claim_sha[:16],
            "format": "sympy_identity_claim",
            "content_sha256": claim_sha,
            "status": "CANDIDATE",
            "verifiable_payload": claim,
            "source_claim_id": c0_node.get("claim_id") or "c0-" + claim_sha[:12],
        },
        "proposer_id": proposer_id,
        "carrier_definitions": [],
        "identities_used": [],
        "claimed_scope": claim.get("scope", "declared_scope"),
    }
    candidate = build_candidate(contract, candidate)
    parent_claim = current["verifiable_payload"]
    parent_recheck, stable_parent, residual, recheck, stable_recheck = _stable_c0_edge_recheck(
        parent_claim, claim
    )
    verdict = recheck["verdict"]
    if verdict == "ZERO":
        residual_evidence = {
            "residual": "0",
            "residual_sha256": canonical_sha({
                "parent_claim": parent_claim,
                "candidate_claim": claim,
                "parent_recheck": stable_parent,
                "edge_residual": residual,
                "residual_recheck": stable_recheck,
            }),
            "recheck_record": recheck,
        }
        status = "VERIFIED_BY_RECHECK"
    elif verdict == "NONZERO":
        residual_evidence = {"counterexample_or_residual": json.dumps(recheck, sort_keys=True)}
        status = "REJECTED_BY_RECHECK"
    else:
        residual_evidence = {"reason": "C0 recheck returned UNKNOWN", "recheck_record": recheck}
        status = "UNKNOWN_BY_RECHECK"
    verification = {
        "candidate_sha256": candidate["candidate_sha256"],
        "verifier_id": "c0_python_sympy_independent_verifier",
        "backend": "sympy",
        "verdict": verdict,
        "verified_scope": claim.get("scope", "declared_scope"),
        "residual_evidence": residual_evidence,
        "independent": True,
        "status": status,
        "contract_sha256": contract["contract_sha256"],
        "recheck_kind": "c0_sympy_identity",
        "recheck_claim": claim,
        "parent_claim_id": current["source_claim_id"],
        "recheck_record_sha256": canonical_sha({"parent": stable_parent, "residual": stable_recheck}),
    }
    verification["verification_sha256"] = canonical_sha(verification)
    return {
        "contract": contract,
        "candidate": candidate,
        "verification": verification,
        "selection_gate": selection_gate(contract, candidate, verification),
        "chain_node": build_chain_node(contract, candidate, verification),
    }


def validate_request_shape(request: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce the action-specific ORCH request contract without silent fields."""
    request = _require_object(request, "REQUEST")
    allowed = {
        "operation", "contract_version", "action", "contract", "candidate",
        "verification", "selection", "c0_node", "proposer_id",
    }
    if set(request) - allowed:
        raise ArchitectureError("REQUEST_UNDECLARED_FIELD")
    if request.get("operation") != "scientific_compactification":
        raise ArchitectureError("OPERATION_UNSUPPORTED")
    if request.get("contract_version") != SCHEMA_VERSION:
        raise ArchitectureError("CONTRACT_VERSION_UNSUPPORTED")
    action = request.get("action")
    required = {
        "bootstrap": {"contract"},
        "adjudicate": {"contract", "candidate", "verification"},
        "select": {"contract", "candidate", "verification", "selection"},
        "bridge_c0": {"contract", "c0_node", "proposer_id"},
    }
    if action not in required:
        raise ArchitectureError("ACTION_UNSUPPORTED")
    if any(key not in request for key in required[action]):
        raise ArchitectureError("REQUEST_ACTION_INPUT_MISSING")
    return request


def handle(request: Dict[str, Any]):
    """Adapter entry point for contract, verdict, selection, and C0 bridge operations."""
    request = validate_request_shape(request)
    action = request.get("action")
    contract = request.get("contract")
    if action == "bootstrap":
        built = build_contract(contract)
        return {"contract": built, "status": "CONTRACT_FROZEN"}, 0
    if action == "adjudicate":
        candidate = build_candidate(contract, request.get("candidate"))
        verification = record_verifier_attestation(contract, candidate, request.get("verification"))
        return {
            "contract": build_contract(contract),
            "candidate": candidate,
            "verification": verification,
            "selection_gate": selection_gate(contract, candidate, verification),
            "chain_node": build_chain_node(contract, candidate, verification),
        }, 0
    if action == "select":
        candidate = build_candidate(contract, request.get("candidate"))
        selection = apply_human_selection(contract, candidate, request.get("verification"), request.get("selection"))
        return {
            "selection": selection,
            "chain_node": build_chain_node(contract, candidate, request.get("verification"), selection),
        }, 0
    if action == "bridge_c0":
        return bridge_c0_node(contract, request.get("c0_node"), request.get("proposer_id")), 0
    raise ArchitectureError("ACTION_UNSUPPORTED")
