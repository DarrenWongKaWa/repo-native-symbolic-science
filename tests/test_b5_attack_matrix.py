"""ATK-B5-01..15: incomplete or cross-bound gradient evidence never upgrades."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.orch_adapters._symbolic_safe_parse import validate_and_parse
from loop_engine.orch_adapters.symbolic_identity_verify import core
from loop_engine.orch_adapters.symbolic_identity_verify import multivariable_t3 as B5
from tests.test_b5_multivariable_t3 import _cli, claim, request

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"


@pytest.fixture(scope="module")
def valid_pair():
    result, rc, process = _cli("multivariable-t3-verify", request(claim()))
    assert rc == 0 and process.stderr == ""
    return claim(), result["symbolic_claim_verifier"]["certificate"]


def _recheck(parent, certificate):
    lhs = validate_and_parse(parent["lhs"], parent["symbols"], real=True)
    rhs = validate_and_parse(parent["rhs"], parent["symbols"], real=True)
    return B5.recheck(parent, lhs, rhs, certificate)


def _assert_rejected(parent, certificate):
    result = _recheck(parent, certificate)
    assert result["ok"] is False


def test_atk_b5_01_one_partial_derivative_nonzero_blocks_parent(monkeypatch):
    monkeypatch.setattr(core, "_second_opinion", lambda *args: {"verdict": "NONZERO"})
    result, rc = B5.verify_request(request(claim()))
    assert rc != 0
    assert result["combined_verdict"] == "MULTIVARIABLE_T3_BLOCKED"
    assert result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["certificate"] is None
    assert result["symbolic_claim_verifier"]["failure_code"] == \
        "MULTIVARIABLE_T3_PARTIAL_NONZERO"


def test_atk_b5_02_only_subset_of_variables_checked_is_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["gradient_certificate_graph"]["children"].pop()
    bad["gradient_certificate_graph"]["ordered_child_hashes"].pop()
    _assert_rejected(parent, bad)


def test_atk_b5_03_base_point_outside_domain_blocks_construction():
    parent = claim()
    parent["domain"] = {"kind": "intersection", "terms": [
        {"kind": "comparison", "left": "x", "operator": ">", "right": "0"},
        {"kind": "real_line", "variable": "y"}]}
    with pytest.raises(B5.MultivariableT3Error) as exc:
        B5.prepare_certificate(
            parent, validate_and_parse(parent["lhs"], parent["symbols"], real=True),
            validate_and_parse(parent["rhs"], parent["symbols"], real=True))
    assert exc.value.code == B5.FAILURE["base"]


def test_atk_b5_04_disconnected_domain_is_rejected():
    parent = claim()
    parent["domain"] = {"kind": "union", "terms": [
        {"kind": "comparison", "left": "x", "operator": "<", "right": "0"},
        {"kind": "comparison", "left": "x", "operator": ">", "right": "0"}]}
    with pytest.raises(B5.MultivariableT3Error) as exc:
        B5.prepare_certificate(
            parent, validate_and_parse(parent["lhs"], parent["symbols"], real=True),
            validate_and_parse(parent["rhs"], parent["symbols"], real=True))
    assert exc.value.code == B5.FAILURE["domain"]


def test_atk_b5_05_inconsistent_child_assumptions_are_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["gradient_certificate_graph"]["children"][1]["assumptions"] = ["y complex"]
    _assert_rejected(parent, bad)


def test_atk_b5_06_mismatched_variable_order_is_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["variable_order_manifest"]["variable_order"] = ["y", "x"]
    _assert_rejected(parent, bad)


def test_atk_b5_07_directional_derivative_cannot_represent_full_gradient(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["gradient_certificate_graph"]["children"][0]["derivative_kind"] = \
        "directional_derivative"
    _assert_rejected(parent, bad)


def test_atk_b5_08_silently_omitted_relevant_variable_is_rejected():
    parent = claim()
    parent["multivariable_t3"]["relevant_variables"] = ["x"]
    result, rc = B5.verify_request(request(parent))
    assert rc != 0 and result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["certificate"] is None


def test_domain_cannot_silently_omit_a_declared_variable():
    parent = claim()
    parent["domain"]["terms"] = [{"kind": "real_line", "variable": "x"}]
    result, rc = B5.verify_request(request(parent))
    assert rc != 0 and result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["failure_code"] == B5.FAILURE["domain"]


def test_atk_b5_09_child_copied_from_another_parent_is_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["gradient_certificate_graph"]["children"][0]["parent_claim_hash"] = \
        "copied-from-another-parent"
    _assert_rejected(parent, bad)


def test_atk_b5_10_child_reused_under_different_scope_is_rejected(valid_pair):
    parent, certificate = valid_pair
    changed_parent = copy.deepcopy(parent)
    changed_parent["scope"] = "different_real_scope"
    _assert_rejected(changed_parent, certificate)


def test_atk_b5_11_coverage_bitmap_tampering_is_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["coverage_manifest"]["coverage_bitmap"] = [True, False]
    _assert_rejected(parent, bad)


@pytest.mark.parametrize("mutate", [
    lambda certificate: certificate.update(parent_claim_hash="tampered"),
    lambda certificate: certificate["gradient_certificate_graph"]["children"][0].update(
        child_hash="tampered"),
    lambda certificate: certificate["connected_domain_certificate"].update(
        domain_certificate_hash="tampered"),
    lambda certificate: certificate["base_point_certificate"].update(
        base_point_hash="tampered"),
])
def test_atk_b5_12_parent_child_domain_and_base_hash_tampering_is_rejected(
        valid_pair, mutate):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    mutate(bad)
    _assert_rejected(parent, bad)


def test_atk_b5_13_unknown_partial_blocks_parent(monkeypatch):
    monkeypatch.setattr(
        core, "_second_opinion",
        lambda *args: {"status": "complete", "verdict": "UNKNOWN"})
    result, rc = B5.verify_request(request(claim()))
    assert rc != 0 and result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["failure_code"] == \
        B5.FAILURE["confirmation"]
    assert result["symbolic_claim_verifier"]["certificate"] is None


def test_atk_b5_14_unsupported_partial_blocks_parent(monkeypatch):
    monkeypatch.setattr(
        core, "_second_opinion",
        lambda *args: {"status": "unsupported", "verdict": "UNKNOWN"})
    result, rc = B5.verify_request(request(claim()))
    assert rc != 0 and result["combined_evidence_level"] == 0
    assert result["symbolic_claim_verifier"]["certificate"] is None


def test_atk_b5_15_base_point_component_mismatch_is_rejected(valid_pair):
    parent, certificate = valid_pair
    bad = copy.deepcopy(certificate)
    bad["base_point_certificate"]["connected_component_hash"] = \
        "different-certified-component"
    _assert_rejected(parent, bad)


def test_proposer_profile_cannot_reach_b5_verifier():
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, str(CTL), "--profile", "proposer",
         "multivariable-t3-verify"],
        input=json.dumps(request(claim())), text=True, capture_output=True,
        cwd=str(REPO), env=environment)
    output = json.loads(process.stdout)
    assert process.returncode != 0
    assert process.stderr == ""
    assert output["orch_error"] == "CAPABILITY_NOT_REGISTERED"
