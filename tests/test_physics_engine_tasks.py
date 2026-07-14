"""
Physics-task regression gate for the SymPy engine adapter.

These 10 tasks are realistic condensed-matter / QFT requests. They exist to pin
behaviour that a pure schema/fixture suite cannot see, because the adapter can
return a well-formed envelope that is scientifically wrong:

  * an unimplemented operation must FAIL CLOSED, never silently return the
    untransformed input labelled EXACT_SYMBOLIC_RESULT
  * the raw input expression must not be rewritten on ingestion
  * a forbidden operation (e.g. authorize_IBP) must be refused even when the
    caller does not restate the policy in its request
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "physics_tasks"))

from run_physics_tasks import call_engine, check  # noqa: E402
from tasks import TASKS  # noqa: E402


@pytest.mark.parametrize("task", TASKS, ids=[t["id"] for t in TASKS])
def test_physics_task(task):
    result = call_engine(task["request"])
    ok, reason = check(task, result)
    assert ok, f"{task['id']}: {reason}"
