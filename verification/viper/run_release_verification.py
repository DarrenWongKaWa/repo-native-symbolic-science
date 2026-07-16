#!/usr/bin/env python3
"""Viper — single release-verification entry point.

Runs the full release gate from the frozen bundle + the shipped repo, in order. Every
step must pass; any failure exits nonzero and NO success label is produced. Emits a
machine-readable report to stdout (and to verification/viper/release_report.json is
intentionally NOT written — the report is rebuildable by re-running this script).

    python verification/viper/run_release_verification.py

Steps: 1 record commit · 2 schema locks · 3 corpus locks · 4 evidence lock ·
5 runtime gold isolation · 6 Gate 1 contract · 7 Gate 2 conformance · 8 real-CLI Gate 3 ·
9 real-CLI Gate 4 · 10 full pytest · 11 secret/switch/alias scan · 12 emit report.
"""
import sys, os, json, hashlib, subprocess, tempfile, re
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
REPO = BUNDLE.parents[1]
PY = sys.executable
SHIPPED = [REPO / "scripts", REPO / "loop_engine"]
FROZEN_TASK_IDS = ["T00_correct", "T01_coeff_5to6", "T03_sign_m7to7", "T04_denom_3to2",
                   "T06_drop_term", "T07_dup_term", "T08_coeff_2to3"]

def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), **kw)

report = {}
FAIL = []
def step(key, ok, detail=""):
    report[key] = detail or ("PASS" if ok else "FAIL")
    if not ok: FAIL.append(key)
    print(f"[{'PASS' if ok else 'FAIL'}] {key}: {report[key]}")
    return ok


