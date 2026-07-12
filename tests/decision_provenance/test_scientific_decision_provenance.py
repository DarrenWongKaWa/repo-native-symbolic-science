#!/usr/bin/env python3
"""
Synthetic fixture tests for the Scientific Decision Provenance Layer.

Tests:
  1. valid promotion (CANDIDATE -> SOURCE_BACKED -> PENDING_INDEPENDENT_VERIFICATION -> ACTIVE_VERIFIED)
  2. invalid transition (CANDIDATE -> ACTIVE_VERIFIED skipped — must fail)
  3. rollback after downstream invalidation
  4. stale JSON rejected in favor of fresh replay
  5. model projection cannot promote a general claim
  6. local identity passes while boundary remains pending
  7. full-rank unique solve (linear system evidence)
  8. inconsistent augmented system (rank vs augmented_rank mismatch)
  9. numerical baseline retained after downstream analytical invalidation
 10. executor self-promotion to ACTIVE_VERIFIED blocked
 11. forbidden standalone evidence rejection
 12. authority ordering comparison
 13. recoverable dormant state transitions (BLOCKED/STALE_NONAUTHORITATIVE -> CANDIDATE)

All tests use synthetic fixtures. Uses no external dependencies beyond stdlib.
"""
import json
import sys
import os
import copy

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from claim_decision_engine import (
    transition,
    is_valid_transition,
    is_terminal,
    is_recoverable_dormant,
    build_rollback_recommendation,
    should_reject_stale_artifact,
    reject_invalid_evidence,
    check_projection_gate,
    check_local_vs_boundary_gate,
    is_projection_promotable_to_general,
    validate_linear_system_evidence,
    compare_authority,
    authority_tier_for_artifact_type,
    retain_numerical_baseline,
)


PASS = 0
FAIL = 1


def make_candidate_claim(claim_id="CLAIM_SYNTH_001", scope="LOCAL_EXACT_IDENTITY"):
    return {
        "claim_id": claim_id,
        "lifecycle_version": "1.0.0",
        "current_state": "CANDIDATE",
        "state_history": [],
        "provenance_artifacts": {
            "artifact_runs": [
                {
                    "artifact_run_id": "AR_001",
                    "artifact_type": "executable_replay",
                    "authority_tier": 0,
                    "artifact_sha": "a" * 64,
                    "timestamp": "2025-01-01T00:00:00Z",
                    "generated_by_role": "executor",
                    "linked_execution_truth_id": "ET_001",
                }
            ]
        },
        "parent_claim_ids": [],
        "authority_level": "FRESH_EXECUTABLE_REPLAY",
        "scope_classification": scope,
        "projection_context": {
            "is_projection": False,
            "injectivity_established": True,
            "cannot_promote_to": [],
        },
        "stale_detection": {
            "staleness_check": {
                "fresher_executable_available": False,
                "parent_claim_invalidated": False,
                "replay_diverged_from_frozen": False,
            }
        },
    }


def make_checkpoints():
    return [
        {
            "checkpoint_id": "CP_001",
            "checkpoint_name": "Initial trusted",
            "timestamp": "2025-01-01T00:00:00Z",
            "trusted": True,
            "frozen_artifact_shas": {},
            "claim_snapshots": [],
            "parent_checkpoint_id": None,
            "invalidated_descendants": [],
        },
        {
            "checkpoint_id": "CP_002",
            "checkpoint_name": "Second trusted",
            "timestamp": "2025-01-02T00:00:00Z",
            "trusted": True,
            "frozen_artifact_shas": {},
            "claim_snapshots": [],
            "parent_checkpoint_id": "CP_001",
            "invalidated_descendants": [],
        },
        {
            "checkpoint_id": "CP_003_INVALID",
            "checkpoint_name": "Invalidated checkpoint",
            "timestamp": "2025-01-03T00:00:00Z",
            "trusted": False,
            "frozen_artifact_shas": {},
            "claim_snapshots": [],
            "parent_checkpoint_id": "CP_002",
            "invalidated_descendants": ["CP_004", "CP_005"],
        },
        {
            "checkpoint_id": "CP_004",
            "checkpoint_name": "Descendant of invalidated",
            "timestamp": "2025-01-04T00:00:00Z",
            "trusted": False,
            "frozen_artifact_shas": {},
            "claim_snapshots": [],
            "parent_checkpoint_id": "CP_003_INVALID",
            "invalidated_descendants": [],
        },
        {
            "checkpoint_id": "CP_005",
            "checkpoint_name": "Another descendant of invalidated",
            "timestamp": "2025-01-05T00:00:00Z",
            "trusted": False,
            "frozen_artifact_shas": {},
            "claim_snapshots": [],
            "parent_checkpoint_id": "CP_003_INVALID",
            "invalidated_descendants": [],
        },
    ]


