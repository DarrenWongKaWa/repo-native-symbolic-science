#!/usr/bin/env python3
"""Gate 1 — frozen verifier I/O contract (self-contained, bundle-local).

Adapted from the prototype verifier_contract.py: the schemas and checks are unchanged;
only the paths point at this frozen bundle instead of the experiment tree, and it never
writes into the bundle (derived schemas go to a temp dir). Validates the frozen evidence
package against the verdict-output contract and a sample Condition-D claim input.

Exit 0 iff every frozen task conforms; nonzero otherwise.
"""
import sys, json, tempfile
from pathlib import Path
import jsonschema

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence" / "frozen_evidence_package.json"

CLAIM_INPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "viper.verifier.claim_input.v1", "type": "object",
    "required": ["lhs", "rhs", "assumptions", "scope", "declared_basis"],
    "additionalProperties": False,
    "properties": {
        "lhs": {"type": "string"}, "rhs": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "scope": {"type": "string"},
        "declared_basis": {"type": "array", "items": {"type": "string"}}},
}
VERDICT_ENUM = ["VERIFIED_SYMBOLIC_IDENTITY", "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE",
                "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE", "CONVENTION_MISMATCH",
                "MISSING_ASSUMPTION", "UNSUPPORTED_CAPABILITY", "TOOL_ISOLATION_UNCONFIRMED"]
VERDICT_OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "viper.verifier.output.v1", "type": "object",
    "required": ["verdict", "evidence_level", "gold_oracle", "verifier",
                 "numerical_evidence", "independent_oracle_agreement"],
    "properties": {
        "verdict": {"type": "string", "enum": VERDICT_ENUM},
        "evidence_level": {"type": "string",
            "enum": ["3_symbolic_certificate", "2_reproducible_numerical_counterexample",
                     "1_numerically_consistent_only", "0_none"]},
        "gold_oracle": {"type": "string"}, "verifier": {"type": "string"},
        "independent_oracle_agreement": {"type": "boolean"},
        "numerical_evidence": {"type": "object",
            "required": ["relative_residual", "absolute_residual", "minimum_denominator_abs_eps_nm",
                         "sample_points_k", "model_seeds", "precision", "tolerance_policy",
                         "excluded_points"],
            "properties": {
                "relative_residual": {"type": "number"}, "absolute_residual": {"type": "number"},
                "minimum_denominator_abs_eps_nm": {"type": "number"},
                "tolerance_policy": {"type": "string"}, "precision": {"type": "string"},
                "excluded_points": {"type": "string"}}}},
}


def conform_frozen_evidence():
    pkg = json.loads(EVIDENCE.read_text())
    ok = 0; total = 0
    for tid, t in pkg["tasks"].items():
        rec = {"verdict": t["verdict"],
               "evidence_level": t["evidence_level"] + ("_only" if t["evidence_level"].endswith("consistent") else ""),
               "gold_oracle": pkg["gold_oracle"], "verifier": pkg["tested_verifier"],
               "independent_oracle_agreement": t["independent_oracle_agreement"],
               "numerical_evidence": t["numerical_evidence"]}
        total += 1
        try:
            jsonschema.validate(rec, VERDICT_OUTPUT_SCHEMA); ok += 1
        except jsonschema.ValidationError as e:
            print(f"  [{tid}] NON-CONFORMANT: {e.message}")
    return ok, total


def main():
    sample = {"lhs": "T_0^SHG (F-23)", "rhs": "sum_n f_n[ d_a G^bc - 2 d_b G^ac - 2 d_c G^ab ]",
              "assumptions": ["v^a_nm = i eps_nm A^a_nm", "n != m"],
              "scope": "two-band sector", "declared_basis": ["d_a G^bc", "d_b G^ac", "d_c G^ab"]}
    jsonschema.validate(sample, CLAIM_INPUT_SCHEMA)
    # derived schemas go to a temp dir — never mutate the frozen bundle
    out = Path(tempfile.mkdtemp(prefix="gate1_"))
    (out / "contract_claim_input.schema.json").write_text(json.dumps(CLAIM_INPUT_SCHEMA, indent=1))
    (out / "contract_verdict_output.schema.json").write_text(json.dumps(VERDICT_OUTPUT_SCHEMA, indent=1))
    ok, total = conform_frozen_evidence()
    print(f"Gate-1 contract: claim-input schema VALID; frozen evidence conforms {ok}/{total}")
    return 0 if ok == total and total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
