"""B3 adversarial contract for the isolated Wolfram ZERO confirmation route."""
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
ENGINE = REPO / "tools" / "independent_zero_engine.py"


def _request(lhs, rhs, symbols=("x",), domain="connected: all real x"):
    return {"operation": "symbolic_identity_verify", "contract_version": "1.0",
            "verification_mode": "symbolic_only",
            "claim": {"lhs": lhs, "rhs": rhs, "symbols": list(symbols),
                      "scope": "real_scalars", "assumptions": ["x real"], "domain": domain}}


def _run(request, env_extra=None):
    env = dict(os.environ)
    env["VIPER_OUTPUT_DIR"] = tempfile.mkdtemp()
    env["PYTHONPATH"] = ""
    if env_extra:
        env.update(env_extra)
    process = subprocess.run([sys.executable, str(CTL), "symbolic-identity-verify"],
                             input=json.dumps(request), text=True, capture_output=True,
                             cwd=str(REPO), env=env)
    return json.loads(process.stdout), process.returncode


def _engine_payload(lhs, rhs, symbols=("x",), domain="connected: all real x"):
    return {"lhs": lhs, "rhs": rhs, "symbols": list(symbols), "scope": "real_scalars",
            "assumptions": ["x real"], "domain": domain}


def _script(tmp_path, source):
    path = tmp_path / "engine.py"
    path.write_text(source)
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(path))}"


def test_engine_reparses_raw_claim_and_confirms_polynomial_t1_and_t2():
    for lhs, rhs, syms in [
        ("(x+y)**2", "x**2+2*x*y+y**2", ("x", "y")),
        ("sin(x)**2+cos(x)**2", "1", ("x",)),
        ("tanh(x)", "(exp(2*x)-1)/(exp(2*x)+1)", ("x",)),
    ]:
        out, rc = _run(_request(lhs, rhs, syms))
        cert = out["symbolic_claim_verifier"]["certificate"]
        second = cert["second_engine"]
        assert rc == 0 and second["verdict"] == "ZERO"
        assert second["route"] == "shipped_wolfram_engine"
        assert second["input_hash"] and second["configuration_hash"]
        assert "canonical_residual" not in second and "cofactor" not in second


def test_b1_composite_t3_binds_a_second_engine_zero_for_its_derivative_child():
    domain = {"kind": "real_line", "variable": "x"}
    out, rc = _run(_request("atan(x)", "asin(x/sqrt(1+x**2))", domain=domain))
    cert = out["symbolic_claim_verifier"]["certificate"]
    second = cert["second_engine"]
    assert rc == 0 and cert["kind"] == "derivative_base_point_composite"
    assert second["verdict"] == "ZERO" and second["input_hash"]


def test_primary_zero_with_second_nonzero_or_unknown_cannot_upgrade(tmp_path):
    nonzero = _script(tmp_path, "import json; print(json.dumps({'verdict':'NONZERO'}))")
    unknown = _script(tmp_path, "import json; print(json.dumps({'status':'complete','verdict':'UNKNOWN'}))")
    for command in (nonzero, unknown):
        out, rc = _run(_request("(x+y)**2", "x**2+2*x*y+y**2", ("x", "y")),
                       {"VIPER_SECOND_CAS_CMD": command})
        assert rc != 0 or out["combined_evidence_level"] < 3
        assert out["combined_verdict"] in {
            "DISPUTED_SECOND_ENGINE_CONFLICT", "SYMBOLIC_ZERO_PENDING_SECOND_ENGINE"}
        assert out["symbolic_claim_verifier"]["certificate"] is None


def test_malformed_partial_and_process_failures_fail_closed(tmp_path):
    malformed = _script(tmp_path, "print('{')")
    partial = _script(tmp_path, "print('[]')")
    missing = f"{shlex.quote(sys.executable)} {shlex.quote(str(tmp_path / 'missing.py'))}"
    for command in (malformed, partial, missing):
        out, _ = _run(_request("x+x", "2*x"), {"VIPER_SECOND_CAS_CMD": command})
        assert out["combined_verdict"] == "SYMBOLIC_ZERO_PENDING_SECOND_ENGINE"
        assert out["combined_evidence_level"] == 1


def test_engine_rejects_extra_parser_forms_and_missing_structured_semantics():
    payload = _engine_payload("evil(x)", "0")
    process = subprocess.run([sys.executable, str(ENGINE)], input=json.dumps(payload), text=True,
                             capture_output=True, cwd=str(REPO))
    out = json.loads(process.stdout)
    assert out["verdict"] == "UNKNOWN" and out["status"] == "unsupported"


def test_manual_status_version_config_and_shared_intermediate_mutations_do_not_confirm():
    sys.path.insert(0, str(REPO))
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    payload = _engine_payload("x+x", "2*x")
    confirmed = {"route": "shipped_wolfram_engine", "status": "complete", "verdict": "ZERO",
                 "engine_identity": core.SECOND_ENGINE_CONFIG["engine_identity"],
                 "implementation_version": core.SECOND_ENGINE_CONFIG["implementation_version"],
                 "parser_version": core.SECOND_ENGINE_CONFIG["parser_version"],
                 "semantic_profile": core.SECOND_ENGINE_CONFIG["semantic_profile"],
                 "configuration_hash": core.SECOND_ENGINE_CONFIG_HASH,
                 "input_hash": core.sha(payload), "process_exit_status": 0}
    assert core._second_zero_confirmed(confirmed, payload)
    for key, value in [("status", "UNKNOWN"), ("implementation_version", "wrong"),
                       ("configuration_hash", "wrong"), ("input_hash", "wrong"),
                       ("canonical_residual", "0")]:
        changed = dict(confirmed)
        changed[key] = value
        if key == "canonical_residual":
            # An injected primary intermediate is ignored, not treated as second-engine proof.
            changed["route"] = "external_override"
        assert not core._second_zero_confirmed(changed, payload)
