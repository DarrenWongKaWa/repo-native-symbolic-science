"""B5 implementation handoff must bind the final pre-packet candidate state."""
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKET = (
    REPO / "verification/viper/reviews/"
    "B5_MULTIVARIABLE_T3_IMPLEMENTATION_HANDOFF.json"
)
BASE = "702b9f9ecacbcfffd5f4685dc8c6d49c7f8d2dbc"


def _git(*arguments):
    return subprocess.check_output(
        ["git", *arguments], cwd=REPO, text=True).strip()


def test_b5_handoff_binds_final_pre_packet_commit_paths_and_hashes():
    packet = json.loads(PACKET.read_text())
    assert packet["state"] == "IMPLEMENTATION_READY_FOR_INDEPENDENT_REVIEW"
    assert packet["author_self_review_only"] is True
    assert packet["base_commit"] == BASE
    parent = packet["packet_parent_commit"]
    assert packet["reviewed_code_end_commit"] == parent
    assert _git("rev-parse", "HEAD^") == parent
    assert packet["cumulative_commit_list"] == _git(
        "rev-list", "--reverse", f"{BASE}..{parent}").splitlines()

    expected_paths = set(
        _git("diff", "--name-only", f"{BASE}..{parent}").splitlines())
    expected_paths.add(packet["packet_path"])
    assert set(packet["cumulative_changed_paths"]) == expected_paths
    assert set(packet["cumulative_changed_file_hashes"]) == (
        expected_paths - {packet["packet_path"]})
    for relative, digest in packet["cumulative_changed_file_hashes"].items():
        assert hashlib.sha256((REPO / relative).read_bytes()).hexdigest() == digest

    body = dict(packet)
    claimed = body.pop("packet_canonical_sha256")
    actual = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert claimed == actual
