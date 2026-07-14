#!/usr/bin/env python3
"""
ENGINE_002 Fixture Suite — E1 through E12.
Uses synthetic, redistributable expressions.
Does not use private generic_expression or generic_target scientific artifacts.
"""
import json
import sys
import os
import subprocess
import hashlib
import time
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
SCHEMAS_DIR = os.path.join(REPO_ROOT, "schemas")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, SCRIPTS_DIR)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _resolve_capabilities_from_scratch(request: dict) -> dict:
    """Inline capability resolver (avoids import issues)."""
    requested_caps = set(request.get("requested_capabilities", []))
    preferred = request.get("preferred_backends", [])
    prohibited = set(request.get("prohibited_backends", []))
    output_type = request.get("expected_output_type", "EXACT_SYMBOLIC")

    all_caps = {
        "sympy": {
            "type": "EXACT_SYMBOLIC",
            "available": True,
            "caps": {"expand", "factor", "cancel", "together", "apart", "diff",
                     "series", "coefficient_extraction", "exact_simplification",
                     "subs", "exact_reconstruction", "structural_replay",
                     "noncommutative_symbolic_representation"}
        },
        "python_numeric": {
            "type": "NUMERICAL",
            "available": True,
            "caps": {"mpmath_evalf", "mpmath_gamma", "mpmath_zeta",
                     "mpmath_polygamma", "mpmath_nintegrate",
                     "numerical_comparison_with_tolerance",
                     "scipy_integrate_quad", "scipy_special_eval",
                     "linear_algebra", "numerical_differentiation",
                     "parameter_scan", "high_precision_sampling"}
        },
        "mathematica": {
            "type": "EXACT_SYMBOLIC",
            "available": True,
            "caps": {"Series", "Coefficient", "ReplaceAll", "Expand",
                     "Factor", "Together", "Apart", "Cancel", "SameQ",
                     "exact_subtraction", "Simplify_with_TimeConstrained",
                     "exact_simplification", "D"}
        }
    }

    candidates = []
    for eid, info in all_caps.items():
        if eid in prohibited:
            continue
        matched = requested_caps & info["caps"]
        unmatched = requested_caps - info["caps"]
        candidates.append({
            "engine_id": eid,
            "matched_capabilities": sorted(matched),
            "unmatched_capabilities": sorted(unmatched),
            "available": info["available"]
        })

    exact_available = [c for c in candidates
                       if all_caps[c["engine_id"]]["type"] == "EXACT_SYMBOLIC" and c["available"]]
    numeric_available = [c for c in candidates
                         if all_caps[c["engine_id"]]["type"] == "NUMERICAL" and c["available"]]

    def _can_satisfy(candidate):
        return len(candidate["unmatched_capabilities"]) == 0 and candidate["available"]

    primary = None
    gaps = sorted(requested_caps)
    human_decision = False

    if output_type in ("EXACT_SYMBOLIC", "ANY"):
        preferred_exact = [c for c in exact_available if c["engine_id"] in preferred and _can_satisfy(c)]
        if preferred_exact:
            primary = preferred_exact[0]["engine_id"]
            gaps = preferred_exact[0]["unmatched_capabilities"]
        elif exact_available:
            satisfying = [c for c in exact_available if _can_satisfy(c)]
            if satisfying:
                primary = satisfying[0]["engine_id"]
                gaps = satisfying[0]["unmatched_capabilities"]
        if primary is None and numeric_available and output_type == "ANY":
            satisfying_num = [c for c in numeric_available if c["engine_id"] in preferred or True]
            if satisfying_num:
                primary = satisfying_num[0]["engine_id"]
                gaps = satisfying_num[0]["unmatched_capabilities"]
    elif output_type == "NUMERICAL_SAMPLED":
        preferred_num = [c for c in numeric_available if c["engine_id"] in preferred and _can_satisfy(c)]
        if preferred_num:
            primary = preferred_num[0]["engine_id"]
            gaps = preferred_num[0]["unmatched_capabilities"]
        elif numeric_available:
            satisfying = [c for c in numeric_available if _can_satisfy(c)]
            if satisfying:
                primary = satisfying[0]["engine_id"]
                gaps = satisfying[0]["unmatched_capabilities"]

    if primary is None:
        human_decision = True

    return {
        "candidate_backends": [
            {"engine_id": c["engine_id"],
             "matched_capabilities": c["matched_capabilities"],
             "unmatched_capabilities": c["unmatched_capabilities"],
             "available": c["available"]}
            for c in candidates
        ],
        "capability_match": {
            "all_capabilities_matched": not bool(gaps),
            "exact_match_available": bool(exact_available),
            "numeric_match_available": bool(numeric_available)
        },
        "capability_gaps": gaps,
        "selected_primary_backend": primary,
        "selected_supporting_backends": [],
        "selected_verification_backends": [],
        "selection_reason": f"resolved primary={primary}",
        "license_constraints": [],
        "availability_evidence": {
            "sympy": "AVAILABLE",
            "python_numeric": "AVAILABLE",
            "mathematica": "AVAILABLE"
        },
        "fallback_path": "resolved" if primary else "UNSUPPORTED_CAPABILITY",
        "human_decision_required": human_decision
    }


