"""B5 validation runtime reliability — permanent regression tests.

These tests lock the architecture properties introduced by the validation-runtime
reliability remediation:

  * process-local trusted attestation reuse is bound to immutable identity facts
    and never weakens fail-closed semantics;
  * one full codesign + Gatekeeper verification per process; subsequent
    resolutions/validations reuse the attestation only while every identity fact
    (no-follow component identity, canonical equality, binary hashes, bundle
    seal) matches;
  * any identity/seal change bypasses the cache and re-runs the full chain
    (still fail-closed);
  * the symbolic budget redesign remains fail-closed: timeout -> UNKNOWN, never
    ZERO;
  * no request-to-request or stale-attestation reuse beyond the design.

Call-count / lifecycle assertions are used instead of wall-clock assertions so
the tests are not flaky.
"""
import subprocess
from pathlib import Path

import pytest

from tools import independent_zero_engine as ENGINE
from tools import wolfram_runtime as RUNTIME


def _valid_provenance(_):
    return {
        "identifier": "wolframscript",
        "team_identifier": "D2Y8ST33G6",
        "cdhash": "a" * 40,
        "authority": "Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)",
    }


def _make_executable(executable):
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)


def _kernel_path(application):
    return application / "Contents" / "Resources" / "Wolfram Player.app" /         "Contents" / "MacOS" / "WolframKernel"


