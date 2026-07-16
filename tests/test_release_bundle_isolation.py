"""Runtime gold isolation — the frozen release-verification bundle must be unreachable
from the production runtime.

If the production verifier / ORCH adapter could import the bundle or look a task up in
the frozen corpus by task ID, gold answers would leak into the runtime and defeat the
independent-oracle design. These tests assert no shipped module references the bundle,
the frozen task IDs, or the frozen corpus/evidence files.
"""
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHIPPED = [REPO / "scripts", REPO / "loop_engine"]
BUNDLE = REPO / "verification" / "viper"
FROZEN_TASK_IDS = ["T00_correct", "T01_coeff_5to6", "T03_sign_m7to7", "T04_denom_3to2",
                   "T06_drop_term", "T07_dup_term", "T08_coeff_2to3"]
NEEDLES = ["verification/viper", "verification.viper", "frozen_evidence_package",
           "families_results", "EVIDENCE_LOCK"] + FROZEN_TASK_IDS


def test_bundle_exists_and_declares_isolation():
    readme = (BUNDLE / "README.md").read_text()
    assert "not accessible to the production verifier" in readme
    assert (BUNDLE / "manifest.json").exists()


def test_no_shipped_module_references_the_bundle():
    leaks = []
    for base in SHIPPED:
        for p in base.rglob("*.py"):
            txt = p.read_text(errors="ignore")
            for n in NEEDLES:
                if n in txt:
                    leaks.append(f"{p.relative_to(REPO)} :: {n}")
    assert not leaks, f"production runtime references the frozen bundle: {leaks}"


def test_production_verifier_cannot_import_bundle():
    """Importing the production adapter must not pull in anything under verification/."""
    code = (
        "import sys; import loop_engine.orch_adapters.geometric_basis_verify_adapter as a;"
        "mods=[m for m in sys.modules if 'verification' in m];"
        "print('LEAK' if mods else 'CLEAN')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO))
    assert "CLEAN" in r.stdout, f"production adapter imported bundle modules: {r.stdout} {r.stderr}"


def test_no_task_id_lookup_path_in_production():
    """No shipped code can resolve a frozen gold answer by task ID."""
    for base in SHIPPED:
        for p in base.rglob("*.py"):
            txt = p.read_text(errors="ignore")
            for tid in FROZEN_TASK_IDS:
                assert tid not in txt, f"frozen task id {tid} referenced in shipped {p.name}"
