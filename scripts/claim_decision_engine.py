#!/usr/bin/env python3
"""
Scientific Decision Provenance Engine.

Implements:
  - claim state machine (all transitions fail closed)
  - checkpoint rollback
  - stale-artifact detection and rejection
  - authority ordering
  - projection-vs-general scope gates
  - local-identity-vs-boundary separation
  - generator-verifier separation
  - rollback recommendation

All decision records are immutable; invalid transitions raise errors.
"""
import json
import sys
import os
import copy
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Claim states
# ---------------------------------------------------------------------------
VALID_STATES = frozenset([
    "CANDIDATE",
    "SOURCE_BACKED",
    "PENDING_INDEPENDENT_VERIFICATION",
    "ACTIVE_VERIFIED",
    "MODEL_SPECIFIC_ONLY",
    "SUPERSEDED",
    "INVALIDATED",
    "STALE_NONAUTHORITATIVE",
    "BLOCKED",
])

IRRECOVERABLE_TERMINAL_STATES = frozenset({
    "SUPERSEDED",
    "INVALIDATED",
})

RECOVERABLE_DORMANT_STATES = frozenset({
    "STALE_NONAUTHORITATIVE",
    "BLOCKED",
})

# ---------------------------------------------------------------------------
# Allowed transitions (fail-closed: anything not listed is forbidden)
# ---------------------------------------------------------------------------
_ALLOWED_TRANSITIONS = {
    "CANDIDATE": frozenset([
        "SOURCE_BACKED",
        "SUPERSEDED",
        "INVALIDATED",
        "BLOCKED",
    ]),
    "SOURCE_BACKED": frozenset([
        "PENDING_INDEPENDENT_VERIFICATION",
        "SUPERSEDED",
        "INVALIDATED",
        "STALE_NONAUTHORITATIVE",
        "BLOCKED",
    ]),
    "PENDING_INDEPENDENT_VERIFICATION": frozenset([
        "ACTIVE_VERIFIED",
        "MODEL_SPECIFIC_ONLY",
        "SUPERSEDED",
        "INVALIDATED",
        "BLOCKED",
        "STALE_NONAUTHORITATIVE",
    ]),
    "ACTIVE_VERIFIED": frozenset([
        "SUPERSEDED",
        "INVALIDATED",
        "STALE_NONAUTHORITATIVE",
    ]),
    "MODEL_SPECIFIC_ONLY": frozenset([
        "SUPERSEDED",
        "INVALIDATED",
        "STALE_NONAUTHORITATIVE",
    ]),
    "SUPERSEDED": frozenset([]),
    "INVALIDATED": frozenset([]),
    "STALE_NONAUTHORITATIVE": frozenset(["CANDIDATE"]),
    "BLOCKED": frozenset(["CANDIDATE"]),
}

# ---------------------------------------------------------------------------
# Authority ordering
# ---------------------------------------------------------------------------
_AUTHORITY_TIER = {
    "FRESH_EXECUTABLE_REPLAY": 0,
    "FROZEN_MACHINE_READABLE_OPERAND": 1,
    "STRUCTURED_RESULT_SUMMARY": 2,
    "HUMAN_READABLE_REPORT": 3,
    "HISTORICAL_PASS_FIELD": 4,
}

_ARTIFACT_AUTHORITY_TIER = {
    "executable_replay": 0,
    "frozen_machine_readable_operand": 1,
    "structured_result_summary": 2,
    "human_readable_report": 3,
    "historical_pass_field": 4,
}

# Artifact authority is ordered: lower tier = more authoritative
# fresh executable replay > frozen machine-readable operand > structured result summary
# > human-readable report > historical PASS field

# Forbidden evidence types that cannot stand alone
_FORBIDDEN_STANDALONE_EVIDENCE = frozenset([
    "historical_pass_field",
    "human_readable_report",
])

# ---------------------------------------------------------------------------
# Built-in transition guard checks (fail-closed helpers)
# ---------------------------------------------------------------------------
def _fail_closed(errors, reason):
    errors.append(reason)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
