"""Demo regression: literal_anan_d3_bridge gates stay certified.

Runs the exact proofs in-process (pure Python/SymPy/mpmath; no Wolfram).
"""
import json
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[1] / "demos" / "literal_anan_d3_bridge"
sys.path.insert(0, str(DEMO / "proofs"))


def _run(script_name: str, module_name: str, output_name: str) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, DEMO / script_name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cert = json.loads((DEMO / "proofs" / "out" / output_name).read_text())
    return cert


def test_thermal_dictionary_all_exact():
    cert = _run("proofs/thermal_dictionary.py", "td", "thermal_dictionary_certificate.json")
    assert cert["overall"] == "PASS_EXACT"
    assert cert["notation_collision"]["symbolic_difference_nonzero"] is True


def test_d3_bridge_pointwise_exact():
    cert = _run("proofs/d3_bridge.py", "d3b", "d3_bridge_certificate.json")
    assert cert["LITERAL_ANAN_D3_THERMAL_BRIDGE"] == "PASS_EXACT"
    assert cert["ARROW_TYPE"] == "POINTWISE_EXACT"


def test_geometry_orbit_invariant():
    cert = _run("proofs/geometry_orbit.py", "geo", "geometry_orbit_certificate.json")
    assert cert["THREE_BAND_LOOP_GEOMETRY_ORBIT_INVARIANT"] == "PASS_EXACT"
    assert len(cert["permutations_checked"]) == 6


def test_negative_controls_fail_as_expected():
    nc1 = _run("negative_controls/wrong_real_energy_fplus.py", "nc1",
               "negative_control_real_energy.json")
    nc2 = _run("negative_controls/pointwise_k_vs_d3.py", "nc2",
               "negative_control_pointwise.json")
    assert nc1["NEGATIVE_CONTROL_REAL_ENERGY_FPLUS"] == "FAIL_AS_EXPECTED"
    assert nc1["values_are_finite_and_different"] is True
    assert nc2["ORDERED_TRIPLE_K_EQUALS_MINUS_D3"] == "FAIL_EXPECTED"


def test_six_orbit_all_gates_pass():
    cert = _run("proofs/six_orbit_identity.py", "six", "six_orbit_status.json")
    assert cert["verdict"] == "LITERAL_ANAN_D3_SIX_ORBIT_PASS_EXACT"
    assert cert["fail_closed_stop"] is None
    for g, v in cert["gates"].items():
        assert v["result"] == "PASS", (g, v["result"])
    # S3.31 endpoint relation must be CONJUGATION (never equality)
    assert float(cert["gates"]["G4_SIX_ORBIT_TO_QM_HD_REDUCTION"]["S3.31_conjugation_M_ba-conj(M_ab)"]) < 1e-20

def test_mutation_pass_red_flags_every_wrong_science():
    cert = _run("negative_controls/mutation_adversarial_pass.py", "mut",
                "mutation_adversarial_pass.json")
    assert cert["overall"].startswith("PASS")
    for m in cert["mutations"]:
        assert m["gate_red"] is True, m["mutation"]
    ids = {m["mutation"] for m in cert["mutations"]}
    assert ids == {"M1_F_NODE_ORDER", "M2_DELTA_INDEX",
                   "M3_CONJUGATION_EQUALITY", "M4_REAL_ENERGY_FPLUS"}
