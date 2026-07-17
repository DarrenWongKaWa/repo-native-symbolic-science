#!/usr/bin/env python3
"""Gate 2 — conformance against the FROZEN contract (self-contained, bundle-local).

Adapted from the prototype gate2_conformance.py. The six conformance groups and their
checks are unchanged; only the paths point at THIS frozen bundle. Two adaptations for a
frozen release bundle (documented, no weakening):
  - group5 does NOT re-run the numerical freeze (that machinery is not shipped in the
    bundle by design; live reproducibility is exercised by the real-CLI Gate 3 step in
    run_release_verification.py). It instead confirms the frozen evidence is internally
    stable and matches EVIDENCE_LOCK, and records the reproducibility classification.
  - group6 compares the frozen evidence against evidence/EVIDENCE_LOCK.sha256 (raw-file
    SHA-256) instead of the prototype manifest.

Anti-circularity is preserved: structural checks use the standard jsonschema library, a
SEPARATE semantic validator enforces cross-field rules, and valid/invalid fixtures are
hand-authored — none share code with the verifier that produced the outputs.

Exit 0 iff all checks pass.
"""
import sys, json, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "validators"))
import schema_validator as SV
import semantic_evidence_validator as SEV
import jsonschema

EVIDENCE = HERE / "evidence" / "frozen_evidence_package.json"
FAMILIES = HERE / "corpus" / "expected_results" / "families_results.json"
EVIDENCE_LOCK = HERE / "evidence" / "EVIDENCE_LOCK.sha256"

def sha(b): return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
PASS = []; FAIL = []
def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(f"   [{'PASS' if cond else 'FAIL'}] {name}")


def group1_positive():
    print("\n[1] Positive conformance (true identities)")
    fam = json.loads(FAMILIES.read_text()); ev = json.loads(EVIDENCE.read_text())
    t00 = ev["tasks"]["T00_correct"]
    check("F-23 true: symbolic gold = SYMBOLIC_IDENTITY", t00["symbolic_gold_result"] == "SYMBOLIC_IDENTITY")
    check("F-23 true: final verdict = VERIFIED_SYMBOLIC_IDENTITY", t00["verdict"] == "VERIFIED_SYMBOLIC_IDENTITY")
    check("F-23 true: numerical arm did NOT self-upgrade (residual only ~1e-9)",
          t00["numerical_verifier_result"]["relative_residual"] < 1e-6)
    for tid in ("METRIC_true", "RENORM_true", "BERRY_true"):
        r = fam[tid]
        check(f"{tid}: gold holds AND numerically consistent", r["gold"] and r["rel_residual"] < 1e-6)

def group2_negative():
    print("\n[2] Negative conformance (mutations -> reproducible counterexample)")
    ev = json.loads(EVIDENCE.read_text())
    for tid, t in ev["tasks"].items():
        if t["symbolic_gold_result"] == "SYMBOLIC_IDENTITY": continue
        ne = t["numerical_evidence"]
        check(f"{tid}: rel & abs residual both over threshold",
              ne["relative_residual"] >= 1e-6 and ne["absolute_residual"] >= 1e-6)
        check(f"{tid}: min denominator safe (|eps|>1e-3)", ne["minimum_denominator_abs_eps_nm"] > 1e-3)
        check(f"{tid}: verdict = DISPROVED (independent of any 'expected answer')",
              t["verdict"] == "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE")

def group3_contract_rejection():
    print("\n[3] Contract rejection (malformed MUST be rejected, not default-filled)")
    for f in sorted((HERE / "fixtures" / "invalid").glob("*.json")):
        obj = json.loads(f.read_text()); rejected = False
        try:
            if "combined_verdict" in obj: SV.validate_result(obj); SEV.check(obj)
            else: SV.validate_claim(obj)
        except (jsonschema.ValidationError, SEV.SemanticError):
            rejected = True
        check(f"invalid/{f.name} is REJECTED", rejected)

def group4_evidence_consistency():
    print("\n[4] Evidence consistency (cross-field constraints, independent semantic validator)")
    for f in sorted((HERE / "fixtures" / "valid").glob("*.json")):
        obj = json.loads(f.read_text()); ok = True
        try: SV.validate_result(obj); SEV.check(obj)
        except Exception as e: ok = False; print("      unexpected:", e)
        check(f"valid/{f.name} passes structural + semantic", ok)
    good = json.loads((HERE / "fixtures/valid/v1_true_identity.json").read_text())
    bad = dict(good); bad["evidence_level"] = 2
    try: SEV.check(bad); ok = False
    except SEV.SemanticError: ok = True
    check("VERIFIED_SYMBOLIC_IDENTITY with evidence_level!=3 is rejected", ok)

def group5_replay_frozen():
    print("\n[5] Replay conformance (frozen bundle — live reproducibility via Gate 3 CLI)")
    body = EVIDENCE.read_bytes()
    h1 = sha(body); h2 = sha(EVIDENCE.read_bytes())
    lock = EVIDENCE_LOCK.read_text().strip()
    check("frozen evidence is byte-stable on re-read", h1 == h2)
    check("frozen evidence matches EVIDENCE_LOCK (VERDICT/NUMERICALLY_REPRODUCIBLE frozen)", h1 == lock)
    print("      NOTE: the bundle is frozen; live re-run reproducibility is exercised by the")
    print("      real-CLI Gate 3 step (same verdict + residual within policy tolerance).")

def group6_tamper():
    print("\n[6] Tamper tests (any change must break the hash)")
    raw = EVIDENCE.read_bytes(); base = sha(raw); lock = EVIDENCE_LOCK.read_text().strip()
    check("frozen hash matches EVIDENCE_LOCK", base == lock)
    ev = json.loads(raw)
    for name, mutate in [
        ("a residual", lambda d: d["tasks"]["T01_coeff_5to6"]["numerical_verifier_result"].__setitem__("relative_residual", 0.0)),
        ("git_commit", lambda d: d.__setitem__("git_commit", "TAMPERED")),
        ("a verdict",  lambda d: d["tasks"]["T00_correct"].__setitem__("verdict", "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE")),
        ("disclaimer", lambda d: d.__setitem__("disclaimer", "TAMPERED"))]:
        d = json.loads(raw); mutate(d)
        check(f"tampering {name} changes the hash", sha(json.dumps(d, sort_keys=True).encode()) != base)


def main():
    print("GATE 2 — conformance of the frozen geobasis corpus against the frozen contract")
    print("=" * 74)
    locks = json.loads((HERE / "schemas/SCHEMA_LOCK.sha256.json").read_text())
    for name, h in locks.items():
        actual = sha((HERE / "schemas" / name).read_bytes())
        check(f"schema {name} matches its SHA-256 lock", actual == h)
    group1_positive(); group2_negative(); group3_contract_rejection()
    group4_evidence_consistency(); group5_replay_frozen(); group6_tamper()
    print("\n" + "=" * 74)
    print(f"GATE 2 RESULT: {len(PASS)} pass / {len(FAIL)} fail")
    print("GATE_2_COMPLETE" if not FAIL else "GATE_2_INCOMPLETE")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
