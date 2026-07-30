"""ATK-B4-001..030 recovery matrix: every failure remains explicit and replayable."""
import copy

import pytest

from loop_engine.orch_adapters._symbolic_safe_parse import sha
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as B2
from loop_engine.orch_adapters.symbolic_identity_verify import core
from loop_engine.orch_adapters.symbolic_identity_verify import domain_obligations as B4
from tests.test_b2_connected_subdomains import _claim as b2_claim, _second_for


def _claim(lhs, rhs="0", symbols=None):
    return {"lhs": lhs, "rhs": rhs, "symbols": symbols or ["x"], "scope": "real_scalars"}


def _real_line():
    return {"kind": "real_line", "variable": "x"}


def _graph(lhs, domain=None):
    claim = _claim(lhs)
    return claim, B4.build_obligation_graph(claim, domain or _real_line(), ["x real"])


def _rehash(graph):
    graph["graph_hash"] = sha({k: v for k, v in graph.items() if k != "graph_hash"})


def _assert_blocks(claim, domain, graph, code=None):
    result = B4.recheck_obligation_graph(claim, domain, ["x real"], graph)
    assert result["ok"] is False
    if code is not None:
        assert result["detail"] == code


def test_atk_b4_001_to_005_cancellation_roots_and_logs_remain_visible():
    for expression, kind in (("(x**2-1)/(x-1)", "DENOMINATOR_NONZERO"), ("x/x", "DENOMINATOR_NONZERO"),
                             ("sqrt(x)*sqrt(x)", "EVEN_ROOT_RADICAND_NONNEGATIVE"),
                             ("sqrt(x**2)", "EVEN_ROOT_RADICAND_NONNEGATIVE"),
                             ("log(x)", "LOG_ARGUMENT_POSITIVE")):
        claim, graph = _graph(expression)
        assert any(node["kind"] == kind for node in graph["obligations"])
        _assert_blocks(claim, _real_line(), graph, B4.FAILURE["unresolved"])


def test_atk_b4_006_to_008_poles_boundary_and_nested_sources_are_not_erased():
    for expression, kind in (("tan(x)", "TAN_COS_NONZERO"),
                             ("asin(1)", "ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE"),
                             ("log(sqrt(x))", "EVEN_ROOT_RADICAND_NONNEGATIVE")):
        claim, graph = _graph(expression)
        assert any(node["kind"] == kind for node in graph["obligations"])
        _assert_blocks(claim, _real_line(), graph, B4.FAILURE["unresolved"])


def test_atk_b4_009_to_012_transform_connected_empty_and_contradictory_fail_closed():
    claim = b2_claim(); context = B2.prepare_log_product_claim(claim)
    transformed = B2.build_positive_exp_transformation(
        context["parent_claim_hash"], context["body"], "x", "u",
        {"lhs": "log(exp(u)*y)", "rhs": "log(exp(u))+log(y)", "symbols": ["u", "y"], "scope": "real_scalars"})
    claim["subdomain"]["transformation"] = transformed
    graph = B4.build_obligation_graph(claim, claim["subdomain"], claim["assumptions"])
    assert {"TRANSFORMATION_IMAGE", "TRANSFORMATION_INVERSE", "TRANSFORMATION_INJECTIVITY"} <= {n["kind"] for n in graph["obligations"]}
    bad_domain = {"kind": "intersection", "terms": [
        {"kind": "comparison", "left": "x", "operator": ">", "right": "1"},
        {"kind": "comparison", "left": "x", "operator": "<", "right": "0"}]}
    with pytest.raises(B4.ObligationError) as empty:
        B4.build_obligation_graph(_claim("x/x"), bad_domain)
    assert empty.value.code == B4.FAILURE["empty"]
    with pytest.raises(B4.ObligationError):
        B4.build_obligation_graph(_claim("x/x"), "x != 0")


def test_atk_b4_013_to_015_cross_claim_hash_provenance_and_graph_hash_tampering():
    claim, graph = _graph("x/x")
    copied = copy.deepcopy(graph); copied["claim_hash"] = "copied"; _rehash(copied)
    _assert_blocks(claim, _real_line(), copied, B4.FAILURE["source"])
    bad_hash = copy.deepcopy(graph); bad_hash["graph_hash"] = "tampered"
    _assert_blocks(claim, _real_line(), bad_hash, B4.FAILURE["graph_hash"])
    moved = copy.deepcopy(graph); moved["obligations"][2]["source_node_path"] = "rhs.left"; _rehash(moved)
    _assert_blocks(claim, _real_line(), moved, B4.FAILURE["source"])


def test_atk_b4_016_to_017_unsupported_cot_is_explicit_and_cannot_be_removed():
    claim, graph = _graph("cot(x)")
    cot = next(n for n in graph["obligations"] if n["kind"] == "COT_SIN_NONZERO")
    assert cot["status"] == "UNSUPPORTED" and cot["failure_code"] == B4.FAILURE["unsupported"]
    deleted = copy.deepcopy(graph)
    deleted["obligations"] = [n for n in deleted["obligations"] if n["obligation_id"] != cot["obligation_id"]]
    deleted["obligations"][-1]["dependencies"] = [n["obligation_id"] for n in deleted["obligations"][:-1]]
    _rehash(deleted)
    _assert_blocks(claim, _real_line(), deleted, B4.FAILURE["source"])


