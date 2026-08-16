#!/usr/bin/env python3
"""Finite-Gamma retarded/advanced resolvent claims (no derivation needed; the
identities are stated directly with explicit real-energy and Gamma>0 semantics).

Claims:
  C1_ret_adv          positive   1/(x+iG) - 1/(x-iG) == -2 i G/(x^2+G^2)
  C2_resolvent        positive   1/((x+iG)(x-iG))   == 1/(x^2+G^2)   (|G^R|^2 structure)
  Cm_adv_to_ret       mutation   advanced x-iG replaced by retarded x+iG
  Cm_double_ret       mutation   product of two retarded resolvents
  Cu_cross            unsupported_grammar
"""
import json

SYM = ["x", "G"]
ASM = ["x real; G real, G>0 (finite Gamma; retarded has +iG, advanced has -iG)"]
records = [
    {"id": "C1_ret_adv", "kind": "positive",
     "obligation": "complex arithmetic in the whitelist judge (I, conjugation structure)",
     "claim": {"lhs": "1/(x+I*G) - 1/(x-I*G)", "rhs": "-2*I*G/(x**2+G**2)",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "C2_resolvent", "kind": "positive",
     "obligation": "complex arithmetic in the whitelist judge (I*I == -1)",
     "claim": {"lhs": "1/((x+I*G)*(x-I*G))", "rhs": "1/(x**2+G**2)",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Cm_adv_to_ret", "kind": "mutation",
     "obligation": "numeric counterexample probe (advanced term replaced by retarded must be refuted)",
     "claim": {"lhs": "1/(x+I*G) - 1/(x+I*G)", "rhs": "-2*I*G/(x**2+G**2)",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Cm_double_ret", "kind": "mutation",
     "obligation": "numeric counterexample probe (two retarded resolvents must not equal the real modulus)",
     "claim": {"lhs": "1/((x+I*G)*(x+I*G))", "rhs": "1/(x**2+G**2)",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
    {"id": "Cu_cross", "kind": "unsupported_grammar",
     "obligation": "whitelist parser (free-text complex-conjugation operator is not judge grammar; fail closed)",
     "claim": {"lhs": "conj2(x+I*G)", "rhs": "x-I*G",
               "symbols": SYM, "scope": "real_scalars", "assumptions": ASM}},
]
for r in records:
    print(json.dumps(r))
