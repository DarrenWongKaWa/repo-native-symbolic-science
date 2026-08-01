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
import stat
import subprocess


ENGINE_IDENTITY = "WOLFRAM_INDEPENDENT_ZERO"
IMPLEMENTATION_VERSION = "1.1"
PARSER_VERSION = "python_ast_to_wolfram_1"
SEMANTIC_PROFILE = "real_identity_zero_v1"
RESOLVER_VERSION = "trusted_wolfram_runtime_v3"

# These are source-controlled production policy, not runtime configuration.  New
# supported platforms must add another fixed candidate and an approved bundle boundary
# in a reviewed source change.
APPROVED_APP_LEXICAL = "/Applications/Wolfram Engine.app"
APPROVED_EXECUTABLE_LEXICAL = (
    "/Applications/Wolfram Engine.app/Contents/Resources/Wolfram Player.app/"
    "Contents/MacOS/wolframscript"
)
APPROVED_KERNEL_LEXICAL = (
    "/Applications/Wolfram Engine.app/Contents/Resources/Wolfram Player.app/"
    "Contents/MacOS/WolframKernel"
)
APPROVED_APPLICATION_BOUNDARIES = (
    APPROVED_APP_LEXICAL,
)
APPROVED_RUNTIME_CANDIDATES = (
    APPROVED_EXECUTABLE_LEXICAL,
)
APPROVED_KERNEL_CANDIDATES = (
    APPROVED_KERNEL_LEXICAL,
)
_CODESIGN = "/usr/bin/codesign"
_GATEKEEPER = "/usr/sbin/spctl"
_EXPECTED_IDENTIFIER = "wolframscript"
_EXPECTED_KERNEL_IDENTIFIER = "WolframKernel"
_EXPECTED_TEAM_IDENTIFIER = "D2Y8ST33G6"
_EXPECTED_AUTHORITY = "Developer ID Application: Wolfram Research, Inc (D2Y8ST33G6)"


