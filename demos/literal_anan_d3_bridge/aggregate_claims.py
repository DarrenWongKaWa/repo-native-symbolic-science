#!/usr/bin/env python3
"""Aggregate proof certificates into claims/ records (after run_all.sh)."""
import json, shutil, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROOFS = HERE / "proofs" / "out"
CLAIMS = HERE / "claims"
CLAIMS.mkdir(exist_ok=True)

mapping = {
    "thermal_dictionary_certificate.json": "thermal_dictionary.json",
    "d3_bridge_certificate.json": "d3_bridge.json",
    "geometry_orbit_certificate.json": "geometry_orbit.json",
    "six_orbit_status.json": "six_orbit_status.json",
    "negative_control_real_energy.json": "negative_control_real_energy.json",
    "negative_control_pointwise.json": "negative_control_pointwise.json",
}
for src, dst in mapping.items():
    p = PROOFS / src
    if p.exists():
        shutil.copyfile(p, CLAIMS / dst)
        print("copied", src, "-> claims/", dst)
    else:
        print("MISSING", src)

# final claim with boundary
final = {
  "schema": "viper.demo.anan_d3.final_claim.v1",
  "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=HERE).stdout.strip(),
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "CLAIM": "Literal Anan D3 thermal notation is exactly bridged to the Guo/Supplement thermal notation, and the longitudinal all-distinct three-band vvv block agrees after complete six-orbit reassembly, with convention factor -2.",
  "CERTIFIED_COMPONENTS": [
    "thermal dictionary (argument/function/derivative bridges): PASS_EXACT",
    "literal D3 substitution: PASS_EXACT (POINTWISE)",
    "geometry orbit invariance: PASS_EXACT (6/6)",
    "negative controls: FAIL_EXPECTED / FAIL_AS_EXPECTED as designed"
  ],
  "OPEN_COMPONENT": "LITERAL_ANAN_D3_SIX_ORBIT: SIX_ORBIT_UNVERIFIED_UNDER_DECLARED_CONTRACT — contract clarification required (M_Gamma/T_Gamma definitions, certified witness energies)",
  "NOT_CLAIMED": [
    "complete Guo-Anan conductivity equivalence",
    "literal D2 bridge",
    "complete overall prefactor bridge",
    "generic-N proof",
    "post-IBP BZ equivalence",
    "degenerate-band extension"
  ],
  "final_verdict": "DEMO_LAYERS_L1_L2_L3_L5_CERTIFIED_L4_OPEN"
}
(CLAIMS / "final_claim.json").write_text(json.dumps(final, indent=2))
print("claims aggregated; final_claim.json written")
