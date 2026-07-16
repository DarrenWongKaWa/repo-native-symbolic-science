"""Gate 4 — orchestration governance attacks, as a product test.

Runs the full attack harness through the REAL ORCH path and asserts:
  1. all five governance rates are perfect and no secret leaked;
  2. the PRODUCTION registry / CLI / shipped source expose NO fault-injection
     capability — the fault seam exists only under tests/ (fault_driver.py).
"""
import sys, os, json, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
GATE4 = REPO / "tests" / "gate4"


def _run_harness(tmp_path):
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = str(tmp_path)
    p = subprocess.run([sys.executable, str(GATE4 / "gate4_attacks.py")],
                       capture_output=True, text=True, env=env, cwd=str(REPO))
    return p


def test_gate4_all_rates_perfect(tmp_path):
    p = _run_harness(tmp_path)
    assert p.returncode == 0, f"harness failed:\n{p.stdout}\n{p.stderr}"
    report = json.loads((GATE4 / "gate4_report.json").read_text())
    assert report["status"] == "GATE_4_COMPLETE"
    assert report["secret_leak_detected"] is False
    for name, r in report["rates"].items():
        assert r["rate"] == 1.0, f"{name} = {r}"
    # every attack recorded the full forensic row
    required = {"attack_id", "attack_group", "input_sha256", "expected_verdict",
                "actual_verdict", "exit_code", "artifact_published", "partial_output_detected",
                "scope_preserved", "subresults_preserved", "provenance_sha256",
                "stdout_secret_scan", "stderr_secret_scan", "replay_status"}
    assert len(report["attacks"]) == 12
    for a in report["attacks"]:
        assert required <= set(a.keys()), f"missing forensic fields in {a['attack_id']}"


def test_no_partial_success_on_any_blocked_attack(tmp_path):
    _run_harness(tmp_path)
    report = json.loads((GATE4 / "gate4_report.json").read_text())
    for a in report["attacks"]:
        assert a["partial_output_detected"] is False, a["attack_id"]


def test_production_registry_has_no_fault_adapter():
    """The real registry the CLI builds must not carry any fault-injection adapter."""
    import orch_controller as ctl
    registry = ctl.build_registry()
    ops = list(registry._adapters.keys())
    assert "geometric_basis_verify" in ops
    banned = ("fault", "force", "fake", "skip_safety", "bypass", "inject")
    for op in ops:
        spec = registry._adapters[op]
        blob = (op + json.dumps(spec)).lower()
        assert not any(b in blob for b in banned), f"fault-ish capability in production registry: {op}"


def test_production_cli_lists_no_fault_operation():
    p = subprocess.run([sys.executable, str(REPO / "scripts" / "orch_controller.py"),
                        "list-operations"], capture_output=True, text=True, cwd=str(REPO))
    ops = json.loads(p.stdout)["operations"]
    for op in ops:
        assert not any(b in op.lower() for b in ("fault", "force", "fake", "inject"))


def test_shipped_source_has_no_fault_switch():
    """No fault-injection switch/env-var may live in shipped (non-test) code."""
    banned = ["--force-conflict", "--skip-safety", "--fake-symbolic-result",
              "VIPER_TEST_FAULT", "fault_driver", "_apply_fault"]
    for base in (REPO / "scripts", REPO / "loop_engine"):
        for path in base.rglob("*.py"):
            text = path.read_text()
            for token in banned:
                assert token not in text, f"fault token {token!r} leaked into shipped file {path}"
