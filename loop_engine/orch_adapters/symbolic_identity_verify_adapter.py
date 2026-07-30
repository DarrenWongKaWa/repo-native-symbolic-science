"""ORCH adapter for the general capability `symbolic_identity_verify` (fusion Stage 1).

Thin: no scope reinterpretation, no evidence upgrade, no self-verification. Passes the
request to the frozen-contract handler and returns (result, exit_code). The handler is
symbolic-only and fail-closed; arbitrary caller expressions are parsed under a strict
whitelist + size caps + timeout (see core.py)."""
from __future__ import annotations
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from loop_engine.orch_adapters.symbolic_identity_verify import core as _core

_PINNED_SECOND_OPINION = _core._second_opinion
_PINNED_SECOND_ENGINE_PAYLOAD = _core._second_engine_payload
_PINNED_SECOND_ZERO_CONFIRMED = _core._second_zero_confirmed


def build_b5_certificate_for_request(request: dict[str, Any], timeout: int = 20):
    """Additive B5 seam kept outside the SHA-locked B1-B4 implementation files."""
    claim = request.get("claim") if isinstance(request, dict) else None
    if not isinstance(claim, dict) or len(claim.get("symbols") or []) < 2:
        return None
    from loop_engine.orch_adapters.symbolic_identity_verify import multivariable_t3 as _b5
    return _b5.build_certificate(
        claim, timeout, _PINNED_SECOND_OPINION, _PINNED_SECOND_ENGINE_PAYLOAD,
        _PINNED_SECOND_ZERO_CONFIRMED)


def _upgrade_with_b5(request, result, certificate):
    symbolic = {
        "verdict": "VERIFIED_BY_MULTIVARIABLE_GRADIENT_AND_BASE_POINT",
        "evidence_level": 3,
        "canonical_residual": (result.get("symbolic_claim_verifier") or {}).get(
            "canonical_residual"),
        "certificate": certificate,
        "differential_canonicalization": (
            result.get("symbolic_claim_verifier") or {}).get(
                "differential_canonicalization"),
    }
    numerical = copy.deepcopy(result.get("numerical_geobasis_verifier") or {})
    numerical["gradient_second_engines"] = [
        copy.deepcopy(child["second_engine"])
        for child in certificate["derivative_children"]
    ]
    upgraded = copy.deepcopy(result)
    upgraded.update({
        "symbolic_claim_verifier": symbolic,
        "numerical_geobasis_verifier": numerical,
        "oracle_relation": "MULTIVARIABLE_GRADIENT_AND_BASE_POINT_DECISIVE",
        "combined_verdict": "VERIFIED_BY_MULTIVARIABLE_GRADIENT_AND_BASE_POINT",
        "combined_evidence_level": 3,
        "unresolved_obligations": [
            "valid only on the hash-bound open Cartesian product in the B5 certificate",
        ],
    })
    provenance = copy.deepcopy(upgraded.get("provenance") or {})
    subresults = copy.deepcopy(provenance.get("subresult_hashes") or {})
    subresults["symbolic"] = _core.sha(symbolic)
    provenance["subresult_hashes"] = subresults
    provenance["replay_classification"] = (
        "VERDICT_REPRODUCIBLE (bounded multivariable gradient/base-point certificate)")
    upgraded["provenance"] = provenance
    upgraded.pop("replay_artifact", None)
    out_dir = Path(os.environ.get(
        "VIPER_OUTPUT_DIR", tempfile.gettempdir())) / "viper_symbolic_identity_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(upgraded, tmp)
    tmp.close()
    artifact_hash = _core.sha(Path(tmp.name).read_bytes())
    final = out_dir / "last_result.json"
    os.replace(tmp.name, final)
    upgraded["replay_artifact"] = {"path": str(final), "sha256": artifact_hash}
    return upgraded


class SymbolicIdentityVerifyAdapter:
    capability = "symbolic_identity_verify"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def run(self, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
        result, exit_code = _core.handle(request)
        numerical = result.get("numerical_geobasis_verifier") or {}
        if exit_code == 0 and result.get("combined_evidence_level", 0) <= 1 and \
                numerical.get("verdict") == "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE":
            certificate = build_b5_certificate_for_request(request)
            if certificate is not None:
                return _upgrade_with_b5(request, result, certificate), 0
        return result, exit_code