class TrustedRuntimeError(RuntimeError):
    """A fail-closed trusted-runtime resolution error with a stable public code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FilesystemIdentity:
    """No-follow identity facts retained for one trusted runtime resolution."""

    device: int
    inode: int
    file_type: str
    canonical_path: str

    def binding(self):
        return {
            "device": self.device,
            "inode": self.inode,
            "file_type": self.file_type,
            "canonical_path": self.canonical_path,
        }


@dataclass(frozen=True)
class TrustedWolframRuntime:
    """The resolved runtime identity allowed to execute the production B3 route."""

    canonical_executable_path: str
    canonical_kernel_path: str
    approved_application_boundary: str
    executable_sha256: str
    kernel_sha256: str
    code_signing_identifier: str
    code_signing_team_identifier: str
    code_signing_cdhash: str
    code_signing_authority: str
    application_filesystem_identity: FilesystemIdentity
    executable_filesystem_identity: FilesystemIdentity
    kernel_filesystem_identity: FilesystemIdentity
    component_filesystem_identities: tuple[tuple[str, FilesystemIdentity], ...]
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

    def filesystem_identity_summary(self):
        """Return the immutable-path facts checked again immediately before execution."""
        return {
            "application": self.application_filesystem_identity.binding(),
            "executable": self.executable_filesystem_identity.binding(),
            "kernel": self.kernel_filesystem_identity.binding(),
            "components": [
                {"lexical_path": path, **identity.binding()}
                for path, identity in self.component_filesystem_identities
            ],
        }

    def binding(self):
        """Structured identity embedded in B3 output and expected configuration."""
        provenance = self.provenance_summary()
        return {
            "resolver_version": self.resolver_version,
            "canonical_executable_path": self.canonical_executable_path,
            "canonical_kernel_path": self.canonical_kernel_path,
            "approved_application_boundary": self.approved_application_boundary,
            "provenance": provenance,
            "provenance_hash": _sha(provenance),
            "kernel_sha256": self.kernel_sha256,
            "filesystem_identity": self.filesystem_identity_summary(),
        }


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_absolute_path(value):
    """Return an absolute lexical path with dot components removed.

    This intentionally does *not* resolve symlinks.  It is used before trust is
    established so containment is always component based rather than a string prefix.
    """
    try:
        candidate = Path(value)
    except (TypeError, ValueError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PATH_NOT_ABSOLUTE") from None
    if not candidate.is_absolute():
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PATH_NOT_ABSOLUTE")
    return Path(os.path.normpath(str(candidate)))


def _strict_realpath(value):
    return Path(value).resolve(strict=True)


def _canonical_existing_path(value, canonicalizer=_strict_realpath):
    """Canonicalize only after the caller has completed no-follow validation."""
    try:
        canonical = Path(canonicalizer(value))
        return _normalized_absolute_path(canonical)
    except (OSError, RuntimeError, TypeError, ValueError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None


def _inside_boundary(candidate, boundary):
    try:
        candidate.relative_to(boundary)
    except ValueError:
        return False
    return True


def _file_type(metadata):
    """Classify one no-follow stat record without treating aliases as directories."""
    mode = metadata.st_mode
    if stat.S_ISLNK(mode):
        return "symbolic_link"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "regular_file"
    return "other"


def _inspect_component_no_follow(component, expected_type, lstat_reader=os.lstat):
    """Require one lexical component to be its expected non-redirecting object type."""
    try:
        metadata = lstat_reader(str(component))
        object_type = _file_type(metadata)
    except (OSError, RuntimeError, TypeError, ValueError, AttributeError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None
    if object_type == "symbolic_link":
        raise TrustedRuntimeError("TRUSTED_RUNTIME_REDIRECTING_COMPONENT")
    if object_type != expected_type:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")
    return FilesystemIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        file_type=object_type,
        canonical_path="",
    )


def _immutable_component_paths(boundary, candidate):
    """Build the complete lexical root-to-executable component chain.

    The immutable app boundary is not enough on its own: a symbolic-link ancestor
    (for example ``/Applications``) redirects the same lexical boundary before the
    application itself is reached.  Return each lexical ancestor, including ``/``,
    so callers can inspect all of them with no-follow semantics before canonicalizing.
    """
    lexical_boundary = _normalized_absolute_path(boundary)
    lexical_candidate = _normalized_absolute_path(candidate)
    if not _inside_boundary(lexical_candidate, lexical_boundary):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")
    relative_candidate = lexical_candidate.relative_to(lexical_boundary)
    if not relative_candidate.parts:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")

    root = Path(lexical_boundary.anchor)
    components = [(root, "directory")]
    current = root
    for part in lexical_boundary.parts[1:]:
        current = current / part
        components.append((current, "directory"))

    current = lexical_boundary
    for index, part in enumerate(relative_candidate.parts):
        current = current / part
        expected_type = "regular_file" if index == len(relative_candidate.parts) - 1 else "directory"
        components.append((current, expected_type))
    return lexical_boundary, lexical_candidate, components


def _identity_with_canonical_path(identity, canonical_path):
    return FilesystemIdentity(
        device=identity.device,
        inode=identity.inode,
        file_type=identity.file_type,
        canonical_path=str(canonical_path),
    )


def _validate_immutable_runtime_paths(boundary, candidate, kernel, *, lstat_reader=os.lstat,
                                      canonicalizer=_strict_realpath):
    """Validate a source-policy app path before following any of its components.

    The configured application bundle is an immutable lexical trust anchor.  Every
    lexical component from that bundle through the configured executable is inspected
    with ``lstat`` first; canonicalization is merely an additional equality check and
    cannot redefine the policy boundary.
    """
    lexical_boundary, lexical_candidate, executable_components = _immutable_component_paths(
        boundary, candidate)
    kernel_boundary, lexical_kernel, kernel_components = _immutable_component_paths(
        boundary, kernel)
    if kernel_boundary != lexical_boundary:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")
    identities = {}
    for component, expected_type in executable_components + kernel_components:
        if component in identities:
            continue
        identities[component] = _inspect_component_no_follow(
            component, expected_type, lstat_reader)

    canonical_boundary = _canonical_existing_path(lexical_boundary, canonicalizer)
    canonical_candidate = _canonical_existing_path(lexical_candidate, canonicalizer)
    canonical_kernel = _canonical_existing_path(lexical_kernel, canonicalizer)
    if canonical_boundary != lexical_boundary or canonical_candidate != lexical_candidate or \
            canonical_kernel != lexical_kernel:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_CANONICAL_PATH_MISMATCH")
    if not _inside_boundary(canonical_candidate, canonical_boundary) or \
            not _inside_boundary(canonical_kernel, canonical_boundary):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")

    return {
        "lexical_boundary": lexical_boundary,
        "lexical_candidate": lexical_candidate,
        "lexical_kernel": lexical_kernel,
        "canonical_boundary": canonical_boundary,
        "canonical_candidate": canonical_candidate,
        "canonical_kernel": canonical_kernel,
        "application_identity": _identity_with_canonical_path(
            identities[lexical_boundary], canonical_boundary),
        "executable_identity": _identity_with_canonical_path(
            identities[lexical_candidate], canonical_candidate),
        "kernel_identity": _identity_with_canonical_path(
            identities[lexical_kernel], canonical_kernel),
        "component_identities": tuple(
            (str(component), identities[component])
            for component in identities
        ),
    }


def _codesign_fields(process):
    fields, authorities = {}, []
    # codesign intentionally writes the inspection record to stderr.
    for line in process.stderr.splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        if key == "Authority":
            authorities.append(value)
        elif key in {"Identifier", "TeamIdentifier", "CDHash"}:
            fields[key] = value
    return fields, authorities


def _codesign_provenance(approved_application_boundary, canonical_path, canonical_kernel,
                         runner=subprocess.run):
    """Verify the fixed application bundle, executable, and local kernel provenance.

    This is called only after immutable lexical-path validation.  Gatekeeper assesses
    the app bundle (the executable is not independently app-assessable), while codesign
    verifies the bundle, executable, and local kernel and extracts the executable identity.
    """
    try:
        bundle_verified = runner(
            [_CODESIGN, "--verify", "--deep", "--strict", "--verbose=2",
             str(approved_application_boundary)],
            capture_output=True, text=True, check=False)
        executable_verified = runner(
            [_CODESIGN, "--verify", "--strict", "--verbose=2", str(canonical_path)],
            capture_output=True, text=True, check=False)
        kernel_verified = runner(
            [_CODESIGN, "--verify", "--strict", "--verbose=2", str(canonical_kernel)],
            capture_output=True, text=True, check=False)
        gatekeeper = runner(
            [_GATEKEEPER, "--assess", "--type", "execute", "--verbose=4",
             str(approved_application_boundary)],
            capture_output=True, text=True, check=False)
        bundle_inspected = runner(
            [_CODESIGN, "-dv", "--verbose=4", str(approved_application_boundary)],
            capture_output=True, text=True, check=False)
        executable_inspected = runner(
            [_CODESIGN, "-dv", "--verbose=4", str(canonical_path)],
            capture_output=True, text=True, check=False)
        kernel_inspected = runner(
            [_CODESIGN, "-dv", "--verbose=4", str(canonical_kernel)],
            capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_UNAVAILABLE") from None
    if bundle_verified.returncode != 0 or executable_verified.returncode != 0 or \
            kernel_verified.returncode != 0 or \
            gatekeeper.returncode != 0 or bundle_inspected.returncode != 0 or \
            executable_inspected.returncode != 0 or kernel_inspected.returncode != 0:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")

    bundle_fields, bundle_authorities = _codesign_fields(bundle_inspected)
    fields, authorities = _codesign_fields(executable_inspected)
    kernel_fields, kernel_authorities = _codesign_fields(kernel_inspected)
    if bundle_fields.get("TeamIdentifier") != _EXPECTED_TEAM_IDENTIFIER or \
            not bundle_fields.get("CDHash") or _EXPECTED_AUTHORITY not in bundle_authorities or \
            fields.get("Identifier") != _EXPECTED_IDENTIFIER or \
            fields.get("TeamIdentifier") != _EXPECTED_TEAM_IDENTIFIER or \
            not fields.get("CDHash") or _EXPECTED_AUTHORITY not in authorities or \
            kernel_fields.get("Identifier") != _EXPECTED_KERNEL_IDENTIFIER or \
            kernel_fields.get("TeamIdentifier") != _EXPECTED_TEAM_IDENTIFIER or \
            not kernel_fields.get("CDHash") or _EXPECTED_AUTHORITY not in kernel_authorities:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_PROVENANCE_FAILED")
    return {
        "identifier": fields["Identifier"],
        "team_identifier": fields["TeamIdentifier"],
        "cdhash": fields["CDHash"],
        "authority": _EXPECTED_AUTHORITY,
    }


def _runtime_binary_hashes(canonical_candidate, canonical_kernel):
    """Hash both fixed binaries, never accepting a partial runtime identity."""
    try:
        return {
            "executable": _file_sha256(canonical_candidate),
            "kernel": _file_sha256(canonical_kernel),
        }
    except OSError:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None


def _same_resolved_filesystem_identity(left, right):
    """Compare every no-follow fact, including lexical ancestors and children."""
    return (
        left["application_identity"] == right["application_identity"] and
        left["executable_identity"] == right["executable_identity"] and
        left["kernel_identity"] == right["kernel_identity"] and
        left["component_identities"] == right["component_identities"]
    )


def _matches_trusted_runtime_identity(resolved, runtime_identity):
    return (
        resolved["application_identity"] == runtime_identity.application_filesystem_identity and
        resolved["executable_identity"] == runtime_identity.executable_filesystem_identity and
        resolved["kernel_identity"] == runtime_identity.kernel_filesystem_identity and
        resolved["component_identities"] == runtime_identity.component_filesystem_identities
    )


def _matches_trusted_runtime_provenance(provenance, runtime_identity):
    return (
        provenance.get("identifier") == runtime_identity.code_signing_identifier and
        provenance.get("team_identifier") == runtime_identity.code_signing_team_identifier and
        provenance.get("cdhash") == runtime_identity.code_signing_cdhash and
        provenance.get("authority") == runtime_identity.code_signing_authority
    )


def _fixed_lexical_runtime_paths():
    """Return the only source-policy paths a production runtime record may represent."""
    return {
        "boundary": _normalized_absolute_path(APPROVED_APP_LEXICAL),
        "candidate": _normalized_absolute_path(APPROVED_EXECUTABLE_LEXICAL),
        "kernel": _normalized_absolute_path(APPROVED_KERNEL_LEXICAL),
    }


def _require_fixed_lexical_runtime_paths(runtime_identity):
    """Reject crafted runtime records that name anything other than source policy."""
    fixed = _fixed_lexical_runtime_paths()
    try:
        record_boundary = _normalized_absolute_path(runtime_identity.approved_application_boundary)
        record_candidate = _normalized_absolute_path(runtime_identity.canonical_executable_path)
        record_kernel = _normalized_absolute_path(runtime_identity.canonical_kernel_path)
    except TrustedRuntimeError:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_FIXED_PATH_MISMATCH") from None
    if record_boundary != fixed["boundary"] or record_candidate != fixed["candidate"] or \
            record_kernel != fixed["kernel"]:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_FIXED_PATH_MISMATCH")
    return fixed


def _descriptor_sha256(descriptor):
    """Hash a duplicated descriptor so no pathname can change the bytes being checked."""
    digest = hashlib.sha256()
    try:
        with os.fdopen(os.dup(descriptor), "rb") as handle:
            handle.seek(0)
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None
    return digest.hexdigest()


def _require_descriptor_identity(descriptor, expected_identity):
    try:
        metadata = os.fstat(descriptor)
    except OSError:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE") from None
    if _file_type(metadata) != expected_identity.file_type or \
            metadata.st_dev != expected_identity.device or metadata.st_ino != expected_identity.inode:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")


def _open_immutable_component_chain(path, component_identities):
    """Open one fixed path through descriptor-relative, no-follow components.

    ``lstat`` plus a later pathname open leaves a final path-rebinding window.  This
    traversal pins each lexical ancestor with an opened directory descriptor and checks
    the recorded device/inode/type before descending to the next component.  The caller
    receives the final regular-file descriptor, not a path that can be redirected later.
    """
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_SECURE_OPEN_UNAVAILABLE")
    lexical_path = _normalized_absolute_path(path)
    expected_by_path = dict(component_identities)
    root = Path(lexical_path.anchor)
    descriptor = None
    try:
        descriptor = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        expected = expected_by_path.get(str(root))
        if expected is None:
            raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
        _require_descriptor_identity(descriptor, expected)
        current = root
        parts = lexical_path.parts[1:]
        for index, part in enumerate(parts):
            next_path = current / part
            is_leaf = index == len(parts) - 1
            flags = os.O_NOFOLLOW | os.O_RDONLY
            if not is_leaf:
                flags |= os.O_DIRECTORY
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
            expected = expected_by_path.get(str(next_path))
            if expected is None:
                raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
            _require_descriptor_identity(descriptor, expected)
            current = next_path
        if _file_type(os.fstat(descriptor)) != "regular_file":
            raise TrustedRuntimeError("TRUSTED_RUNTIME_UNEXPECTED_FILE_TYPE")
        return descriptor
    except TrustedRuntimeError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
        raise TrustedRuntimeError("TRUSTED_RUNTIME_SECURE_OPEN_FAILED") from None


def _resolve_runtime_candidates(candidates, boundaries, provenance_reader=None, *,
                                kernel_candidates=APPROVED_KERNEL_CANDIDATES,
                                lstat_reader=os.lstat, canonicalizer=_strict_realpath):
    """Resolve source-controlled candidates; injectable only for focused unit tests.

    Production calls this with no arguments beyond source constants.  The optional
    readers exist solely as an in-process test seam and are not reachable from CLI,
    environment, request, claim, certificate, or stored evidence inputs.
    """
    for configured_candidate in candidates:
        candidate = _normalized_absolute_path(configured_candidate)
        matching_boundaries = []
        for configured_boundary in boundaries:
            boundary = _normalized_absolute_path(configured_boundary)
            if _inside_boundary(candidate, boundary):
                matching_boundaries.append(boundary)
        if not matching_boundaries:
            raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")

        for boundary in matching_boundaries:
            matching_kernels = [
                _normalized_absolute_path(configured_kernel)
                for configured_kernel in kernel_candidates
                if _inside_boundary(_normalized_absolute_path(configured_kernel), boundary)
            ]
            if not matching_kernels:
                raise TrustedRuntimeError("TRUSTED_RUNTIME_OUTSIDE_APPROVED_BOUNDARY")
            if len(matching_kernels) != 1:
                raise TrustedRuntimeError("TRUSTED_RUNTIME_AMBIGUOUS_KERNEL")
            kernel = matching_kernels[0]
            try:
                resolved = _validate_immutable_runtime_paths(
                    boundary, candidate, kernel, lstat_reader=lstat_reader,
                    canonicalizer=canonicalizer)
            except TrustedRuntimeError as error:
                # A missing platform-specific installation may leave another reviewed
                # candidate available; every redirect, type, canonical, or containment
                # failure is a hard stop and can never trigger a fallback.
                if error.code == "TRUSTED_RUNTIME_UNAVAILABLE":
                    continue
                raise

            canonical_candidate = resolved["canonical_candidate"]
            if not os.access(canonical_candidate, os.X_OK):
                raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE")
            # Establish a byte identity *before* provenance inspection.  A mutation
            # during or after signature/Gatekeeper checks must never become the stored
            # trusted hash merely because it kept its inode and pathname.
            initial_hashes = _runtime_binary_hashes(
                canonical_candidate, resolved["canonical_kernel"])
            if provenance_reader is None:
                provenance = _codesign_provenance(
                    resolved["lexical_boundary"], canonical_candidate,
                    resolved["canonical_kernel"])
            else:
                provenance = provenance_reader(canonical_candidate)

            # Bind provenance to the byte snapshot.  Both no-follow facts and content
            # hashes must survive the signature/Gatekeeper interval before resolution
            # can yield a runtime record.
            current = _validate_immutable_runtime_paths(
                boundary, candidate, kernel, lstat_reader=lstat_reader,
                canonicalizer=canonicalizer)
            if not _same_resolved_filesystem_identity(current, resolved) or \
                    _runtime_binary_hashes(
                        current["canonical_candidate"], current["canonical_kernel"]) != initial_hashes:
                raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")

            # Repeat no-follow inspection after the post-provenance hash.  A later
            # byte mutation retains the original hash in the returned record and is
            # rejected by the mandatory pre-execution validation below.
            ready = _validate_immutable_runtime_paths(
                boundary, candidate, kernel, lstat_reader=lstat_reader,
                canonicalizer=canonicalizer)
            if not _same_resolved_filesystem_identity(ready, resolved):
                raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
            return TrustedWolframRuntime(
                canonical_executable_path=str(ready["canonical_candidate"]),
                canonical_kernel_path=str(ready["canonical_kernel"]),
                approved_application_boundary=str(ready["canonical_boundary"]),
                executable_sha256=initial_hashes["executable"],
                kernel_sha256=initial_hashes["kernel"],
                code_signing_identifier=provenance["identifier"],
                code_signing_team_identifier=provenance["team_identifier"],
                code_signing_cdhash=provenance["cdhash"],
                code_signing_authority=provenance["authority"],
                application_filesystem_identity=ready["application_identity"],
                executable_filesystem_identity=ready["executable_identity"],
                kernel_filesystem_identity=ready["kernel_identity"],
                component_filesystem_identities=ready["component_identities"],
            )
    raise TrustedRuntimeError("TRUSTED_RUNTIME_UNAVAILABLE")


def resolve_trusted_wolfram_runtime():
    """Resolve the one production Wolfram runtime; no caller input is accepted."""
    return _resolve_runtime_candidates(
        APPROVED_RUNTIME_CANDIDATES, APPROVED_APPLICATION_BOUNDARIES,
        kernel_candidates=APPROVED_KERNEL_CANDIDATES)


def validate_trusted_wolfram_runtime_identity(runtime_identity):
    """Fail closed if the lexical trust anchor changed before execution.

    ``TrustedWolframRuntime`` instances are created by the resolver in production.  This
    helper replays the fixed source policy, no-follow/canonical checks, complete signed
    bundle provenance, Gatekeeper assessment, and byte hashes immediately before use.
    """
    if not isinstance(runtime_identity, TrustedWolframRuntime):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_INVALID")
    fixed = _require_fixed_lexical_runtime_paths(runtime_identity)
    current = _validate_immutable_runtime_paths(
        fixed["boundary"], fixed["candidate"], fixed["kernel"])
    if not _matches_trusted_runtime_identity(current, runtime_identity):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
    hashes_before_provenance = _runtime_binary_hashes(
        current["canonical_candidate"], current["canonical_kernel"])
    if hashes_before_provenance != {
            "executable": runtime_identity.executable_sha256,
            "kernel": runtime_identity.kernel_sha256}:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")

    provenance = _codesign_provenance(
        current["lexical_boundary"], current["canonical_candidate"],
        current["canonical_kernel"])
    if not _matches_trusted_runtime_provenance(provenance, runtime_identity):
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")

    after_provenance = _validate_immutable_runtime_paths(
        fixed["boundary"], fixed["candidate"], fixed["kernel"])
    if not _matches_trusted_runtime_identity(after_provenance, runtime_identity) or \
            _runtime_binary_hashes(
                after_provenance["canonical_candidate"], after_provenance["canonical_kernel"]) != \
            hashes_before_provenance:
        raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
    return after_provenance


def validate_trusted_wolfram_runtime_execution_binding(runtime_identity):
    """Perform the last no-follow descriptor and hash binding before fixed-path execution.

    macOS does not permit the signed Mach-O runtime to be executed through ``/dev/fd``;
    production therefore executes the mandated fixed lexical path after this guard rather
    than switching to an alternate engine.  The guard still resolves every component by
    descriptor relative to its already-open parent and verifies the exact bytes reached by
    that traversal after the full bundle codesign/Gatekeeper recheck.
    """
    resolved = validate_trusted_wolfram_runtime_identity(runtime_identity)
    executable_descriptor = _open_immutable_component_chain(
        resolved["lexical_candidate"], runtime_identity.component_filesystem_identities)
    kernel_descriptor = None
    try:
        kernel_descriptor = _open_immutable_component_chain(
            resolved["lexical_kernel"], runtime_identity.component_filesystem_identities)
        if _descriptor_sha256(executable_descriptor) != runtime_identity.executable_sha256 or \
                _descriptor_sha256(kernel_descriptor) != runtime_identity.kernel_sha256:
            raise TrustedRuntimeError("TRUSTED_RUNTIME_IDENTITY_CHANGED")
        return resolved
    except Exception:
        raise
    finally:
        os.close(executable_descriptor)
        if kernel_descriptor is not None:
            os.close(kernel_descriptor)


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
