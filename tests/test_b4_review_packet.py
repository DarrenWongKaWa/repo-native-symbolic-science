"""B4 packet boundary is non-recursive and derives its cumulative coverage from Git."""
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/viper/reviews/B4_DOMAIN_OBLIGATIONS_REVIEW.json"


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).splitlines()


def test_b4_packet_covers_git_derived_parent_range_without_self_commit_recursion():
    packet = json.loads(PACKET.read_text())
    required = {"review_start_commit", "reviewed_code_end_commit", "packet_parent_commit", "packet_path",
                "packet_canonical_sha256", "self_reference_policy", "cumulative_commit_list",
                "cumulative_changed_paths", "cumulative_changed_file_hashes"}
    assert required <= set(packet)
    assert packet["packet_path"] == "verification/viper/reviews/B4_DOMAIN_OBLIGATIONS_REVIEW.json"
    assert "cannot contain the SHA of the Git commit" in packet["self_reference_policy"]
    expected_commits = list(reversed(_git("rev-list", "--first-parent", f"{packet['review_start_commit']}..{packet['packet_parent_commit']}")))
    assert packet["cumulative_commit_list"] == expected_commits
    expected_paths = set(_git("diff", "--name-only", f"{packet['review_start_commit']}..{packet['packet_parent_commit']}"))
    expected_paths.add(packet["packet_path"])
    assert set(packet["cumulative_changed_paths"]) == expected_paths
    assert set(packet["cumulative_changed_file_hashes"]) == expected_paths - {packet["packet_path"]}
    for rel, digest in packet["cumulative_changed_file_hashes"].items():
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == digest
    body = dict(packet); actual = body.pop("packet_canonical_sha256")
    assert actual == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