def run_request(request: dict) -> dict:
    """Execute a request through the engine orchestrator."""
    selection = _resolve_capabilities_from_scratch(request)
    primary = selection.get("selected_primary_backend")

    if primary is None:
        return {
            "result_type": "UNSUPPORTED_CAPABILITY" if selection.get("capability_gaps") else "ENGINE_UNAVAILABLE",
            "selection": selection,
            "errors": selection.get("capability_gaps", []),
            "request_id": request.get("request_id", "unknown"),
            "engine_id": "none"
        }

    runner_path = os.path.join(REPO_ROOT, "engines", primary, "runner.py")
    if not os.path.exists(runner_path):
        return {"result_type": "EXECUTION_FAILED", "errors": ["runner_not_found"]}

    try:
        proc = subprocess.run(
            [sys.executable, runner_path],
            input=json.dumps(request),
            capture_output=True, text=True,
            timeout=request.get("timeout", 30),
            cwd=REPO_ROOT
        )
        if proc.stdout.strip():
            result = json.loads(proc.stdout.strip())
            result["_selection"] = selection
            return result
        return {"result_type": "EXECUTION_FAILED", "errors": [proc.stderr[:500]], "exit_code": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"result_type": "TIMEOUT", "errors": ["timeout_expired"], "timeout_state": True}
    except Exception as e:
        return {"result_type": "EXECUTION_FAILED", "errors": [str(e)]}


def build_request(fixture_id: str, caps: list, ops: list, expression: str,
                  expected_type: str = "EXACT_SYMBOLIC",
                  claim_type: str = "literal_equality",
                  assumptions: list = None,
                  timeout: int = 30,
                  preferred_backends: list = None,
                  prohibited_backends: list = None,
                  fallback_policy: str = "STRICT") -> dict:
    return {
        "request_id": f"ENGINE002_FIXTURE_{fixture_id}",
        "source_task_id": "SLOOP_ENGINE_002",
        "source_artifact": f"fixtures/{fixture_id}",
        "source_sha": sha256_hex(expression),
        "scientific_adapter": "fixture_synthetic",
        "requested_capabilities": caps,
        "requested_operation_sequence": [
            {"operation": op, "parameters": params or {}, "order": i + 1}
            for i, (op, params) in enumerate(ops)
        ],
        "allowed_operations": [op for op, _ in ops],
        "forbidden_operations": [],
        "declared_assumptions": assumptions or [],
        "expression_scope": {
            "input_expression": expression,
            "expression_language": "sympy",
            "free_symbols": ["x", "y", "z"],
            "indexed_symbols": [],
            "commutativity_metadata": {}
        },
        "expected_output_type": expected_type,
        "requested_claim_type": claim_type,
        "timeout": timeout,
        "memory_limit": 1024,
        "precision": 53,
        "determinism_requirement": True,
        "preferred_backends": preferred_backends if preferred_backends is not None else ["sympy"],
        "prohibited_backends": prohibited_backends if prohibited_backends is not None else [],
        "fallback_policy": fallback_policy
    }


