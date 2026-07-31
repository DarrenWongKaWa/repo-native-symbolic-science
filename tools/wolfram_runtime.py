"""Trusted B3 Wolfram runtime resolution and configuration binding.

This module deliberately has no environment, request, command-line, certificate, or
evidence input.  Production B3 execution can use only a repository-controlled,
canonical path inside an approved Wolfram application bundle.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess


ENGINE_IDENTITY = "WOLFRAM_INDEPENDENT_ZERO"
IMPLEMENTATION_VERSION = "1.1"
PARSER_VERSION = "python_ast_to_wolfram_1"
SEMANTIC_PROFILE = "real_identity_zero_v1"
RESOLVER_VERSION = "trusted_wolfram_runtime_v1"

# These are source-controlled production policy, not runtime configuration.  New
# supported platforms must add another fixed candidate and an approved bundle boundary
# in a reviewed source change.
APPROVED_APPLICATION_BOUNDARIES = (
    "/Applications/Wolfram Engine.app",
)
APPROVED_RUNTIME_CANDIDATES = (
    "/Applications/Wolfram Engine.app/Contents/Resources/Wolfram Player.app/"
    "Contents/MacOS/wolframscript",
)
_CODESIGN = "/usr/bin/codesign"
_EXPECTED_IDENTIFIER = "wolframscript"
_EXPECTED_TEAM_IDENTIFIER = "D2Y8ST33G6"
_EXPECTED_AUTHORITY = "Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)"


class TrustedRuntimeError(RuntimeError):
    """A fail-closed trusted-runtime resolution error with a stable public code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TrustedWolframRuntime:
    """The resolved runtime identity allowed to execute the production B3 route."""

    canonical_executable_path: str
    approved_application_boundary: str
    executable_sha256: str
    code_signing_identifier: str
    code_signing_team_identifier: str
    code_signing_cdhash: str
    code_signing_authority: str
    resolver_version: str = RESOLVER_VERSION

    def provenance_summary(self):
        """Return only deterministic, independently verified provenance facts."""
        return {
            "executable_sha256": self.executable_sha256,
            "codesign_identifier": self.code_signing_identifier,
            "codesign_team_identifier": self.code_signing_team_identifier,
            "codesign_cdhash": self.code_signing_cdhash,
            "codesign_authority": self.code_signing_authority,
        }

    def binding(self):
        """Structured identity embedded in B3 output and expected configuration."""
        provenance = self.provenance_summary()
        return {
            "resolver_version": self.resolver_version,
            "canonical_executable_path": self.canonical_executable_path,
            "approved_application_boundary": self.approved_application_boundary,
            "provenance": provenance,
            "provenance_hash": _sha(provenance),
        }


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_existing_path(value):
    path = Path(value)
    if not path.is_absolute():
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PATH_NOT_ABSOLUTE")
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None


def _inside_boundary(candidate, boundary):
    try:
        candidate.relative_to(boundary)
    except ValueError:
        return False
    return True


def _codesign_provenance(canonical_path):
    """Verify the local Apple code signature without using caller-controlled PATH."""
    try:
        verified = subprocess.run(
            [_CODESIGN, "--verify", "--strict", "--verbose=2", str(canonical_path)],
            capture_output=True, text=True, check=False)
        inspected = subprocess.run(
            [_CODESIGN, "-dv", "--verbose=4", str(canonical_path)],
            capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_UNAVAILABLE") from None
    if verified.returncode != 0 or inspected.returncode != 0:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")

    fields, authorities = {}, []
    # codesign intentionally writes the inspection record to stderr.
    for line in inspected.stderr.splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        if key == "Authority":
            authorities.append(value)
        elif key in {"Identifier", "TeamIdentifier", "CDHash"}:
            fields[key] = value
    if fields.get("Identifier") != _EXPECTED_IDENTIFIER or \
            fields.get("TeamIdentifier") != _EXPECTED_TEAM_IDENTIFIER or \
            not fields.get("CDHash") or _EXPECTED_AUTHORITY not in authorities:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")
    return {
        "identifier": fields["Identifier"],
        "team_identifier": fields["TeamIdentifier"],
        "cdhash": fields["CDHash"],
        "authority": _EXPECTED_AUTHORITY,
    }


def _resolve_runtime_candidates(candidates, boundaries, provenance_reader=_codesign_provenance):
    """Resolve source-controlled candidates; injectable only for focused unit tests."""
    canonical_boundaries = []
    for boundary in boundaries:
        try:
            canonical_boundaries.append(_canonical_existing_path(boundary))
        except TrustedRuntimeError:
            # A missing platform-specific boundary is not an alternate executable source.
            continue
    if not canonical_boundaries:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE")

    for configured_candidate in candidates:
        candidate = Path(configured_candidate)
        if not candidate.is_absolute():
            raise TrustedRuntimeError("TRUSTED_RUNTIME_PATH_NOT_ABSOLUTE")
        try:
            canonical_candidate = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        matching_boundaries = [
            boundary for boundary in canonical_boundaries
            if _inside_boundary(canonical_candidate, boundary)
        ]
        if not matching_boundaries:
            raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")
        if not canonical_candidate.is_file() or not os.access(canonical_candidate, os.X_OK):
            raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE")
        provenance = provenance_reader(canonical_candidate)
        boundary = matching_boundaries[0]
        return TrustedWolframRuntime(
            canonical_executable_path=str(canonical_candidate),
            approved_application_boundary=str(boundary),
            executable_sha256=_file_sha256(canonical_candidate),
            code_signing_identifier=provenance["identifier"],
            code_signing_team_identifier=provenance["team_identifier"],
            code_signing_cdhash=provenance["cdhash"],
            code_signing_authority=provenance["authority"],
        )
    raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE")


def resolve_trusted_wolfram_runtime():
    """Resolve the one production Wolfram runtime; no caller input is accepted."""
    return _resolve_runtime_candidates(
        APPROVED_RUNTIME_CANDIDATES, APPROVED_APPLICATION_BOUNDARIES)


def build_expected_configuration(runtime_identity):
    """Derive B3's expected configuration only from source policy and trusted facts."""
    if not isinstance(runtime_identity, TrustedWolframRuntime):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_INVALID")
    return {
        "engine_identity": ENGINE_IDENTITY,
        "implementation_version": IMPLEMENTATION_VERSION,
        "parser_version": PARSER_VERSION,
        "semantic_profile": SEMANTIC_PROFILE,
        "resolver_version": RESOLVER_VERSION,
        "canonical_executable_path": runtime_identity.canonical_executable_path,
        "trusted_runtime": runtime_identity.binding(),
    }


def expected_configuration_hash(runtime_identity):
    return _sha(build_expected_configuration(runtime_identity))
