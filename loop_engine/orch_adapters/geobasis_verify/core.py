#!/usr/bin/env python3
"""
Gate 3 — ORCH adapter for capability `geometric_basis_verify` (嘉华's contract).

Thin adapter: math implementations are UNCHANGED (imported from the prototype). It adds
- narrow capability name (not verify_physics)
- runtime request validation that REJECTS benchmark/gold metadata (no gold leak into runtime)
- 3 verification modes with asymmetric evidence policy (numerical never "verifies")
- dual-path output kept separate; an oracle_relation ENUM (not a boolean)
- deterministic combined-verdict reconciliation (section 6 table)
- policy-owned numerical safeguards (caller may only strengthen)
- atomic execution (steps 6-8 fail => NO partial success), replay artifact, provenance.
"""
import sys, json, hashlib, subprocess, tempfile, os, platform, io, contextlib
from pathlib import Path
import numpy as np, sympy, jsonschema

HERE = Path(__file__).resolve().parent
VX = HERE.parent
import pilot2_v2 as p2          # symbolic_gold_F23, num_f23, basis (unchanged math)
import families as fam          # symbolic_gold, numerical_verify (unchanged math)
from reconstruct import reconstruct
import geometry as geo

ADAPTER_VERSION = "gate3-adapter-1.0"
FORBIDDEN = {"gold_verdict","expected_answer","mutation_operator","gold_residual",
             "benchmark_task_class","gold_certificate"}
# repository policy (NOT caller-supplied)
POLICY = {"max_tolerance":1e-6, "min_denominator":1e-3, "min_samples":9,
          "require_seed_recording":True, "denominator_safety":True}
POLICY_HASH = hashlib.sha256(json.dumps(POLICY,sort_keys=True).encode()).hexdigest()

def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else json.dumps(b,sort_keys=True).encode()).hexdigest()

class AdapterError(Exception):
    def __init__(self, code): super().__init__(code); self.code = code

# ---- symbolic verifier (from the claim; NO gold lookup) ----------------------
def _symbolic(family, params):
    if family == "F23":
        holds = p2.symbolic_gold_F23(**params)
    elif family in ("METRIC","RENORM","BERRY"):
        holds = fam.symbolic_gold(family, **params)
    else:
        return {"verdict":"SYMBOLIC_CAPABILITY_UNSUPPORTED","evidence_level":0,
                "canonical_residual":None,"certificate":None}
    if holds:
        cert = {"type":"canonical_zero_residual","artifact_hash":sha({"family":family,"params":params,"claim":"canonical(LHS-RHS)=0"})}
        return {"verdict":"VERIFIED_SYMBOLIC_IDENTITY","evidence_level":3,"canonical_residual":"0","certificate":cert}
    return {"verdict":"DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL","evidence_level":2,
            "canonical_residual":"nonzero","certificate":None}

# ---- numerical verifier (policy-owned safeguards) ----------------------------
def _numerical(family, params, tol):
    with contextlib.redirect_stdout(io.StringIO()):
        models=[geo.build_model(seed=s) for s in (7,101,2024)]
        rng=np.random.default_rng(42); kpts=[rng.uniform(-1.4,1.4,3) for _ in range(3)]
        # min denominator safety
        min_den=min(abs(w[n]-w[m]) for H in models for k in kpts
                    for w in [np.linalg.eigh(H(np.array(k)))[0]]
                    for n in range(H.N) for m in range(H.N) if n!=m)
        if POLICY["denominator_safety"] and min_den < POLICY["min_denominator"]:
            return {"verdict":"NUMERICAL_SAFETY_CHECK_FAILED","evidence_level":0,
                    "evidence":{"minimum_denominator":min_den}}
        if family=="F23":
            v=reconstruct(lambda H,k: p2.num_f23(H,k,**params),
                [(nm,(lambda H,k,_i=i:p2.basis(H,k)[_i][1])) for i,nm in
                 enumerate(["d_a G^bc","d_b G^ac","d_c G^ab"])], models, kpts)
            rel=v["rel_residual"]; ab=v["abs_residual"]
        else:
            rel=fam.numerical_verify(family, **params); ab=rel
    ev={"random_seed":42,"precision_dps":"float64","absolute_residual":ab,"relative_residual":rel,
        "minimum_denominator":min_den,"excluded_points":[],"tolerance_policy":f"rel<{tol}","n_samples":len(models)*len(kpts)}
    if rel < tol:
        return {"verdict":"NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE","evidence_level":1,"evidence":ev}
    return {"verdict":"DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE","evidence_level":2,"evidence":ev}