# ---------------------------------------------------------------------------
# Test 1: Valid promotion chain
# ---------------------------------------------------------------------------
def test_valid_promotion():
    claim = make_candidate_claim("CLAIM_PROMO_001")
    results = []

    # CANDIDATE -> SOURCE_BACKED
    claim, errs = transition(claim, "SOURCE_BACKED", "DEC_001", "executor", ["AR_001"], "source linked")
    results.append(("CANDIDATE->SOURCE_BACKED", len(errs) == 0, errs))

    # SOURCE_BACKED -> PENDING_INDEPENDENT_VERIFICATION
    claim, errs = transition(claim, "PENDING_INDEPENDENT_VERIFICATION", "DEC_002", "executor", ["AR_001"], "submitted for verification")
    results.append(("SOURCE_BACKED->PENDING_INDEPENDENT_VERIFICATION", len(errs) == 0, errs))

    # PENDING_INDEPENDENT_VERIFICATION -> ACTIVE_VERIFIED (by independent verifier)
    claim, errs = transition(claim, "ACTIVE_VERIFIED", "DEC_003", "independent_verifier", ["AR_001"], "independently verified")
    results.append(("PENDING_INDEPENDENT_VERIFICATION->ACTIVE_VERIFIED", len(errs) == 0, errs))

    # Verify final state
    results.append(("final_state==ACTIVE_VERIFIED", claim["current_state"] == "ACTIVE_VERIFIED", []))

    return results


