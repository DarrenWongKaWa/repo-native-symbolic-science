#!/usr/bin/env python3
"""Raw-to-compact candidate loop for a narrow Wolfram `Sum` fixture.

The external proposer is deliberately untrusted: it receives the raw expression
and returns JSON *plans*, never code.  This script independently parses the
frozen raw text, validates each plan, and emits a compact Wolfram candidate only
when every structural gate passes.  No expected compact formula is read by the
verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shlex
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from loop_engine.scientific_compactification import core as scientific_loop

DEFAULT_RAW = HERE / "raw" / "synthetic_unknown_tensor.wl"
SOURCE_MANIFEST = HERE / "SOURCE_MANIFEST.json"
DEFAULT_OUTPUT = HERE / "out"
MAX_CANDIDATES = 8
MAX_BACKEND_OUTPUT_BYTES = 64_000
BACKEND_TIMEOUT_SECONDS = 180


class DemoError(Exception):
    """A fail-closed input, proposer, or structural-verification error."""


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_raw(raw_path, manifest_path=SOURCE_MANIFEST):
    """Load bytes first, and pin the committed public fixture to its manifest."""
    raw_bytes = raw_path.read_bytes()
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DemoError("RAW_NOT_UTF8") from error
    raw_sha256 = sha256_bytes(raw_bytes)
    provenance = "EXTERNAL_UNPINNED"
    if raw_path.resolve() == DEFAULT_RAW.resolve():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise DemoError("SOURCE_MANIFEST_UNAVAILABLE") from error
        if (manifest.get("raw_source") != "raw/" + DEFAULT_RAW.name or
                manifest.get("raw_sha256") != raw_sha256 or
                manifest.get("raw_bytes") != len(raw_bytes)):
            raise DemoError("SOURCE_MANIFEST_MISMATCH")
        provenance = "MANIFEST_LOCKED_PUBLIC_FIXTURE"
    return raw, raw_bytes, raw_sha256, provenance


def split_top_level(text, delimiter):
    """Split at a Wolfram delimiter only when no brackets are open."""
    pieces = []
    start = 0
    stack = []
    pairs = {"[": "]", "(": ")", "{": "}"}
    closers = set(pairs.values())
    index = 0
    while index < len(text):
        if text.startswith("(*", index):
            end = text.find("*)", index + 2)
            if end == -1:
                raise DemoError("RAW_UNCLOSED_WOLFRAM_COMMENT")
            index = end + 2
            continue
        char = text[index]
        if char in pairs:
            stack.append(pairs[char])
        elif char in closers:
            if not stack or char != stack.pop():
                raise DemoError("RAW_UNBALANCED_DELIMITERS")
        elif char == delimiter and not stack:
            pieces.append(text[start:index].strip())
            start = index + 1
        index += 1
    if stack:
        raise DemoError("RAW_UNBALANCED_DELIMITERS")
    pieces.append(text[start:].strip())
    return pieces


def function_body(expression, head):
    prefix = head + "["
    if not expression.startswith(prefix) or not expression.endswith("]"):
        raise DemoError("RAW_EXPECTED_" + head.upper())
    return expression[len(prefix):-1]


def assignment_rhs(raw):
    """Return the assigned expression, retaining all internal source bytes."""
    offset = 0
    while raw[offset:].lstrip().startswith("(*"):
        offset += len(raw[offset:]) - len(raw[offset:].lstrip())
        end = raw.find("*)", offset + 2)
        if end == -1:
            raise DemoError("RAW_UNCLOSED_WOLFRAM_COMMENT")
        offset = end + 2
    assignment = raw.find("=", offset)
    if assignment == -1:
        raise DemoError("RAW_ASSIGNMENT_MISSING")
    rhs = raw[assignment + 1:].strip()
    if not rhs.endswith(";"):
        raise DemoError("RAW_TERMINATING_SEMICOLON_MISSING")
    return rhs[:-1].strip()


def iterator_variables(iterators):
    variables = []
    for iterator in iterators:
        if not iterator.startswith("{") or not iterator.endswith("}"):
            raise DemoError("RAW_SUM_ITERATOR_MALFORMED")
        parts = split_top_level(iterator[1:-1], ",")
        if not parts or not parts[0]:
            raise DemoError("RAW_SUM_ITERATOR_MALFORMED")
        variables.append(parts[0])
    return variables


def parse_raw(raw):
    """Parse only the structural boundaries needed for the restricted demo."""
    rhs = assignment_rhs(raw)
    source_terms = split_top_level(rhs, "+")
    terms = []
    for position, source_term in enumerate(source_terms):
        sum_args = split_top_level(function_body(source_term, "Sum"), ",")
        if len(sum_args) < 2:
            raise DemoError("RAW_SUM_MALFORMED")
        factors = split_top_level(sum_args[0], "*")
        if len(factors) < 2:
            raise DemoError("RAW_SUM_HAS_TOO_FEW_FACTORS")
        iterators = sum_args[1:]
        terms.append({
            "position": position,
            "source": source_term,
            "factors": factors,
            "iterators": iterators,
            "iterator_variables": iterator_variables(iterators),
        })
    return {"rhs": rhs, "terms": terms}


def proposer_envelope(raw, raw_sha256, n_candidates):
    """The only input given to the untrusted language-model backend."""
    return {
        "task": "raw_structural_compaction",
        "claim_boundary": (
            "Propose data-only grouping plans. Do not claim mathematical or scientific "
            "correctness; an independent structural verifier will decide."
        ),
        "raw_expression_sha256": raw_sha256,
        "raw_expression": raw,
        "candidate_protocol": {
            "response": "JSON array with at most n_candidates entries",
            "candidate": {
                "candidate_id": "short unique string",
                "groups": [
                    {
                        "term_indices": "two source Sum positions",
                        "kernel_factor_index": "shared final product-factor position",
                        "common_prefix_factor_count": (
                            "number of identical leading factors to factor outside "
                            "the parenthesized sum"
                        ),
                    }
                ],
                "note": "optional short rationale",
            },
            "constraints": [
                "Every source term must occur exactly once across groups.",
                "Each group must contain exactly two terms.",
                "Do not emit Wolfram, Python, Markdown, shell commands, or prose outside JSON.",
            ],
        },
        "n_candidates": n_candidates,
    }


def call_proposer(command, envelope, n_candidates):
    """Call the configured model backend; its stdout is candidate data, never code."""
    if not command:
        raise DemoError("PROPOSER_BACKEND_NOT_CONFIGURED")
    try:
        argv = shlex.split(command)
    except ValueError as error:
        raise DemoError("PROPOSER_COMMAND_MALFORMED") from error
    if not argv:
        raise DemoError("PROPOSER_BACKEND_NOT_CONFIGURED")
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        process.stdin.write(json.dumps(envelope).encode("utf-8"))
        process.stdin.close()
    except OSError as error:
        raise DemoError("PROPOSER_BACKEND_UNAVAILABLE") from error

    chunks = []
    byte_count = 0
    deadline = time.monotonic() + BACKEND_TIMEOUT_SECONDS
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise DemoError("PROPOSER_BACKEND_TIMEOUT")
            ready, _, _ = select.select([process.stdout], [], [], remaining)
            if not ready:
                process.kill()
                process.wait()
                raise DemoError("PROPOSER_BACKEND_TIMEOUT")
            chunk = os.read(process.stdout.fileno(), min(8192, MAX_BACKEND_OUTPUT_BYTES + 1 - byte_count))
            if not chunk:
                break
            chunks.append(chunk)
            byte_count += len(chunk)
            if byte_count > MAX_BACKEND_OUTPUT_BYTES:
                process.kill()
                process.wait()
                raise DemoError("PROPOSER_OUTPUT_TOO_LARGE")
        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.wait()
        raise DemoError("PROPOSER_BACKEND_TIMEOUT") from error
    finally:
        process.stdout.close()
    if returncode != 0:
        raise DemoError("PROPOSER_BACKEND_FAILED")
    try:
        response = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as error:
        raise DemoError("PROPOSER_OUTPUT_NOT_UTF8") from error
    try:
        candidates = json.loads(response)
    except json.JSONDecodeError as error:
        raise DemoError("PROPOSER_OUTPUT_NOT_JSON") from error
    if not isinstance(candidates, list) or not candidates:
        raise DemoError("PROPOSER_OUTPUT_NOT_CANDIDATE_LIST")
    if len(candidates) > MAX_CANDIDATES or len(candidates) > n_candidates:
        raise DemoError("PROPOSER_OUTPUT_TOO_MANY_CANDIDATES")
    return candidates


def _diagnostic(candidate, code, detail):
    candidate_id = candidate.get("candidate_id") if isinstance(candidate, dict) else None
    return {
        "candidate_id": candidate_id or "unnamed-candidate",
        "node_status": "DIAGNOSTIC",
        "verdict": code,
        "detail": detail,
    }


def verify_candidate(candidate, parsed):
    """Independently validate a proposed compactification against the raw AST.

    The verifier contains no expected term positions, kernel hashes, or target
    compact formula.  It accepts any plan that exactly covers the raw source and
    meets the declared structural factorization rules.
    """
    if not isinstance(candidate, dict):
        return _diagnostic({}, "CANDIDATE_NOT_OBJECT", "candidate is not a JSON object")
    candidate_id = candidate.get("candidate_id")
    groups = candidate.get("groups")
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", candidate_id):
        return _diagnostic(
            candidate, "CANDIDATE_ID_MALFORMED",
            "candidate_id must use 1-64 ASCII letters, digits, dot, underscore, or hyphen",
        )
    if not isinstance(groups, list) or not groups:
        return _diagnostic(candidate, "CANDIDATE_GROUPS_MALFORMED", "groups must be nonempty")

    terms = parsed["terms"]
    covered = []
    compiled_groups = []
    for group_number, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            return _diagnostic(candidate, "GROUP_NOT_OBJECT", "group %d is not an object" % group_number)
        indices = group.get("term_indices")
        kernel_index = group.get("kernel_factor_index")
        prefix_count = group.get("common_prefix_factor_count", 0)
        if (not isinstance(indices, list) or len(indices) != 2 or
                not all(type(item) is int for item in indices)):
            return _diagnostic(candidate, "GROUP_TERM_INDICES_MALFORMED", "each group needs two integers")
        if indices != sorted(indices):
            return _diagnostic(candidate, "GROUP_ORDER_NOT_SOURCE_ORDER", "groups must preserve source order")
        if len(set(indices)) != 2 or any(index < 0 or index >= len(terms) for index in indices):
            return _diagnostic(candidate, "GROUP_TERM_INDEX_OUT_OF_RANGE", "source term index invalid")
        if type(kernel_index) is not int or type(prefix_count) is not int:
            return _diagnostic(candidate, "GROUP_FACTOR_INDEX_MALFORMED", "factor indexes must be integers")
        left, right = (terms[indices[0]], terms[indices[1]])
        if left["iterators"] != right["iterators"]:
            return _diagnostic(candidate, "ITERATOR_DOMAIN_MISMATCH", "paired sums have different iterators")
        if kernel_index != len(left["factors"]) - 1 or kernel_index != len(right["factors"]) - 1:
            return _diagnostic(candidate, "KERNEL_NOT_FINAL_FACTOR", "kernel must be the final factor in both terms")
        if left["factors"][kernel_index] != right["factors"][kernel_index]:
            return _diagnostic(candidate, "KERNEL_LITERAL_MISMATCH", "proposed kernel bodies differ")
        if prefix_count < 0 or prefix_count >= kernel_index:
            return _diagnostic(candidate, "COMMON_PREFIX_OUT_OF_RANGE", "common prefix leaves no grouped factor")
        if left["factors"][:prefix_count] != right["factors"][:prefix_count]:
            return _diagnostic(candidate, "COMMON_PREFIX_LITERAL_MISMATCH", "leading factors differ")
        covered.extend(indices)
        compiled_groups.append({
            "term_indices": indices,
            "kernel": left["factors"][kernel_index],
            "kernel_sha256": sha256_text(left["factors"][kernel_index]),
            "prefix": left["factors"][:prefix_count],
            "left_remainder": left["factors"][prefix_count:kernel_index],
            "right_remainder": right["factors"][prefix_count:kernel_index],
            "iterators": left["iterators"],
            "iterator_variables": left["iterator_variables"],
        })

    if covered != list(range(len(terms))):
        return _diagnostic(
            candidate, "TERM_SOURCE_ORDER_NOT_EXACT",
            "groups must cover each source term exactly once in source order",
        )
    return {
        "candidate_id": candidate_id,
        "node_status": "STRUCTURAL_CERTIFIED",
        "verdict": "PASS",
        "detail": "all candidate groups replay from byte-identical raw components",
        "compiled_groups": compiled_groups,
    }


def _join_factors(factors):
    return "*".join(factors)


def compact_wolfram(raw_sha256, candidate_id, groups):
    """Render only a structurally certified plan, preserving kernel bytes verbatim."""
    lines = [
        "(* STRUCTURAL_CERTIFIED compactification candidate. *)",
        "(* Raw SHA-256: %s *)" % raw_sha256,
        "(* Candidate ID: %s *)" % candidate_id,
        "(* This is a structural candidate, not a scientific theorem or a Gamma expansion. *)",
        "",
        "ClearAll[%s];" % ", ".join(
            ["RawKernel%d" % index for index in range(1, len(groups) + 1)] + ["CompactUnknownRawTensorABC"]
        ),
        "",
    ]
    for index, group in enumerate(groups, start=1):
        args = ", ".join(variable + "_" for variable in group["iterator_variables"])
        lines.append("RawKernel%d[%s] := %s;" % (index, args, group["kernel"]))
        lines.append("")
    rendered_sums = []
    for index, group in enumerate(groups, start=1):
        prefix = _join_factors(group["prefix"])
        left = _join_factors(group["left_remainder"])
        right = _join_factors(group["right_remainder"])
        grouped = "(%s + %s)" % (left, right)
        if prefix:
            grouped = prefix + "*" + grouped
        grouped += "*RawKernel%d[%s]" % (index, ", ".join(group["iterator_variables"]))
        rendered_sums.append("Sum[%s, %s]" % (grouped, ", ".join(group["iterators"])))
    lines.append("CompactUnknownRawTensorABC =\n  " + " +\n  ".join(rendered_sums) + ";")
    return "\n".join(lines) + "\n"


def replay_rendered_candidate(parsed, raw_sha256, candidate_id, groups, rendered):
    """Post-render gate: replay the certified plan back to the raw source.

    This is deliberately not a Wolfram evaluation or a scientific proof.  It
    verifies that the bytes written to `compact_candidate.wl` are exactly the
    compact template generated from the accepted plan, then re-expands that
    plan from its raw components and compares every source summand literally.
    """
    expected = compact_wolfram(raw_sha256, candidate_id, groups)
    replayed_terms = []
    for group in groups:
        for remainder in (group["left_remainder"], group["right_remainder"]):
            factors = group["prefix"] + remainder + [group["kernel"]]
            replayed_terms.append(
                "Sum[%s, %s]" % (_join_factors(factors), ", ".join(group["iterators"]))
            )
    raw_terms = [term["source"] for term in parsed["terms"]]
    return {
        "rendered_template_literal_match": rendered == expected,
        "replayed_term_sequence_literal_match": replayed_terms == raw_terms,
        "replayed_rhs_literal_match": " + ".join(replayed_terms) == parsed["rhs"],
    }


def chain_hash(record):
    canonical = {key: value for key, value in record.items() if key != "node_sha256"}
    return sha256_text(json.dumps(canonical, sort_keys=True, separators=(",", ":")))


def write_json_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def target_architecture_state(raw_path, raw_sha256, raw_provenance, proposer_id,
                              selected, compact_text, parent_node_sha256):
    """Map this narrow demo into the repo-wide target architecture.

    Structural replay is intentionally recorded as *pending* independent
    verification.  The demo's own process must not turn its replay result into
    an exact CAS residual verdict or automatically select a next C_i node.
    """
    contract = scientific_loop.build_contract({
        "schema_version": "1.0",
        "loop_id": "raw-compaction-" + raw_sha256[:16],
        "scientific_contract": {
            "scope": "STRUCTURAL_ONLY",
            "scientific_invention_forbidden": True,
            "definitions": [],
            "index_semantics": [],
            "assumptions": [],
            "authorized_carrier_definitions": [
                "RawKernel%d" % index for index, _ in enumerate(
                    (selected or {}).get("compiled_groups", []), start=1
                )
            ],
            "declared_claim_scope": "STRUCTURAL_ONLY",
            "allowed_operations": ["finite_sum_distributivity"],
            "forbidden_operations": [
                "scientific_interpretation", "gamma_expansion", "limit_reordering",
                "integration_by_parts", "tensor_symmetry_assumption", "canonical_promotion"
            ],
            "preferences": [],
            "stopping_rule": "human_selection_after_independent_zero_residual",
        },
        "current_representation": {
            "representation_id": "C0-raw-" + raw_sha256[:16],
            "format": "wolfram_sum_expression",
            "content_sha256": raw_sha256,
            "status": "RAW_INGESTED",
            "source_path": str(raw_path),
            "provenance_status": raw_provenance,
        },
        "verification_policy": {
            "independent_verifier_required": True,
            "accepted_backends": ["sympy", "mathematica", "wolfram"],
        },
        "selection_policy": {"human_selection_required": True},
    })
    if selected is None:
        return {"contract": contract, "status": "NO_PROPOSAL"}
    candidate = scientific_loop.build_candidate(contract, {
        "candidate_id": selected["candidate_id"],
        "parent_representation_id": contract["current_representation"]["representation_id"],
        "candidate_representation": {
            "representation_id": "candidate-" + sha256_text(compact_text)[:16],
            "format": "wolfram_compact_candidate",
            "content_sha256": sha256_text(compact_text),
            "status": "CANDIDATE",
        },
        "proposer_id": proposer_id or "unspecified-external-backend",
        "carrier_definitions": [
            "RawKernel%d" % index for index, _ in enumerate(selected["compiled_groups"], start=1)
        ],
        "identities_used": ["finite_sum_distributivity"],
        "claimed_scope": "STRUCTURAL_ONLY",
    })
    pending = scientific_loop.pending_independent_verification(
        contract, candidate,
        "Raw-text replay is executor-local structural evidence; no independent CAS residual was supplied.",
    )
    gate = scientific_loop.blocked_selection_gate(contract, candidate, pending)
    return {
        "contract": contract,
        "candidate": candidate,
        "verification": pending,
        "selection_gate": gate,
        "chain_node": scientific_loop.build_pending_chain_node(
            contract, candidate, pending, parent_node_sha256
        ),
        "status": "PENDING_INDEPENDENT_VERIFICATION",
    }


def run_loop(raw_path, proposer_command, output_dir, n_candidates, proposer_id=None,
             emit_external_wolfram=False):
    raw, raw_bytes, raw_sha256, raw_provenance = load_raw(raw_path)
    parsed = parse_raw(raw)
    envelope = proposer_envelope(raw, raw_sha256, n_candidates)
    candidates = call_proposer(proposer_command, envelope, n_candidates)

    raw_node = {
        "node_type": "RAW_INGESTED",
        "raw_path": str(raw_path),
        "raw_sha256": raw_sha256,
        "raw_bytes": len(raw_bytes),
        "provenance_status": raw_provenance,
        "top_level_sum_count": len(parsed["terms"]),
        "timestamp_utc": utc_now(),
    }
    raw_node["node_sha256"] = chain_hash(raw_node)
    nodes = [raw_node]
    selected = None
    for position, candidate in enumerate(candidates, start=1):
        verdict = verify_candidate(candidate, parsed)
        node = {
            "node_type": "PROPOSED_COMPACTION",
            "position": position,
            "parent_node_sha256": raw_node["node_sha256"],
            "candidate": candidate,
            "candidate_sha256": sha256_text(json.dumps(candidate, sort_keys=True)),
            "verdict": verdict,
            "timestamp_utc": utc_now(),
        }
        node["node_sha256"] = chain_hash(node)
        nodes.append(node)
        if selected is None and verdict["node_status"] == "STRUCTURAL_CERTIFIED":
            selected = verdict

    output_dir.mkdir(parents=True, exist_ok=True)
    compact_path = None
    compact_text = None
    post_render_replay = None
    render_permitted = (
        raw_provenance == "MANIFEST_LOCKED_PUBLIC_FIXTURE" or emit_external_wolfram
    )
    if selected is not None:
        compact_text = compact_wolfram(raw_sha256, selected["candidate_id"], selected["compiled_groups"])
    if selected is not None and render_permitted:
        compact_path = output_dir / "compact_candidate.wl"
        compact_path.write_text(compact_text)
        post_render_replay = replay_rendered_candidate(
            parsed, raw_sha256, selected["candidate_id"], selected["compiled_groups"],
            compact_path.read_text(),
        )
        if not all(post_render_replay.values()):
            raise DemoError("POST_RENDER_STRUCTURAL_REPLAY_FAILED")
    elif selected is not None:
        post_render_replay = {
            "status": "WITHHELD_EXTERNAL_RAW",
            "reason": "pass --emit-external-wolfram only for an authorized local raw source",
        }
    summary = {
        "candidates_received": len(candidates),
        "structural_certified": sum(
            node["verdict"]["node_status"] == "STRUCTURAL_CERTIFIED" for node in nodes[1:]
        ),
        "diagnostic": sum(node["verdict"]["node_status"] == "DIAGNOSTIC" for node in nodes[1:]),
        "selected_candidate_id": selected["candidate_id"] if selected else None,
    }
    evidence = {
        "demo": "raw_compaction_loop",
        "status": "STRUCTURAL_CERTIFIED" if selected else "NO_CANDIDATE_CERTIFIED",
        "claim_boundary": (
            "Exact structural factorization of the supplied raw text only; not a new "
            "scientific identity, physical simplification, or canonical result."
        ),
        "proposer": {
            "proposer_id": proposer_id or "unspecified-external-backend",
            "command_sha256": sha256_text(proposer_command),
            "request_envelope_sha256": sha256_text(json.dumps(envelope, sort_keys=True)),
            "response_sha256": sha256_text(json.dumps(candidates, sort_keys=True)),
            "trust_level": "UNTRUSTED_DATA_ONLY",
            "candidate_language": "JSON grouping plan",
        },
        "verifier": {
            "name": "raw_text_structural_verifier_v1",
            "trusted_input": "raw expression and candidate JSON only",
            "known_target_formula": False,
        },
        "raw": {
            "path": str(raw_path), "sha256": raw_sha256,
            "bytes": len(raw_bytes), "provenance_status": raw_provenance,
            "external_wolfram_output_permitted": bool(emit_external_wolfram),
        },
        "summary": summary,
        "nodes": nodes,
        "generated_compact_candidate": str(compact_path) if compact_path else None,
        "post_render_structural_replay": post_render_replay,
        "target_architecture": target_architecture_state(
            raw_path, raw_sha256, raw_provenance, proposer_id, selected,
            compact_text, raw_node["node_sha256"],
        ),
        "timestamp_utc": utc_now(),
    }
    evidence["chain_sha256"] = sha256_text(json.dumps(evidence, sort_keys=True))
    write_json_atomic(output_dir / "evidence.json", evidence)
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--proposer-cmd", default=os.environ.get("GUO_COMPACTION_PROPOSER_CMD"))
    parser.add_argument("--proposer-id", default=os.environ.get("GUO_COMPACTION_PROPOSER_ID"))
    parser.add_argument(
        "--emit-external-wolfram", action="store_true",
        help="allow compact_candidate.wl for a non-manifest local --raw input",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-candidates", type=int, default=MAX_CANDIDATES)
    args = parser.parse_args(argv)
    if args.n_candidates < 1 or args.n_candidates > MAX_CANDIDATES:
        parser.error("--n-candidates must be between 1 and %d" % MAX_CANDIDATES)
    try:
        evidence = run_loop(
            args.raw, args.proposer_cmd, args.out_dir, args.n_candidates, args.proposer_id,
            args.emit_external_wolfram,
        )
    except (DemoError, OSError) as error:
        print("[RAW-COMPACTION] %s" % error, file=sys.stderr)
        return 2
    print("[RAW-COMPACTION] %s" % evidence["status"])
    print("[RAW-COMPACTION] %s" % json.dumps(evidence["summary"], sort_keys=True))
    print("[RAW-COMPACTION] evidence: %s" % (args.out_dir / "evidence.json"))
    return 0 if evidence["status"] == "STRUCTURAL_CERTIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
