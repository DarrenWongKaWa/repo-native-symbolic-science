"""ORCH adapter for the general capability `symbolic_identity_verify` (fusion Stage 1).

Thin: no scope reinterpretation, no evidence upgrade, no self-verification. Passes the
request to the frozen-contract handler and returns (result, exit_code). The handler is
symbolic-only and fail-closed; arbitrary caller expressions are parsed under a strict
whitelist + size caps + timeout (see core.py)."""
from __future__ import annotations
from typing import Any
from loop_engine.orch_adapters.symbolic_identity_verify import core as _core


class SymbolicIdentityVerifyAdapter:
    capability = "symbolic_identity_verify"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def run(self, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
        return _core.handle(request)
