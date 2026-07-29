"""ORCH adapter for `propose_equation_candidates` (fusion Stage 2).

Thin proposer: emits UNVERIFIED candidate claims only. Never executes model code, never
scores, never self-verifies. Passes the request to the frozen-contract handler."""
from __future__ import annotations
from typing import Any
from loop_engine.orch_adapters.propose_equation_candidates import core as _core


class ProposeEquationCandidatesAdapter:
    capability = "propose_equation_candidates"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def run(self, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
        return _core.handle(request)