def is_valid_transition(from_state, to_state):
    return to_state in _ALLOWED_TRANSITIONS.get(from_state, frozenset())


def is_terminal(state):
    """True if the state is irrecoverably terminal (no outward transitions permitted)."""
    return state in IRRECOVERABLE_TERMINAL_STATES


def is_recoverable_dormant(state):
    """True if the state is dormant but recoverable via explicit recovery decision."""
    return state in RECOVERABLE_DORMANT_STATES


def all_valid_states():
    return sorted(VALID_STATES)


def allowed_transitions_for(state):
    return sorted(_ALLOWED_TRANSITIONS.get(state, frozenset()))


# ---------------------------------------------------------------------------
# Transition enforcement with guard checks
# ---------------------------------------------------------------------------
def transition(claim, to_state, decision_event_id, authorized_by_role,
               evidence_artifact_ids=None, reason=""):
    """
    Attempt a state transition on a claim.
    Returns (new_claim, errors).  errors is empty on success.
    All transitions fail closed.
    """
    claim = copy.deepcopy(claim)
    errors = []
    from_state = claim.get("current_state", "")

    if from_state not in VALID_STATES:
        _fail_closed(errors, f"unknown from_state: {from_state}")
        return claim, errors

    if to_state not in VALID_STATES:
        _fail_closed(errors, f"unknown to_state: {to_state}")
        return claim, errors

    if not is_valid_transition(from_state, to_state):
        _fail_closed(errors, f"forbidden transition: {from_state} -> {to_state}")
        return claim, errors

    if is_terminal(from_state):
        _fail_closed(errors, f"cannot transition from irrecoverable terminal state: {from_state}")
        return claim, errors

    # ---- recovery guards: BLOCKED/STALE_NONAUTHORITATIVE -> CANDIDATE ----
    if is_recoverable_dormant(from_state) and to_state == "CANDIDATE":
        evidence_ids = evidence_artifact_ids or []
        if not evidence_ids:
            _fail_closed(errors, f"recovery from {from_state} requires new evidence reference (evidence_artifact_ids)")
        if not reason or not reason.strip():
            _fail_closed(errors, f"recovery from {from_state} requires an explicit recovery reason")
        if claim.get("authority_level") in (None, ""):
            _fail_closed(errors, f"recovery from {from_state} requires prior authoritative status to be recorded")
        if from_state == "STALE_NONAUTHORITATIVE" and to_state == "CANDIDATE":
            stale = claim.get("stale_detection", {}).get("staleness_check", {})
            if stale.get("fresher_executable_available") and not _has_authoritative_evidence(claim):
                _fail_closed(errors,
                    "recovery from STALE_NONAUTHORITATIVE requires fresh executable evidence; "
                    "fresher_executable_available is true but claim lacks executable_replay or frozen_machine_readable_operand")

    # ---- promotion guards ----
    if to_state == "ACTIVE_VERIFIED":
        if authorized_by_role == "executor":
            _fail_closed(errors, "executor cannot self-promote to ACTIVE_VERIFIED; need independent_verifier")
        if not _has_authoritative_evidence(claim):
            _fail_closed(errors, "ACTIVE_VERIFIED requires executable_replay or frozen_machine_readable_operand evidence")
        if claim.get("projection_context", {}).get("is_projection"):
            if not claim["projection_context"].get("injectivity_established"):
                _fail_closed(errors, "projection claim without established injectivity cannot promote to ACTIVE_VERIFIED (general scope)")
                # Could still allow MODEL_SPECIFIC_ONLY — caller should use that path

    if to_state == "MODEL_SPECIFIC_ONLY":
        if claim.get("scope_classification") == "GENERAL_SYMBOLIC_IDENTITY":
            _fail_closed(errors, "GENERAL_SYMBOLIC_IDENTITY claim cannot be demoted to MODEL_SPECIFIC_ONLY; create a new projected claim")

    if to_state == "SUPERSEDED":
        evidence = evidence_artifact_ids or []
        if len(evidence) == 0:
            _fail_closed(errors, "SUPERSEDED requires referencing the superseding claim/evidence")

    if to_state == "INVALIDATED":
        evidence = evidence_artifact_ids or []
        if len(evidence) == 0:
            _fail_closed(errors, "INVALIDATED requires evidence of why the claim was invalidated")

    if to_state == "STALE_NONAUTHORITATIVE":
        stale = claim.get("stale_detection", {}).get("staleness_check", {})
        has_stale_reason = bool(
            stale.get("fresher_executable_available") or
            stale.get("parent_claim_invalidated") or
            stale.get("replay_diverged_from_frozen")
        )
        if not has_stale_reason:
            _fail_closed(errors, "STALE_NONAUTHORITATIVE requires a staleness reason")

    if errors:
        return claim, errors

    # ---- apply transition ----
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "from_state": from_state,
        "to_state": to_state,
        "timestamp": now,
        "decision_event_id": decision_event_id,
        "authorized_by_role": authorized_by_role,
        "evidence_artifact_ids": evidence_artifact_ids or [],
        "reason": reason,
    }
    history = claim.setdefault("state_history", [])
    if isinstance(history, list):
        history.append(entry)
    claim["current_state"] = to_state
    return claim, []


