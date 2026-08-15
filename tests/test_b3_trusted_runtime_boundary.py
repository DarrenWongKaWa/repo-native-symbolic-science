"""Fail-closed tests for B3's immutable Wolfram application trust anchor."""
import subprocess
from pathlib import Path

import pytest

from tools import independent_zero_engine as ENGINE
from tools import wolfram_runtime as RUNTIME


def _valid_provenance(_):
    """Test-only provenance seam; production performs codesign and Gatekeeper checks."""
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
    return application / "Contents" / "Resources" / "Wolfram Player.app" / \
        "Contents" / "MacOS" / "WolframKernel"


def _make_installation(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    executable = application / "Contents" / "Resources" / "Wolfram Player.app" / \
        "Contents" / "MacOS" / "wolframscript"
    _make_executable(executable)
    _make_executable(_kernel_path(application))
    return application, executable


def _resolve(application, executable, **kwargs):
    return RUNTIME._resolve_runtime_candidates(
        (str(executable),), (str(application),), _valid_provenance,
        kernel_candidates=(str(_kernel_path(application)),), **kwargs)


def _assert_rejected(application, executable, expected_code=None, **kwargs):
    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        _resolve(application, executable, **kwargs)
    if expected_code is not None:
        assert error.value.code == expected_code


def _patch_fixed_policy(monkeypatch, application, executable):
    """Expose a temporary fixed installation only through the in-process test seam."""
    monkeypatch.setattr(RUNTIME, "APPROVED_APP_LEXICAL", str(application))
    monkeypatch.setattr(RUNTIME, "APPROVED_EXECUTABLE_LEXICAL", str(executable))
    monkeypatch.setattr(RUNTIME, "APPROVED_KERNEL_LEXICAL", str(_kernel_path(application)))


def _codesign_record(identifier):
    return "\n".join((
        f"Identifier={identifier}",
        "TeamIdentifier=D2Y8ST33G6",
        "CDHash=" + "a" * 40,
        "Authority=Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)",
    ))


def test_fixed_application_lexical_anchor_rejects_a_symlink(tmp_path):
    target = tmp_path / "redirect_target"
    _make_executable(target / "wolframscript")
    application = tmp_path / "Wolfram Engine.app"
    application.symlink_to(target, target_is_directory=True)
    _assert_rejected(
        application, application / "wolframscript",
        "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_reviewer_redirected_approved_boundary_fails_closed_with_valid_provenance(tmp_path):
    """Faithful B5-RV3-001: the policy boundary aliases an external executable tree."""
    target = tmp_path / "redirect_target"
    _make_executable(target / "wolframscript")
    alias = tmp_path / "approved.app"
    alias.symlink_to(target, target_is_directory=True)
    _assert_rejected(
        alias, alias / "wolframscript", "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_child_component_symlink_inside_fixed_executable_path_fails_closed(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    application.mkdir()
    redirected_contents = tmp_path / "redirected_contents"
    _make_executable(
        redirected_contents / "Resources" / "Wolfram Player.app" / "Contents" / "MacOS" /
        "wolframscript")
    (application / "Contents").symlink_to(redirected_contents, target_is_directory=True)
    candidate = application / "Contents" / "Resources" / "Wolfram Player.app" / \
        "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(application, candidate, "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_ancestor_component_symlink_before_fixed_application_path_fails_closed(tmp_path):
    """No lexical ancestor may redirect the fixed application boundary."""
    target_parent = tmp_path / "target_parent"
    application = target_parent / "Wolfram Engine.app"
    executable = application / "Contents" / "Resources" / "Wolfram Player.app" / \
        "Contents" / "MacOS" / "wolframscript"
    _make_executable(executable)
    _make_executable(_kernel_path(application))
    redirected_parent = tmp_path / "redirected_parent"
    redirected_parent.symlink_to(target_parent, target_is_directory=True)
    lexical_application = redirected_parent / "Wolfram Engine.app"
    lexical_executable = lexical_application / "Contents" / "Resources" / "Wolfram Player.app" / \
        "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(
        lexical_application, lexical_executable,
        "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_genuine_temporary_fixed_installation_resolves_without_redirection(tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    assert runtime.approved_application_boundary == str(application)
    assert runtime.canonical_executable_path == str(executable)
    assert runtime.canonical_kernel_path == str(_kernel_path(application))
    assert all(identity.file_type != "symbolic_link"
               for _, identity in runtime.component_filesystem_identities)


def test_approved_application_canonicalization_cannot_redefine_lexical_anchor(tmp_path):
    application, executable = _make_installation(tmp_path)
    redirected = tmp_path / "canonical_elsewhere"
    redirected.mkdir()

    def canonicalizer(value):
        return redirected if Path(value) == application else Path(value)

    _assert_rejected(
        application, executable, "TRUSTED_RUNTIME_CANONICAL_PATH_MISMATCH",
        canonicalizer=canonicalizer)


def test_approved_executable_canonicalization_cannot_redefine_lexical_path(tmp_path):
    application, executable = _make_installation(tmp_path)
    redirected = tmp_path / "canonical_elsewhere"
    redirected.write_text("not the approved executable")

    def canonicalizer(value):
        return redirected if Path(value) == executable else Path(value)

    _assert_rejected(
        application, executable, "TRUSTED_RUNTIME_CANONICAL_PATH_MISMATCH",
        canonicalizer=canonicalizer)


def test_candidate_outside_approved_application_boundary_fails_closed(tmp_path):
    application, _ = _make_installation(tmp_path)
    outside = tmp_path / "outside" / "wolframscript"
    _make_executable(outside)
    _assert_rejected(
        application, outside, "TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")


def test_string_prefix_sibling_is_not_contained_by_the_approved_application(tmp_path):
    application, _ = _make_installation(tmp_path)
    sibling = tmp_path / "Wolfram Engine.app.evil"
    outside = sibling / "Contents" / "MacOS" / "wolframscript"
    _make_executable(outside)
    _assert_rejected(
        application, outside, "TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")


def test_redirected_executable_fails_closed_even_when_provenance_seam_is_valid(tmp_path):
    application, executable = _make_installation(tmp_path)
    redirected = tmp_path / "redirected_wolframscript"
    _make_executable(redirected)
    executable.unlink()
    executable.symlink_to(redirected)
    _assert_rejected(
        application, executable, "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_redirected_fixed_kernel_fails_closed_before_execution(tmp_path):
    application, executable = _make_installation(tmp_path)
    kernel = _kernel_path(application)
    redirected = tmp_path / "redirected_kernel"
    _make_executable(redirected)
    kernel.unlink()
    kernel.symlink_to(redirected)
    _assert_rejected(
        application, executable, "TRUSTED_RUNTIME_REDIRECTING_COMPONENT")


def test_missing_application_boundary_fails_closed(tmp_path):
    application = tmp_path / "missing.app"
    executable = application / "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNAVAILABLE")


def test_missing_executable_fails_closed(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    application.mkdir()
    executable = application / "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNAVAILABLE")


def test_wrong_fixed_executable_file_type_fails_closed(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    executable = application / "Contents" / "MacOS" / "wolframscript"
    executable.mkdir(parents=True)
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")


def test_wrong_fixed_application_file_type_fails_closed(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    application.write_text("not a bundle")
    executable = application / "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")


def test_wrong_intermediate_component_file_type_fails_closed(tmp_path):
    application = tmp_path / "Wolfram Engine.app"
    application.mkdir()
    (application / "Contents").write_text("not a directory")
    executable = application / "Contents" / "MacOS" / "wolframscript"
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")


def test_wrong_fixed_kernel_file_type_fails_closed(tmp_path):
    application, executable = _make_installation(tmp_path)
    kernel = _kernel_path(application)
    kernel.unlink()
    kernel.mkdir()
    _assert_rejected(application, executable, "TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")


def test_provenance_failure_fails_closed_after_immutable_path_validation(tmp_path):
    application, executable = _make_installation(tmp_path)

    def failing_provenance(_):
        raise RUNTIME.TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        RUNTIME._resolve_runtime_candidates(
            (str(executable),), (str(application),), failing_provenance,
            kernel_candidates=(str(_kernel_path(application)),))
    assert error.value.code == "TRUSTED_RUNTIME_PROVENANCE_FAILED"


def test_identity_change_between_resolution_and_execution_fails_before_runner(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))
    executable.unlink()
    executable.write_text("#!/bin/sh\n# replacement\nexit 0\n")
    executable.chmod(0o755)
    calls = []

    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="True\n", stderr="")

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        ENGINE.run_wolfram_code(runtime, "True", runner)
    assert error.value.code == "TRUSTED_RUNTIME_IDENTITY_CHANGED"
    assert calls == []


def test_in_place_executable_mutation_after_resolution_fails_before_runner(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    executable.write_text("#!/bin/sh\n# mutated in place\nexit 0\n")
    executable.chmod(0o755)
    calls = []

    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="True\n", stderr="")

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        ENGINE.run_wolfram_code(runtime, "True", runner)
    assert error.value.code == "TRUSTED_RUNTIME_IDENTITY_CHANGED"
    assert calls == []


def test_identity_change_during_runner_cannot_return_a_trusted_result(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))

    def runner(command, **kwargs):
        executable.unlink()
        executable.write_text("#!/bin/sh\n# replacement during launch\nexit 0\n")
        executable.chmod(0o755)
        return subprocess.CompletedProcess(command, 0, stdout="True\n", stderr="")

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        ENGINE.run_wolfram_code(runtime, "True", runner)
    assert error.value.code == "TRUSTED_RUNTIME_IDENTITY_CHANGED"


def test_launch_interval_identity_change_becomes_unknown_output(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))

    def runner(command, **kwargs):
        executable.unlink()
        executable.write_text("#!/bin/sh\n# replacement during launch\nexit 0\n")
        executable.chmod(0o755)
        return subprocess.CompletedProcess(command, 0, stdout="True\n", stderr="")

    result = ENGINE.evaluate_with_runtime(
        {
            "lhs": "x+x", "rhs": "2*x", "symbols": ["x"], "scope": "real_scalars",
            "assumptions": ["x real"], "domain": "connected: all real x",
        }, runtime, runner)
    assert result["status"] == "process_failure"
    assert result["verdict"] == "UNKNOWN"