# ---------------------------------------------------------------------------
# Test 2: Invalid transition (skip states)
# ---------------------------------------------------------------------------
def test_invalid_transition():
    results = []

    # CANDIDATE -> ACTIVE_VERIFIED (skip SOURCE_BACKED, PENDING_INDEPENDENT_VERIFICATION)
    claim = make_candidate_claim("CLAIM_SKIP_001")
    claim, errs = transition(claim, "ACTIVE_VERIFIED", "DEC_BAD", "independent_verifier", ["AR_001"], "skip attempt")
    results.append(("CANDIDATE->ACTIVE_VERIFIED_blocked", len(errs) > 0, errs))

    # PENDING_INDEPENDENT_VERIFICATION -> SUPERSEDED (direct) - should be allowed
    claim = make_candidate_claim("CLAIM_SUPER_001")
    claim["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"
    claim["state_history"] = [{
        "from_state": "CANDIDATE", "to_state": "SOURCE_BACKED",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_X",
        "authorized_by_role": "executor", "evidence_artifact_ids": [], "reason": ""
    }, {
        "from_state": "SOURCE_BACKED", "to_state": "PENDING_INDEPENDENT_VERIFICATION",
        "timestamp": "2025-01-01T01:00:00Z", "decision_event_id": "DEC_Y",
        "authorized_by_role": "executor", "evidence_artifact_ids": [], "reason": ""
    }]
    claim, errs = transition(claim, "SUPERSEDED", "DEC_SUPER", "integration_executor", ["AR_NEW_001"],
                             "superseded by new claim")
    results.append(("PENDING_INDEPENDENT_VERIFICATION->SUPERSEDED_allowed", len(errs) == 0, errs))

    # From terminal state -> nothing allowed
    sup_claim = {"claim_id": "TERM", "current_state": "SUPERSEDED", "state_history": [],
                 "provenance_artifacts": {"artifact_runs": []}, "parent_claim_ids": [],
                 "authority_level": "FRESH_EXECUTABLE_REPLAY", "scope_classification": "LOCAL_EXACT_IDENTITY",
                 "projection_context": {}, "stale_detection": {"staleness_check": {}},
                 "lifecycle_version": "1.0.0"}
    sup_claim, errs = transition(sup_claim, "ACTIVE_VERIFIED", "DEC_BAD2", "human_scientist", [], "terminal reactivation")
    results.append(("SUPERSEDED->ACTIVE_VERIFIED_blocked", len(errs) > 0, errs))

    return results


# ---------------------------------------------------------------------------
# Test 3: Rollback after downstream invalidation
# ---------------------------------------------------------------------------
def test_rollback_after_invalidation():
    checkpoints = make_checkpoints()
    rec = build_rollback_recommendation(checkpoints, "CP_003_INVALID")
    results = []
    results.append(("rollback_not_none", rec is not None, []))
    if rec:
        results.append(("target_is_CP_002", rec["target_checkpoint_id"] == "CP_002", []))
        results.append(("includes_CP_003", "CP_003_INVALID" in rec["invalidated_claim_ids"], []))
        results.append(("includes_CP_004", "CP_004" in rec["invalidated_claim_ids"], []))
        results.append(("includes_CP_005", "CP_005" in rec["invalidated_claim_ids"], []))
        results.append(("has_rollback_id", bool(rec.get("rollback_id")), []))
    return results


# ---------------------------------------------------------------------------
# Test 4: Stale JSON rejected in favor of fresh replay
# ---------------------------------------------------------------------------
def test_stale_rejection():
    results = []

    stale_claim = make_candidate_claim("CLAIM_STALE_001")
    stale_claim["current_state"] = "ACTIVE_VERIFIED"
    stale_claim["provenance_artifacts"]["artifact_runs"] = [
        {
            "artifact_run_id": "AR_OLD",
            "artifact_type": "human_readable_report",
            "authority_tier": 3,
            "artifact_sha": "b" * 64,
            "timestamp": "2024-01-01T00:00:00Z",
            "generated_by_role": "report_generator",
        }
    ]
    stale_claim["authority_level"] = "HUMAN_READABLE_REPORT"
    stale_claim["stale_detection"]["staleness_check"]["fresher_executable_available"] = True

    should_reject, reason = should_reject_stale_artifact(stale_claim, fresh_replay_available=True)
    results.append(("stale_claim_rejected", should_reject, [reason]))

    fresh_claim = make_candidate_claim("CLAIM_FRESH_001")
    fresh_claim["current_state"] = "ACTIVE_VERIFIED"
    should_reject, reason = should_reject_stale_artifact(fresh_claim, fresh_replay_available=False)
    results.append(("fresh_claim_not_rejected_when_no_replay", not should_reject, [reason]))

    return results


# ---------------------------------------------------------------------------
# Test 5: Model projection cannot promote a general claim
# ---------------------------------------------------------------------------
def test_projection_cannot_promote_general():
    results = []

    projection = {
        "projection_id": "PROJ_001",
        "source_claim_id": "CLAIM_A",
        "target_claim_id": "CLAIM_B",
        "projection_method": "model_specific_parity_reduction",
        "injectivity_established": False,
        "authorized_scope": "MODEL_SPECIFIC_EQUIVALENCE",
        "local_exact_identity_gate": {"passed": True, "method": "exact_substitution", "evidence_artifact_id": "EV_001"},
        "boundary_applicability_gate": {"passed": True, "method": "boundary_check", "evidence_artifact_id": "EV_002"},
        "cannot_promote_to_general": True,
        "reason": "projection not injective",
    }

    errors = check_projection_gate(projection)
    results.append(("MODEL_SPECIFIC_EQUIVALENCE_authorized_for_projection", len(errors) == 0, errors))

    promotable, reason = is_projection_promotable_to_general(projection)
    results.append(("projection_NOT_promotable_to_general", not promotable, [reason]))

    gen_projection = copy.deepcopy(projection)
    gen_projection["authorized_scope"] = "GENERAL_SYMBOLIC_IDENTITY"
    gen_projection["injectivity_established"] = False
    gen_projection["cannot_promote_to_general"] = False
    errors2 = check_projection_gate(gen_projection)
    results.append(("GENERAL_SYMBOLIC_IDENTITY_rejected_without_injectivity", len(errors2) > 0, errors2))

    valid_gen = copy.deepcopy(gen_projection)
    valid_gen["injectivity_established"] = True
    valid_gen["local_exact_identity_gate"]["passed"] = True
    valid_gen["boundary_applicability_gate"]["passed"] = True
    errors3 = check_projection_gate(valid_gen)
    results.append(("GENERAL_SYMBOLIC_IDENTITY_accepted_with_injectivity", len(errors3) == 0, errors3))
    promotable2, _ = is_projection_promotable_to_general(valid_gen)
    results.append(("projection_promotable_to_general_with_gates", promotable2, []))

    return results


# ---------------------------------------------------------------------------
# Test 6: Local identity passes while boundary remains pending
# ---------------------------------------------------------------------------
def test_local_vs_boundary():
    results = []

    proj = {
        "projection_id": "PROJ_002",
        "source_claim_id": "CLAIM_C",
        "target_claim_id": "CLAIM_D",
        "projection_method": "local_identity",
        "injectivity_established": True,
        "authorized_scope": "MODEL_SPECIFIC_EQUIVALENCE",
        "local_exact_identity_gate": {"passed": True, "method": "exact_local", "evidence_artifact_id": "EV_003"},
        "boundary_applicability_gate": {"passed": False, "method": "pending", "evidence_artifact_id": ""},
        "cannot_promote_to_general": True,
        "reason": "boundary not established",
    }

    gates = check_local_vs_boundary_gate(proj)
    results.append(("local_passed", gates["local_exact_identity"], []))
    results.append(("boundary_NOT_passed", not gates["boundary_applicability"], []))
    results.append(("both_NOT_passed", not gates["both_passed"], []))
    results.append(("local_only", gates["local_only"], []))

    errors = check_projection_gate(proj)
    results.append(("MODEL_SPECIFIC_valid_with_local_only", len(errors) == 0, errors))

    promotable, _ = is_projection_promotable_to_general(proj)
    results.append(("not_promotable_with_boundary_pending", not promotable, []))

    return results


# ---------------------------------------------------------------------------
# Test 7: Full-rank unique solve
# ---------------------------------------------------------------------------
def test_full_rank_unique_solve():
    evidence = {
        "evidence_id": "LS_001",
        "claim_id": "CLAIM_FULLRANK",
        "system_description": "3x3 full-rank system",
        "matrix_shape": [3, 3],
        "rank": 3,
        "augmented_rank": 3,
        "nullity": 0,
        "left_nullspace_dimension": 0,
        "consistent": True,
        "unique_solution": True,
        "basis_ordering": [
            {"variable_name": "x1", "index": 0},
            {"variable_name": "x2", "index": 1},
            {"variable_name": "x3", "index": 2},
        ],
        "solution": {
            "method": "exact_rref",
            "vector": [1.0, 2.0, 3.0],
            "nullspace_basis_vectors": [],
        },
        "equation_residuals": [
            {"equation_index": 0, "residual": 0.0, "tol": 1e-12, "below_tolerance": True},
            {"equation_index": 1, "residual": 0.0, "tol": 1e-12, "below_tolerance": True},
            {"equation_index": 2, "residual": 0.0, "tol": 1e-12, "below_tolerance": True},
        ],
        "generator_engine": "sympy",
        "verifier_engine": "python_numeric",
        "generated_at": "2025-01-01T00:00:00Z",
    }
    result = validate_linear_system_evidence(evidence)
    results = [
        ("full_rank_valid", result["valid"], result["errors"]),
        ("no_warnings", len(result["warnings"]) == 0, []),
    ]
    return results


# ---------------------------------------------------------------------------
# Test 8: Inconsistent augmented system
# ---------------------------------------------------------------------------
def test_inconsistent_augmented():
    evidence = {
        "evidence_id": "LS_002",
        "claim_id": "CLAIM_INCONS",
        "system_description": "3x3 inconsistent: rank=2, aug_rank=3",
        "matrix_shape": [3, 3],
        "rank": 2,
        "augmented_rank": 3,
        "nullity": 1,
        "left_nullspace_dimension": 1,
        "consistent": False,
        "unique_solution": False,
        "basis_ordering": [
            {"variable_name": "x1", "index": 0},
            {"variable_name": "x2", "index": 1},
            {"variable_name": "x3", "index": 2},
        ],
        "equation_residuals": [
            {"equation_index": 0, "residual": 1e-15, "tol": 1e-12, "below_tolerance": True},
            {"equation_index": 1, "residual": 1e-15, "tol": 1e-12, "below_tolerance": True},
            {"equation_index": 2, "residual": 5.0, "tol": 1e-12, "below_tolerance": False},
        ],
        "generator_engine": "sympy",
        "verifier_engine": "python_numeric",
        "generated_at": "2025-01-01T00:00:00Z",
    }
    result = validate_linear_system_evidence(evidence)
    results = [
        ("inconsistent_system_valid_schema", result["valid"], result["errors"]),
        ("consistency_check_rank_neq_aug_rank", evidence["rank"] != evidence["augmented_rank"], []),
        ("nullity_correct", evidence["nullity"] == 1, []),
        ("left_nullspace_correct", evidence["left_nullspace_dimension"] == 1, []),
    ]
    return results


# ---------------------------------------------------------------------------
# Test 9: Numerical baseline retained after downstream analytical invalidation
# ---------------------------------------------------------------------------
def test_numerical_baseline_retention():
    evidence = {
        "evidence_id": "LS_003",
        "claim_id": "CLAIM_NUM_BASELINE",
        "system_description": "System with numerical baseline",
        "matrix_shape": [2, 2],
        "rank": 2,
        "augmented_rank": 2,
        "nullity": 0,
        "left_nullspace_dimension": 0,
        "consistent": True,
        "unique_solution": True,
        "basis_ordering": [
            {"variable_name": "a", "index": 0},
            {"variable_name": "b", "index": 1},
        ],
        "solution": {"method": "exact_rref", "vector": [0.5, 1.5], "nullspace_basis_vectors": []},
        "equation_residuals": [
            {"equation_index": 0, "residual": 0.0, "tol": 1e-12, "below_tolerance": True},
            {"equation_index": 1, "residual": 0.0, "tol": 1e-12, "below_tolerance": True},
        ],
        "numerical_baseline": {
            "baseline_id": "BASELINE_LS_003",
            "rank_numerical": 2,
            "solution_numerical": [0.5, 1.5],
            "residual_norm": 1e-12,
            "retained": False,
        },
        "generator_engine": "python_numeric",
        "verifier_engine": "sympy",
        "generated_at": "2025-01-01T00:00:00Z",
    }

    invalidation = {"reason": "analytical_identity_disproved_by_counterexample"}
    retained = retain_numerical_baseline(evidence, invalidation)
    results = [
        ("numerical_baseline_retained", retained["numerical_baseline"]["retained"] == True, []),
        ("baseline_id_preserved", retained["numerical_baseline"]["baseline_id"] == "BASELINE_LS_003", []),
        ("rank_preserved", retained["numerical_baseline"]["rank_numerical"] == 2, []),
        ("solution_preserved", retained["numerical_baseline"]["solution_numerical"] == [0.5, 1.5], []),
        ("residual_norm_preserved", retained["numerical_baseline"]["residual_norm"] == 1e-12, []),
    ]
    return results


# ---------------------------------------------------------------------------
# Test 10: Executor self-promotion to ACTIVE_VERIFIED blocked
# ---------------------------------------------------------------------------
def test_executor_self_promotion_blocked():
    results = []

    claim = make_candidate_claim("CLAIM_SELF_001")
    claim, errs = transition(claim, "SOURCE_BACKED", "DEC_A", "executor", ["AR_001"], "")
    claim, errs = transition(claim, "PENDING_INDEPENDENT_VERIFICATION", "DEC_B", "executor", ["AR_001"], "")
    claim, errs = transition(claim, "ACTIVE_VERIFIED", "DEC_C", "executor", ["AR_001"], "self-promotion")

    results.append(("executor_blocked_from_ACTIVE_VERIFIED", len(errs) > 0, errs))
    results.append(("state_still_PENDING", claim["current_state"] == "PENDING_INDEPENDENT_VERIFICATION", []))

    return results


# ---------------------------------------------------------------------------
# Test 11: Forbidden standalone evidence rejection (PASS, all_zero without executable)
# ---------------------------------------------------------------------------
def test_forbidden_standalone_evidence():
    results = []

    forbidden_claim = make_candidate_claim("CLAIM_FORBID_EV")
    forbidden_claim["current_state"] = "SOURCE_BACKED"
    forbidden_claim["provenance_artifacts"]["artifact_runs"] = [
        {
            "artifact_run_id": "AR_PASS",
            "artifact_type": "historical_pass_field",
            "authority_tier": 4,
            "artifact_sha": "c" * 64,
            "timestamp": "2025-01-01T00:00:00Z",
            "generated_by_role": "report_generator",
        }
    ]
    forbidden_claim["authority_level"] = "HISTORICAL_PASS_FIELD"

    errs = reject_invalid_evidence(forbidden_claim)
    results.append(("historical_pass_field_rejected_without_executable", len(errs) > 0, errs))

    valid_claim = make_candidate_claim("CLAIM_VALID_EV")
    errs = reject_invalid_evidence(valid_claim)
    results.append(("executable_replay_accepted", len(errs) == 0, errs))

    return results


# ---------------------------------------------------------------------------
# Test 12: Authority ordering comparison
# ---------------------------------------------------------------------------
def test_authority_ordering():
    results = []

    fresh = {"artifact_type": "executable_replay", "authority_tier": 0}
    frozen = {"artifact_type": "frozen_machine_readable_operand", "authority_tier": 1}
    summary = {"artifact_type": "structured_result_summary", "authority_tier": 2}
    report = {"artifact_type": "human_readable_report", "authority_tier": 3}
    historical = {"artifact_type": "historical_pass_field", "authority_tier": 4}

    results.append(("fresh_outranks_frozen", compare_authority(fresh, frozen) < 0, []))
    results.append(("frozen_outranks_summary", compare_authority(frozen, summary) < 0, []))
    results.append(("summary_outranks_report", compare_authority(summary, report) < 0, []))
    results.append(("report_outranks_historical", compare_authority(report, historical) < 0, []))
    results.append(("fresh_same_as_fresh", compare_authority(fresh, fresh) == 0, []))

    results.append(("tier_executable==0", authority_tier_for_artifact_type("executable_replay") == 0, []))
    results.append(("tier_historical==4", authority_tier_for_artifact_type("historical_pass_field") == 4, []))

    return results


# ---------------------------------------------------------------------------
# Test 13: Recoverable dormant state transitions
# ---------------------------------------------------------------------------
def test_recoverable_dormant_transitions():
    results = []

    # --- 13a: BLOCKED -> CANDIDATE with recovery evidence: PASS ---
    blocked_claim = make_candidate_claim("CLAIM_BLOCKED_RECOVER")
    blocked_claim["current_state"] = "BLOCKED"
    blocked_claim["state_history"] = [{
        "from_state": "CANDIDATE", "to_state": "BLOCKED",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_BLK",
        "authorized_by_role": "human_scientist", "evidence_artifact_ids": ["AR_GUARD"],
        "reason": "blocked by explicit guard",
    }]
    blocked_claim["authority_level"] = "FRESH_EXECUTABLE_REPLAY"

    claim, errs = transition(
        blocked_claim, "CANDIDATE", "DEC_RECOVER_001", "human_scientist",
        ["AR_RECOVER_FRESH_EXECUTABLE"], "guard resolved with new executable verification"
    )
    results.append(("BLOCKED->CANDIDATE_with_recovery_evidence:PASS", len(errs) == 0, errs))
    if len(errs) == 0:
        results.append(("recovered_to_CANDIDATE", claim["current_state"] == "CANDIDATE", []))

    # --- 13b: BLOCKED -> CANDIDATE without recovery evidence: FAIL ---
    blocked_no_ev = make_candidate_claim("CLAIM_BLOCKED_NOEV")
    blocked_no_ev["current_state"] = "BLOCKED"
    blocked_no_ev["state_history"] = [{
        "from_state": "CANDIDATE", "to_state": "BLOCKED",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_BLK2",
        "authorized_by_role": "human_scientist", "evidence_artifact_ids": ["AR_GUARD"],
        "reason": "blocked by guard",
    }]
    blocked_no_ev["authority_level"] = "FRESH_EXECUTABLE_REPLAY"

    claim, errs = transition(
        blocked_no_ev, "CANDIDATE", "DEC_RECOVER_002", "human_scientist",
        [], ""  # no evidence, no reason
    )
    results.append(("BLOCKED->CANDIDATE_without_recovery_evidence:FAIL", len(errs) > 0, errs))
    results.append(("state_remains_BLOCKED", claim["current_state"] == "BLOCKED", []))

    # --- 13c: STALE_NONAUTHORITATIVE -> CANDIDATE with fresh executable: PASS ---
    stale_claim = make_candidate_claim("CLAIM_STALE_RECOVER")
    stale_claim["current_state"] = "STALE_NONAUTHORITATIVE"
    stale_claim["state_history"] = [{
        "from_state": "ACTIVE_VERIFIED", "to_state": "STALE_NONAUTHORITATIVE",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_STALE",
        "authorized_by_role": "independent_verifier", "evidence_artifact_ids": ["AR_OLD"],
        "reason": "fresher executable available",
    }]
    stale_claim["authority_level"] = "FRESH_EXECUTABLE_REPLAY"
    stale_claim["provenance_artifacts"]["artifact_runs"] = [
        {
            "artifact_run_id": "AR_FRESH_RECOVER",
            "artifact_type": "executable_replay",
            "authority_tier": 0,
            "artifact_sha": "f" * 64,
            "timestamp": "2025-06-01T00:00:00Z",
            "generated_by_role": "executor",
            "linked_execution_truth_id": "ET_FRESH",
        }
    ]
    stale_claim["stale_detection"]["staleness_check"] = {
        "fresher_executable_available": False,  # resolved now
        "parent_claim_invalidated": False,
        "replay_diverged_from_frozen": False,
    }

    claim, errs = transition(
        stale_claim, "CANDIDATE", "DEC_RECOVER_003", "independent_verifier",
        ["AR_FRESH_RECOVER"], "re-lifecycling with fresh executable replay"
    )
    results.append(("STALE_NONAUTHORITATIVE->CANDIDATE_with_fresh_executable:PASS", len(errs) == 0, errs))
    if len(errs) == 0:
        results.append(("recovered_to_CANDIDATE", claim["current_state"] == "CANDIDATE", []))

    # --- 13d: STALE_NONAUTHORITATIVE -> CANDIDATE without evidence: FAIL ---
    stale_no_ev = make_candidate_claim("CLAIM_STALE_NOEV")
    stale_no_ev["current_state"] = "STALE_NONAUTHORITATIVE"
    stale_no_ev["state_history"] = [{
        "from_state": "ACTIVE_VERIFIED", "to_state": "STALE_NONAUTHORITATIVE",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_STALE2",
        "authorized_by_role": "independent_verifier", "evidence_artifact_ids": ["AR_OLD"],
        "reason": "stale",
    }]
    stale_no_ev["authority_level"] = "HISTORICAL_PASS_FIELD"

    claim, errs = transition(
        stale_no_ev, "CANDIDATE", "DEC_RECOVER_004", "executor",
        [], ""  # no evidence, no reason
    )
    results.append(("STALE_NONAUTHORITATIVE->CANDIDATE_without_evidence:FAIL", len(errs) > 0, errs))
    results.append(("state_remains_STALE", claim["current_state"] == "STALE_NONAUTHORITATIVE", []))

    # --- 13e: STALE_NONAUTHORITATIVE -> ACTIVE_VERIFIED directly: FAIL ---
    stale_direct = make_candidate_claim("CLAIM_STALE_DIRECT")
    stale_direct["current_state"] = "STALE_NONAUTHORITATIVE"
    stale_direct["state_history"] = [{
        "from_state": "ACTIVE_VERIFIED", "to_state": "STALE_NONAUTHORITATIVE",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_SD",
        "authorized_by_role": "independent_verifier", "evidence_artifact_ids": [],
        "reason": "stale",
    }]
    stale_direct["authority_level"] = "FRESH_EXECUTABLE_REPLAY"

    claim, errs = transition(
        stale_direct, "ACTIVE_VERIFIED", "DEC_BAD_DIRECT", "human_scientist",
        ["AR_SOME"], "attempted direct jump to ACTIVE_VERIFIED"
    )
    results.append(("STALE_NONAUTHORITATIVE->ACTIVE_VERIFIED_directly:FAIL", len(errs) > 0, errs))
    results.append(("state_remains_STALE_after_blocked_jump", claim["current_state"] == "STALE_NONAUTHORITATIVE", []))

    # --- 13f: Unrelated terminal transitions remain blocked ---
    # INVALIDATED -> CANDIDATE
    inv_claim = {"claim_id": "CLAIM_INV", "current_state": "INVALIDATED", "state_history": [],
                 "provenance_artifacts": {"artifact_runs": []}, "parent_claim_ids": [],
                 "authority_level": "FRESH_EXECUTABLE_REPLAY", "scope_classification": "LOCAL_EXACT_IDENTITY",
                 "projection_context": {}, "stale_detection": {"staleness_check": {}},
                 "lifecycle_version": "1.0.0"}
    inv_claim, errs = transition(inv_claim, "CANDIDATE", "DEC_BAD3", "human_scientist",
                                  ["AR_X"], "attempted recovery from INVALIDATED")
    results.append(("INVALIDATED->CANDIDATE:FAIL", len(errs) > 0, errs))

    # SUPERSEDED -> CANDIDATE
    sup_claim = {"claim_id": "CLAIM_SUP", "current_state": "SUPERSEDED", "state_history": [],
                 "provenance_artifacts": {"artifact_runs": []}, "parent_claim_ids": [],
                 "authority_level": "FRESH_EXECUTABLE_REPLAY", "scope_classification": "LOCAL_EXACT_IDENTITY",
                 "projection_context": {}, "stale_detection": {"staleness_check": {}},
                 "lifecycle_version": "1.0.0"}
    sup_claim, errs = transition(sup_claim, "CANDIDATE", "DEC_BAD4", "human_scientist",
                                  ["AR_X"], "attempted recovery from SUPERSEDED")
    results.append(("SUPERSEDED->CANDIDATE:FAIL", len(errs) > 0, errs))

    # BLOCKED -> ACTIVE_VERIFIED (skip CANDIDATE)
    blocked_skip = make_candidate_claim("CLAIM_BLOCKED_SKIP")
    blocked_skip["current_state"] = "BLOCKED"
    blocked_skip["state_history"] = [{"from_state": "CANDIDATE", "to_state": "BLOCKED",
        "timestamp": "2025-01-01T00:00:00Z", "decision_event_id": "DEC_BS",
        "authorized_by_role": "human_scientist", "evidence_artifact_ids": ["AR_G"],
        "reason": "blocked"}]
    blocked_skip["authority_level"] = "FRESH_EXECUTABLE_REPLAY"
    claim, errs = transition(blocked_skip, "ACTIVE_VERIFIED", "DEC_BAD5", "independent_verifier",
                              ["AR_Y"], "skip candidate")
    results.append(("BLOCKED->ACTIVE_VERIFIED_directly:FAIL", len(errs) > 0, errs))

    return results


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------
def run_all():
    test_suites = {
        "1_valid_promotion": test_valid_promotion,
        "2_invalid_transition": test_invalid_transition,
        "3_rollback_after_invalidation": test_rollback_after_invalidation,
        "4_stale_rejection": test_stale_rejection,
        "5_projection_cannot_promote_general": test_projection_cannot_promote_general,
        "6_local_vs_boundary": test_local_vs_boundary,
        "7_full_rank_unique_solve": test_full_rank_unique_solve,
        "8_inconsistent_augmented": test_inconsistent_augmented,
        "9_numerical_baseline_retention": test_numerical_baseline_retention,
        "10_executor_self_promotion_blocked": test_executor_self_promotion_blocked,
        "11_forbidden_standalone_evidence": test_forbidden_standalone_evidence,
        "12_authority_ordering": test_authority_ordering,
        "13_recoverable_dormant_transitions": test_recoverable_dormant_transitions,
    }

    passed = 0
    failed = 0
    total = 0

    for suite_name, suite_fn in test_suites.items():
        print(f"\n{'='*60}")
        print(f"Suite: {suite_name}")
        try:
            results = suite_fn()
            for name, ok, detail in results:
                total += 1
                status = "PASS" if ok else "FAIL"
                if ok:
                    passed += 1
                else:
                    failed += 1
                marker = "  " if ok else "XX"
                detail_str = ""
                if not ok and detail:
                    detail_str = f"  detail: {detail}"
                print(f"  [{status}] {marker} {name}{detail_str}")
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()
            total += 1
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed > 0:
        return FAIL
    return PASS


if __name__ == "__main__":
    sys.exit(run_all())
