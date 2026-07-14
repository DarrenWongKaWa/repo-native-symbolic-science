#!/usr/bin/env python3
"""
10 physics-background simulated test tasks for the Repo-Native Symbolic Science
SymPy engine adapter (engines/sympy/runner.py).

Each task is a realistic request a condensed-matter / QFT theorist would make,
expressed as an engine_request. Each has a machine-checkable expectation, so the
suite is a genuine pass/fail gate rather than a smoke test.

Run:  python3 physics_tasks/run_physics_tasks.py
"""

# Every task: id, physics context, engine request, and how to check the result.
#   expect_expr    -> raw_output must be symbolically equal to this sympy expression
#   expect_type    -> result_type must equal this
#   expect_unchanged -> raw_output must be symbolically equal to the input (immutability)
TASKS = [

    # 1. Drude conductivity, DC limit. sigma(w) = n e^2 tau / (m (1 - I w tau))
    #    Set w -> 0, must give the textbook DC Drude result n e^2 tau / m.
    {
        "id": "P01_drude_dc_limit",
        "physics": "Drude conductivity: take the DC limit omega -> 0.",
        "request": {
            "request_id": "P01",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "n*e**2*tau/(m*(1 - I*omega*tau))"},
            "requested_operation_sequence": [
                {"operation": "subs", "order": 1, "parameters": {"omega": "0"}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "n*e**2*tau/m",
    },

    # 2. Retarded Green function / Lorentzian: partial-fraction a two-pole propagator.
    {
        "id": "P02_two_pole_partial_fractions",
        "physics": "Two-pole propagator 1/((w-a)(w-b)): partial-fraction decomposition.",
        "request": {
            "request_id": "P02",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "1/((w - a)*(w - b))"},
            "requested_operation_sequence": [
                {"operation": "apart", "order": 1, "parameters": {"variable": "w"}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "1/((w - a)*(w - b))",  # must stay mathematically equal
    },

    # 3. Band velocity of a massive Dirac cone: E = sqrt(v^2 k^2 + m^2), v_k = dE/dk.
    {
        "id": "P03_dirac_band_velocity",
        "physics": "Massive Dirac cone E=sqrt(v^2 k^2 + m^2); band velocity dE/dk.",
        "request": {
            "request_id": "P03",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "sqrt(v**2*k**2 + m**2)"},
            "requested_operation_sequence": [
                {"operation": "diff", "order": 1, "parameters": {"variable": "k"}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "v**2*k/sqrt(v**2*k**2 + m**2)",
    },

    # 4. Effective mass: E = hbar^2 k^2/(2m), 1/m* ~ d^2E/dk^2 = hbar^2/m.
    #    Exercises an n-th derivative (n=2).
    {
        "id": "P04_effective_mass_second_derivative",
        "physics": "Parabolic band E=hbar^2 k^2/(2m); effective mass needs d^2E/dk^2.",
        "request": {
            "request_id": "P04",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "hbar**2*k**2/(2*m)"},
            "requested_operation_sequence": [
                {"operation": "diff", "order": 1, "parameters": {"variable": "k", "n": 2}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "hbar**2/m",
    },

    # 5. Sommerfeld / Fermi function: series expansion of 1/(exp(x)+1) about x=0.
    {
        "id": "P05_fermi_function_series",
        "physics": "Fermi function 1/(exp(x)+1): low-energy series expansion about x=0.",
        "request": {
            "request_id": "P05",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "1/(exp(x) + 1)"},
            "requested_operation_sequence": [
                {"operation": "series_with_explicit_variables", "order": 1,
                 "parameters": {"variable": "x", "point": 0, "n": 3}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        # leading behaviour 1/2 - x/4 + O(x^3)
        "expect_contains": ["1/2", "x/4"],
    },

    # 6. Relaxation-time integral: int_0^oo exp(-a t) dt = 1/a  (a > 0).
    {
        "id": "P06_relaxation_time_integral",
        "physics": "Boltzmann relaxation kernel: integrate exp(-a t) over t in [0, oo).",
        "request": {
            "request_id": "P06",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "exp(-a*t)"},
            "declared_assumptions": ["a_positive=True"],
            "requested_operation_sequence": [
                {"operation": "integrate_with_explicit_domain", "order": 1,
                 "parameters": {"variable": "t", "lower": "0", "upper": "oo"}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "1/a",
    },

    # 7. Hall conductivity tensor: [[s_xx, s_xy], [-s_xy, s_xx]]; det = s_xx^2 + s_xy^2.
    {
        "id": "P07_hall_tensor_determinant",
        "physics": "2x2 Hall conductivity tensor; determinant sets the resistivity inversion.",
        "request": {
            "request_id": "P07",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "Matrix([[s_xx, s_xy], [-s_xy, s_xx]])"},
            "requested_operation_sequence": [
                {"operation": "determinant", "order": 1}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "s_xx**2 + s_xy**2",
    },

    # 8. Exact-equality check: (x^2-1)/(x-1) - (x+1) must be exactly 0.
    #    This is the framework's own "exact symbolic claim" primitive.
    {
        "id": "P08_exact_equality_check",
        "physics": "Verify a claimed simplification exactly: (x^2-1)/(x-1) == x+1.",
        "request": {
            "request_id": "P08",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "(x**2 - 1)/(x - 1)"},
            "requested_operation_sequence": [
                {"operation": "exact_subtraction", "order": 1, "parameters": {"other": "x + 1"}}
            ],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_expr": "0",
    },

    # 9. IMMUTABILITY: ingest a raw expression, request NO operations.
    #    The framework's headline rule is that the raw expression is frozen.
    #    It must come back byte-for-byte equivalent, NOT auto-simplified.
    {
        "id": "P09_raw_expression_immutability",
        "physics": "Freeze a raw self-energy expression; request zero operations.",
        "request": {
            "request_id": "P09",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "(k**2 - kF**2)/(k - kF)"},
            "requested_operation_sequence": [],
        },
        "expect_type": "EXACT_SYMBOLIC_RESULT",
        "expect_unchanged": "(k**2 - kF**2)/(k - kF)",
    },

    # 10. POLICY: integration by parts must NOT be auto-authorized.
    #     README: "The framework does not automatically authorize IBP".
    #     The engine's own forbidden_operations.json lists authorize_IBP.
    #     A bare request (caller does not restate the policy) must still be refused.
    {
        "id": "P10_ibp_must_be_refused",
        "physics": "Ask the engine to authorize integration-by-parts on a boundary term.",
        "request": {
            "request_id": "P10",
            "engine_id": "sympy",
            "expression_scope": {"input_expression": "f(k)*Derivative(g(k), k)"},
            "requested_operation_sequence": [
                {"operation": "authorize_IBP", "order": 1}
            ],
        },
        "expect_type": "POLICY_VIOLATION",
    },
]
