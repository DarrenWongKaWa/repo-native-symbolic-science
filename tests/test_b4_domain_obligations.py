"""B4 source-preserving domain-obligation IR and ATK-B4 core attacks."""
import copy
import pytest
from loop_engine.orch_adapters.symbolic_identity_verify import domain_obligations as B4
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as B2
from tests.test_b2_connected_subdomains import _certificate as b2_certificate


def _domain(*terms): return {"kind": "intersection", "terms": list(terms)}
def _cmp(v, op, n): return {"kind": "comparison", "left": v, "operator": op, "right": n}
def _claim(lhs, rhs, symbols=["x"]): return {"lhs": lhs, "rhs": rhs, "symbols": symbols, "scope": "real_scalars"}


def test_source_preserved_denominator_and_log_obligations_recheck_on_explicit_domains():
    claim = _claim("(x**2-1)/(x-1)", "x+1")
    graph = B4.build_obligation_graph(claim, _domain(_cmp("x", ">", "1")), ["real"])
    assert any(o["source_expression"] == "x - 1" for o in graph["obligations"])
    assert B4.recheck_obligation_graph(claim, _domain(_cmp("x", ">", "1")), ["real"], graph)["ok"]
    log_claim = _claim("log(x*y)", "log(x)+log(y)", ["x", "y"])
    domain = _domain(_cmp("x", ">", "0"), _cmp("y", ">", "0"))
    graph = B4.build_obligation_graph(log_claim, domain, ["real"])
    assert all(o["status"] == "PROVED" for o in graph["obligations"])
    assert B4.recheck_obligation_graph(log_claim, domain, ["real"], graph)["ok"]


@pytest.mark.parametrize("lhs,rhs", [("x/x", "1"), ("sqrt(x)*sqrt(x)", "x"), ("sqrt(x**2)", "x")])
def test_atk_b4_simplification_traps_remain_visible_and_block_unconditional_replay(lhs, rhs):
    claim = _claim(lhs, rhs)
    graph = B4.build_obligation_graph(claim, {"kind": "real_line", "variable": "x"})
    assert any(o["status"] != "PROVED" for o in graph["obligations"])
    assert not B4.recheck_obligation_graph(claim, {"kind": "real_line", "variable": "x"}, [], graph)["ok"]


@pytest.mark.parametrize("mutate", [
    lambda g: g.update(graph_hash="wrong"),
    lambda g: g["obligations"][0].update(source_node_path="rhs.args[0]"),
    lambda g: g["obligations"][0].update(dependencies=["missing"]),
    lambda g: g["obligations"][0].update(dependencies=[g["obligations"][0]["obligation_id"]]),
    lambda g: g["obligations"][0].update(status="UNRESOLVED"),
])
def test_atk_b4_tamper_cycle_missing_dependency_source_and_builder_status_are_rejected(mutate):
    claim = _claim("(x**2-1)/(x-1)", "x+1")
    domain = _domain(_cmp("x", ">", "1")); graph = B4.build_obligation_graph(claim, domain)
    bad = copy.deepcopy(graph); mutate(bad)
    assert not B4.recheck_obligation_graph(claim, domain, [], bad)["ok"]


def test_atk_b4_empty_unknown_and_free_text_domains_fail_closed():
    claim = _claim("x/x", "1")
    with pytest.raises(B4.ObligationError): B4.build_obligation_graph(claim, _domain(_cmp("x", ">", "1"), _cmp("x", "<", "0")))
    with pytest.raises(B4.ObligationError): B4.build_obligation_graph(claim, "x != 0")


def test_b4_additively_binds_a_b2_certificate_without_changing_its_verdict():
    claim, certificate = b2_certificate()
    graph = B4.build_obligation_graph({k: claim[k] for k in ("lhs", "rhs", "symbols", "scope")}, claim["subdomain"], claim["assumptions"])
    extended = B4.attach_to_b2_certificate(certificate, {k: claim[k] for k in ("lhs", "rhs", "symbols", "scope")}, claim["assumptions"], graph)
    assert B2.recheck(claim, extended)["ok"]
    copied = copy.deepcopy(extended); copied["domain_obligation_graph_hash"] = "wrong"
    assert not B2.recheck(claim, copied)["ok"]