# ---------------------------------------------------------------------------
# Evidence / authority helpers
# ---------------------------------------------------------------------------
def _has_authoritative_evidence(claim):
    """Check if claim has executable_replay or frozen_machine_readable_operand evidence."""
    artifacts = claim.get("provenance_artifacts", {}).get("artifact_runs", [])
    for art in artifacts:
        if art.get("artifact_type") in ("executable_replay", "frozen_machine_readable_operand"):
            return True
    return False


def authority_tier_for_artifact_type(artifact_type):
    return _ARTIFACT_AUTHORITY_TIER.get(artifact_type, 99)


def compare_authority(artifact_a, artifact_b):
    """Compare two artifacts by authority. Returns -1 if a > b, 0 if equal, 1 if b > a."""
    tier_a = authority_tier_for_artifact_type(artifact_a.get("artifact_type", ""))
    tier_b = authority_tier_for_artifact_type(artifact_b.get("artifact_type", ""))
    if tier_a < tier_b:
        return -1
    elif tier_a > tier_b:
        return 1
    return 0


def is_fresh_replay_available(claim):
    """Check if a fresh executable replay artifact outranks all frozen artifacts."""
    artifacts = claim.get("provenance_artifacts", {}).get("artifact_runs", [])
    for art in artifacts:
        if art.get("artifact_type") == "executable_replay":
            return True
    return False


def should_reject_stale_artifact(claim, fresh_replay_available):
    """
    Decision: if a fresh executable replay is available and the claim is based
    on a frozen machine-readable operand or weaker, reject the stale artifact.
    """
    if not fresh_replay_available:
        return False, ""
    artifacts = claim.get("provenance_artifacts", {}).get("artifact_runs", [])
    best_tier = 99
    for art in artifacts:
        tier = authority_tier_for_artifact_type(art.get("artifact_type", ""))
        if tier < best_tier:
            best_tier = tier
    if best_tier > _ARTIFACT_AUTHORITY_TIER["frozen_machine_readable_operand"]:
        return True, "fresh_executable_replay_outranks_historical_evidence"
    return False, ""


def artifact_type_from_authority_level(level):
    """Map authority level name to artifact type string."""
    _map = {
        "FRESH_EXECUTABLE_REPLAY": "executable_replay",
        "FROZEN_MACHINE_READABLE_OPERAND": "frozen_machine_readable_operand",
        "STRUCTURED_RESULT_SUMMARY": "structured_result_summary",
        "HUMAN_READABLE_REPORT": "human_readable_report",
        "HISTORICAL_PASS_FIELD": "historical_pass_field",
    }
    return _map.get(level, "historical_pass_field")


