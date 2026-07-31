"""B3 adversarial contract for the isolated Wolfram ZERO confirmation route."""
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from tools import independent_zero_engine as ENGINE_MODULE
from tools import wolfram_runtime as WOLFRAM_RUNTIME

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


def _synthetic_trusted_runtime():
    """A lower-level test identity; production always calls the resolver itself."""
    return WOLFRAM_RUNTIME.TrustedWolframRuntime(
        canonical_executable_path=WOLFRAM_RUNTIME.APPROVED_RUNTIME_CANDIDATES[0],
        approved_application_boundary=WOLFRAM_RUNTIME.APPROVED_APPLICATION_BOUNDARIES[0],
        executable_sha256="a" * 64,
        code_signing_identifier="wolframscript",
        code_signing_team_identifier="D2Y8ST33G6",
        code_signing_cdhash="b" * 40,
        code_signing_authority="Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)",
    )


def _confirmed_second(payload, runtime_identity):
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    expected = core.expected_second_engine_configuration(runtime_identity)
    return {
        "route": "shipped_wolfram_engine", "status": "complete", "verdict": "ZERO",
        "engine_identity": expected["engine_identity"],
        "implementation_version": expected["implementation_version"],
        "parser_version": expected["parser_version"],
        "semantic_profile": expected["semantic_profile"],
        "trusted_runtime": expected["trusted_runtime"],
        "configuration_hash": core.expected_second_engine_configuration_hash(runtime_identity),
        "input_hash": core.sha(payload), "process_exit_status": 0,
    }


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


def test_primary_zero_with_second_nonzero_or_unknown_cannot_upgrade(monkeypatch):
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    for second in (
            {"status": "complete", "verdict": "NONZERO"},
            {"status": "complete", "verdict": "UNKNOWN"}):
        monkeypatch.setattr(core, "_second_opinion", lambda *_: second)
        out, rc = core.handle(_request("(x+y)**2", "x**2+2*x*y+y**2", ("x", "y")))
        assert rc != 0 or out["combined_evidence_level"] < 3
        assert out["combined_verdict"] in {
            "DISPUTED_SECOND_ENGINE_CONFLICT", "SYMBOLIC_ZERO_PENDING_SECOND_ENGINE"}
        assert out["symbolic_claim_verifier"]["certificate"] is None


def test_malformed_partial_and_process_failures_fail_closed(monkeypatch):
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    for second in (
            {"status": "malformed_output", "verdict": "UNKNOWN"},
            {"status": "process_failure", "verdict": "UNKNOWN"},
            {"status": "timeout", "verdict": "UNKNOWN"}):
        monkeypatch.setattr(core, "_second_opinion", lambda *_: second)
        out, _ = core.handle(_request("x+x", "2*x"))
        assert out["combined_verdict"] == "SYMBOLIC_ZERO_PENDING_SECOND_ENGINE"
        assert out["combined_evidence_level"] == 1


def test_engine_rejects_extra_parser_forms_and_missing_structured_semantics():
    payload = _engine_payload("evil(x)", "0")
    process = subprocess.run([sys.executable, str(ENGINE)], input=json.dumps(payload), text=True,
                             capture_output=True, cwd=str(REPO))
    out = json.loads(process.stdout)
    assert out["verdict"] == "UNKNOWN" and out["status"] == "unsupported"


def test_manual_status_version_config_and_shared_intermediate_mutations_do_not_confirm():
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    payload = _engine_payload("x+x", "2*x")
    runtime_identity = _synthetic_trusted_runtime()
    confirmed = _confirmed_second(payload, runtime_identity)
    assert core._second_zero_confirmed(confirmed, payload, runtime_identity)
    for key, value in [("status", "UNKNOWN"), ("implementation_version", "wrong"),
                       ("configuration_hash", "wrong"), ("input_hash", "wrong"),
                       ("canonical_residual", "0")]:
        changed = dict(confirmed)
        changed[key] = value
        if key == "canonical_residual":
            # An injected primary intermediate is ignored, not treated as second-engine proof.
            changed["route"] = "external_override"
        assert not core._second_zero_confirmed(changed, payload, runtime_identity)


def test_viper_wolfram_cmd_does_not_change_the_resolved_runtime(monkeypatch):
    baseline = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    monkeypatch.setenv("VIPER_WOLFRAM_CMD", "/not/used/by/b3")
    changed = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    assert changed.canonical_executable_path == baseline.canonical_executable_path


def test_viper_wolfram_cmd_does_not_change_the_expected_configuration_hash(monkeypatch):
    baseline_runtime = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    baseline = WOLFRAM_RUNTIME.expected_configuration_hash(baseline_runtime)
    monkeypatch.setenv("VIPER_WOLFRAM_CMD", "/not/used/by/b3")
    changed_runtime = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    changed = WOLFRAM_RUNTIME.expected_configuration_hash(changed_runtime)
    assert changed == baseline


