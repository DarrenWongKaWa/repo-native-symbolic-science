#!/usr/bin/env python3
"""
Run the 10 physics tasks against engines/sympy/runner.py and check each result.

Checking is symbolic (sympy.simplify(a - b) == 0), not string comparison, so a
mathematically-correct answer in a different form still passes.

Exit 0 only if all 10 pass.
"""
import json
import subprocess
import sys
from pathlib import Path

import sympy as sp

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "engines" / "sympy" / "runner.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tasks import TASKS  # noqa: E402


def call_engine(request: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"result_type": "NO_JSON_FROM_ENGINE",
                "errors": [proc.stdout[-300:], proc.stderr[-300:]]}


def sym_equal(got: str, want: str) -> bool:
    """True if `got` and `want` are the same expression mathematically."""
    try:
        diff = sp.simplify(sp.sympify(got) - sp.sympify(want))
        return diff == 0
    except Exception:
        return False


def check(task: dict, result: dict):
    """Return (passed, reason)."""
    got_type = result.get("result_type")
    want_type = task.get("expect_type")

    if got_type != want_type:
        return False, f"result_type={got_type!r}, expected {want_type!r} " \
                      f"(errors: {str(result.get('errors'))[:120]})"

    # A policy refusal has no output to compare.
    if want_type == "POLICY_VIOLATION":
        return True, "correctly refused"

    out = result.get("raw_output", "")

    if "expect_unchanged" in task:
        if sym_equal(out, task["expect_unchanged"]):
            # equal is not enough: it must be *unchanged in form*
            if sp.sympify(out) == sp.sympify(task["expect_unchanged"]):
                return True, f"raw expression preserved: {out}"
            return False, (f"raw expression was MUTATED on ingestion: "
                           f"got {out!r}, expected the frozen input "
                           f"{task['expect_unchanged']!r}")
        return False, f"got {out!r}, expected {task['expect_unchanged']!r}"

    if "expect_expr" in task:
        if sym_equal(out, task["expect_expr"]):
            return True, f"{out}"
        return False, f"got {out!r}, expected (symbolically) {task['expect_expr']!r}"

    if "expect_contains" in task:
        missing = [s for s in task["expect_contains"] if s not in out]
        if not missing:
            return True, f"{out[:60]}"
        return False, f"got {out!r}, missing {missing}"

    return False, "task has no expectation"


def main():
    print("=" * 74)
    print("10 PHYSICS TASKS  ->  engines/sympy/runner.py")
    print("=" * 74)
    npass = 0
    failures = []
    for t in TASKS:
        result = call_engine(t["request"])
        ok, reason = check(t, result)
        npass += ok
        mark = "PASS" if ok else "FAIL"
        print(f"\n[{mark}] {t['id']}")
        print(f"       {t['physics']}")
        print(f"       -> {reason}")
        if not ok:
            failures.append(t["id"])

    print("\n" + "=" * 74)
    print(f"RESULT: {npass}/{len(TASKS)} passed")
    if failures:
        print("FAILED: " + ", ".join(failures))
    print("=" * 74)
    return 0 if npass == len(TASKS) else 1


if __name__ == "__main__":
    sys.exit(main())