def test_atk_b4_018_to_020_subdomain_scope_numeric_claims_and_b3_domain_binding():
    claim = b2_claim(); context = B2.prepare_log_product_claim(claim); second = _second_for(context, claim)
    core._second_opinion = lambda *args: second
    result, rc = core._connected_subdomain_result({"claim": claim}, claim, 1)
    assert rc == 0 and result["combined_verdict"] == "VERIFIED_ON_EXPLICIT_SUBDOMAIN"
    cert = result["symbolic_claim_verifier"]["certificate"]
    assert B2.recheck(claim, cert)["ok"]
    bad = copy.deepcopy(cert); bad["second_engine_confirmation"]["input_hash"] = "different-domain"
    bad["artifact_hash"] = sha({k: v for k, v in bad.items() if k != "artifact_hash"})
    assert B2.recheck(claim, bad)["ok"] is False


def test_atk_b4_021_to_023_cycles_missing_and_fake_dependencies_are_rejected():
    claim, graph = _graph("sqrt(x)")
    target = next(n for n in graph["obligations"] if n["kind"] == "EVEN_ROOT_RADICAND_NONNEGATIVE")
    for dependencies in ([target["obligation_id"]], [], [next(n for n in graph["obligations"] if n["kind"] == "CONNECTED_DOMAIN")["obligation_id"]]):
        bad = copy.deepcopy(graph)
        next(n for n in bad["obligations"] if n["obligation_id"] == target["obligation_id"])["dependencies"] = dependencies
        _rehash(bad)
        _assert_blocks(claim, _real_line(), bad, B4.FAILURE["cycle"] if dependencies == [target["obligation_id"]] else B4.FAILURE["source"])


@pytest.mark.parametrize("expression, expected_kind, expected_status", [
    ("sqrt(x)", "EVEN_ROOT_RADICAND_NONNEGATIVE", "UNRESOLVED"),
    ("x**(1/2)", "FRACTIONAL_POWER_BASE_CONDITION", "UNRESOLVED"),
    ("x**(-1/2)", "FRACTIONAL_POWER_BASE_CONDITION", "UNRESOLVED"),
    ("x**(2/3)", "FRACTIONAL_POWER_BASE_CONDITION", "PROVED"),
    ("x**(-2/3)", "FRACTIONAL_POWER_BASE_CONDITION", "UNRESOLVED"),
    ("x**0", "RATIONAL_POWER_BASE_CONDITION", "PROVED"),
    ("x**-2", "RATIONAL_POWER_BASE_CONDITION", "UNRESOLVED"),
    ("x**a", "FRACTIONAL_POWER_BASE_CONDITION", "UNSUPPORTED"),
    ("x**0.5", "FRACTIONAL_POWER_BASE_CONDITION", "UNSUPPORTED"),
])
def test_atk_b4_024_to_025_fractional_power_classification(expression, expected_kind, expected_status):
    symbols = ["x", "a"] if expression == "x**a" else ["x"]
    claim = _claim(expression, symbols=symbols)
    graph = B4.build_obligation_graph(claim, _real_line())
    node = next(n for n in graph["obligations"] if n["kind"] == expected_kind)
    assert node["status"] == expected_status
    if expected_status == "UNSUPPORTED":
        assert node["failure_code"] == B4.FAILURE["unsupported"]


def test_atk_b4_026_to_027_open_asin_and_b1_intermediates_are_independent_load_bearing_nodes():
    claim = _claim("atan(x)", "asin(x/sqrt(1+x**2))")
    graph = B4.build_obligation_graph(claim, _real_line(), ["x real"])
    kinds = {n["kind"] for n in graph["obligations"]}
    assert {"ASIN_ARGUMENT_IN_CLOSED_RANGE", "ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE", "DIFFERENTIABILITY", "BASE_POINT_MEMBERSHIP"} <= kinds
    open_node = next(n for n in graph["obligations"] if n["kind"] == "ASIN_ARGUMENT_IN_OPEN_RANGE_FOR_DERIVATIVE")
    assert open_node["dependencies"] and open_node["status"] == "PROVED"
    bad = copy.deepcopy(graph); bad["obligations"] = [n for n in bad["obligations"] if n["kind"] != "DIFFERENTIABILITY"]
    bad["obligations"][-1]["dependencies"] = [n["obligation_id"] for n in bad["obligations"][:-1]]; _rehash(bad)
    _assert_blocks(claim, _real_line(), bad, B4.FAILURE["source"])


def test_atk_b4_028_to_030_new_b2_binds_graph_legacy_is_legacy_and_inventory_cannot_lie():
    claim = b2_claim(); context = B2.prepare_log_product_claim(claim); second = _second_for(context, claim)
    core._second_opinion = lambda *args: second
    result, _ = core._connected_subdomain_result({"claim": claim}, claim, 1)
    fresh = result["symbolic_claim_verifier"]["certificate"]
    assert {"domain_obligation_graph", "domain_obligation_graph_hash", "domain_obligation_graph_version", "domain_obligation_summary"} <= set(fresh)
    legacy = B2.build_certificate(context, second)
    assert B2.recheck(claim, legacy)["ok"]
    tampered = copy.deepcopy(fresh); tampered["domain_obligation_graph"]["extraction_inventory"]["coverage_complete"] = False
    tampered["domain_obligation_graph"]["graph_hash"] = sha({k: v for k, v in tampered["domain_obligation_graph"].items() if k != "graph_hash"})
    tampered["domain_obligation_graph_hash"] = tampered["domain_obligation_graph"]["graph_hash"]
    tampered["domain_obligation_summary"]["graph_hash"] = tampered["domain_obligation_graph_hash"]
    tampered["artifact_hash"] = sha({k: v for k, v in tampered.items() if k != "artifact_hash"})
    assert B2.recheck(claim, tampered)["ok"] is False
