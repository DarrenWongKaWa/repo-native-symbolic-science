#!/usr/bin/env python3
"""Gate 4 — Orchestration Governance Attacks (嘉华's five attack groups).

Every attack is routed through the REAL ORCH path. Input attacks go straight through the
production CLI `scripts/orch_controller.py geometric-basis-verify`. Fault attacks (an
oracle disagreement or a mid-write I/O failure that a valid input cannot produce) go
through tests/gate4/fault_driver.py, which reuses the SAME production registry and SAME
routing seam and injects the fault only by monkeypatching the vendored verifier inside
its own subprocess. No fault-making capability is exposed to a normal caller.

Each attack records the full forensic row 嘉华 required and the report gives FIVE
SEPARATE rates (never one overall pass):
  FailClosedComplianceRate, EvidenceEscalationPreventionRate,
  ScopePreservationRate, ConflictContainmentRate, ArtifactIntegrityRate.
"""
import sys, os, json, hashlib, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CTL = REPO / "scripts" / "orch_controller.py"
DRIVER = HERE / "fault_driver.py"
SECRET_CANARY = "VIPER-CANARY-9f3a2b"   # planted in env; must never appear in any output
SUCCESS_VERDICTS = {"VERIFIED_SYMBOLIC_IDENTITY", "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"}


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def base_req(mode="symbolic_and_numerical", scope="two_band", family="F23", **claim_extra):
    claim = {"family": family, "params": {}, "scope": scope,
             "assumptions": ["v=i eps A", "n!=m"],
             "declared_basis": ["d_a_G_bc", "d_b_G_ac", "d_c_G_ab"]}
    claim.update(claim_extra)
    return {"operation": "geometric_basis_verify", "contract_version": "1.0",
            "verification_mode": mode, "claim": claim}


def run_cli(req, extra_env=None):
    env = dict(os.environ); env["AWS_SECRET_ACCESS_KEY"] = f"sk-{SECRET_CANARY}"
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([sys.executable, str(CTL), "geometric-basis-verify"],
                       input=json.dumps(req), capture_output=True, text=True, env=env, cwd=str(REPO))
    return p


def run_fault(req, fault_mode):
    env = dict(os.environ); env["AWS_SECRET_ACCESS_KEY"] = f"sk-{SECRET_CANARY}"
    p = subprocess.run([sys.executable, str(DRIVER), fault_mode],
                       input=json.dumps(req), capture_output=True, text=True, env=env, cwd=str(REPO))
    return p


def forensic(attack_id, group, req, proc, expected):
    """Build the full forensic row for one attack."""
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"_unparseable_stdout": proc.stdout[:200]}
    combined = payload.get("combined_verdict")
    orch_err = payload.get("orch_error") or payload.get("error")
    actual = combined or orch_err or "NO_VERDICT"
    exit_code = proc.returncode
    is_success = exit_code == 0 and combined in SUCCESS_VERDICTS and not orch_err
    replay = payload.get("replay_artifact") or {}
    artifact_published = bool(replay.get("sha256")) and is_success
    partial = is_success and expected.get("must_block", False)
    req_scope = req["claim"].get("scope")
    echoed_scope = payload.get("scope")
    scope_preserved = (echoed_scope == req_scope) if echoed_scope is not None else True
    sym = payload.get("symbolic_claim_verifier"); num = payload.get("numerical_geobasis_verifier")
    if group == "B":  # both oracles must survive a disagreement
        subresults_preserved = bool(sym) and bool(num)
    else:
        subresults_preserved = True
    prov = payload.get("provenance")
    out_scan = "LEAK" if SECRET_CANARY in proc.stdout else "CLEAN"
    err_scan = "LEAK" if SECRET_CANARY in proc.stderr else "CLEAN"
    if is_success:
        replay_status = f"PUBLISHED:{replay.get('sha256','')[:12]}"
    elif combined == "INDEPENDENT_ORACLE_CONFLICT":
        replay_status = "WITHHELD_FAILCLOSED"
    else:
        replay_status = "WITHHELD"
    return {
        "attack_id": attack_id, "attack_group": group,
        "input_sha256": sha(req)[:16], "expected_verdict": expected["verdict"],
        "actual_verdict": actual, "exit_code": exit_code,
        "artifact_published": artifact_published, "partial_output_detected": partial,
        "scope_preserved": scope_preserved, "subresults_preserved": subresults_preserved,
        "provenance_sha256": (sha(prov)[:16] if prov else None),
        "stdout_secret_scan": out_scan, "stderr_secret_scan": err_scan,
        "replay_status": replay_status,
        # per-attack pass judgements feeding the rate members:
        "_escalation_prevented": (combined != "VERIFIED_SYMBOLIC_IDENTITY"
                                  and (payload.get("combined_evidence_level") or 0) <= 1),
        "_blocked": (exit_code != 0 and not is_success),
        "_conflict_contained": (
            (attack_id == "B1" and combined == "INDEPENDENT_ORACLE_CONFLICT"
             and exit_code != 0 and bool(sym) and bool(num) and not artifact_published) or
            (attack_id == "B2" and combined == "DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL"
             and bool(sym) and bool(num))),
        "_no_spurious_artifact": (not partial) and (artifact_published <= is_success),
        "_matches_expected": (actual == expected["verdict"]),
    }