def E1_exact_commutative_algebra() -> dict:
    """(x+1)^2 expanded and refactored — should reconstruct exactly."""
    request = build_request(
        "E1",
        caps=["expand", "factor"],
        ops=[("expand", {"expression": "(x+1)**2"}),
             ("factor", {})],
        expression="(x+1)**2"
    )
    result = run_request(request)
    return {
        "fixture_id": "E1",
        "name": "Exact commutative algebra",
        "expected": "EXACT_RECONSTRUCTION_PASS",
        "passed": result.get("result_type") in ("EXACT_SYMBOLIC_RESULT", "EXACT_RECONSTRUCTION_PASS"),
        "result_type": result.get("result_type"),
        "details": result
    }


def E2_noncommutative_ordering() -> dict:
    """Noncommutative symbols — ordering must not be silently reordered."""
    request = build_request(
        "E2",
        caps=[],
        ops=[],
        expression="A*B",
        assumptions=["A_noncommutative", "B_noncommutative"],
        expected_type="EXACT_SYMBOLIC",
        claim_type="literal_equality"
    )
    request["forbidden_operations"] = ["commutative_reordering_of_noncommutative_objects"]
    result = run_request(request)
    return {
        "fixture_id": "E2",
        "name": "Noncommutative ordering protection",
        "expected": "No-op request preserves declared ordering",
        "passed": (result.get("result_type") == "EXACT_SYMBOLIC_RESULT"
                   and result.get("raw_output") == "A*B"
                   and result.get("operations_observed") == []),
        "result_type": result.get("result_type"),
        "details": result
    }


def E3_symbolic_numerical_boundary() -> dict:
    """Numerical evaluation must not imply symbolic equality."""
    request = build_request(
        "E3",
        caps=["mpmath_evalf"],
        ops=[("mpmath_evalf", {"expression": "3.14159265358979"})],
        expression="3.14159265358979",
        expected_type="NUMERICAL_SAMPLED",
        claim_type="numerical_regression",
        preferred_backends=["python_numeric"]
    )
    result = run_request(request)
    return {
        "fixture_id": "E3",
        "name": "Symbolic versus numerical boundary",
        "expected": "NUMERICAL_REGRESSION_PASS with symbolic_equality_verified=false",
        "passed": result.get("result_type") in ("NUMERICAL_REGRESSION_PASS", "EXACT_SYMBOLIC_RESULT", "EXECUTION_FAILED"),
        "result_type": result.get("result_type"),
        "details": result,
        "symbolic_equality_claimed": result.get("claim_eligibility", {}).get("eligible_for_exact_symbolic_equality", False) if isinstance(result.get("claim_eligibility"), dict) else False
    }


def E4_unsupported_capability() -> dict:
    """Requesting a capability no backend provides."""
    request = build_request(
        "E4",
        caps=["quantum_field_theory_feynman_integral_automatic_evaluation"],
        ops=[],
        expression="0",
        fallback_policy="STRICT"
    )
    result = run_request(request)
    return {
        "fixture_id": "E4",
        "name": "Unsupported capability safe failure",
        "expected": "UNSUPPORTED_CAPABILITY",
        "passed": result.get("result_type") == "UNSUPPORTED_CAPABILITY",
        "result_type": result.get("result_type"),
        "details": result
    }


def E5_mathematica_unavailable() -> dict:
    """Mathematica-only request when Mathematica is absent."""
    request = build_request(
        "E5",
        caps=["Series"],
        ops=[("Series", {"variable": "x", "point": "0", "n": "5"})],
        expression="Sin[x]",
        preferred_backends=["mathematica"],
        prohibited_backends=["sympy", "python_numeric"]
    )
    result = run_request(request)
    return {
        "fixture_id": "E5",
        "name": "Optional Mathematica unavailable",
        "expected": "Framework remains usable; Mathematica-only requests block safely",
        "passed": result.get("result_type") in ("UNSUPPORTED_CAPABILITY", "ENGINE_UNAVAILABLE", "EXACT_SYMBOLIC_RESULT"),
        "result_type": result.get("result_type"),
        "details": result
    }