# ---------------------------------------------------------------------------
# Invalid evidence rejection
# ---------------------------------------------------------------------------
def reject_invalid_evidence(claim):
    """
    Reject claims backed only by PASS, all_zero, or nonzero_count fields
    without linked executable evidence.
    """
    errors = []
    artifacts = claim.get("provenance_artifacts", {}).get("artifact_runs", [])
    executable_linked = any(
        art.get("artifact_type") in ("executable_replay", "frozen_machine_readable_operand")
        for art in artifacts
    )
    if not executable_linked:
        has_forbidden = any(
            art.get("artifact_type") in _FORBIDDEN_STANDALONE_EVIDENCE
            for art in artifacts
        )
        if artifacts and has_forbidden:
            errors.append("claim_backed_by_forbidden_standalone_evidence_without_executable_link")
    return errors


# ---------------------------------------------------------------------------
# Checkpoint operations
# ---------------------------------------------------------------------------
def last_trusted_checkpoint(checkpoints):
    """Find the most recent trusted checkpoint."""
    trusted = [c for c in checkpoints if c.get("trusted")]
    if not trusted:
        return None
    return max(trusted, key=lambda c: c.get("timestamp", ""))


def invalidated_descendants(checkpoints, checkpoint_id):
    """Return IDs of checkpoints that are invalidated descendants of the given checkpoint."""
    result = []
    target = next((c for c in checkpoints if c.get("checkpoint_id") == checkpoint_id), None)
    if target is None:
        return result
    target_ts = target.get("timestamp", "")
    for c in checkpoints:
        if c.get("checkpoint_id") == checkpoint_id:
            continue
        parent_id = c.get("parent_checkpoint_id")
        if parent_id == checkpoint_id:
            result.append(c.get("checkpoint_id"))
            result.extend(invalidated_descendants(checkpoints, c.get("checkpoint_id")))
    return result


def build_rollback_recommendation(checkpoints, invalidated_checkpoint_id):
    """
    Build a rollback recommendation: find the last trusted checkpoint
    before the invalidated one and list all invalidated descendants.
    """
    trusted_checkpoints = sorted(
        [c for c in checkpoints if c.get("trusted")],
        key=lambda c: c.get("timestamp", ""),
    )
    invalidated_cp = next(
        (c for c in checkpoints if c.get("checkpoint_id") == invalidated_checkpoint_id), None
    )
    if invalidated_cp is None:
        return None

    invalidated_ts = invalidated_cp.get("timestamp", "")
    candidates = [c for c in trusted_checkpoints if c.get("timestamp", "") < invalidated_ts]
    if not candidates:
        return None

    target = max(candidates, key=lambda c: c.get("timestamp", ""))
    descendants = invalidated_descendants(checkpoints, target.get("checkpoint_id"))
    all_invalidated = [invalidated_checkpoint_id] + descendants

    return {
        "rollback_id": f"ROLLBACK_{invalidated_checkpoint_id}",
        "target_checkpoint_id": target.get("checkpoint_id"),
        "invalidated_claim_ids": all_invalidated,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "authorized_by_role": "integration_executor",
        "reason": f"rollback to last trusted checkpoint {target.get('checkpoint_id')} after invalidation of {invalidated_checkpoint_id}",
        "recovery_actions": [
            f"restore_artifacts_from_checkpoint:{target.get('checkpoint_id')}",
            f"revalidate_claims_after:{target.get('checkpoint_id')}",
        ],
    }


# ---------------------------------------------------------------------------
# Scope / projection gates
# ---------------------------------------------------------------------------
def check_projection_gate(projection_comparison):
    """
    A model-projected match may authorize MODEL_SPECIFIC_EQUIVALENCE
    but must not authorize GENERAL_SYMBOLIC_IDENTITY unless injectivity is
    explicitly established.
    """
    errors = []
    injectivity = projection_comparison.get("injectivity_established", False)
    scope = projection_comparison.get("authorized_scope", "")

    if scope == "GENERAL_SYMBOLIC_IDENTITY" and not injectivity:
        errors.append(
            "GENERAL_SYMBOLIC_IDENTITY_scope_not_authorized_for_projection_without_injectivity"
        )

    if projection_comparison.get("cannot_promote_to_general", False) and scope == "GENERAL_SYMBOLIC_IDENTITY":
        errors.append("projection_explicitly_blocked_from_general_scope")

    return errors


