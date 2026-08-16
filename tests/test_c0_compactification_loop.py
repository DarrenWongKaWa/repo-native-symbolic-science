"""C0 — Minimal Certified Compactification Loop — regression tests (pure Python).

No Wolfram.  Verifier semantics must stay fail-closed: only an exact symbolic
zero yields ZERO; only an exact counterexample yields NONZERO; undecided is
UNKNOWN.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from loop_engine.orch_adapters.compactification_loop import core as C0
from loop_engine.orch_adapters.compactification_loop.core import AdapterError

SYMS = [{"name": "va", "real": False}, {"name": "vb", "real": False},
        {"name": "eps", "real": True, "nonzero": True}]
SCOPE = "complex_scalars_with_real_eps"


@pytest.fixture(autouse=True)
def _env_isolation(monkeypatch):
    monkeypatch.delenv("VIPER_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("VIPER_PROPOSER_CMD", raising=False)


def _parent():
    seed = C0.load_seed("METRIC_true_seed")
    return {"claim_id": seed["seed_id"], "lhs": seed["claim"]["lhs"],
            "rhs": seed["claim"]["rhs"], "symbols": seed["claim"]["symbols"],
            "scope": seed["claim"]["scope"]}


# --------------------------------------------------------------------------- #
# seed + verifier semantics
# --------------------------------------------------------------------------- #

def test_seed_verifies_zero():
    seed = C0.load_seed("METRIC_true_seed")
    assert seed["status"] == "CERTIFIED"
    rec = C0.verify_seed(seed)
    assert rec["verdict"] == C0.VERDICT_ZERO


def test_verifier_zero_polynomial():
    rec = C0.python_verify({"lhs": "(x+1)^2", "rhs": "x^2 + 2*x + 1", "symbols": ["x"]})
    assert rec["verdict"] == C0.VERDICT_ZERO


def test_verifier_zero_trig():
    rec = C0.python_verify({"lhs": "sin(x)^2 + cos(x)^2", "rhs": "1", "symbols": ["x"]})
    assert rec["verdict"] == C0.VERDICT_ZERO


def test_verifier_zero_exponential():
    rec = C0.python_verify({"lhs": "exp(x)*exp(y)", "rhs": "exp(x+y)",
                            "symbols": ["x", "y"]})
    assert rec["verdict"] == C0.VERDICT_ZERO


def test_verifier_nonzero_with_exact_counterexample():
    rec = C0.python_verify({"lhs": "x", "rhs": "x+1", "symbols": ["x"]})
    assert rec["verdict"] == C0.VERDICT_NONZERO
    assert rec["counterexample"]["exact_value"] != "0"


def test_verifier_unknown_fail_closed():
    # polynomial vanishing on every exact probe point but not identically zero
    rec = C0.python_verify({
        "lhs": "(x-1)*(x-1/2)*(x+1)*(x+2)*(x-2)*(x+1/2)",
        "rhs": "0", "symbols": ["x"]})
    assert rec["verdict"] == C0.VERDICT_UNKNOWN
    assert rec["evidence"][0]["kind"] == "simplification_undecided_no_exact_counterexample"


def test_verifier_complex_conjugate_family():
    # METRIC family identity must be ZERO for complex va,vb and real eps
    rec = C0.python_verify({
        "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^2",
        "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^2",
        "symbols": SYMS})
    assert rec["verdict"] == C0.VERDICT_ZERO


# --------------------------------------------------------------------------- #
# parse discipline
# --------------------------------------------------------------------------- #

def test_parse_rejects_undeclared_symbol():
    with pytest.raises(AdapterError) as exc:
        C0.parse_side("x + z", [{"name": "x", "real": True}])
    assert exc.value.code == "UNDECLARED_OR_DISALLOWED_NAME"


def test_parse_rejects_disallowed_characters():
    with pytest.raises(AdapterError) as exc:
        C0.parse_side("x; import os", [{"name": "x", "real": True}])
    assert exc.value.code in ("DISALLOWED_CHARACTERS", "UNDECLARED_OR_DISALLOWED_NAME")


def test_parse_rejects_empty():
    with pytest.raises(AdapterError) as exc:
        C0.parse_side("", [{"name": "x", "real": True}])
    assert exc.value.code == "EMPTY_EXPRESSION"


# --------------------------------------------------------------------------- #
# residual construction
# --------------------------------------------------------------------------- #

def test_residual_construction_exact_form():
    parent = _parent()
    cand = {"claim_id": "c1", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
            "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
            "symbols": SYMS, "scope": SCOPE}
    residual = C0.construct_residual(parent, cand)
    assert residual["construction"] == "difference_of_differences"
    assert residual["lhs"] == f"({cand['lhs']} - {cand['rhs']})"
    assert residual["rhs"] == f"({parent['lhs']} - {parent['rhs']})"
    assert len(residual["sha256"]) == 64


def test_residual_rejects_new_symbols():
    parent = _parent()
    cand = {"claim_id": "c2", "lhs": "w + va", "rhs": "va",
            "symbols": [{"name": "w", "real": True}], "scope": SCOPE}
    with pytest.raises(AdapterError) as exc:
        C0.construct_residual(parent, cand)
    assert exc.value.code == "CANDIDATE_SYMBOLS_NOT_WITHIN_PARENT_SCOPE"


def test_residual_rejects_scope_mismatch():
    parent = _parent()
    cand = {"claim_id": "c3", "lhs": "va", "rhs": "va",
            "symbols": SYMS, "scope": "real_scalars"}
    with pytest.raises(AdapterError) as exc:
        C0.construct_residual(parent, cand)
    assert exc.value.code == "SCOPE_MISMATCH_BETWEEN_PARENT_AND_CANDIDATE"


# --------------------------------------------------------------------------- #
# chain records + loop step
# --------------------------------------------------------------------------- #

def test_chain_node_certified_has_certificate_diagnostic_does_not():
    parent = _parent()
    nodes = C0.run_loop_step(parent, [
        {"claim_id": "ok", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
         "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
         "symbols": SYMS, "scope": SCOPE},
        {"claim_id": "bad", "lhs": "(va*conjugate(vb) - vb*conjugate(va))/eps^2",
         "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^2",
         "symbols": SYMS, "scope": SCOPE},
    ], "c0-test")["nodes"]
    assert nodes[0]["node_status"] == C0.NODE_CERTIFIED
    assert nodes[0]["certificate"]["kind"] == "c0_python_exact_residual_chain"
    assert nodes[1]["node_status"] == C0.NODE_DIAGNOSTIC
    assert nodes[1]["certificate"] is None
    assert nodes[1]["evidence"]["verdict"] == C0.VERDICT_NONZERO


def test_run_loop_step_summary_and_hashes():
    parent = _parent()
    step = C0.run_loop_step(parent, [
        {"claim_id": "ok", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
         "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
         "symbols": SYMS, "scope": SCOPE},
        {"claim_id": "bad", "lhs": "(va*conjugate(vb) - vb*conjugate(va))/eps^2",
         "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^2",
         "symbols": SYMS, "scope": SCOPE},
        {"claim_id": "odd", "lhs": "va", "rhs": "va + w",
         "symbols": [{"name": "w", "real": True}], "scope": SCOPE},
    ], "c0-test")
    assert step["summary"] == {"candidates": 3, "certified": 1,
                               "diagnostic": 1, "unverified": 1}
    for node in step["nodes"]:
        assert len(node["node_sha256"]) == 64
        assert len(node["claim_sha256"]) == 64


def test_verifier_zero_after_complex_normalization():
    # 2*re(va*conjugate(vb)) == va*conjugate(vb) + conjugate(va)*vb (exact, complex)
    rec = C0.python_verify({
        "lhs": "2*re(va*conjugate(vb))",
        "rhs": "va*conjugate(vb) + conjugate(va)*vb",
        "symbols": [{"name": "va", "real": False}, {"name": "vb", "real": False}]})
    assert rec["verdict"] == C0.VERDICT_ZERO
    assert rec["complex_normalized"] is True


def test_verifier_zero_polarization_identity():
    # |va+vb|^2 - |va-vb|^2 == 2*(va*conjugate(vb) + conjugate(va)*vb)
    rec = C0.python_verify({
        "lhs": "(Abs(va+vb)^2 - Abs(va-vb)^2)",
        "rhs": "2*(va*conjugate(vb) + conjugate(va)*vb)",
        "symbols": [{"name": "va", "real": False}, {"name": "vb", "real": False}]})
    assert rec["verdict"] == C0.VERDICT_ZERO


def test_handle_rejects_unverified_parent_claim():
    # F-01: a false parent (1 == 2) must never certify a child.
    with pytest.raises(AdapterError) as exc:
        C0.handle({
            "operation": "compactification_step", "contract_version": "1.0",
            "chain_id": "x", "parent_claim": {
                "claim_id": "false-parent", "lhs": "x", "rhs": "x+1",
                "symbols": ["x"], "scope": "declared_symbols"},
            "candidates": [
                {"claim_id": "child", "lhs": "x", "rhs": "x",
                 "symbols": ["x"], "scope": "declared_symbols"},
            ]})
    assert exc.value.code == "PARENT_CLAIM_NOT_CERTIFIED"


def test_verifier_never_emits_bogus_counterexample_on_true_identity():
    # F-02: Abs(sqrt(va)) == sqrt(Abs(va)) is true; nested-radical probe values
    # equal 0 but are not canonicalized.  Verdict must be ZERO or UNKNOWN,
    # never NONZERO with a bogus counterexample.
    rec = C0.python_verify({
        "lhs": "Abs(sqrt(va))", "rhs": "sqrt(Abs(va))",
        "symbols": [{"name": "va", "real": False}]})
    assert rec["verdict"] in (C0.VERDICT_ZERO, C0.VERDICT_UNKNOWN)
    assert "counterexample" not in rec


def test_symbol_name_reserved_rejected():
    with pytest.raises(AdapterError) as exc:
        C0.parse_side("sin", [{"name": "sin", "real": True}])
    assert exc.value.code == "SYMBOL_NAME_RESERVED"


def test_run_loop_step_uniquifies_duplicate_claim_ids():
    parent = _parent()
    dup = {"claim_id": "same", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
           "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
           "symbols": SYMS, "scope": SCOPE}
    step = C0.run_loop_step(parent, [dict(dup), dict(dup)], "c0-dup")
    ids = [n["claim_id"] for n in step["nodes"]]
    assert ids[0] != ids[1]
    assert ids[0] == "same" or ids[1].startswith("same")


# --------------------------------------------------------------------------- #
# ORCH boundary (handle)
# --------------------------------------------------------------------------- #

def test_handle_requires_seed_or_parent():
    with pytest.raises(AdapterError) as exc:
        C0.handle({"operation": "compactification_step", "contract_version": "1.0",
                   "chain_id": "x", "candidates": []})
    assert exc.value.code in ("SEED_OR_PARENT_CLAIM_REQUIRED", "PARENT_CLAIM_MISSING")


def test_handle_requires_candidates_or_propose():
    with pytest.raises(AdapterError) as exc:
        C0.handle({"operation": "compactification_step", "contract_version": "1.0",
                   "chain_id": "x", "seed_id": "METRIC_true_seed"})
    assert exc.value.code in ("CANDIDATES_OR_PROPOSE_REQUIRED", "CANDIDATES_EMPTY")


def test_handle_full_step_and_schema():
    import jsonschema
    schema = json.loads(
        (C0.SCHEMAS_DIR / "claim_chain.schema.json").read_text())
    step, code = C0.handle({
        "operation": "compactification_step", "contract_version": "1.0",
        "chain_id": "c0-handle-test", "seed_id": "METRIC_true_seed",
        "candidates": [
            {"claim_id": "h1", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
             "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
             "symbols": SYMS, "scope": SCOPE},
        ]})
    assert code == 0
    assert step["summary"]["certified"] == 1
    jsonschema.validate(step, schema)  # must not raise
    assert step["replay_artifact"]["sha256"]


def test_proposer_route_with_canned_backend(tmp_path, monkeypatch):
    canned = tmp_path / "canned_proposer.sh"
    canned.write_text("""#!/bin/sh