def test_path_prefix_does_not_change_the_resolved_runtime(monkeypatch, tmp_path):
    baseline = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    changed = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    assert changed.canonical_executable_path == baseline.canonical_executable_path


def test_production_resolver_returns_an_absolute_canonical_path():
    runtime_identity = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    resolved = Path(runtime_identity.canonical_executable_path)
    assert resolved.is_absolute()
    assert resolved == resolved.resolve(strict=True)


def test_resolver_rejects_a_path_outside_its_approved_application_boundary(tmp_path):
    boundary = tmp_path / "Wolfram Engine.app"
    boundary.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("not a runtime")
    with pytest.raises(WOLFRAM_RUNTIME.TrustedRuntimeError) as error:
        WOLFRAM_RUNTIME._resolve_runtime_candidates(
            [str(outside)], [str(boundary)], lambda _: {})
    assert error.value.code == "TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY"


def test_resolver_rejects_a_symlink_that_resolves_outside_the_boundary(tmp_path):
    boundary = tmp_path / "Wolfram Engine.app"
    executable_dir = boundary / "Contents" / "MacOS"
    executable_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("not a runtime")
    candidate = executable_dir / "wolframscript"
    candidate.symlink_to(outside)
    with pytest.raises(WOLFRAM_RUNTIME.TrustedRuntimeError) as error:
        WOLFRAM_RUNTIME._resolve_runtime_candidates(
            [str(candidate)], [str(boundary)], lambda _: {})
    assert error.value.code == "TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY"


def test_missing_approved_runtime_returns_unknown_and_never_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(
        WOLFRAM_RUNTIME, "APPROVED_RUNTIME_CANDIDATES", (str(tmp_path / "missing"),))
    result = ENGINE_MODULE.run(_engine_payload("x+x", "2*x"))
    assert result["status"] == "process_failure"
    assert result["verdict"] == "UNKNOWN"
    assert result["verdict"] != "ZERO"


def test_failed_provenance_returns_unknown_and_never_zero(monkeypatch):
    def failed_provenance(_):
        raise WOLFRAM_RUNTIME.TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")

    with pytest.raises(WOLFRAM_RUNTIME.TrustedRuntimeError) as error:
        WOLFRAM_RUNTIME._resolve_runtime_candidates(
            WOLFRAM_RUNTIME.APPROVED_RUNTIME_CANDIDATES,
            WOLFRAM_RUNTIME.APPROVED_APPLICATION_BOUNDARIES,
            failed_provenance)
    assert error.value.code == "TRUSTED_RUNTIME_PROVENANCE_FAILED"
    monkeypatch.setattr(
        ENGINE_MODULE, "resolve_trusted_wolfram_runtime", lambda: failed_provenance(None))
    result = ENGINE_MODULE.run(_engine_payload("x+x", "2*x"))
    assert result["status"] == "process_failure"
    assert result["verdict"] == "UNKNOWN"
    assert result["verdict"] != "ZERO"


def test_trusted_absolute_path_is_passed_to_the_subprocess_and_true_is_zero():
    runtime_identity = WOLFRAM_RUNTIME.resolve_trusted_wolfram_runtime()
    seen = {}

    def runner(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="True\n", stderr="")

    result = ENGINE_MODULE.evaluate_with_runtime(
        _engine_payload("x+x", "2*x"), runtime_identity, runner)
    assert seen["command"][0] == runtime_identity.canonical_executable_path
    assert Path(seen["command"][0]).is_absolute()
    assert seen["command"][1] == "-code"
    assert result["verdict"] == "ZERO"


def test_mocked_trusted_runtime_false_is_nonzero():
    runtime_identity = _synthetic_trusted_runtime()

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="False\n", stderr="")

    result = ENGINE_MODULE.evaluate_with_runtime(
        _engine_payload("x+x", "2*x"), runtime_identity, runner)
    assert result["verdict"] == "NONZERO"


def test_symbolic_or_malformed_runtime_output_is_unknown():
    runtime_identity = _synthetic_trusted_runtime()
    for output in ("x == x\n", "not a verdict\n"):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        result = ENGINE_MODULE.evaluate_with_runtime(
            _engine_payload("x+x", "2*x"), runtime_identity, runner)
        assert result["verdict"] == "UNKNOWN"


def test_stored_transcript_cannot_define_the_expected_configuration():
    from loop_engine.orch_adapters.symbolic_identity_verify import core
    payload = _engine_payload("x+x", "2*x")
    trusted_runtime = _synthetic_trusted_runtime()
    stored_runtime = replace(trusted_runtime, executable_sha256="c" * 64)
    transcript = _confirmed_second(payload, stored_runtime)
    assert core._second_zero_confirmed(transcript, payload, trusted_runtime) is False
    assert transcript["configuration_hash"] == \
        core.expected_second_engine_configuration_hash(stored_runtime)
