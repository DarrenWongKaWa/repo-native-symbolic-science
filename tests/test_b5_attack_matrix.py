"""Reconciled B5 attack boundary retained beside the merged candidate matrix.

The validated candidate folds the former ATK-B5 cases into
``test_b5_multivariable_t3.py``.  This file keeps the one legacy-surface attack
that is specific to the main-based adapter seam.
"""

from loop_engine.orch_adapters import symbolic_identity_verify_adapter as adapter


def test_univariate_requests_do_not_enter_multivariable_b5_route():
    request = {
        "claim": {
            "lhs": "x",
            "rhs": "x",
            "symbols": ["x"],
            "scope": "real_scalars",
            "assumptions": ["x real"],
            "domain": {"kind": "real_line", "variable": "x"},
        }
    }
    assert adapter.build_b5_certificate_for_request(request) is None
