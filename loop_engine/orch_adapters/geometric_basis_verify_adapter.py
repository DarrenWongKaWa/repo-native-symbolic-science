"""ORCH adapter for the narrow capability `geometric_basis_verify` (Gate 3.5).

Loaded by the REAL OrchRegistry via importlib. Self-contained: it wraps the vendored
geobasis verifier (loop_engine.orch_adapters.geobasis_verify.core) whose math is a
byte-copy of the verified prototype. Thin: no scope reinterpretation, no oracle
averaging, no evidence upgrade -- it passes the request to the frozen-contract handler
and returns (result, exit_code)."""
from __future__ import annotations
from typing import Any
from loop_engine.orch_adapters.geobasis_verify import core as _core


class GeometricBasisVerifyAdapter:
    capability = "geometric_basis_verify"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def run(self, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
        return _core.handle(request)