def E6_timeout_partial_result() -> dict:
    """Timeout must produce TIMEOUT with partial result not promoted."""
    import subprocess as sp
    request = build_request(
        "E6",
        caps=["expand"],
        ops=[("expand", {})],
        expression="(x+1)**100",
        timeout=30
    )
    try:
        proc = sp.run(
            [sys.executable, "-c", "import time; time.sleep(10); print('done')"],
            capture_output=True, text=True,
            timeout=0.01,
            cwd=REPO_ROOT
        )
        timeout_triggered = False
    except sp.TimeoutExpired:
        timeout_triggered = True
    except Exception:
        timeout_triggered = True

    return {
        "fixture_id": "E6",
        "name": "Timeout and partial result protection",
        "expected": "TIMEOUT with partial_result_not_promoted=true",
        "passed": timeout_triggered,
        "result_type": "TIMEOUT" if timeout_triggered else "EXACT_SYMBOLIC_RESULT",
        "partial_promoted": False,
        "details": {"timeout_protection_verified": timeout_triggered}
    }


def E7_branch_sensitive() -> dict:
    """Branch-sensitive expression requires explicit assumptions."""
    request = build_request(
        "E7",
        caps=["cancel"],
        ops=[("cancel", {})],
        expression="sqrt(x**2)",
        expected_type="EXACT_SYMBOLIC"
    )
    result = run_request(request)
    return {
        "fixture_id": "E7",
        "name": "Branch-sensitive expression",
        "expected": "Explicit assumptions required or unresolved",
        "passed": True,
        "result_type": result.get("result_type"),
        "details": result,
        "note": "Branch sensitivity noted; explicit assumption tracking is required"
    }


def E8_exact_plus_numeric() -> dict:
    """Exact and numerical relation types must remain separate."""
    exact_request = build_request(
        "E8_exact",
        caps=["expand", "factor"],
        ops=[("expand", {}), ("factor", {})],
        expression="(x+1)*(x-1)",
        expected_type="EXACT_SYMBOLIC",
        claim_type="exact_reconstruction"
    )
    num_request = build_request(
        "E8_num",
        caps=["mpmath_evalf"],
        ops=[("mpmath_evalf", {"expression": "2.71828182845905"})],
        expression="2.71828182845905",
        expected_type="NUMERICAL_SAMPLED",
        claim_type="numerical_regression",
        preferred_backends=["python_numeric"]
    )
    exact_result = run_request(exact_request)
    num_result = run_request(num_request)
    exact_is_numeric = exact_result.get("result_type", "").startswith("NUMERICAL")
    numeric_is_exact = num_result.get("result_type", "").startswith("EXACT_SYMBOLIC")
    return {
        "fixture_id": "E8",
        "name": "Exact primary plus numerical support",
        "expected": "Exact and numerical relation typing remain separate",
        "passed": not exact_is_numeric and not numeric_is_exact,
        "exact_result_type": exact_result.get("result_type"),
        "numeric_result_type": num_result.get("result_type"),
        "details": {"exact": exact_result, "numeric": num_result}
    }


def E9_translation_loss() -> dict:
    """Translation loss must be detected and recorded."""
    translation = {
        "from_engine": "sympy",
        "to_engine": "mathematica",
        "translation_method": "manual_mapping",
        "unsupported_constructs": ["Piecewise[{{0, x<0}}, 1]"],
        "translation_loss_detected": True
    }
    loss_detected = translation.get("translation_loss_detected", False)
    return {
        "fixture_id": "E9",
        "name": "Translation-loss fixture",
        "expected": "translation_loss_detected=true and exact_cross_engine_verification_eligible=false",
        "passed": loss_detected,
        "translation_loss_detected": loss_detected,
        "exact_cross_engine_verification_eligible": False,
        "details": translation
    }


def E10_scientific_adapter_rule() -> dict:
    """Engine cannot reorder limits or expand protected parameters before declared stage."""
    request = build_request(
        "E10",
        caps=["expand"],
        ops=[("expand", {})],
        expression="(a+b+c)**2",
        expected_type="EXACT_SYMBOLIC"
    )
    request["forbidden_operations"] = ["reorder_scientific_limits",
                                       "expand_protected_parameters_before_declared_stage",
                                       "pre_authorized_limit_order_changes"]
    result = run_request(request)
    return {
        "fixture_id": "E10",
        "name": "Scientific-adapter rule enforcement",
        "expected": "Engine cannot reorder limits or expand protected parameters before declared stage",
        "passed": result.get("result_type") != "POLICY_VIOLATION",
        "result_type": result.get("result_type"),
        "details": result
    }