def test_provenance_interval_mutation_cannot_become_the_stored_hash(tmp_path):
    application, executable = _make_installation(tmp_path)

    def mutating_provenance(_):
        executable.write_text("#!/bin/sh\n# changed after provenance began\nexit 0\n")
        executable.chmod(0o755)
        return _valid_provenance(None)

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        RUNTIME._resolve_runtime_candidates(
            (str(executable),), (str(application),), mutating_provenance,
            kernel_candidates=(str(_kernel_path(application)),))
    assert error.value.code == "TRUSTED_RUNTIME_IDENTITY_CHANGED"


def test_pre_execution_rechecks_the_intact_bundle_provenance(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    sealed_child = application / "Contents" / "Info.plist"
    sealed_child.write_text("trusted bundle child")
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    sealed_child.write_text("mutated after resolution")
    checks, calls = [], []

    def recheck(boundary, candidate, kernel):
        checks.append((boundary, candidate, kernel))
        if sealed_child.read_text() != "trusted bundle child":
            raise RUNTIME.TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")
        return _valid_provenance(candidate)

    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="True\n", stderr="")

    monkeypatch.setattr(RUNTIME, "_codesign_provenance", recheck)
    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        ENGINE.run_wolfram_code(runtime, "True", runner)
    assert error.value.code == "TRUSTED_RUNTIME_PROVENANCE_FAILED"
    assert checks == [(application, executable, _kernel_path(application))]
    assert calls == []