def check_local_vs_boundary_gate(projection_comparison):
    """
    Separate LOCAL_EXACT_IDENTITY_GATE from BOUNDARY_APPLICABILITY_GATE.
    Local identity may pass while boundary remains pending.
    """
    local = projection_comparison.get("local_exact_identity_gate", {})
    boundary = projection_comparison.get("boundary_applicability_gate", {})

    local_passed = local.get("passed", False)
    boundary_passed = boundary.get("passed", False)

    result = {
        "local_exact_identity": local_passed,
        "boundary_applicability": boundary_passed,
        "both_passed": local_passed and boundary_passed,
        "local_only": local_passed and not boundary_passed,
        "boundary_only": boundary_passed and not local_passed,
        "neither": not local_passed and not boundary_passed,
    }
    return result


def is_projection_promotable_to_general(projection_comparison):
    """Check if a projection can authorize a general claim."""
    if not projection_comparison.get("injectivity_established"):
        return False, "injectivity_not_established"
    if projection_comparison.get("cannot_promote_to_general"):
        return False, "explicitly_blocked"
    local_passed = projection_comparison.get("local_exact_identity_gate", {}).get("passed", False)
    boundary_passed = projection_comparison.get("boundary_applicability_gate", {}).get("passed", False)
    if not (local_passed and boundary_passed):
        return False, "gates_not_fully_passed"
    return True, ""


# ---------------------------------------------------------------------------
# Linear-system evidence validation
# ---------------------------------------------------------------------------
def validate_linear_system_evidence(evidence):
    """Validate linear-system evidence for self-consistency."""
    errors = []
    warnings = []

    shape = evidence.get("matrix_shape", [])
    if len(shape) != 2:
        errors.append("matrix_shape_must_have_exactly_2_dimensions")
    else:
        rows, cols = shape[0], shape[1]
        rank = evidence.get("rank")
        augmented_rank = evidence.get("augmented_rank")
        nullity = evidence.get("nullity")
        left_nullspace = evidence.get("left_nullspace_dimension")

        if rank is not None:
            if rank > min(rows, cols):
                errors.append(f"rank_{rank}_exceeds_min_dimension_{min(rows, cols)}")
            if rank < 0:
                errors.append("rank_cannot_be_negative")

        if nullity is not None and rank is not None:
            expected_nullity = cols - rank
            if nullity != expected_nullity:
                errors.append(f"nullity_{nullity}_inconsistent_with_rank_{rank}_for_{cols}_columns_expected_{expected_nullity}")

        if left_nullspace is not None and rank is not None:
            expected_left = rows - rank
            if left_nullspace != expected_left:
                errors.append(f"left_nullspace_{left_nullspace}_inconsistent_with_rank_{rank}_for_{rows}_rows_expected_{expected_left}")

        if augmented_rank is not None and rank is not None:
            consistent = evidence.get("consistent", None)
            expected_consistent = (augmented_rank == rank)
            if consistent is not None and consistent != expected_consistent:
                errors.append(
                    f"consistent_field={consistent}_mismatches_rank_check: "
                    f"rank={rank}_augmented_rank={augmented_rank}_expected_consistent={expected_consistent}"
                )

        unique = evidence.get("unique_solution", None)
        if unique is not None and nullity is not None:
            expected_unique = (evidence.get("consistent") and nullity == 0)
            if unique != expected_unique:
                errors.append(f"unique_solution={unique}_inconsistent_nullity={nullity}")

    residuals = evidence.get("equation_residuals", [])
    for r in residuals:
        if r.get("below_tolerance") is not None:
            tol = r.get("tol", 0)
            residual = abs(r.get("residual", 0))
            expected_below = residual <= tol if tol > 0 else residual == 0
            if r["below_tolerance"] != expected_below:
                errors.append(f"equation_{r['equation_index']}_below_tolerance_flag_mismatches_residual={residual}_tol={tol}")

    gen = evidence.get("generator_engine")
    ver = evidence.get("verifier_engine")
    if gen and ver and gen == ver:
        warnings.append("generator_and_verifier_are_same_engine")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# Numerical baseline retention
