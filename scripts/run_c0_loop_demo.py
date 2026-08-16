#!/usr/bin/env python3
"""C0 — end-to-end minimal certified compactification loop demo.

One full loop step with a REAL LLM proposer (config-driven subprocess via
VIPER_PROPOSER_CMD; default: codex exec) and the independent Python/SymPy
residual verifier.  No Wolfram.  Evidence is written atomically and hashed.

Usage:
    VIPER_PROPOSER_CMD="codex exec --skip-git-repo-check -" \
        python scripts/run_c0_loop_demo.py --seed METRIC_true_seed --n-candidates 4
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from loop_engine.orch_adapters.compactification_loop import core as C0

DEFAULT_PROPOSER = "codex exec --skip-git-repo-check -"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", default="METRIC_true_seed")
    ap.add_argument("--n-candidates", type=int, default=4)
    ap.add_argument("--proposer-cmd", default=None,
                    help="LLM backend command (stdin prompt -> stdout JSON array); "
                         "defaults to $VIPER_PROPOSER_CMD or codex exec")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out_dir or os.environ.get("VIPER_OUTPUT_DIR")
                   or Path(tempfile.gettempdir()) / "viper_c0_demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    proposer_cmd = args.proposer_cmd or os.environ.get("VIPER_PROPOSER_CMD")         or DEFAULT_PROPOSER

    print(f"[C0] seed: {args.seed}")
    seed = C0.load_seed(args.seed)
    seed_verdict = C0.verify_seed(seed)
    print(f"[C0] seed verification: {seed_verdict['verdict']} "
          f"({seed_verdict['seconds']}s)")
    if seed_verdict["verdict"] != C0.VERDICT_ZERO:
        print("[C0] SEED NOT ZERO — aborting (fail-closed)")
        return 1

    ci = seed["claim"]
    problem = {
        "description": (
            f"We hold the CERTIFIED identity C_i over complex va, vb and real "
            f"nonzero eps:\n  {ci['lhs']}  ==  {ci['rhs']}\n"
            f"(frozen geobasis corpus family METRIC_true, per-summand form).\n"
            f"Propose the NEXT identity C_{{i+1}} you believe holds over the SAME "
            f"variables, as a compactification step. Candidates that are variants, "
            f"scalings, or generalizations are fine; they will be adjudicated "
            f"independently."),
        "symbols": [s["name"] for s in ci["symbols"]],
        "n_candidates": args.n_candidates,
    }

    print(f"[C0] proposer backend: {proposer_cmd}")
    os.environ["VIPER_PROPOSER_CMD"] = proposer_cmd
    t0 = time.time()
    step, code = C0.handle({
        "operation": "compactification_step",
        "contract_version": "1.0",
        "chain_id": f"c0-demo-{args.seed}",
        "seed_id": args.seed,
        "propose": {"problem": problem},
    })
    wall = round(time.time() - t0, 2)
    if code != 0:
        print(f"[C0] step failed: {step}")
        return code

    print(f"[C0] loop step complete in {wall}s")
    print(f"[C0] summary: {step['summary']}")
    for node in step["nodes"]:
        status = node["node_status"]
        verdict = node["residual_verdict"]
        print(f"  - {node['claim_id']}: residual {verdict} -> {status}")
        print(f"      candidate: {node['claim']['lhs']} == {node['claim']['rhs']}")
        if status == C0.NODE_CERTIFIED:
            print(f"      certificate: {node['certificate']['kind']} "
                  f"(residual_sha256 {node['certificate']['residual_sha256'][:16]}...)")
        elif status == C0.NODE_DIAGNOSTIC:
            ce = node["evidence"].get("counterexample", {})
            print(f"      DIAGNOSTIC: simplified residual = "
                  f"{node['evidence'].get('simplified_difference', '')[:100]}")
            print(f"      exact counterexample: {ce}")

    evidence = {
        "demo": "c0_minimal_compactification_loop",
        "seed_id": args.seed,
        "proposer_cmd": proposer_cmd,
        "problem": problem,
        "step": step,
        "wall_seconds": wall,
        "repository_commit": C0._safe.git_head(REPO),
        "calculations": "python_sympy_exact (no Wolfram)",
        "timestamp_utc": C0._now_iso(),
    }
    ev_path = out_dir / "c0_demo_evidence.json"
    tmp = out_dir / "c0_demo_evidence.json.tmp"
    tmp.write_text(json.dumps(evidence, indent=2))
    tmp.replace(ev_path)
    digest = hashlib.sha256(ev_path.read_bytes()).hexdigest()
    print(f"[C0] evidence: {ev_path} sha256={digest}")
    print(f"[C0] DONE — certified={step['summary']['certified']} "
          f"diagnostic={step['summary']['diagnostic']} "
          f"unverified={step['summary']['unverified']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