def test_descriptor_binding_rechecks_the_checked_temporary_executable_and_kernel(monkeypatch, tmp_path):
    application, executable = _make_installation(tmp_path)
    runtime = _resolve(application, executable)
    _patch_fixed_policy(monkeypatch, application, executable)
    monkeypatch.setattr(RUNTIME, "_codesign_provenance", lambda *_: _valid_provenance(None))
    resolved = RUNTIME.validate_trusted_wolfram_runtime_execution_binding(runtime)
    assert resolved["canonical_candidate"] == executable
    assert resolved["canonical_kernel"] == _kernel_path(application)


def test_codesign_and_gatekeeper_target_the_fixed_bundle_and_binaries():
    commands = []

    def runner(command, **kwargs):
        commands.append(command)
        if "-dv" not in command:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        target = command[-1]
        identifier = {
            RUNTIME.APPROVED_APP_LEXICAL: "com.wolfram.WolframEngine",
            RUNTIME.APPROVED_EXECUTABLE_LEXICAL: "wolframscript",
            RUNTIME.APPROVED_KERNEL_LEXICAL: "WolframKernel",
        }[target]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr=_codesign_record(identifier))

    provenance = RUNTIME._codesign_provenance(
        RUNTIME.APPROVED_APP_LEXICAL, RUNTIME.APPROVED_EXECUTABLE_LEXICAL,
        RUNTIME.APPROVED_KERNEL_LEXICAL, runner)
    assert provenance == _valid_provenance(None)
    assert commands[0][-1] == RUNTIME.APPROVED_APP_LEXICAL
    assert commands[1][-1] == RUNTIME.APPROVED_EXECUTABLE_LEXICAL
    assert commands[2][-1] == RUNTIME.APPROVED_KERNEL_LEXICAL
    assert commands[3] == [RUNTIME._GATEKEEPER, "--assess", "--type", "execute", "--verbose=4",
                           RUNTIME.APPROVED_APP_LEXICAL]
    assert commands[4][-1] == RUNTIME.APPROVED_APP_LEXICAL
    assert commands[5][-1] == RUNTIME.APPROVED_EXECUTABLE_LEXICAL
    assert commands[6][-1] == RUNTIME.APPROVED_KERNEL_LEXICAL


