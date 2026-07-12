#!/usr/bin/env python3
"""
Sigma XXX Repair Lineage Flagship Benchmark — Repository-Native Tests.

Tests covering:
  1. wrong r-index is rejected
  2. source-backed repair becomes candidate
  3. stale false positive loses authority
  4. stale false negative may recover only with fresh evidence
  5. invalid analytic descendant rolls back to seven-kernel
  6. independent numerical baseline remains active
  7. model projection cannot promote general identity
  8. reference transcription remains blocked until source authentication
  9. repaired exact solve is promoted only after equation-by-equation verification
  10. executor self-promotion blocked

All tests fail closed.
"""
import json
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, SCRIPTS_DIR)

from claim_decision_engine import (
    transition, is_valid_transition, is_recoverable_dormant,
    build_rollback_recommendation, should_reject_stale_artifact,
    reject_invalid_evidence, check_projection_gate,
    check_local_vs_boundary_gate, validate_linear_system_evidence,
    compare_authority, authority_tier_for_artifact_type,
    retain_numerical_baseline, is_projection_promotable_to_general,
)


REPAIR_LINEAGE_DIR = os.path.join(BENCHMARK_DIR, "repair_lineage")


def load_json(rel_path):
    with open(os.path.join(REPAIR_LINEAGE_DIR, rel_path)) as f:
        return json.load(f)


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def make_candidate(claim_id="CLAIM_TEST", scope="LOCAL_EXACT_IDENTITY"):
    return {
        "claim_id": claim_id,
        "lifecycle_version": "1.0.0",
        "current_state": "CANDIDATE",
        "state_history": [],
        "provenance_artifacts": {
            "artifact_runs": [
                {
                    "artifact_run_id": "AR_TEST",
                    "artifact_type": "executable_replay",
                    "authority_tier": 0,
                    "artifact_sha": "0" * 64,
                    "timestamp": now_iso(),
                    "generated_by_role": "executor",
                    "linked_execution_truth_id": "ET_TEST",
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


# ---------------------------------------------------------------------------
# Test 1: Wrong r-index is rejected
# ---------------------------------------------------------------------------
def test_wrong_r_index_rejected():
    """Fixture A: Wrong r-index produces EXACT_RESIDUAL_NONZERO and is denied promotion."""
    fixture = load_json("fixtures/derivative_order_alignment/fixture_manifest.json")
    wrong = fixture["wrong_candidate"]
    repaired = fixture["source_backed_candidate"]

    assert wrong["expected_residual"] == "EXACT_RESIDUAL_NONZERO", "Wrong r-index should have nonzero residual"
    assert wrong["expected_promotion"] == "denied", "Wrong r-index promotion should be denied"
    assert repaired["r_primitive"] == "r_target - 1", "Repaired sets r_primitive = r_target - 1"
    assert repaired["expected_result"] == "TARGET_DERIVATIVE_IMAGE_ALIGNED", "Repaired should align with target derivative"


# ---------------------------------------------------------------------------
# Test 2: Source-backed repair becomes candidate
# ---------------------------------------------------------------------------
def test_source_backed_repair_becomes_candidate():
    """Fixture A + F: The source-backed r-index repair can enter CANDIDATE state."""
    claim = make_candidate("CLAIM_REPAIRED_PAIR")
    new_claim, errors = transition(
        claim, "SOURCE_BACKED", "DEC_TEST_SB", "executor",
        reason="source-backed r-index repair",
        evidence_artifact_ids=["AR_PAIR_REPAIRED"]
    )
    assert len(errors) == 0, f"Should succeed: {errors}"
    assert new_claim["current_state"] == "SOURCE_BACKED"

    new_claim2, errors2 = transition(
        new_claim, "PENDING_INDEPENDENT_VERIFICATION", "DEC_TEST_PIV",
        "independent_verifier", reason="independent replay",
        evidence_artifact_ids=["AR_REPLAY_INDEPENDENT"]
    )
    assert len(errors2) == 0, f"Should succeed: {errors2}"
    assert new_claim2["current_state"] == "PENDING_INDEPENDENT_VERIFICATION"


# ---------------------------------------------------------------------------
# Test 3: Stale false positive loses authority
# ---------------------------------------------------------------------------
def test_stale_false_positive_loses_authority():
    """Fixture C: Fresh executable replay outranks stale false-positive report."""
    fixture = load_json("historical/stale_false_positive/fixture_manifest.json")
    exp = fixture["expected_adjudication"]
    assert exp["stale_report_verdict"] == "STALE_OR_DEFECTIVE_SUMMARY_REJECTED"
    assert exp["claim_promotion"] == "denied"
    assert exp["authority_rule"] == "fresh_coefficient_audit_authoritative"

    # Verify authority tier ordering
    fresh_tier = authority_tier_for_artifact_type("executable_replay")
    historical_tier = authority_tier_for_artifact_type("historical_pass_field")
    assert fresh_tier < historical_tier, f"executable_replay (tier {fresh_tier}) must outrank historical_pass_field (tier {historical_tier})"

    # Fresh executable replay should outrank stale
    stale_claim = fixture["claim"]
    should_reject, reason = should_reject_stale_artifact(stale_claim, fresh_replay_available=True)
    assert should_reject, "Stale artifact should be rejected when fresh replay is available"


# ---------------------------------------------------------------------------
# Test 4: Stale false negative may recover only with fresh evidence
# ---------------------------------------------------------------------------
def test_stale_false_negative_recovery_requires_evidence():
    """Fixture D: STALE_NONAUTHORITATIVE -> CANDIDATE requires fresh executable evidence."""
    fixture = load_json("historical/stale_false_negative/fixture_manifest.json")
    exp = fixture["expected_state_transitions"]
    assert exp["stale_report_state"] == "STALE_NONAUTHORITATIVE"

    dormant = make_candidate("CLAIM_STALE_FN")
    dormant["current_state"] = "STALE_NONAUTHORITATIVE"
    dormant["stale_detection"]["staleness_check"]["fresher_executable_available"] = True
    dormant["authority_level"] = "STRUCTURED_RESULT_SUMMARY"

    # Recovery without evidence — fails
    _, errs = transition(dormant, "CANDIDATE", "DEC_SFN_NOEV", "integration_executor",
                          reason="trying to recover without evidence")
    assert len(errs) > 0, "Should fail without evidence_artifact_ids"

    # Recovery without reason — fails
    _, errs2 = transition(dormant, "CANDIDATE", "DEC_SFN_NOREASON", "integration_executor",
                           evidence_artifact_ids=["AR_FRESH"])
    assert len(errs2) > 0, "Should fail without explicit reason"

    # Recovery with evidence + reason — succeeds
    _, errs3 = transition(dormant, "CANDIDATE", "DEC_SFN_OK", "integration_executor",
                           evidence_artifact_ids=["AR_FRESH"], reason="fresh replay demonstrates solution")
    assert len(errs3) == 0, f"Should succeed with evidence + reason: {errs3}"


# ---------------------------------------------------------------------------
# Test 5: Invalid analytic descendant rolls back to seven-kernel
# ---------------------------------------------------------------------------
def test_rollback_to_seven_kernel():
    """Fixture E: Rollback after pair reduction invalidation targets seven-kernel checkpoint."""
    cps = load_json("fixtures/checkpoint_rollback/checkpoints.json")["checkpoints"]
    rec = build_rollback_recommendation(cps, "CP_PAIR_REDUCTION_HISTORICAL")
    assert rec is not None, "Should produce rollback recommendation"
    assert rec["target_checkpoint_id"] == "CP_SEVEN_KERNEL", \
        f"Expected CP_SEVEN_KERNEL, got {rec['target_checkpoint_id']}"
    assert "CP_PAIR_REDUCTION_HISTORICAL" in rec["invalidated_claim_ids"]
    assert "CP_CLOSED_FORM_HISTORICAL" in rec["invalidated_claim_ids"]

    # Verify CP_SEVEN_KERNEL is not in the invalidated list
    assert "CP_SEVEN_KERNEL" not in rec["invalidated_claim_ids"]


# ---------------------------------------------------------------------------
# Test 6: Independent numerical baseline remains active
# ---------------------------------------------------------------------------
def test_numerical_baseline_retained():
    """Fixture H: Numerical baseline from independent derivation path is retained."""
    fixture = load_json("fixtures/numerical_provenance/fixture_manifest.json")
    baselines = fixture["provenance_ledger"]["baselines"]
    retainable = next(b for b in baselines if b["status"] == "RETAINABLE_BASELINE")
    recompute = next(b for b in baselines if b["status"] == "RECOMPUTE_REQUIRED")

    assert retainable["independent_of_invalidated_branch"] == True
    assert recompute["independent_of_invalidated_branch"] == False
    assert retainable["baseline_id"] == "BL_RAW_FINITE_GAMMA_NUMERICAL"
    assert recompute["baseline_id"] == "BL_HISTORICAL_CLOSED_FORM_NUMERICAL"

    # Test baseline retention function
    ev = {
        "evidence_id": "EV_BASELINE",
        "claim_id": "CLAIM_BASELINE",
        "system_description": "test",
        "matrix_shape": [12, 12], "rank": 12, "augmented_rank": 12,
        "nullity": 0, "left_nullspace_dimension": 0, "consistent": True
    }
    retained = retain_numerical_baseline(ev, {"reason": "downstream invalidation"})
    assert retained["numerical_baseline"]["retained"] == True

    # Verify checkpoints: numerical baseline not affected by analytical rollback
    cps = load_json("fixtures/checkpoint_rollback/checkpoints.json")["checkpoints"]
    num_cp = next(c for c in cps if c["checkpoint_id"] == "CP_NUMERICAL_BASELINE")
    assert num_cp["trusted"] == True
    # Numerical baseline descends from CP_DECOMPOSITION, not CP_SEVEN_KERNEL
    assert num_cp["parent_checkpoint_id"] == "CP_DECOMPOSITION"


# ---------------------------------------------------------------------------
# Test 7: Model projection cannot promote general identity
# ---------------------------------------------------------------------------
def test_model_projection_cannot_promote_general_identity():
    """Fixture G: MODEL_SPECIFIC_EQUIVALENCE allowed; GENERAL_SYMBOLIC_IDENTITY denied."""
    fixture = load_json("fixtures/projection_trap/fixture_manifest.json")
    exp = fixture["expected_adjudication"]
    assert exp["scope_classification"]["authorized"] == "MODEL_SPECIFIC_EQUIVALENCE"
    assert exp["scope_classification"]["denied"] == "GENERAL_SYMBOLIC_IDENTITY"

    proj = fixture["expected_adjudication"]["projection_comparison"]
    # This projection_comparison has authorized_scope="MODEL_SPECIFIC_EQUIVALENCE" which is fine
    # Test with GENERAL_SYMBOLIC_IDENTITY scope (should be blocked)
    proj_general = dict(proj)
    proj_general["authorized_scope"] = "GENERAL_SYMBOLIC_IDENTITY"
    proj_general["injectivity_established"] = False
    errs = check_projection_gate(proj_general)
    # Non-injective projection with GENERAL scope should error
    assert len(errs) > 0, "Projection without injectivity should be blocked from general scope"

    # Test with injectivity established
    proj2 = dict(proj)
    proj2["injectivity_established"] = True
    proj2["cannot_promote_to_general"] = False
    ok, reason = is_projection_promotable_to_general(proj2)
    # With injectivity + both gates passed, should be promotable
    assert ok, f"With injectivity established, should be promotable. Got: {reason}"

    # Test: GENERAL_SYMBOLIC_IDENTITY claim cannot be demoted
    gen_claim = make_candidate("CLAIM_GENERAL", "GENERAL_SYMBOLIC_IDENTITY")
    gen_claim["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"
    _, errs_demote = transition(gen_claim, "MODEL_SPECIFIC_ONLY", "DEC_DEMOTE",
                                 "independent_verifier", reason="trying demote")
    assert len(errs_demote) > 0, "GENERAL_SYMBOLIC_IDENTITY claim cannot be demoted"


# ---------------------------------------------------------------------------
# Test 8: Reference transcription blocked until source authentication
# ---------------------------------------------------------------------------
def test_reference_transcription_blocked_until_auth():
    """Fixture I: BLOCKED comparison requires source-authenticated recovery."""
    fixture = load_json("fixtures/reference_authentication_recovery/fixture_manifest.json")
    seq = fixture["methodological_sequence"]

    assert seq["step_1_derived_transcription"]["status"] == "BLOCKED_BY_TRANSCRIPTION_AMBIGUITY"
    assert seq["step_1_derived_transcription"]["claim_state"] == "BLOCKED"
    assert seq["step_2_source_authentication"]["status"] == "AMBIGUITIES_RESOLVED"
    assert seq["step_3_recovery"]["from_state"] == "BLOCKED"
    assert seq["step_3_recovery"]["to_state"] == "CANDIDATE"

    # Verify authority ordering
    assert fixture["authority_order"]["most_authoritative"] is not None
    assert "PDF" in fixture["authority_order"]["most_authoritative"]
    assert fixture["authority_order"]["less_authoritative"] is not None
    assert "Markdown" in fixture["authority_order"]["less_authoritative"]

    # Verify recovery requires evidence
    blocked_claim = make_candidate("CLAIM_REF")
    blocked_claim["current_state"] = "BLOCKED"
    blocked_claim["authority_level"] = "FROZEN_MACHINE_READABLE_OPERAND"

    # Without evidence — fails
    _, errs = transition(blocked_claim, "CANDIDATE", "DEC_BLK_NOEV",
                          "integration_executor", reason="try recovery")
    assert len(errs) > 0, "BLOCKED recovery without evidence should fail"

    # With evidence + reason — succeeds
    _, errs2 = transition(blocked_claim, "CANDIDATE", "DEC_BLK_OK",
                           "integration_executor",
                           evidence_artifact_ids=["AR_020_REF"],
                           reason="PDF-authenticated objects resolve ambiguity")
    assert len(errs2) == 0, f"BLOCKED recovery with evidence should succeed: {errs2}"

    # Timestamp alone fails
    blocked_claim2 = make_candidate("CLAIM_REF2")
    blocked_claim2["current_state"] = "BLOCKED"
    blocked_claim2["authority_level"] = "FROZEN_MACHINE_READABLE_OPERAND"
    _, errs3 = transition(blocked_claim2, "CANDIDATE", "DEC_BLK_TS",
                           "integration_executor",
                           reason="timestamp-only recovery: " + now_iso())
    assert len(errs3) > 0, "Timestamp alone should fail"


# ---------------------------------------------------------------------------
# Test 9: Repaired exact solve only after equation-by-equation verification
# ---------------------------------------------------------------------------
def test_repaired_exact_solve_requires_verification():
    """Fixture B + F: ACTIVE_VERIFIED requires equation-by-equation zero residuals."""
    fixture = load_json("fixtures/exact_coupled_solve/fixture_manifest.json")
    exp = fixture["expected_evidence"]["linear_system_evidence"]

    # Validate the linear system evidence
    result = validate_linear_system_evidence(exp)
    assert result["valid"], f"Linear system evidence should be valid: {result['errors']}"

    # Check system properties
    assert exp["matrix_shape"] == [12, 12]
    assert exp["rank"] == 12
    assert exp["augmented_rank"] == 12
    assert exp["nullity"] == 0
    assert exp["left_nullspace_dimension"] == 0
    assert exp["consistent"] == True
    assert exp["unique_solution"] == True

    # All equation residuals must be zero
    residuals = exp["equation_residuals"]
    assert len(residuals) == 12
    for r in residuals:
        assert r["residual"] == 0.0
        assert r["below_tolerance"] == True

    # Promotion to ACTIVE_VERIFIED requires independent_verifier, not executor
    claim = make_candidate("CLAIM_SOLVE")
    claim["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"
    _, errs_exec = transition(claim, "ACTIVE_VERIFIED", "DEC_SOLVE_EXEC", "executor",
                               evidence_artifact_ids=["AR_SOLVE"], reason="claiming verified")
    assert len(errs_exec) > 0, "Executor cannot self-promote to ACTIVE_VERIFIED"

    # Independent_verifier can promote
    claim2 = make_candidate("CLAIM_SOLVE2")
    claim2["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"
    _, errs_ver = transition(claim2, "ACTIVE_VERIFIED", "DEC_SOLVE_VER", "independent_verifier",
                              evidence_artifact_ids=["AR_SOLVE"], reason="equation-by-equation zero residuals confirmed")
    assert len(errs_ver) == 0, f"Independent_verifier should be able to promote: {errs_ver}"


# ---------------------------------------------------------------------------
# Test 10: Executor self-promotion blocked
# ---------------------------------------------------------------------------
def test_executor_self_promotion_blocked():
    """Executor cannot promote their own claim to ACTIVE_VERIFIED."""
    claim = make_candidate("CLAIM_EXEC")
    claim["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"

    _, errs = transition(claim, "ACTIVE_VERIFIED", "DEC_EXEC_SELF", "executor",
                          evidence_artifact_ids=["AR_X"], reason="self promotion")
    assert len(errs) > 0
    has_self_promote = any("self-promote" in e.lower() for e in errs)
    assert has_self_promote, f"Should block executor self-promotion: {errs}"

    # Independent_verifier can still do it
    claim2 = make_candidate("CLAIM_EXEC2")
    claim2["current_state"] = "PENDING_INDEPENDENT_VERIFICATION"
    _, errs2 = transition(claim2, "ACTIVE_VERIFIED", "DEC_EXEC_VER", "independent_verifier",
                           evidence_artifact_ids=["AR_X"], reason="independent verification")
    assert len(errs2) == 0, f"Independent_verifier should succeed: {errs2}"


# ---------------------------------------------------------------------------
# Test 11: Exact 12x12 matrix solve
# ---------------------------------------------------------------------------
def test_exact_12x12_matrix_solve():
    """Fixture B: Verify 12x12 matrix equation Mx = b holds exactly."""
    mat = load_json("fixtures/exact_coupled_solve/matrix.json")
    rhs = load_json("fixtures/exact_coupled_solve/rhs.json")
    sol = load_json("fixtures/exact_coupled_solve/solution.json")

    M = mat["matrix"]
    b = rhs["rhs"]
    x = sol["solution"]

    assert len(M) == 12
    assert all(len(row) == 12 for row in M)
    assert len(b) == 12
    assert len(x) == 12

    calc_b = [sum(M[i][j] * x[j] for j in range(12)) for i in range(12)]
    assert calc_b == b, f"Mx != b. Expected {b}, got {calc_b}"

    residuals = [calc_b[i] - b[i] for i in range(12)]
    assert all(r == 0 for r in residuals), f"Nonzero residuals: {residuals}"


# ---------------------------------------------------------------------------
# Test 12: All fixtures have manifest.json
# ---------------------------------------------------------------------------
def test_all_fixtures_have_manifest():
    """Every fixture directory must contain a manifest file."""
    fixture_dirs = [
        "fixtures/derivative_order_alignment",
        "fixtures/exact_coupled_solve",
        "fixtures/checkpoint_rollback",
        "fixtures/projection_trap",
        "fixtures/numerical_provenance",
        "fixtures/reference_authentication_recovery",
        "historical/stale_false_positive",
        "historical/stale_false_negative",
    ]
    for d in fixture_dirs:
        path = os.path.join(REPAIR_LINEAGE_DIR, d)
        assert os.path.isdir(path), f"Directory missing: {d}"
        manifest = os.path.join(path, "fixture_manifest.json")
        assert os.path.isfile(manifest), f"Manifest missing: {d}/fixture_manifest.json"

    # Active directory has its own manifest
    active_manifest = os.path.join(REPAIR_LINEAGE_DIR, "active", "repaired_promotion_manifest.json")
    assert os.path.isfile(active_manifest), "Active manifest missing"


# ---------------------------------------------------------------------------
# Test 13: Expected verdict files are present and parseable
# ---------------------------------------------------------------------------
def test_expected_verdict_files():
    """All expected verdict files are present and parseable."""
    import yaml
    expected_files = [
        "expected/claim_transitions.yaml",
        "expected/checkpoint_decisions.yaml",
        "expected/verification_results.yaml",
        "expected/authority_adjudications.yaml",
    ]
    for f in expected_files:
        path = os.path.join(REPAIR_LINEAGE_DIR, f)
        assert os.path.isfile(path), f"Expected file missing: {f}"
        with open(path) as fh:
            content = yaml.safe_load(fh)
        assert content is not None, f"Failed to parse {f}"


# ---------------------------------------------------------------------------
# Test 14: No private paths in public benchmark files
# ---------------------------------------------------------------------------
def test_no_private_paths():
    """No personal absolute paths should appear in any public benchmark file."""
    forbidden = ["/Users/wangjiahua", "Desktop/25-26", "test_situte"]
    found = []
    for root, dirs, files in os.walk(REPAIR_LINEAGE_DIR):
        for name in files:
            if name.endswith((".json", ".yaml", ".yml", ".md", ".py", ".txt")):
                path = os.path.join(root, name)
                with open(path) as f:
                    try:
                        content = f.read()
                    except UnicodeDecodeError:
                        continue
                for pattern in forbidden:
                    if pattern in content and "private_source_packages_available_at" not in content:
                        found.append(f"{path}: {pattern}")
    assert len(found) == 0, f"Private paths found: {found}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_all():
    tests = [
        ("wrong_r_index_rejected", test_wrong_r_index_rejected),
        ("source_backed_repair_candidate", test_source_backed_repair_becomes_candidate),
        ("stale_false_positive_loses_authority", test_stale_false_positive_loses_authority),
        ("stale_false_negative_recovery_requires_evidence", test_stale_false_negative_recovery_requires_evidence),
        ("rollback_to_seven_kernel", test_rollback_to_seven_kernel),
        ("numerical_baseline_retained", test_numerical_baseline_retained),
        ("model_projection_cannot_promote_general_identity", test_model_projection_cannot_promote_general_identity),
        ("reference_transcription_blocked_until_auth", test_reference_transcription_blocked_until_auth),
        ("repaired_solve_requires_verification", test_repaired_exact_solve_requires_verification),
        ("executor_self_promotion_blocked", test_executor_self_promotion_blocked),
        ("exact_12x12_matrix_solve", test_exact_12x12_matrix_solve),
        ("all_fixtures_have_manifest", test_all_fixtures_have_manifest),
        ("no_private_paths", test_no_private_paths),
    ]

    # Test 13: Expected verdict files (needs yaml)
    try:
        import yaml
        tests.append(("expected_verdict_files", test_expected_verdict_files))
    except ImportError:
        pass

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name} — {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