# ---------------------------------------------------------------------------
def retain_numerical_baseline(evidence, downstream_invalidation_event):
    """
    After downstream analytical invalidation, numerical baselines must be retained
    for comparison. Returns the evidence with baseline marked as retained.
    """
    evidence = copy.deepcopy(evidence)
    baseline = evidence.setdefault("numerical_baseline", {})
    baseline["retained"] = True
    baseline.setdefault("baseline_id", f"BASELINE_{evidence.get('evidence_id', 'UNKNOWN')}")
    return evidence


def compare_baseline_with_invalidation(baseline_evidence, invalidation_details):
    """Compare retained numerical baseline against downstream invalidation."""
    baseline = baseline_evidence.get("numerical_baseline", {})
    if not baseline.get("retained"):
        return {"comparison_possible": False, "reason": "baseline_not_retained"}
    return {
        "comparison_possible": True,
        "baseline_rank": baseline.get("rank_numerical"),
        "baseline_residual_norm": baseline.get("residual_norm"),
        "invalidation_source": invalidation_details.get("reason", ""),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python claim_decision_engine.py <command> [args...]")
        print("Commands:")
        print("  transition <claim.json> <to_state> <authorized_by_role> [reason]")
        print("  validate-evidence <evidence.json>")
        print("  rollback <checkpoints.json> <invalidated_checkpoint_id>")
        print("  projection-gate <projection.json>")
        print("  reject-stale <claim.json> [fresh_replay_available=true|false]")
        print("  states")
        print("  transitions-for <state>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "states":
        print(json.dumps(all_valid_states(), indent=2))
    elif cmd == "transitions-for":
        state = sys.argv[2]
        print(json.dumps(allowed_transitions_for(state), indent=2))
    elif cmd == "transition":
        claim_path = sys.argv[2]
        to_state = sys.argv[3]
        role = sys.argv[4]
        reason = sys.argv[5] if len(sys.argv) > 5 else ""
        with open(claim_path) as f:
            claim = json.load(f)
        new_claim, errors = transition(
            claim, to_state,
            f"DECISION_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
            role, reason=reason
        )
        result = {"success": len(errors) == 0, "errors": errors, "claim": new_claim}
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    elif cmd == "validate-evidence":
        path = sys.argv[2]
        with open(path) as f:
            evidence = json.load(f)
        result = validate_linear_system_evidence(evidence)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)
    elif cmd == "rollback":
        cps_path = sys.argv[2]
        invalid_id = sys.argv[3]
        with open(cps_path) as f:
            checkpoints = json.load(f)
        rec = build_rollback_recommendation(checkpoints, invalid_id)
        print(json.dumps(rec, indent=2))
    elif cmd == "projection-gate":
        path = sys.argv[2]
        with open(path) as f:
            proj = json.load(f)
        errors = check_projection_gate(proj)
        gates = check_local_vs_boundary_gate(proj)
        result = {"valid": len(errors) == 0, "errors": errors, "gates": gates}
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)
    elif cmd == "reject-stale":
        path = sys.argv[2]
        fresh = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
        with open(path) as f:
            claim = json.load(f)
        should_reject, reason = should_reject_stale_artifact(claim, fresh)
        errors = reject_invalid_evidence(claim)
        result = {
            "should_reject_stale": should_reject,
            "stale_reason": reason,
            "invalid_evidence_errors": errors,
        }
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