def main() -> int:
    rows = []
    # ---- Group A — Evidence escalation --------------------------------------
    rows.append(forensic("A1", "A", base_req(mode="numerical_only"),
        run_cli(base_req(mode="numerical_only")),
        {"verdict": "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"}))
    rows.append(forensic("A2", "A", base_req(),
        run_fault(base_req(), "symbolic_unsupported"),
        {"verdict": "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"}))
    rows.append(forensic("A3", "A", base_req(mode="numerical_only"),
        run_cli(base_req(mode="numerical_only")),
        {"verdict": "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"}))
    # ---- Group B — Oracle conflict ------------------------------------------
    rows.append(forensic("B1", "B", base_req(),
        run_fault(base_req(), "numerical_counterexample"),
        {"verdict": "INDEPENDENT_ORACLE_CONFLICT", "must_block": True}))
    rows.append(forensic("B2", "B", base_req(),
        run_fault(base_req(), "symbolic_disproved"),
        {"verdict": "DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL"}))
    # ---- Group C — Policy weakening -----------------------------------------
    creq = base_req(); creq["policy_overrides"] = {"tolerance": 1e-1}
    rows.append(forensic("C1", "C", creq, run_cli(creq),
        {"verdict": "POLICY_VIOLATION", "must_block": True}))
    dreq = base_req(); dreq["policy_overrides"] = {"denominator_safety": False}
    rows.append(forensic("C2", "C", dreq, run_cli(dreq),
        {"verdict": "POLICY_VIOLATION", "must_block": True}))
    # ---- Group D — Atomicity & artifact integrity ---------------------------
    rows.append(forensic("D1", "D", base_req(),
        run_fault(base_req(), "raise_on_write"),
        {"verdict": "OSError", "must_block": True}))
    rows.append(forensic("D2", "D", base_req(),
        run_fault(base_req(), "numerical_counterexample"),
        {"verdict": "INDEPENDENT_ORACLE_CONFLICT", "must_block": True}))
    # ---- Group E — Boundary & leakage ---------------------------------------
    rows.append(forensic("E1", "E", base_req(gold_verdict="VERIFIED"),
        run_cli(base_req(gold_verdict="VERIFIED")),
        {"verdict": "BENCHMARK_METADATA_NOT_ALLOWED", "must_block": True}))
    rows.append(forensic("E2", "E", base_req(),
        run_cli(base_req()), {"verdict": "VERIFIED_SYMBOLIC_IDENTITY"}))
    rows.append(forensic("E3", "E", base_req(scope="hyperband"),
        run_cli(base_req(scope="hyperband")),
        {"verdict": "SCHEMA_VALIDATION_FAILED", "must_block": True}))

    # ---- five SEPARATE rates -------------------------------------------------
    def rate(members, key):
        sel = [r for r in rows if r["attack_id"] in members]
        passed = sum(1 for r in sel if r[key])
        return {"passed": passed, "total": len(sel),
                "rate": round(passed / len(sel), 4) if sel else None}

    fail_closed_members = ["B1", "C1", "C2", "D1", "D2", "E1", "E3"]
    rates = {
        "FailClosedComplianceRate": rate(fail_closed_members, "_blocked"),
        "EvidenceEscalationPreventionRate": rate(["A1", "A2", "A3"], "_escalation_prevented"),
        "ScopePreservationRate": rate([r["attack_id"] for r in rows], "scope_preserved"),
        "ConflictContainmentRate": rate(["B1", "B2"], "_conflict_contained"),
        "ArtifactIntegrityRate": rate([r["attack_id"] for r in rows], "_no_spurious_artifact"),
    }
    leak_any = any(r["stdout_secret_scan"] == "LEAK" or r["stderr_secret_scan"] == "LEAK" for r in rows)
    all_pass = all(v["rate"] == 1.0 for v in rates.values()) and not leak_any

    report = {
        "gate": "GATE_4_ORCHESTRATION_GOVERNANCE",
        "total_attacks": len(rows),
        "attack_groups": {"A": "evidence_escalation", "B": "oracle_conflict",
                          "C": "policy_weakening", "D": "atomicity_artifact_integrity",
                          "E": "boundary_leakage"},
        "rates": rates,
        "secret_leak_detected": leak_any,
        "all_rates_perfect": all_pass,
        "status": "GATE_4_COMPLETE" if all_pass else "GATE_4_FAILED",
        "attacks": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
    }
    (HERE / "gate4_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"rates": rates, "secret_leak_detected": leak_any,
                      "status": report["status"]}, indent=2))
    for r in rows:
        print(f"  [{r['attack_id']}/{r['attack_group']}] exp={r['expected_verdict'][:34]:<34} "
              f"act={r['actual_verdict'][:34]:<34} rc={r['exit_code']} "
              f"scope={'ok' if r['scope_preserved'] else 'X'} "
              f"secret={r['stdout_secret_scan']}/{r['stderr_secret_scan']} {r['replay_status']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
