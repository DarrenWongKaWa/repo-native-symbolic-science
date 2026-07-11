#!/usr/bin/env python3
"""
Capability resolver for ENGINE_002.
Routes computation requests to backends based on declared capabilities,
availability evidence, and policy constraints.
"""
import json
import sys
import os
import hashlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def resolve_capabilities(request: dict) -> dict:
    """
    Given a computation request with declared capabilities, resolve the best
    available backend(s). Returns an engine_selection artifact.
    """
    requested_caps = set(request.get("requested_capabilities", []))
    preferred = request.get("preferred_backends", [])
    prohibited = request.get("prohibited_backends", [])
    fallback_policy = request.get("fallback_policy", "STRICT")
    output_type = request.get("expected_output_type", "EXACT_SYMBOLIC")
    claim_type = request.get("requested_claim_type", "literal_equality")

    registry_path = os.path.join(REPO_ROOT, "engines", "engine_registry.json")
    try:
        registry = load_json(registry_path)
    except Exception:
        registry = {"registered_engines": []}

    candidate_backends = []
    for entry in registry.get("registered_engines", []):
        engine_id = entry["engine_id"]
        if engine_id in prohibited:
            continue

        cap_path = os.path.join(REPO_ROOT, "engines", engine_id, "capability.json")
        try:
            cap = load_json(cap_path)
        except Exception:
            cap = {}

        availability = cap.get("availability_status", "NOT_CONFIGURED")
        supported_ops = set(cap.get("supported_operations", []))
        unsupported_ops = set(cap.get("unsupported_operations", []))

        matched = requested_caps.intersection(supported_ops)
        unmatched = requested_caps - supported_ops

        candidate_backends.append({
            "engine_id": engine_id,
            "engine_type": entry.get("engine_type", "UNKNOWN"),
            "matched_capabilities": sorted(matched),
            "unmatched_capabilities": sorted(unmatched),
            "available": availability == "AVAILABLE",
            "optional": entry.get("optional", False)
        })

    all_matched = any(
        len(c["unmatched_capabilities"]) == 0 and c["available"]
        for c in candidate_backends
    )

    exact_candidates = [c for c in candidate_backends
                        if c["engine_type"] == "EXACT_SYMBOLIC" and c["available"]]
    numeric_candidates = [c for c in candidate_backends
                          if c["engine_type"] in ("NUMERICAL",) and c["available"]]

    primary = None
    supporting = []
    verification = []
    gaps = []
    human_decision = False

    if output_type == "EXACT_SYMBOLIC":
        if exact_candidates:
            preferred_exact = [c for c in exact_candidates if c["engine_id"] in preferred]
            primary = (preferred_exact[0] if preferred_exact else exact_candidates[0])["engine_id"]
            for c in numeric_candidates:
                supporting.append(c["engine_id"])
            for c in exact_candidates:
                if c["engine_id"] != primary:
                    verification.append(c["engine_id"])
    elif output_type == "NUMERICAL_SAMPLED":
        if numeric_candidates:
            primary = numeric_candidates[0]["engine_id"]
            for c in numeric_candidates:
                if c["engine_id"] != primary:
                    verification.append(c["engine_id"])
    elif output_type == "ANY":
        available = [c for c in candidate_backends if c["available"]]
        if available:
            primary = available[0]["engine_id"]

    if primary is None:
        if fallback_policy == "ALLOW_ANY_AVAILABLE":
            available = [c for c in candidate_backends if c["available"]]
            if available:
                primary = available[0]["engine_id"]
                gaps = sorted(requested_caps - set(available[0].get("matched_capabilities", [])))
            else:
                gaps = sorted(requested_caps)
        elif fallback_policy == "ALLOW_NUMERICAL_FALLBACK" and output_type == "EXACT_SYMBOLIC":
            primary = None
            gaps = sorted(requested_caps)
            human_decision = True
        else:
            gaps = sorted(requested_caps)
            human_decision = True

    return {
        "candidate_backends": [
            {
                "engine_id": c["engine_id"],
                "matched_capabilities": c["matched_capabilities"],
                "unmatched_capabilities": c["unmatched_capabilities"],
                "available": c["available"]
            }
            for c in candidate_backends
        ],
        "capability_match": {
            "all_capabilities_matched": all_matched,
            "exact_match_available": bool(exact_candidates),
            "numeric_match_available": bool(numeric_candidates)
        },
        "capability_gaps": gaps,
        "selected_primary_backend": primary,
        "selected_supporting_backends": supporting,
        "selected_verification_backends": verification,
        "selection_reason": f"Resolved {len(requested_caps)} capabilities: "
                            f"primary={primary}, supporting={supporting}, verify={verification}",
        "license_constraints": [
            "mathematica_optional_license_must_not_block_generic_ci"
        ] if "mathematica" in str([primary] + supporting + verification) else [],
        "availability_evidence": {
            "sympy": "AVAILABLE" if any(c["engine_id"] == "sympy" and c["available"] for c in exact_candidates) else "UNAVAILABLE",
            "python_numeric": "AVAILABLE" if any(c["engine_id"] == "python_numeric" and c["available"] for c in numeric_candidates) else "UNAVAILABLE",
            "mathematica": "NOT_CONFIGURED"
        },
        "fallback_path": "UNSUPPORTED_CAPABILITY" if primary is None and gaps else "resolved",
        "human_decision_required": human_decision
    }


def main():
    if len(sys.argv) > 1:
        request = json.loads(sys.argv[1])
    else:
        request = json.load(sys.stdin)
    result = resolve_capabilities(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
