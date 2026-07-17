"""Independent semantic validator: evidence-level / verdict cross-field constraints.
Deliberately a SEPARATE implementation from schema_validator and from the code that
produces verifier results (anti-circularity, per 嘉华's Gate-2 note)."""
class SemanticError(ValueError): pass
def check(res):
    v = res["combined_verdict"]; lvl = res["evidence_level"]
    if v == "VERIFIED_SYMBOLIC_IDENTITY":
        if lvl != 3: raise SemanticError("VERIFIED_SYMBOLIC_IDENTITY requires evidence_level=3")
        if not res["symbolic_oracle"].get("certificate"):
            raise SemanticError("VERIFIED_SYMBOLIC_IDENTITY requires a symbolic certificate")
        if res["numerical_verifier"]["verdict"] == "VERIFIED_SYMBOLIC_IDENTITY":
            raise SemanticError("numerical verifier may NOT self-upgrade to symbolic verification")
    if v == "DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE" and lvl < 2:
        raise SemanticError("DISPROVED requires evidence_level>=2")
    if v == "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE" and lvl == 3:
        raise SemanticError("NUMERICALLY_CONSISTENT must NOT claim symbolic level 3")
    # agreement must be consistent with the two oracle verdicts
    so, no = res["symbolic_oracle"]["verdict"], res["numerical_verifier"]["verdict"]
    sym_holds = so == "VERIFIED_SYMBOLIC_IDENTITY"
    num_holds = no == "NUMERICALLY_CONSISTENT_WITHIN_TOLERANCE"
    if res["agreement"] != (sym_holds == num_holds):
        raise SemanticError("agreement flag inconsistent with oracle verdicts")
    if (sym_holds != num_holds) and v != "INDEPENDENT_ORACLE_DISAGREEMENT":
        raise SemanticError("disagreeing oracles must yield INDEPENDENT_ORACLE_DISAGREEMENT (fail-closed)")