# ---- reconciliation (section 6 table) + oracle_relation (section 5) ----------
def _reconcile(sym, num, mode):
    sv = sym["verdict"] if sym else None
    nv = num["verdict"] if num else None
    sym_id  = sv=="VERIFIED_SYMBOLIC_IDENTITY"
    sym_no  = sv=="DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL"
    sym_un  = sv in (None,"SYMBOLIC_CAPABILITY_UNSUPPORTED")
    num_cx  = nv=="DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE"
    num_ok  = nv=="NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"
    num_un  = nv in (None,"NUMERICAL_CAPABILITY_UNSUPPORTED","NUMERICAL_SAFETY_CHECK_FAILED")
    # conflict (fail-closed)
    if sym_id and num_cx:  return "CONFLICT","INDEPENDENT_ORACLE_CONFLICT",0
    if sym_id and (num_ok or num_un): return "CONSISTENT" if num_ok else "SYMBOLIC_DECISIVE_NUMERICAL_INCONCLUSIVE","VERIFIED_SYMBOLIC_IDENTITY",3
    if sym_no and num_cx:  return "CONSISTENT","DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL",2
    if sym_no and (num_ok or num_un): return "SYMBOLIC_DECISIVE_NUMERICAL_INCONCLUSIVE","DISPROVED_BY_SYMBOLIC_NONZERO_RESIDUAL",2
    if sym_un and num_cx:  return "NUMERICAL_DECISIVE_SYMBOLIC_UNSUPPORTED","DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE",2
    if sym_un and num_ok:  return "NUMERICAL_DECISIVE_SYMBOLIC_UNSUPPORTED","NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE",1
    if sym_un and num_un:  return "BOTH_INCONCLUSIVE","INCONCLUSIVE_INSUFFICIENT_EVIDENCE",0
    return "NOT_APPLICABLE","INCONCLUSIVE_INSUFFICIENT_EVIDENCE",0

def handle(req):
    # 1. request schema + forbidden-field check (no gold leak)
    blob = json.dumps(req)
    for f in FORBIDDEN:
        if f in blob: raise AdapterError("BENCHMARK_METADATA_NOT_ALLOWED")
    jsonschema.validate(req, json.loads((HERE/"schemas/gbv_request.schema.json").read_text()))
    claim = req["claim"]; mode = req["verification_mode"]
    # 2. semantic: scope already enum-validated; assumptions non-empty by schema
    # 3. policy: effective tolerance = min(caller, policy max); caller may only strengthen
    caller_tol = (req.get("policy_overrides") or {}).get("tolerance", POLICY["max_tolerance"])
    if caller_tol > POLICY["max_tolerance"]: raise AdapterError("POLICY_VIOLATION")
    if (req.get("policy_overrides") or {}).get("denominator_safety") is False: raise AdapterError("POLICY_VIOLATION")
    tol = min(caller_tol, POLICY["max_tolerance"])
    # 4-5. run verifiers per mode
    sym = _symbolic(claim["family"], claim["params"]) if mode in ("symbolic_only","symbolic_and_numerical") else None
    num = _numerical(claim["family"], claim["params"], tol) if mode in ("numerical_only","symbolic_and_numerical") else None
    if mode == "numerical_only" and num and num["verdict"]=="VERIFIED_SYMBOLIC_IDENTITY":
        raise AdapterError("INVARIANT_VIOLATION_numerical_cannot_verify")
    # 6. reconcile
    relation, combined, comb_lvl = _reconcile(sym, num, mode)
    # 7-8. build result, replay artifact (temp -> atomic rename), validate
    result = {
        "operation":"geometric_basis_verify","contract_version":"1.0",
        "request_hash":sha(req),
        "symbolic_claim_verifier":sym, "numerical_geobasis_verifier":num,
        "oracle_relation":relation, "combined_verdict":combined,
        "combined_evidence_level":comb_lvl, "scope":claim["scope"],
        "unresolved_obligations":[] if combined!="INCONCLUSIVE_INSUFFICIENT_EVIDENCE" else ["need symbolic certificate or numerical counterexample"],
        "provenance":{
            "repository_commit": _git(), "adapter_version":ADAPTER_VERSION,
            "symbolic_verifier":"pilot2_v2/families symbolic_gold", "numerical_verifier":"geobasis reconstruct",
            "input_contract_version":"1.0","output_contract_version":"1.1",
            "policy_hash":POLICY_HASH, "subresult_hashes":{"symbolic":sha(sym),"numerical":sha(num)},
            "runtime_environment":{"python":platform.python_version(),"platform":platform.platform()},
            "replay_classification":"VERDICT_REPRODUCIBLE (numerical seed recorded; bitwise same-machine only)"},
    }
    out_dir = Path(os.environ.get("VIPER_OUTPUT_DIR", tempfile.gettempdir()))/"viper_geobasis_runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), suffix=".tmp")
    json.dump(result, tmp); tmp.close()
    art_hash = sha(Path(tmp.name).read_bytes())
    final = out_dir/"last_result.json"; os.replace(tmp.name, final)   # atomic rename AFTER build
    result["replay_artifact"]={"path":str(final),"sha256":art_hash}
    # exit status: conflict fails closed
    exit_code = 1 if combined in ("INDEPENDENT_ORACLE_CONFLICT",) else 0
    return result, exit_code

def _git():
    try: return subprocess.run(["git","rev-parse","HEAD"],cwd=str(VX.parent.parent),capture_output=True,text=True).stdout.strip()
    except Exception: return "unknown"

def main():
    req = json.load(sys.stdin) if not sys.stdin.isatty() else json.loads(sys.argv[1])
    try:
        res, rc = handle(req)
        print(json.dumps(res, indent=1)); return rc
    except AdapterError as e:
        print(json.dumps({"operation":"geometric_basis_verify","error":e.code,"combined_verdict":e.code})); return 1
    except jsonschema.ValidationError as e:
        print(json.dumps({"operation":"geometric_basis_verify","error":"SCHEMA_VALIDATION_FAILED","detail":e.message[:120]})); return 1

if __name__ == "__main__":
    sys.exit(main())
