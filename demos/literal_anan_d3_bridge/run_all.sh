#!/usr/bin/env bash
# Run every proof and negative control in this demo, then aggregate the claims.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)"
PY="${VIPER_PY:-python3.12}"
echo "=== thermal dictionary (bridges) ==="
"$PY" "$DEMO/proofs/thermal_dictionary.py"
echo "=== D3 bridge ==="
"$PY" "$DEMO/proofs/d3_bridge.py"
echo "=== geometry orbit ==="
"$PY" "$DEMO/proofs/geometry_orbit.py"
echo "=== six-orbit identity ==="
"$PY" "$DEMO/proofs/six_orbit_identity.py"
echo "=== negative controls ==="
"$PY" "$DEMO/negative_controls/wrong_real_energy_fplus.py"
"$PY" "$DEMO/negative_controls/pointwise_k_vs_d3.py"
echo "=== ALL DEMO GATES EXECUTED ==="