def main():
    # 1 — record commit ------------------------------------------------------------
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip() or "UNKNOWN"
    report["release_commit"] = head
    print(f"[..] release_commit: {head}")

    # 2 — schema locks -------------------------------------------------------------
    locks = json.loads((BUNDLE / "schemas/SCHEMA_LOCK.sha256.json").read_text())
    ok = all(sha_file(BUNDLE / "schemas" / n) == h for n, h in locks.items())
    step("schema_locks", ok, "MATCH" if ok else "MISMATCH")

    # 3 — corpus locks -------------------------------------------------------------
    clocks = json.loads((BUNDLE / "corpus/CORPUS_LOCK.sha256.json").read_text())
    ok = all(sha_file(BUNDLE / rel) == h for rel, h in clocks.items())
    step("corpus_locks", ok, "MATCH" if ok else "MISMATCH")

    # 4 — evidence lock ------------------------------------------------------------
    ev_lock = (BUNDLE / "evidence/EVIDENCE_LOCK.sha256").read_text().strip()
    ok = sha_file(BUNDLE / "evidence/frozen_evidence_package.json") == ev_lock
    step("evidence_lock", ok, "MATCH" if ok else "MISMATCH")

    # 5 — runtime gold isolation ---------------------------------------------------
    # No shipped module may reference the bundle, a frozen task ID, or the frozen files.
    needles = ["verification/viper", "verification.viper", "frozen_evidence_package",
               "families_results", "EVIDENCE_LOCK"] + FROZEN_TASK_IDS
    leaks = []
    for base in SHIPPED:
        for p in base.rglob("*.py"):
            txt = p.read_text(errors="ignore")
            for n in needles:
                if n in txt:
                    leaks.append(f"{p.relative_to(REPO)}::{n}")
    step("runtime_gold_isolation", not leaks, "PASS" if not leaks else f"LEAK {leaks[:3]}")

    # 6 — Gate 1 contract ----------------------------------------------------------
    r = run([PY, str(BUNDLE / "gate1_contract.py")])
    step("gate1", r.returncode == 0, "PASS" if r.returncode == 0 else f"FAIL {r.stdout[-120:]}")

    # 7 — Gate 2 conformance -------------------------------------------------------
    r = run([PY, str(BUNDLE / "gate2_conformance.py")])
    g2ok = r.returncode == 0 and "GATE_2_COMPLETE" in r.stdout
    step("gate2", g2ok, "PASS" if g2ok else f"FAIL {r.stdout[-160:]}")

    # 8 — real-CLI Gate 3 (CLI -> real ORCH -> production adapter -> vendored verifier)
    tmp = tempfile.mkdtemp(prefix="release_g3_")
    env = dict(os.environ); env["VIPER_OUTPUT_DIR"] = tmp; env["PYTHONPATH"] = ""
    req = json.dumps({"operation": "geometric_basis_verify", "contract_version": "1.0",
                      "verification_mode": "symbolic_and_numerical",
                      "claim": {"family": "F23", "params": {}, "scope": "two_band",
                                "assumptions": ["v=i eps A", "n!=m"],
                                "declared_basis": ["d_a_G_bc", "d_b_G_ac", "d_c_G_ab"]}})
    r = subprocess.run([PY, "scripts/orch_controller.py", "geometric-basis-verify"],
                       input=req, capture_output=True, text=True, cwd=str(REPO), env=env)
    try: verdict = json.loads(r.stdout).get("combined_verdict")
    except Exception: verdict = None
    g3ok = r.returncode == 0 and verdict == "VERIFIED_SYMBOLIC_IDENTITY"
    step("gate3", g3ok, "PASS" if g3ok else f"FAIL verdict={verdict} rc={r.returncode}")

    # 9 — real-CLI Gate 4 governance attacks ---------------------------------------
    r = subprocess.run([PY, "tests/gate4/gate4_attacks.py"], capture_output=True, text=True,
                       cwd=str(REPO), env=env)
    try:
        g4 = json.loads((REPO / "tests/gate4/gate4_report.json").read_text())
        rates = g4.get("rates", {})
        g4ok = r.returncode == 0 and all(v["rate"] == 1.0 for v in rates.values()) and not g4.get("secret_leak_detected")
    except Exception:
        g4ok = False; g4 = {}
    step("gate4", g4ok, "PASS" if g4ok else "FAIL")

    # 10 — full pytest -------------------------------------------------------------
    r = run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    m = re.search(r"(\d+) passed", r.stdout + r.stderr)
    passed = m.group(1) if m else "0"
    nofail = "failed" not in (r.stdout + r.stderr) and m is not None
    report["full_test_suite"] = f"{passed}/{passed}" if nofail else "FAIL"
    step("full_test_suite", nofail, report["full_test_suite"])

    # 11 — secret / fault-switch / generalization-alias scan -----------------------
    # tight enough to avoid CLI-flag false positives like "--task-registry-path"
    secret_re = re.compile(r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY")
    switches = ["--force-conflict", "--skip-safety", "--fake-symbolic-result", "VIPER_TEST_FAULT"]
    aliases = ["verify_physics", "prove_identity"]
    hits = []
    for base in SHIPPED:
        for p in base.rglob("*.py"):
            txt = p.read_text(errors="ignore")
            if secret_re.search(txt): hits.append(f"secret:{p.name}")
            for s in switches:
                if s in txt: hits.append(f"switch:{s}:{p.name}")
    # aliases must not appear as live registered operations
    ops = run([PY, "scripts/orch_controller.py", "list-operations"]).stdout
    try: op_list = json.loads(ops).get("operations", [])
    except Exception: op_list = []
    for a in aliases:
        if a in op_list: hits.append(f"alias:{a}")
    step("secret_scan", not hits, "CLEAN" if not hits else f"HITS {hits[:4]}")

    # 12 — verdict + final label ---------------------------------------------------
    report["verdict_reproducible"] = report.get("gate3") == "PASS"
    all_pass = not FAIL
    report["full_viper_repository_workflow"] = all_pass
    print("\n" + "=" * 70)
    print(json.dumps(report, indent=2))
    if not all_pass:
        print(f"\nRELEASE VERIFICATION FAILED: {FAIL}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