def _make_installation(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    executable = application / "Contents" / "Resources" / "Wolfram Player.app" /         "Contents" / "MacOS" / "wolframscript"
    _make_executable(executable)
    _make_executable(_kernel_path(application))
    return application, executable


def _patch_fixed_policy(monkeypatch, application, executable):
    """Point every source-policy constant set at a temporary fixed installation."""
    kernel = _kernel_path(application)
    monkeypatch.setattr(RUNTIME, "APPROVED_APP_LEXICAL", str(application))
    monkeypatch.setattr(RUNTIME, "APPROVED_EXECUTABLE_LEXICAL", str(executable))
    monkeypatch.setattr(RUNTIME, "APPROVED_KERNEL_LEXICAL", str(kernel))
    monkeypatch.setattr(RUNTIME, "APPROVED_APPLICATION_BOUNDARIES", (str(application),))
    monkeypatch.setattr(RUNTIME, "APPROVED_RUNTIME_CANDIDATES", (str(executable),))
    monkeypatch.setattr(RUNTIME, "APPROVED_KERNEL_CANDIDATES", (str(kernel),))


@pytest.fixture(autouse=True)
def _reset_attestation_cache():
    RUNTIME.clear_runtime_attestation_cache()
    yield
    RUNTIME.clear_runtime_attestation_cache()


def test_second_resolution_reuses_attestation_without_new_provenance(monkeypatch, tmp_path):
    """One full codesign/Gatekeeper verification per process, then fact-bound reuse."""
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []

    def counting_provenance(boundary, candidate, kernel):
        provenance_calls.append((str(boundary), str(candidate), str(kernel)))
        return _valid_provenance(candidate)

    monkeypatch.setattr(RUNTIME, "_codesign_provenance", counting_provenance)

    first = RUNTIME.resolve_trusted_wolfram_runtime()
    assert len(provenance_calls) == 1
    second = RUNTIME.resolve_trusted_wolfram_runtime()
    assert second == first
    # The second resolution is served from the attestation: no new provenance chain.
    assert len(provenance_calls) == 1


def test_validate_identity_reuses_attestation_after_warm_resolution(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []
    monkeypatch.setattr(
        RUNTIME, "_codesign_provenance",
        lambda boundary, candidate, kernel: (
            provenance_calls.append((str(boundary), str(candidate), str(kernel))) or
            _valid_provenance(candidate)))

    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    assert len(provenance_calls) == 1
    RUNTIME.validate_trusted_wolfram_runtime_identity(identity)
    RUNTIME.validate_trusted_wolfram_runtime_identity(identity)
    # Both validations reuse the attestation; no new provenance chain.
    assert len(provenance_calls) == 1


def test_execution_binding_reuses_attestation_and_keeps_descriptor_binding(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []
    monkeypatch.setattr(
        RUNTIME, "_codesign_provenance",
        lambda boundary, candidate, kernel: (
            provenance_calls.append((str(boundary), str(candidate), str(kernel))) or
            _valid_provenance(candidate)))

    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    resolved = RUNTIME.validate_trusted_wolfram_runtime_execution_binding(identity)
    assert resolved["canonical_candidate"] == executable
    assert resolved["canonical_kernel"] == _kernel_path(application)
    # The execution binding still performs the descriptor-bound identity check
    # but does not re-run the provenance chain on a warm attestation.
    assert len(provenance_calls) == 1


def test_bundle_seal_change_forces_full_reprovenance_and_fails_closed(monkeypatch, tmp_path):
    """A changed sealed bundle manifest must bypass the cache and fail closed."""
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []

    def strict_provenance(boundary, candidate, kernel):
        provenance_calls.append((str(boundary), str(candidate), str(kernel)))
        return _valid_provenance(candidate)

    monkeypatch.setattr(RUNTIME, "_codesign_provenance", strict_provenance)
    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    assert len(provenance_calls) == 1

    # The signed bundle's Info.plist changed after resolution: the seal no longer
    # matches, so the cache is bypassed and the full chain re-runs.
    sealed_child = application / "Contents" / "Info.plist"
    sealed_child.write_text("mutated after resolution")

    def failing_provenance(boundary, candidate, kernel):
        provenance_calls.append(("failed", str(boundary)))
        raise RUNTIME.TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")

    monkeypatch.setattr(RUNTIME, "_codesign_provenance", failing_provenance)
    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        RUNTIME.validate_trusted_wolfram_runtime_identity(identity)
    assert error.value.code == "TRUSTED_RUNTIME_PROVENANCE_FAILED"
    assert any(call[0] == "failed" for call in provenance_calls)


def test_runtime_identity_change_bypasses_cache_and_fails_closed(monkeypatch, tmp_path):
    """A changed executable must not be served from the attestation cache."""
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))

    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    executable.write_text("#!/bin/sh\n# replacement\nexit 0\n")
    executable.chmod(0o755)

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        RUNTIME.validate_trusted_wolfram_runtime_identity(identity)
    assert error.value.code == "TRUSTED_RUNTIME_IDENTITY_CHANGED"


def test_cache_clear_forces_full_reprovenance(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []
    monkeypatch.setattr(
        RUNTIME, "_codesign_provenance",
        lambda boundary, candidate, kernel: (
            provenance_calls.append((str(boundary), str(candidate), str(kernel))) or
            _valid_provenance(candidate)))
    RUNTIME.resolve_trusted_wolfram_runtime()
    assert len(provenance_calls) == 1
    RUNTIME.clear_runtime_attestation_cache()
    RUNTIME.resolve_trusted_wolfram_runtime()
    assert len(provenance_calls) == 2


def test_timeout_still_returns_unknown_never_zero(monkeypatch, tmp_path):
    """The fail-closed timeout semantics are unchanged by the budget redesign."""
    from tools import wolfram_runtime as WR

    def timed_out_runner(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 30))

    monkeypatch.setattr(WR, "_codesign_provenance", lambda *_: _valid_provenance(None))

    # Build a valid identity through the temp seam without touching the real bundle.
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    identity = WR.resolve_trusted_wolfram_runtime()

    result = ENGINE.evaluate_with_runtime(
        {"lhs": "x+x", "rhs": "2*x", "symbols": ["x"], "scope": "real_scalars",
         "assumptions": ["x real"], "domain": "connected: all real x"},
        identity, runner=timed_out_runner)
    assert result["status"] == "timeout"
    assert result["verdict"] == "UNKNOWN"


def test_engine_runs_stay_bounded_per_request(monkeypatch, tmp_path):
    """N symbolic requests in one process trigger exactly one provenance chain."""
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    provenance_calls = []
    monkeypatch.setattr(
        RUNTIME, "_codesign_provenance",
        lambda boundary, candidate, kernel: (
            provenance_calls.append((str(boundary), str(candidate), str(kernel))) or
            _valid_provenance(candidate)))

    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    payload = {"lhs": "x+x", "rhs": "2*x", "symbols": ["x"], "scope": "real_scalars",
               "assumptions": ["x real"], "domain": "connected: all real x"}
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="True\n", stderr="")

    for _ in range(3):
        result = ENGINE.evaluate_with_runtime(payload, identity, runner=runner)
        assert result["verdict"] == "ZERO"
        assert result["status"] == "complete"
    # One full provenance verification for the whole process; three fresh symbolic
    # evaluations (each request re-evaluated, no result reuse).
    assert len(provenance_calls) == 1
    assert len(calls) == 3


def test_wolfram_cmd_and_path_still_have_no_effect(monkeypatch, tmp_path):
    """Environment can never select the runtime, even with a warm attestation."""
    application, executable = _make_installation(tmp_path)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))
    monkeypatch.setenv("VIPER_WOLFRAM_CMD", "/not/used/by/b3")
    monkeypatch.setenv("PATH", "/not/used")

    identity = RUNTIME.resolve_trusted_wolfram_runtime()
    assert identity.canonical_executable_path == str(executable)
    assert identity.canonical_kernel_path == str(_kernel_path(application))
    RUNTIME.validate_trusted_wolfram_runtime_identity(identity)
