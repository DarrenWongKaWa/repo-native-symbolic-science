"""B5 bounded multivariable gradient/base-point contract and attack matrix."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.orch_adapters._symbolic_safe_parse import sha, validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import core
from loop_engine.orch_adapters.symbolic_identity_verify import multivariable_t3 as B5
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as RC
from loop_engine.orch_adapters import symbolic_identity_verify_adapter as ADAPTER
from scripts.orch_controller import route_recheck_symbolic_certificate


REPO = Path(__file__).resolve().parents[1]
CONTROLLER = REPO / "scripts" / "orch_controller.py"
ALL_REAL = {"kind": "intersection", "terms": [
    {"kind": "real_line", "variable": "x"},
    {"kind": "real_line", "variable": "y"},
]}
OPEN_RECTANGLE = {"kind": "intersection", "terms": [
    {"kind": "interval", "variable": "x", "lower": "-1", "upper": "1",
     "lower_closed": False, "upper_closed": False},
    {"kind": "interval", "variable": "y", "lower": "-2", "upper": "2",
     "lower_closed": False, "upper_closed": False},
]}
POLYNOMIAL_CLAIM = {
    "lhs": "(x+y)**3",
    "rhs": "x**3+3*x**2*y+3*x*y**2+y**3",
    "symbols": ["x", "y"],
    "scope": "real_scalars",
    "assumptions": ["x real", "y real"],
    "domain": ALL_REAL,
}
TRIG_CLAIM = {
    "lhs": "sin(x+y)",
    "rhs": "sin(x)*cos(y)+cos(x)*sin(y)",
    "symbols": ["x", "y"],
    "scope": "real_scalars",
    "assumptions": ["x real", "y real"],
    "domain": ALL_REAL,
}


def _build(claim):
    return ADAPTER.build_b5_certificate_for_request({"claim": claim})


@pytest.fixture(scope="module")
def polynomial_certificate():
    certificate = _build(POLYNOMIAL_CLAIM)
    assert certificate is not None
    return certificate


@pytest.fixture(scope="module")
def trig_certificate():
    certificate = _build(TRIG_CLAIM)
    assert certificate is not None
    return certificate


def _outer_hash(certificate):
    body = copy.deepcopy(certificate)
    body.pop("artifact_hash", None)
    certificate["artifact_hash"] = sha(body)


def _reseal(certificate):
    base = certificate.get("base_point_certificate")
    if isinstance(base, dict):
        body = copy.deepcopy(base)
        body.pop("base_point_hash", None)
        base["base_point_hash"] = sha(body)
    for child in certificate.get("derivative_children", []):
        child["exact_certificate_hash"] = sha(child.get("exact_certificate"))
        child["second_engine_hash"] = sha(child.get("second_engine"))
        body = copy.deepcopy(child)
        body.pop("child_hash", None)
        child["child_hash"] = sha(body)
    bundle = certificate.get("domain_obligation_graph")
    if isinstance(bundle, dict):
        body = copy.deepcopy(bundle)
        body.pop("graph_hash", None)
        bundle["graph_hash"] = sha(body)
        certificate["domain_obligation_graph_hash"] = bundle["graph_hash"]
    certificate["coverage_hash"] = sha(certificate.get("coverage"))
    _outer_hash(certificate)


def _reseal_exact_envelope(envelope):
    envelope["context_binding_hash"] = sha(envelope.get("context_binding"))
    envelope["proof_hash"] = sha(envelope.get("proof"))
    body = copy.deepcopy(envelope)
    body.pop("artifact_hash", None)
    envelope["artifact_hash"] = sha(body)


def _assert_rejected(certificate, claim=POLYNOMIAL_CLAIM):
    assert B5.recheck(claim, certificate)["ok"] is False


def test_two_variable_polynomial_has_complete_exact_gradient(polynomial_certificate):
    certificate = polynomial_certificate
    assert certificate["kind"] == B5.CERTIFICATE_KIND
    assert [child["variable"] for child in certificate["derivative_children"]] == ["x", "y"]
    assert all(child["second_engine"]["verdict"] == "ZERO"
               for child in certificate["derivative_children"])
    assert certificate["coverage_complete"] is True
    assert all(
        item["proof_route"] ==
        "structural_globally_real_differentiable_expression_v1"
        for item in certificate["differentiability_obligations"])
    assert B5.recheck(POLYNOMIAL_CLAIM, certificate)["ok"]


def test_two_variable_transcendental_identity_uses_existing_t1_children(trig_certificate):
    assert all(child["exact_certificate"]["proof"]["kind"] == "trig_ideal_cofactor"
               for child in trig_certificate["derivative_children"])
    assert B5.recheck(TRIG_CLAIM, trig_certificate)["ok"]


def test_open_rectangle_selects_exact_interior_base_point():
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["domain"] = OPEN_RECTANGLE
    certificate = _build(claim)
    assert certificate is not None
    assert certificate["base_point_certificate"]["point"] == {"x": "0", "y": "0"}
    assert B5.recheck(claim, certificate)["ok"]


def test_full_json_round_trip_replays(polynomial_certificate):
    serialized = json.loads(json.dumps(polynomial_certificate, sort_keys=True))
    assert B5.recheck(POLYNOMIAL_CLAIM, serialized)["ok"]
    result, exit_code = route_recheck_symbolic_certificate(json.dumps({
        "claim": POLYNOMIAL_CLAIM,
        "certificate": serialized,
    }))
    assert exit_code == 0 and result["recheck_ok"] is True


def test_b5_cli_build_and_recheck_emit_one_json_object(
        tmp_path, polynomial_certificate):
    request = {
        "operation": "symbolic_identity_verify",
        "contract_version": "1.0",
        "verification_mode": "symbolic_only",
        "claim": POLYNOMIAL_CLAIM,
    }
    env = dict(os.environ)
    env["VIPER_OUTPUT_DIR"] = str(tmp_path / "runtime")
    env["PYTHONPATH"] = ""
    build = subprocess.run(
        [sys.executable, str(CONTROLLER), "symbolic-identity-verify"],
        input=json.dumps(request), capture_output=True, text=True,
        cwd=str(REPO), env=env, check=False)
    build_lines = build.stdout.strip().splitlines()
    assert build.returncode == 0 and len(build_lines) == 1
    built = json.loads(build_lines[0])
    assert built["symbolic_claim_verifier"]["certificate"]["kind"] == \
        B5.CERTIFICATE_KIND
    assert build.stderr == ""

    replay = subprocess.run(
        [sys.executable, str(CONTROLLER), "recheck-symbolic-certificate"],
        input=json.dumps({
            "claim": POLYNOMIAL_CLAIM,
            "certificate": polynomial_certificate,
        }),
        capture_output=True, text=True, cwd=str(REPO), env=env, check=False)
    replay_lines = replay.stdout.strip().splitlines()
    assert replay.returncode == 0 and len(replay_lines) == 1
    assert json.loads(replay_lines[0])["recheck_ok"] is True
    assert replay.stderr == ""


def test_additive_adapter_seam_uses_real_b3_route():
    certificate = ADAPTER.build_b5_certificate_for_request(
        {"claim": TRIG_CLAIM})
    assert certificate is not None
    assert B5.recheck(TRIG_CLAIM, certificate)["ok"]


@pytest.mark.parametrize("claim", [POLYNOMIAL_CLAIM, TRIG_CLAIM])
def test_real_adapter_issues_and_replays_b5_certificate(claim):
    result, exit_code = ADAPTER.SymbolicIdentityVerifyAdapter().run({"claim": claim})
    certificate = result["symbolic_claim_verifier"]["certificate"]
    assert exit_code == 0
    assert result["combined_evidence_level"] == 3
    assert certificate["kind"] == B5.CERTIFICATE_KIND
    assert B5.recheck(claim, certificate)["ok"]
    assert result["replay_artifact"]["sha256"]


def test_mutated_primary_module_runner_cannot_replace_pinned_b5_b3_route(monkeypatch):
    monkeypatch.setattr(core, "_second_opinion", lambda *args: {
        "status": "complete", "verdict": "UNKNOWN", "route": "injected"})
    certificate = ADAPTER.build_b5_certificate_for_request(
        {"claim": POLYNOMIAL_CLAIM})
    assert certificate is not None
    assert all(child["second_engine"]["route"] == "shipped_wolfram_engine"
               for child in certificate["derivative_children"])


def test_mutated_primary_module_validator_cannot_replace_pinned_b5_replay(
        monkeypatch, polynomial_certificate):
    monkeypatch.setattr(core, "_second_zero_confirmed", lambda *_: True)
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"][0]["second_engine"] = {"attacker": "forged"}
    _reseal(bad)
    _assert_rejected(bad)


def test_b5_promotion_does_not_depend_on_numerical_agreement(monkeypatch):
    result = {
        "combined_evidence_level": 0,
        "combined_verdict": "INCONCLUSIVE_INSUFFICIENT_EVIDENCE",
        "symbolic_claim_verifier": {"canonical_residual": "unresolved"},
        "numerical_geobasis_verifier": {"verdict": "INCONCLUSIVE"},
        "provenance": {"subresult_hashes": {}},
    }
    monkeypatch.setattr(core, "handle", lambda request: (copy.deepcopy(result), 0))
    upgraded, exit_code = ADAPTER.SymbolicIdentityVerifyAdapter().run({
        "claim": POLYNOMIAL_CLAIM,
        "policy_overrides": {"simplify_timeout_seconds": 7},
    })
    assert exit_code == 0
    assert upgraded["combined_evidence_level"] == 3
    assert upgraded["symbolic_claim_verifier"]["certificate"]["kind"] == B5.CERTIFICATE_KIND


@pytest.mark.parametrize("mutation", [
    lambda c: c["derivative_children"].pop(),
    lambda c: c["derivative_children"].append(copy.deepcopy(c["derivative_children"][0])),
    lambda c: c["derivative_children"].reverse(),
])
def test_missing_duplicate_or_swapped_children_fail_closed(polynomial_certificate, mutation):
    bad = copy.deepcopy(polynomial_certificate)
    mutation(bad)
    _reseal(bad)
    _assert_rejected(bad)


def test_swapped_declared_variable_order_fails_closed(polynomial_certificate):
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["symbols"] = ["y", "x"]
    assert B5.recheck(claim, polynomial_certificate)["ok"] is False


def test_foreign_child_from_another_parent_fails_closed(
        polynomial_certificate, trig_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"][0] = copy.deepcopy(
        trig_certificate["derivative_children"][0])
    _reseal(bad)
    _assert_rejected(bad)


@pytest.mark.parametrize("field,value", [
    ("variable", "y"),
    ("normalized_domain", {"schema": "foreign"}),
    ("assumptions", ["foreign"]),
    ("scope", "complex_scalars"),
])
def test_child_variable_domain_assumptions_and_scope_are_bound(
        polynomial_certificate, field, value):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"][0][field] = value
    _reseal(bad)
    _assert_rejected(bad)


@pytest.mark.parametrize("field", [
    "parent_claim_hash", "domain_hash", "variable_order_hash",
])
def test_parent_domain_and_variable_order_hash_forgery_fails_closed(
        polynomial_certificate, field):
    bad = copy.deepcopy(polynomial_certificate)
    bad[field] = "forged"
    _outer_hash(bad)
    _assert_rejected(bad)


def test_child_and_base_point_hash_forgery_fails_closed(polynomial_certificate):
    child_bad = copy.deepcopy(polynomial_certificate)
    child_bad["derivative_children"][0]["child_hash"] = "forged"
    _outer_hash(child_bad)
    _assert_rejected(child_bad)
    base_bad = copy.deepcopy(polynomial_certificate)
    base_bad["base_point_certificate"]["base_point_hash"] = "forged"
    _outer_hash(base_bad)
    _assert_rejected(base_bad)


def test_resealed_exact_child_proof_cannot_understate_required_grid(
        polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    exact = bad["derivative_children"][0]["exact_certificate"]
    exact["per_variable_values"] = [0]
    exact["grid_points"] = 1
    _reseal(bad)
    _assert_rejected(bad)


def test_coverage_bitmap_and_completeness_fields_cannot_promote_partial_gradient(
        polynomial_certificate):
    bitmap = copy.deepcopy(polynomial_certificate)
    bitmap["coverage_bitmap"] = [True, True]
    _outer_hash(bitmap)
    _assert_rejected(bitmap)
    incomplete = copy.deepcopy(polynomial_certificate)
    incomplete["derivative_children"].pop()
    incomplete["coverage_complete"] = True
    _reseal(incomplete)
    _assert_rejected(incomplete)


def test_directional_derivative_only_evidence_fails_closed(polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"] = [copy.deepcopy(bad["derivative_children"][0])]
    bad["derivative_children"][0]["variable"] = "x+y"
    bad["coverage"] = [{"variable": "x+y",
                        "derivative_claim_hash": bad["derivative_children"][0]["derivative_claim_hash"]}]
    bad["coverage_complete"] = True
    _reseal(bad)
    _assert_rejected(bad)


@pytest.mark.parametrize("mutation", [
    lambda evidence: evidence.update(verdict="UNKNOWN"),
    lambda evidence: evidence.update(verdict="NONZERO"),
    lambda evidence: evidence.update(status="malformed_output"),
    lambda evidence: evidence.update(route="external_override"),
    lambda evidence: evidence.update(engine_identity="wrong"),
    lambda evidence: evidence.update(implementation_version="wrong"),
    lambda evidence: evidence.update(parser_version="wrong"),
    lambda evidence: evidence.update(semantic_profile="wrong"),
    lambda evidence: evidence.update(configuration_hash="wrong"),
    lambda evidence: evidence.update(input_hash="wrong"),
    lambda evidence: evidence.update(process_exit_status=9),
    lambda evidence: evidence.update(exit_status=9),
    lambda evidence: evidence.update(stdout="False"),
    lambda evidence: evidence.update(process_stdout="forged"),
])
def test_unknown_nonzero_malformed_or_mismatched_b3_child_blocks_parent(
        polynomial_certificate, mutation):
    bad = copy.deepcopy(polynomial_certificate)
    mutation(bad["derivative_children"][0]["second_engine"])
    _reseal(bad)
    _assert_rejected(bad)


def test_empty_union_free_text_and_closed_domains_are_ineligible():
    domains = [
        {"kind": "intersection", "terms": [
            {"kind": "comparison", "left": "x", "operator": ">", "right": "1"},
            {"kind": "comparison", "left": "x", "operator": "<", "right": "0"},
            {"kind": "real_line", "variable": "y"},
        ]},
        {"kind": "union", "terms": []},
        "x and y are connected",
        {"kind": "intersection", "terms": [
            {"kind": "interval", "variable": "x", "lower": "0", "upper": "1",
             "lower_closed": True, "upper_closed": False},
            {"kind": "real_line", "variable": "y"},
        ]},
    ]
    for domain in domains:
        claim = copy.deepcopy(POLYNOMIAL_CLAIM)
        claim["domain"] = domain
        assert _build(claim) is None


@pytest.mark.parametrize("lhs", [
    "x/x + y",
    "sqrt(x)**2 + y",
])
def test_parent_source_definedness_cannot_be_erased_before_b4(lhs):
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = lhs
    claim["rhs"] = "1+y" if lhs.startswith("x/x") else "x+y"
    assert _build(claim) is None


def test_outside_or_boundary_base_point_fails_reconstruction(polynomial_certificate):
    for point in ({"x": "100", "y": "0"}, {"x": "-1", "y": "0"}):
        claim = copy.deepcopy(POLYNOMIAL_CLAIM)
        claim["domain"] = OPEN_RECTANGLE
        certificate = _build(claim)
        assert certificate is not None
        certificate["base_point_certificate"]["point"] = point
        _reseal(certificate)
        assert B5.recheck(claim, certificate)["ok"] is False


@pytest.mark.parametrize("lhs", [
    "sqrt(x**2+1)+y",
    "asin(x)+y",
    "log(x)+y",
])
def test_unsupported_radical_or_branch_differentiability_fails_closed(lhs):
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = lhs
    claim["rhs"] = lhs
    assert _build(claim) is None


def test_missing_differentiability_obligation_blocks_parent(polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["differentiability_obligations"].pop()
    _outer_hash(bad)
    _assert_rejected(bad)


def test_b3_evidence_from_another_domain_fails_closed(polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"][0]["normalized_domain"] = {
        "schema": "other-domain"}
    bad["derivative_children"][0]["second_engine"]["input_hash"] = "other-domain"
    _reseal(bad)
    _assert_rejected(bad)


def test_b4_graph_copied_from_another_claim_fails_closed(
        polynomial_certificate, trig_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["domain_obligation_graph"]["child_graphs"][0]["graph"] = copy.deepcopy(
        trig_certificate["domain_obligation_graph"]["child_graphs"][0]["graph"])
    _reseal(bad)
    _assert_rejected(bad)


def test_b4_stored_status_is_rebuilt_not_trusted(polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    graph = bad["domain_obligation_graph"]["child_graphs"][0]["graph"]
    graph["obligations"][0]["status"] = "UNRESOLVED"
    node_body = copy.deepcopy(graph["obligations"][0])
    node_body.pop("artifact_hash", None)
    graph["obligations"][0]["artifact_hash"] = sha(node_body)
    graph_body = copy.deepcopy(graph)
    graph_body.pop("graph_hash", None)
    graph["graph_hash"] = sha(graph_body)
    _reseal(bad)
    _assert_rejected(bad)


def test_child_list_reordered_after_creation_fails_even_when_rehashed(polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"] = list(reversed(bad["derivative_children"]))
    bad["coverage"] = list(reversed(bad["coverage"]))
    _reseal(bad)
    _assert_rejected(bad)


def test_legacy_b1_certificate_is_not_reinterpreted_as_b5():
    lhs = validate_and_parse("atan(x)", ["x"], real=True)
    rhs = validate_and_parse("asin(x/sqrt(1+x**2))", ["x"], real=True)
    legacy = RC.build_derivative_base_point_composite_certificate(
        lhs, rhs, ["x"], {"kind": "real_line", "variable": "x"})
    assert legacy["kind"] == "derivative_base_point_composite"
    assert B5.recheck(POLYNOMIAL_CLAIM, legacy)["ok"] is False


def test_b5_rejects_reserved_declared_symbol_shadowing():
    reserved_names = [
        "pi", "E", "I", "oo", "zoo", "nan", "Rational", "Integer", "Float",
        "Symbol", *core.POLICY["allowed_functions"],
    ]
    for reserved in sorted(set(reserved_names)):
        claim = copy.deepcopy(POLYNOMIAL_CLAIM)
        claim.update(
            lhs="x",
            rhs="x",
            symbols=[reserved, "x"],
            assumptions=[f"{reserved} real", "x real"],
            domain={"kind": "intersection", "terms": [
                {"kind": "real_line", "variable": reserved},
                {"kind": "real_line", "variable": "x"},
            ]},
        )
        assert _build(claim) is None, reserved

    false_if_pi_is_a_variable = copy.deepcopy(POLYNOMIAL_CLAIM)
    false_if_pi_is_a_variable.update(
        lhs="sin(pi)",
        rhs="0",
        symbols=["pi", "x"],
        assumptions=["pi real", "x real"],
        domain={"kind": "intersection", "terms": [
            {"kind": "real_line", "variable": "pi"},
            {"kind": "real_line", "variable": "x"},
        ]},
    )
    assert _build(false_if_pi_is_a_variable) is None


def test_b5_rejects_floor_division_source_erased_pole():
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = "x//x+y"
    claim["rhs"] = "1+y"
    assert _build(claim) is None


def test_b5_rejects_bitxor_source_operator():
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = "x^2+y"
    claim["rhs"] = "x**2+y"
    assert _build(claim) is None


def test_b5_rejects_rounded_float_base_equality():
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = "x+y+(0.1+0.000000000000000001)"
    claim["rhs"] = "x+y+0.1"
    assert _build(claim) is None


def test_b5_source_hardening_preserves_pre_b5_decimal_parser():
    lhs = validate_and_parse("x+0.5", ["x"], real=True)
    rhs = validate_and_parse("0.5+x", ["x"], real=True)
    assert lhs == rhs
    assert any(atom.__class__.__name__ == "Float" for atom in lhs.atoms())

    b5_claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    b5_claim["lhs"] = "x+y+0.5"
    b5_claim["rhs"] = "y+x+0.5"
    assert _build(b5_claim) is None


def test_b5_source_hardening_preserves_legacy_b1_certificate_replay():
    lhs = validate_and_parse("atan(x)", ["x"], real=True)
    rhs = validate_and_parse("asin(x/sqrt(1+x**2))", ["x"], real=True)
    legacy = RC.build_derivative_base_point_composite_certificate(
        lhs, rhs, ["x"], {"kind": "real_line", "variable": "x"})
    assert legacy is not None
    assert RC.recheck({
        "lhs": "atan(x)",
        "rhs": "asin(x/sqrt(1+x**2))",
        "symbols": ["x"],
    }, legacy)["ok"] is True


def test_b5_rejects_nonfinite_parent_and_base_values():
    for lhs, rhs in [
        ("oo+x", "oo"),
        ("-oo+x", "-oo"),
        ("oo-oo+x", "oo-oo"),
        ("1/0+x", "1/0"),
        ("I*x+y", "y"),
    ]:
        claim = copy.deepcopy(POLYNOMIAL_CLAIM)
        claim["lhs"] = lhs
        claim["rhs"] = rhs
        assert _build(claim) is None, (lhs, rhs)


def test_b5_accepts_exact_rational_source_arithmetic():
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = "x+y+1/10"
    claim["rhs"] = "y+x+1/10"
    certificate = _build(claim)
    assert certificate is not None
    assert certificate["base_point_certificate"]["lhs_value"] == "1/10"
    assert B5.recheck(claim, certificate)["ok"]


def test_b5_rechecker_rejects_fabricated_resealed_b3_transcript(
        polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    second = bad["derivative_children"][0]["second_engine"]
    second["process_stderr"] = "REVIEWER_SYNTHETIC_NOT_PROCESS_OUTPUT"
    _reseal(bad)
    _assert_rejected(bad)


def test_b5_rechecker_rejects_resealed_malformed_exact_child(
        polynomial_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    envelope = bad["derivative_children"][0]["exact_certificate"]
    proof = envelope["proof"]
    proof.update({
        "artifact_hash": "FORGED_INTERNAL_HASH",
        "total_degree": -999,
        "symbols": ["foreign"],
        "grid_points": -999,
        "all_residuals_exactly_zero": False,
        "recheck_procedure": "numerical guess",
        "attacker_extra": "accepted",
    })
    _reseal_exact_envelope(envelope)
    _reseal(bad)
    _assert_rejected(bad)


def test_b5_rejects_resealed_foreign_parent_child_with_identical_derivative(
        polynomial_certificate):
    shifted_claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    shifted_claim["lhs"] = "(x+y)**3+1"
    shifted_claim["rhs"] = "x**3+3*x**2*y+3*x*y**2+y**3+1"
    shifted_certificate = _build(shifted_claim)
    assert shifted_certificate is not None
    source = copy.deepcopy(polynomial_certificate["derivative_children"][0])
    target = shifted_certificate["derivative_children"][0]
    assert source["derivative_claim"] == target["derivative_claim"]
    source["parent_claim_hash"] = target["parent_claim_hash"]
    source["derivative_claim_hash"] = target["derivative_claim_hash"]
    bad = copy.deepcopy(shifted_certificate)
    bad["derivative_children"][0] = source
    _reseal(bad)
    assert B5.recheck(shifted_claim, bad)["ok"] is False


def test_b5_rechecker_fails_closed_when_fresh_b3_replay_is_unavailable(
        monkeypatch, polynomial_certificate):
    monkeypatch.setattr(B5, "_run_pinned_b3_payload", lambda *_: {
        "status": "process_failure",
        "route": "shipped_wolfram_engine",
    })
    _assert_rejected(polynomial_certificate)


def test_b5_rejects_extra_child_fields_and_incorrect_child_slots(
        polynomial_certificate):
    extra = copy.deepcopy(polynomial_certificate)
    extra["derivative_children"][0]["attacker_extra"] = "forged"
    _reseal(extra)
    _assert_rejected(extra)

    wrong_slot = copy.deepcopy(polynomial_certificate)
    wrong_slot["derivative_children"][0]["slot_index"] = 1
    _reseal(wrong_slot)
    _assert_rejected(wrong_slot)


def test_b5_rejects_copied_b3_evidence_from_another_claim(
        polynomial_certificate, trig_certificate):
    bad = copy.deepcopy(polynomial_certificate)
    bad["derivative_children"][0]["second_engine"] = copy.deepcopy(
        trig_certificate["derivative_children"][0]["second_engine"])
    _reseal(bad)
    _assert_rejected(bad)


def test_b5_child_context_binds_slot_parent_and_b3_input(polynomial_certificate):
    for slot_index, child in enumerate(polynomial_certificate["derivative_children"]):
        binding = child["context_binding"]
        assert set(binding) == B5._CONTEXT_FIELDS
        assert binding["slot_index"] == slot_index
        assert binding["derivative_variable"] == child["variable"]
        assert binding["parent_claim_hash"] == polynomial_certificate["parent_claim_hash"]
        assert child["context_binding_hash"] == sha(binding)
        assert child["exact_certificate"]["context_binding"] == binding
        assert child["exact_certificate"]["artifact_hash"]
        assert child["second_engine"]["input_hash"]


@pytest.mark.parametrize("source", [
    "x//y",
    "(x,y)",
    "sin(x,y)",
])
def test_b5_rejects_other_unsupported_source_ast_forms(source):
    claim = copy.deepcopy(POLYNOMIAL_CLAIM)
    claim["lhs"] = source
    claim["rhs"] = source
    assert _build(claim) is None