cat <<'CANEOF'
[{"lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3", "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3", "note": "p=3 variant"},
 {"lhs": "(va*conjugate(vb) - vb*conjugate(va))/eps^2", "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^2", "note": "antisymmetric"},
 {"lhs": "va + va", "rhs": "va", "note": "no conjugate"}]
CANEOF
""")
    canned.chmod(0o755)
    monkeypatch.setenv("VIPER_PROPOSER_CMD", str(canned))
    step, code = C0.handle({
        "operation": "compactification_step", "contract_version": "1.0",
        "chain_id": "c0-proposer-route", "seed_id": "METRIC_true_seed",
        "propose": {"problem": {"description": "continue the METRIC identity chain",
                                "symbols": ["va", "vb", "eps"],
                                "n_candidates": 3}}})
    assert code == 0
    statuses = {n["claim_id"]: n["node_status"] for n in step["nodes"]}
    assert step["summary"]["candidates"] == 3
    assert "certified" in step["summary"] and step["summary"]["certified"] >= 1
    assert step["summary"]["diagnostic"] >= 1


def test_controller_cli_roundtrip():
    payload = json.dumps({
        "operation": "compactification_step", "contract_version": "1.0",
        "chain_id": "c0-cli", "seed_id": "METRIC_true_seed",
        "candidates": [
            {"claim_id": "cli-ok", "lhs": "(va*conjugate(vb) + vb*conjugate(va))/eps^3",
             "rhs": "(va*conjugate(vb) + conjugate(va)*vb)/eps^3",
             "symbols": SYMS, "scope": SCOPE},
        ]})
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "orch_controller.py"),
         "compactification-step"],
        input=payload, capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr[-500:]
    result = json.loads(proc.stdout)
    assert result["summary"]["certified"] == 1
    assert result["nodes"][0]["residual_verdict"] == "ZERO"


def test_profile_scoping():
    def ops(profile):
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "orch_controller.py"),
             "--profile", profile, "list-operations"],
            capture_output=True, text=True, cwd=str(REPO))
        return set(json.loads(proc.stdout)["operations"])
    assert "compactification_step" in ops("full")
    assert "compactification_step" not in ops("proposer")
    assert "compactification_step" not in ops("judge")