def test_gatekeeper_failure_fails_closed():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, int(command[0] == RUNTIME._GATEKEEPER),
                                           stdout="", stderr="")

    with pytest.raises(RUNTIME.TrustedRuntimeError) as error:
        RUNTIME._codesign_provenance(
            RUNTIME.APPROVED_APP_LEXICAL, RUNTIME.APPROVED_EXECUTABLE_LEXICAL,
            RUNTIME.APPROVED_KERNEL_LEXICAL, runner)
    assert error.value.code == "TRUSTED_RUNTIME_PROVENANCE_FAILED"


def test_normal_genuine_fixed_installation_has_an_immutable_lexical_identity():
    runtime = RUNTIME.resolve_trusted_wolfram_runtime()
    assert runtime.approved_application_boundary == RUNTIME.APPROVED_APP_LEXICAL
    assert runtime.canonical_executable_path == RUNTIME.APPROVED_EXECUTABLE_LEXICAL
    assert runtime.canonical_kernel_path == RUNTIME.APPROVED_KERNEL_LEXICAL
    assert runtime.application_filesystem_identity.file_type == "directory"
    assert runtime.executable_filesystem_identity.file_type == "regular_file"
    assert runtime.kernel_filesystem_identity.file_type == "regular_file"
    assert runtime.application_filesystem_identity.canonical_path == RUNTIME.APPROVED_APP_LEXICAL
    assert runtime.executable_filesystem_identity.canonical_path == RUNTIME.APPROVED_EXECUTABLE_LEXICAL
    assert runtime.kernel_filesystem_identity.canonical_path == RUNTIME.APPROVED_KERNEL_LEXICAL
    assert runtime.code_signing_team_identifier == "D2Y8ST33G6"
    assert runtime.code_signing_authority == \
        "Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)"
