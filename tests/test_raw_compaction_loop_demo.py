"""Integration tests for the raw Wolfram compaction demo."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "demos" / "raw_compaction_loop"
RUNNER = DEMO / "run_demo.py"
FIXTURE = DEMO / "fixtures" / "mock_proposer.py"
RAW = DEMO / "raw" / "synthetic_unknown_tensor.wl"

SPEC = importlib.util.spec_from_file_location("raw_compaction_demo", RUNNER)
DEMO_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO_MODULE)


def test_mock_loop_rejects_bad_plan_then_certifies_raw_compaction(tmp_path):
    output = tmp_path / "out"
    command = "%s %s" % (sys.executable, FIXTURE)
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--proposer-cmd", command,
         "--out-dir", str(output)],
        text=True,
        capture_output=True,
        cwd=str(REPO),
    )
    assert completed.returncode == 0, completed.stderr
    evidence = json.loads((output / "evidence.json").read_text())
    assert evidence["status"] == "STRUCTURAL_CERTIFIED"
    assert evidence["summary"] == {
        "candidates_received": 2,
        "structural_certified": 1,
        "diagnostic": 1,
        "selected_candidate_id": "shared-piecewise-kernels",
    }
    assert evidence["verifier"]["known_target_formula"] is False
    assert evidence["nodes"][1]["verdict"]["verdict"] == "COMMON_PREFIX_LITERAL_MISMATCH"
    assert evidence["raw"]["provenance_status"] == "MANIFEST_LOCKED_PUBLIC_FIXTURE"
    assert all(evidence["post_render_structural_replay"].values())
    architecture = evidence["target_architecture"]
    assert architecture["status"] == "PENDING_INDEPENDENT_VERIFICATION"
    assert architecture["verification"]["independent"] is False
    assert architecture["selection_gate"]["status"] == "BLOCKED_INDEPENDENT_VERIFICATION"
    assert (output / "compact_candidate.wl").is_file()
    compact = (output / "compact_candidate.wl").read_text()
    assert "RawKernel1[n_, m_]" in compact
    assert "RawKernel2[n_, m_, ell_]" in compact
    assert "u1[a, m, n]*(u1[b, n, ell]*u1[c, ell, m] + u1[b, ell, m]*u1[c, n, ell])" in compact


def test_missing_proposer_is_fail_closed(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--out-dir", str(tmp_path / "out")],
        text=True,
        capture_output=True,
        cwd=str(REPO),
    )
    assert completed.returncode == 2
    assert "PROPOSER_BACKEND_NOT_CONFIGURED" in completed.stderr


def test_demo_raw_matches_manifest_hash():
    manifest = json.loads((DEMO / "SOURCE_MANIFEST.json").read_text())
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == manifest["raw_sha256"]
    assert len(RAW.read_bytes()) == manifest["raw_bytes"]


def test_manifest_mismatch_is_fail_closed(tmp_path):
    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text(json.dumps({
        "raw_source": "raw/synthetic_unknown_tensor.wl",
        "raw_sha256": "0" * 64,
        "raw_bytes": len(RAW.read_bytes()),
    }))
    try:
        DEMO_MODULE.load_raw(RAW, manifest_path=bad_manifest)
        assert False, "a mismatched default-fixture manifest must fail"
    except DEMO_MODULE.DemoError as error:
        assert str(error) == "SOURCE_MANIFEST_MISMATCH"


def test_injected_candidate_id_and_boolean_indices_are_rejected():
    parsed = DEMO_MODULE.parse_raw(RAW.read_text())
    injected = {
        "candidate_id": "x*)Quit[]",
        "groups": [{"term_indices": [0, 1], "kernel_factor_index": 2,
                    "common_prefix_factor_count": 0}],
    }
    verdict = DEMO_MODULE.verify_candidate(injected, parsed)
    assert verdict["verdict"] == "CANDIDATE_ID_MALFORMED"
    boolean_index = {
        "candidate_id": "boolean-index",
        "groups": [{"term_indices": [True, 1], "kernel_factor_index": 2,
                    "common_prefix_factor_count": 0}],
    }
    verdict = DEMO_MODULE.verify_candidate(boolean_index, parsed)
    assert verdict["verdict"] == "GROUP_TERM_INDICES_MALFORMED"


def test_reordered_coverage_is_rejected_even_when_each_group_is_valid():
    raw = "X = " + " + ".join(
        "Sum[v%d[n]*kernel[n], {n, 1, Nb}]" % index for index in range(4)
    ) + ";"
    parsed = DEMO_MODULE.parse_raw(raw)
    candidate = {
        "candidate_id": "reordered-coverage",
        "groups": [
            {"term_indices": [0, 3], "kernel_factor_index": 1,
             "common_prefix_factor_count": 0},
            {"term_indices": [1, 2], "kernel_factor_index": 1,
             "common_prefix_factor_count": 0},
        ],
    }
    verdict = DEMO_MODULE.verify_candidate(candidate, parsed)
    assert verdict["verdict"] == "TERM_SOURCE_ORDER_NOT_EXACT"


def test_proposer_response_cannot_exceed_requested_candidate_count(tmp_path):
    backend = tmp_path / "too_many.py"
    backend.write_text("import json, sys\njson.load(sys.stdin)\njson.dump([{}, {}], sys.stdout)\n")
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--proposer-cmd", "%s %s" % (sys.executable, backend),
         "--n-candidates", "1", "--out-dir", str(tmp_path / "out")],
        text=True,
        capture_output=True,
        cwd=str(REPO),
    )
    assert completed.returncode == 2
    assert "PROPOSER_OUTPUT_TOO_MANY_CANDIDATES" in completed.stderr


def test_proposer_stdout_cap_is_fail_closed(tmp_path):
    backend = tmp_path / "oversize.py"
    backend.write_text("import sys\nsys.stdin.read()\nsys.stdout.write('x' * 65000)\n")
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--proposer-cmd", "%s %s" % (sys.executable, backend),
         "--out-dir", str(tmp_path / "out")],
        text=True,
        capture_output=True,
        cwd=str(REPO),
    )
    assert completed.returncode == 2
    assert "PROPOSER_OUTPUT_TOO_LARGE" in completed.stderr
