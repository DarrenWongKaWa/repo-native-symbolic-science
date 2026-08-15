"""B4 packet boundary is non-recursive and derives its cumulative coverage from Git."""
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/viper/reviews/B4_DOMAIN_OBLIGATIONS_REVIEW.json"


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).splitlines()


def _git_blob(commit, path):
    """Read the immutable reviewed blob, not a later additive working-tree revision."""
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO)


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
        # B4's packet freezes its reviewed parent range. Later reviewed fixes may change
        # live production files, so the packet must continue to authenticate that exact
        # historical tree rather than spuriously treating an additive later commit as a
        # rewrite of the B4 evidence.
        assert hashlib.sha256(_git_blob(packet["packet_parent_commit"], rel)).hexdigest() == digest
    body = dict(packet); actual = body.pop("packet_canonical_sha256")
    assert actual == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
