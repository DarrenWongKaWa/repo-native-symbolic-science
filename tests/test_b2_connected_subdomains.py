"""ATK-B2: explicit connected-subdomain identities must remain conditional and hash-bound."""
import copy

import pytest

from loop_engine.orch_adapters._symbolic_safe_parse import AdapterError, sha
from loop_engine.orch_adapters.symbolic_identity_verify import connected_subdomain as B2
from loop_engine.orch_adapters.symbolic_identity_verify import core


BODY = {"lhs": "log(x*y)", "rhs": "log(x)+log(y)", "symbols": ["x", "y"], "scope": "real_scalars"}
PARENT = {**BODY, "domain": {"kind": "intersection", "terms": [
    {"kind": "real_line", "variable": "x"}, {"kind": "real_line", "variable": "y"}]}}
PARENT_HASH = sha({"schema": B2.SCHEMA, "claim": BODY,
                   "predicate": B2.analyze_predicate(PARENT["domain"], BODY["symbols"])["predicate"],
                   "profile": B2.PROFILE})


def _claim(**changes):
    predicate = {"kind": "intersection", "terms": [
        {"kind": "comparison", "left": "x", "operator": ">", "right": "0"},
        {"kind": "comparison", "left": "y", "operator": ">", "right": "0"}]}
    value = {**BODY, "assumptions": ["x,y are real"], "parent_claim": copy.deepcopy(PARENT),
             "subdomain": {"schema": B2.SCHEMA, "parent_claim_hash": PARENT_HASH, "variables": ["x", "y"],
                           "predicate": predicate, "connected_component": {"kind": "positive_orthant", "variables": ["x", "y"]},
                           "definedness_obligations": [], "side_conditions": [], "scope_mapping": {"relation": "restriction"}}}
    value.update(changes)
    return value


def _second_for(context, claim):
    payload = core._second_engine_payload(BODY["lhs"], BODY["rhs"], BODY["symbols"], BODY["scope"], context["subdomain"], claim["assumptions"])
    return {"route": "shipped_wolfram_engine", "status": "complete", "verdict": "ZERO",
            "engine_identity": core.SECOND_ENGINE_CONFIG["engine_identity"],
            "implementation_version": core.SECOND_ENGINE_CONFIG["implementation_version"],
            "parser_version": core.SECOND_ENGINE_CONFIG["parser_version"],
            "semantic_profile": core.SECOND_ENGINE_CONFIG["semantic_profile"],
            "configuration_hash": core.SECOND_ENGINE_CONFIG_HASH, "input_hash": sha(payload), "process_exit_status": 0}


def _certificate():
    claim = _claim(); context = B2.prepare_log_product_claim(claim)
    return claim, B2.build_certificate(context, _second_for(context, claim))


def _exp_transformation():
    transformed = {"lhs": "log(exp(u)*y)", "rhs": "log(exp(u))+log(y)",
                   "symbols": ["u", "y"], "scope": "real_scalars"}
    return B2.build_positive_exp_transformation(PARENT_HASH, BODY, "x", "u", transformed)


def test_log_product_positive_quadrant_is_conditional_and_recheckable():
    claim, certificate = _certificate()
    assert certificate["scope_relation"] == "STRICT_SUBDOMAIN_OF_PARENT"
    assert certificate["proof_certificate"]["kind"] == "real_log_product_positive"
    assert B2.recheck(claim, certificate)["ok"]
    assert certificate["kind"] != "VERIFIED_GLOBAL_IDENTITY"


@pytest.mark.parametrize("mutate", [
    lambda c: c["subdomain"].update(parent_claim_hash="wrong"),
    lambda c: c["subdomain"].update(predicate={"kind": "intersection", "terms": [{"kind": "comparison", "left": "x", "operator": ">", "right": "0"}]}),
    lambda c: c["subdomain"].update(predicate={"kind": "intersection", "terms": [{"kind": "comparison", "left": "x", "operator": ">=", "right": "0"}, {"kind": "comparison", "left": "y", "operator": ">", "right": "0"}]}),
    lambda c: c["subdomain"].update(predicate={"kind": "union", "terms": []}),
    lambda c: c["subdomain"].update(predicate={"kind": "interval", "variable": "x", "lower": "0.0", "upper": "+inf", "lower_closed": False, "upper_closed": False}),
    lambda c: c["subdomain"].update(predicate={"kind": "intersection", "terms": [{"kind": "comparison", "left": "x", "operator": ">", "right": "1"}, {"kind": "comparison", "left": "x", "operator": "<", "right": "0"}]}),
    lambda c: c["subdomain"].update(connected_component={"kind": "positive_orthant", "variables": ["x"]}),
    lambda c: c["subdomain"].update(transformation={"kind": "unknown"}),
])
def test_atk_b2_invalid_predicates_fail_closed(mutate):
    claim = _claim(); mutate(claim)
    with pytest.raises(AdapterError):
        B2.prepare_log_product_claim(claim)


