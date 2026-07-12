#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== supp002r2 Public Baseline Regression Suite ==="
echo "Repo root: $REPO_ROOT"
echo ""

FAILURES=0

# --- Mutation tests ---
echo "--- Mutation Tests ---"
python3 "$REPO_ROOT/validators/supplement_validator.py" \
    "$REPO_ROOT/fixtures/supplement/two_sector_response" \
    --mutation-tests || {
    echo "FAIL: Mutation tests failed"
    FAILURES=$((FAILURES + 1))
}

# --- Self test ---
echo ""
echo "--- Self Test ---"
python3 "$REPO_ROOT/validators/supplement_validator.py" \
    "$REPO_ROOT/fixtures/supplement/two_sector_response" \
    --self-test || {
    echo "FAIL: Self test failed"
    FAILURES=$((FAILURES + 1))
}

# --- Full validation on supplement fixture ---
echo ""
echo "--- Full Validation on Fixture ---"
python3 "$REPO_ROOT/validators/supplement_validator.py" \
    "$REPO_ROOT/fixtures/supplement/two_sector_response" || {
    echo "FAIL: Full validation on fixture failed"
    FAILURES=$((FAILURES + 1))
}

# --- Pytest suite ---
echo ""
echo "--- Pytest Suite ---"
if command -v pytest &>/dev/null; then
    PYTEST="pytest"
elif command -v python3 &>/dev/null && python3 -m pytest --version &>/dev/null 2>&1; then
    PYTEST="python3 -m pytest"
else
    echo "WARN: pytest not found, skipping pytest suite"
    PYTEST=""
fi

if [ -n "$PYTEST" ]; then
    $PYTEST "$REPO_ROOT/tests/test_supp002r2_validator.py" -v || {
        echo "FAIL: Pytest suite failed"
        FAILURES=$((FAILURES + 1))
    }
fi

# --- Summary ---
echo ""
echo "========================================"
if [ "$FAILURES" -eq 0 ]; then
    echo "ALL REGRESSION CHECKS PASSED"
    exit 0
else
    echo "REGRESSION FAILURES: $FAILURES"
    exit 1
fi
