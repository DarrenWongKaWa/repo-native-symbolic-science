"""ORCH adapter for `compactification_step` (C0 — minimal certified compactification loop).

Thin: validates and dispatches one loop step (certified parent + candidates ->
residual construction -> independent Python/SymPy verification -> chain nodes).
Calculations are Python-only; no Wolfram. The step never promotes canonical state
and never self-verifies a candidate without an independent residual adjudication.
"""
from __future__ import annotations
from typing import Any
from loop_engine.orch_adapters.compactification_loop import core as _core


class CompactificationLoopAdapter:
    capability = "compactification_step"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def run(self, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
        return _core.handle(request)
