"""Gate 3.5 conformance for the geometric_basis_verify ORCH adapter (product test)."""
import json, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
CTL = REPO / "scripts" / "orch_controller.py"

def _cli(args, stdin=""):
    p = subprocess.run([sys.executable, str(CTL)]+args, input=stdin, capture_output=True, text=True, cwd=str(REPO))
    try: return json.loads(p.stdout), p.returncode
    except Exception: return {"_raw": p.stdout}, p.returncode

REQ = json.dumps({"operation":"geometric_basis_verify","contract_version":"1.0",
  "verification_mode":"symbolic_and_numerical",
  "claim":{"family":"F23","params":{},"scope":"two_band","assumptions":["v=i eps A"],"declared_basis":["d_a_G_bc"]}})

def test_capability_registered():
    out,_ = _cli(["list-operations"]); assert "geometric_basis_verify" in out["operations"]
def test_no_overgeneral_alias():
    out,_ = _cli(["list-operations"]); assert not ({"verify_physics","prove_identity"} & set(out["operations"]))
def test_true_identity_routes_and_verifies():
    out,rc = _cli(["geometric-basis-verify"], REQ)
    assert out["combined_verdict"]=="VERIFIED_SYMBOLIC_IDENTITY" and out["oracle_relation"]=="CONSISTENT" and rc==0
def test_scope_preserved():
    out,_ = _cli(["geometric-basis-verify"], REQ); assert out["scope"]=="two_band"
def test_gold_metadata_rejected():
    r=json.loads(REQ); r["claim"]["gold_verdict"]="VERIFIED"
    out,rc=_cli(["geometric-basis-verify"], json.dumps(r)); assert out.get("orch_error")=="BENCHMARK_METADATA_NOT_ALLOWED" and rc!=0
def test_policy_cannot_be_weakened():
    r=json.loads(REQ); r["policy_overrides"]={"tolerance":1e-1}
    out,rc=_cli(["geometric-basis-verify"], json.dumps(r)); assert out.get("orch_error")=="POLICY_VIOLATION" and rc!=0
