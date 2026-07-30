"""B5 bounded multivariable gradient/base-point contract and attack matrix."""
import copy
import json

import pytest

from loop_engine.orch_adapters._symbolic_safe_parse import sha, validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import core
from loop_engine.orch_adapters.symbolic_identity_verify import multivariable_t3 as B5
from loop_engine.orch_adapters.symbolic_identity_verify import recheck as RC
from loop_engine.orch_adapters import symbolic_identity_verify_adapter as ADAPTER
from scripts.orch_controller import route_recheck_symbolic_certificate


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


def _assert_rejected(certificate, claim=POLYNOMIAL_CLAIM):
    assert B5.recheck(claim, certificate)["ok"] is False


def test_two_variable_polynomial_has_complete_exact_gradient(polynomial_certificate):
    certificate = polynomial_certificate
    assert certificate["kind"] == B5.CERTIFICATE_KIND
    assert [child["variable"] for child in certificate["derivative_children"]] == ["x", "y"]
    assert all(child["second_engine"]["verdict"] == "ZERO"
               for child in certificate["derivative_children"])
    assert certificate["coverage_complete"] is True
    assert B5.recheck(POLYNOMIAL_CLAIM, certificate)["ok"]


def test_two_variable_transcendental_identity_uses_existing_t1_children(trig_certificate):
    assert all(child["exact_certificate"]["kind"] == "trig_ideal_cofactor"
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