@pytest.mark.parametrize("field", ["parent_claim_hash", "child_claim_hash", "subdomain_hash", "scope_relation", "side_conditions"])
def test_atk_b2_certificate_binding_tampering_is_rejected(field):
    claim, certificate = _certificate()
    bad = copy.deepcopy(certificate)
    bad[field] = "wrong" if field != "side_conditions" else []
    assert not B2.recheck(claim, bad)["ok"]


def test_atk_b2_strict_subdomain_can_never_be_reported_global(monkeypatch):
    claim = _claim()
    context = B2.prepare_log_product_claim(claim)
    second = _second_for(context, claim)
    monkeypatch.setattr(core, "_second_opinion", lambda *args: second)
    result, rc = core._connected_subdomain_result({"claim": claim}, claim, 1)
    assert rc == 0 and result["combined_verdict"] == "VERIFIED_ON_EXPLICIT_SUBDOMAIN"
    assert "VERIFIED_GLOBAL_IDENTITY" not in result["combined_verdict"]


def test_positive_exp_transformation_is_exact_and_rejects_bad_image_inverse_and_hashes():
    cert = _exp_transformation()
    assert B2.recheck_positive_exp_transformation(cert, BODY)["ok"]
    for field, bad_value in [("inverse", "log(u)"), ("parent_claim_hash", "other"),
                             ("image_domain", {"kind": "interval", "variable": "x", "lower": "0", "upper": "+inf", "lower_closed": True, "upper_closed": False})]:
        altered = copy.deepcopy(cert); altered[field] = bad_value
        assert not B2.recheck_positive_exp_transformation(altered, BODY)["ok"]


def test_exp_transformation_is_accepted_by_the_live_b2_route_and_binds_exact_substitution():
    claim = _claim(); claim["subdomain"]["transformation"] = _exp_transformation()
    context = B2.prepare_log_product_claim(claim)
    assert context["subdomain"]["transformation"]["transformed_claim"]["symbols"] == ["u", "y"]
    assert B2.recheck_positive_exp_transformation(context["subdomain"]["transformation"], BODY)["ok"]


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(rhs="log(x)+log(x)"),
    lambda c: c["parent_claim"].update(lhs="log(x*y)+1"),
    lambda c: c.update(scope="complex_scalars"),
    lambda c: c["subdomain"].update(predicate="x > 0 and y > 0"),
    lambda c: c["subdomain"].update(connected_component={"kind": "cartesian_product_intervals", "variables": ["x", "y"]}),
    lambda c: c["subdomain"].update(scope_relation="SAME_DOMAIN_AS_PARENT"),
])
def test_atk_b2_parent_child_and_free_text_escalations_fail_closed(mutate):
    claim = _claim(); mutate(claim)
    with pytest.raises(AdapterError):
        B2.prepare_log_product_claim(claim)


def test_atk_b2_certificate_cannot_be_cloned_to_a_different_parent_or_child_request():
    claim, certificate = _certificate()
    other_parent = copy.deepcopy(claim); other_parent["parent_claim"]["domain"] = {"kind": "interval", "variable": "x", "lower": "0", "upper": "+inf", "lower_closed": False, "upper_closed": False}
    assert not B2.recheck(other_parent, certificate)["ok"]
    other_child = copy.deepcopy(claim); other_child["rhs"] = "log(x)+log(x)"
    assert not B2.recheck(other_child, certificate)["ok"]


@pytest.mark.parametrize("field", ["configuration_hash", "input_hash", "semantic_profile", "implementation_version", "parser_version"])
def test_atk_b2_b3_profile_tampering_or_mismatched_scope_zero_is_rejected(field):
    claim, certificate = _certificate()
    bad = copy.deepcopy(certificate)
    bad["second_engine_confirmation"][field] = "wrong"
    bad["artifact_hash"] = sha({k: v for k, v in bad.items() if k != "artifact_hash"})
    assert not B2.recheck(claim, bad)["ok"]
    mismatched = copy.deepcopy(certificate)
    mismatched["second_engine_confirmation"]["input_hash"] = sha({"smaller": "x>1,y>1"})
    mismatched["artifact_hash"] = sha({k: v for k, v in mismatched.items() if k != "artifact_hash"})
    assert not B2.recheck(claim, mismatched)["ok"]


def test_atk_b2_exp_transformation_rejects_semantic_change_and_parameter_collision():
    cert = _exp_transformation()
    wrong = copy.deepcopy(cert); wrong["transformed_claim"]["rhs"] = "u+log(y)"
    assert not B2.recheck_positive_exp_transformation(wrong, BODY)["ok"]
    collision = copy.deepcopy(cert); collision["parameter_variable"] = "y"
    assert not B2.recheck_positive_exp_transformation(collision, BODY)["ok"]
