"""Pytest wrapper for the theoretical-physics stress examples.

Runs examples/physics_stress/run_all.py end to end (real CLI judge + pinned
second engine). Positive claims must certify or stay fail-closed; every
wrong-physics mutation must be refuted with reproducible nonzero evidence;
unsupported grammar must fail closed.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_physics_stress_end_to_end():
    p = subprocess.run([sys.executable, str(REPO / "examples" / "physics_stress" / "run_all.py")],
                       capture_output=True, text=True, cwd=str(REPO), timeout=3600)
    assert p.returncode == 0, f"physics stress run failed:\n{p.stdout}\n{p.stderr}"
    assert "HARD_THEORETICAL_PHYSICS_EXAMPLES=PASS" in p.stdout
