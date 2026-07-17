#!/usr/bin/env python3
"""Gate-4 TEST-ONLY fault driver.

This is the ONLY place in the tree where a fault-injection capability exists, and it
lives under tests/ — never under scripts/ or loop_engine/. A normal caller of the
production CLI (`scripts/orch_controller.py geometric-basis-verify`) or of the
OrchRegistry has NO way to reach any of this.

It still exercises the REAL ORCH routing: it builds the production registry with the
production `build_registry()` and calls the production `route_geometric_basis_verify()`
seam (real capability lookup, real importlib adapter load, verbatim exit-code
propagation). The ONLY thing it does differently is monkeypatch the vendored verifier
functions IN ITS OWN PROCESS before routing, to manufacture an oracle disagreement or a
mid-write I/O failure that could not otherwise be produced from a valid input.

Usage:  echo <request-json> | python fault_driver.py <fault_mode>
Fault modes (test-process monkeypatch only):
  none                     no fault (control)
  numerical_counterexample force numerical oracle to report a reproducible counterexample
  symbolic_unsupported     force symbolic oracle to report capability-unsupported
  symbolic_disproved       force symbolic oracle to report a nonzero-residual disproof
  raise_on_write           raise an I/O error during the atomic artifact write
"""
import sys, json, os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import orch_controller as ctl                                   # production CLI module
from loop_engine.orch_adapters.geobasis_verify import core       # vendored verifier (real)


def _apply_fault(mode: str) -> None:
    """Monkeypatch the vendored verifier — confined to THIS process only."""
    if mode == "none":
        return
    if mode == "numerical_counterexample":
        core._numerical = lambda fam, params, tol: {
            "verdict": "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE",
            "evidence_level": 2, "evidence": {"relative_residual": 0.87, "injected": True}}
    elif mode == "symbolic_unsupported":
        core._symbolic = lambda fam, params: {
            "verdict": "SYMBOLIC_CAPABILITY_UNSUPPORTED", "evidence_level": 0,
            "canonical_residual": None, "certificate": None}
    elif mode == "symbolic_disproved":
        core._symbolic = lambda fam, params: {
            "verdict": "DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL", "evidence_level": 2,
            "canonical_residual": "nonzero", "certificate": None}
    elif mode == "raise_on_write":
        def _boom(*a, **k):
            raise OSError("injected mid-write I/O failure (atomicity probe)")
        core.os.replace = _boom
    else:
        print(json.dumps({"driver_error": "UNKNOWN_FAULT_MODE", "mode": mode}))
        sys.exit(3)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "none"
    _apply_fault(mode)
    registry = ctl.build_registry()                              # REAL production registry
    result, exit_code = ctl.route_geometric_basis_verify(registry, sys.stdin.read())  # REAL routing
    print(json.dumps(result))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