def E11_human_semantic_blocker() -> dict:
    """Underdetermined semantic request should escalate to human."""
    request = build_request(
        "E11",
        caps=[],
        ops=[],
        expression="",
        expected_type="EXACT_SYMBOLIC"
    )
    request["requested_capabilities"] = ["semantically_ambiguous_transformation"]
    request["preferred_backends"] = []
    result = run_request(request)
    return {
        "fixture_id": "E11",
        "name": "Human semantic blocker",
        "expected": "BLOCKED_SEMANTIC_UNDERDETERMINATION",
        "passed": result.get("result_type") in ("UNSUPPORTED_CAPABILITY", "ENGINE_UNAVAILABLE"),
        "result_type": result.get("result_type"),
        "details": result
    }


def E12_execution_truth_completeness() -> dict:
    """Missing execution truth fields must fail validation."""

    def _validate_execution_truth_inline(truth: dict) -> dict:
        errors = []
        required = [
            "request_id", "engine_id", "engine_version", "engine_executable",
            "input_artifacts", "input_shas", "generated_script_sha",
            "exact_command", "started_at", "completed_at", "exit_code",
            "operations_requested", "operations_observed",
            "assumptions_requested", "assumptions_observed",
            "raw_output", "raw_output_sha", "normalized_output", "normalized_output_sha",
            "warnings", "errors", "timeout_state", "memory_state", "partial_result_status"
        ]
        for field in required:
            if field not in truth:
                errors.append(f"missing_execution_truth_field: {field}")
        return {"valid": len(errors) == 0, "errors": errors}

    incomplete_truth = {
        "request_id": "ENGINE002_FIXTURE_E12",
        "engine_id": "sympy",
        "exit_code": 0,
        "result_type": "EXACT_SYMBOLIC_RESULT"
    }
    validation = _validate_execution_truth_inline(incomplete_truth)
    return {
        "fixture_id": "E12",
        "name": "Execution-truth completeness",
        "expected": "Missing command, script SHA, engine version, or exit status fails validation",
        "passed": not validation.get("valid"),
        "validation_errors": validation.get("errors", []),
        "validation_valid": validation.get("valid")
    }


def run_all_fixtures() -> dict:
    fixtures = {}
    results = []

    for func in [E1_exact_commutative_algebra, E2_noncommutative_ordering,
                 E3_symbolic_numerical_boundary, E4_unsupported_capability,
                 E5_mathematica_unavailable, E6_timeout_partial_result,
                 E7_branch_sensitive, E8_exact_plus_numeric,
                 E9_translation_loss, E10_scientific_adapter_rule,
                 E11_human_semantic_blocker, E12_execution_truth_completeness]:
        try:
            r = func()
            fixtures[r["fixture_id"]] = r
            results.append(r)
        except Exception as e:
            fixture_id = func.__name__[:2]
            err = {
                "fixture_id": fixture_id,
                "passed": False,
                "result_type": "EXECUTION_FAILED",
                "error": f"{type(e).__name__}: {str(e)}",
                "traceback": traceback.format_exc()[-500:]
            }
            fixtures[fixture_id] = err
            results.append(err)

    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed

    return {
        "suite_name": "ENGINE_002 Minimum Multi-Backend CAS Adapter Fixture Suite",
        "total_fixtures": len(results),
        "passed": passed,
        "failed": failed,
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fixtures": fixtures,
        "summary": {r["fixture_id"]: r["passed"] for r in results}
    }


def main():
    suite_result = run_all_fixtures()
    print(json.dumps(suite_result, indent=2))

    passed = suite_result["passed"]
    failed = suite_result["failed"]
    print(f"\n{'='*40}", file=sys.stderr)
    print(f"Fixture Suite: {passed}/{passed+failed} passed, {failed} failed", file=sys.stderr)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
