#!/usr/bin/env python3
"""Physics-stress end-to-end driver.

For each example, run its derive_claims.py (mechanical claim strings), submit
every claim through the REAL controller CLI (symbolic-identity-verify with the
pinned second engine), and evaluate against the honest verdict ladder:

  positive            -> certified (L3) or fail-closed pending-second-engine; DISPROVED fails
  positive_route_boundary -> same ladder; documents the long-string capability boundary
  mutation / negative_control -> must be DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE
                               (or a second-engine NONZERO/CONFLICT verdict)
  unsupported_grammar -> must fail closed (orch_error, nonzero exit)

Exit code 0 iff every expectation is met. Prints a summary table and a
one-line HARD_THEORETICAL_PHYSICS_EXAMPLES result.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import common  # noqa: E402

EXAMPLES = ["a_dirac_berry_curvature", "b_quantum_metric", "c_finite_gamma_resolvent", "d_gauge_equivalence"]


def load_claims() -> list[tuple[str, dict]]:
    rows = []
    for ex in EXAMPLES:
        script = HERE / ex / "derive_claims.py"
        p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                           cwd=str(REPO))
        if p.returncode != 0:
            print(f"[FAIL] {ex}/derive_claims.py exit {p.returncode}: {p.stderr[:400]}")
            sys.exit(1)
        for line in p.stdout.strip().splitlines():
            if line.strip():
                rows.append((ex, json.loads(line)))
    return rows


def main() -> int:
    rows = load_claims()
    failures = []
    print(f"{'example':<26} {'claim':<24} {'kind':<18} {'label':<42} detail")
    print("-" * 130)
    for ex, rec in rows:
        verdict = common.judge(common.envelope(rec["claim"], rec["claim"]["symbols"],
                                               rec["claim"]["scope"], rec["claim"]["assumptions"]))
        ok, label, detail = common.evaluate(rec["kind"], verdict)
        print(f"{ex:<26} {rec['id']:<24} {rec['kind']:<18} {label:<42} {detail[:60]}")
        if not ok:
            failures.append((ex, rec["id"], label, detail))
    print("-" * 130)
    total = len(rows)
    print(f"SUMMARY: {total - len(failures)}/{total} claims met their expectation")
    if failures:
        print("FAILURES:")
        for ex, cid, label, detail in failures:
            print(f"  - {ex}/{cid}: {label} :: {detail}")
        print("HARD_THEORETICAL_PHYSICS_EXAMPLES=FAIL")
        return 1
    print("HARD_THEORETICAL_PHYSICS_EXAMPLES=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
