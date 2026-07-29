#!/usr/bin/env python3
"""Second-opinion CAS — audit-the-auditor #5.

Every safeguard so far (differential canonicalization, numeric cross-check, re-checkable
certificates) still runs inside ONE engine: sympy. A bug shared across sympy's routines is
invisible to all of them. This script is a SECOND, INDEPENDENT engine.

It reads {"lhs":..,"rhs":..,"symbols":[..]} on stdin and prints
{"engine":..,"verdict":"ZERO"|"NONZERO"|"UNKNOWN","detail":..} on stdout.

Engines used (whichever are importable under the interpreter this runs on):
  * symengine — independent C++ core; expands the difference and tests for zero.
  * python-flint / Arb — rigorous ball arithmetic; an enclosure that EXCLUDES zero is a
    proof of non-zero (stronger than float sampling, which can only suggest).

Run it under an interpreter that has those installed and point the judge at it with
    VIPER_SECOND_CAS_CMD="/path/to/python /path/to/tools/second_cas_opinion.py"
Nothing here is imported by the judge; it is invoked as a separate process.
"""
import json, sys


def _symengine_opinion(lhs, rhs, symbols):
    import symengine as se
    # symengine.sympify takes exactly one argument; symbols are created from the text
    d = se.expand(se.sympify(f"({lhs})-({rhs})"))
    return ("ZERO", "symengine expand -> 0") if d == 0 else ("UNKNOWN", f"symengine expand -> {str(d)[:70]}")


def _flint_opinion(lhs, rhs, symbols):
    """Rigorous non-zero proof via Arb ball arithmetic at sample points."""
    import flint
    flint.ctx.prec = 256
    env = {"arb": flint.arb}
    pts = [("0.3721"), ("-0.8134"), ("1.4142"), ("2.7183")]
    for p in pts:
        loc = {s: flint.arb(p) for s in symbols}
        fns = {"sin": lambda z: z.sin(), "cos": lambda z: z.cos(), "exp": lambda z: z.exp(),
               "log": lambda z: z.log(), "sqrt": lambda z: z.sqrt(), "tanh": lambda z: z.tanh(),
               "sinh": lambda z: z.sinh(), "cosh": lambda z: z.cosh(), "atan": lambda z: z.atan(),
               "asin": lambda z: z.asin(), "tan": lambda z: z.tan()}
        try:
            val = eval(compile(f"({lhs})-({rhs})", "<claim>", "eval"), {"__builtins__": {}}, {**loc, **fns})
        except Exception:
            continue
        try:
            if not val.contains(flint.arb(0)):
                return ("NONZERO", f"Arb enclosure at {p} excludes 0: {val} — rigorous counterexample")
        except Exception:
            continue
    return ("UNKNOWN", "Arb enclosures all contain 0 (consistent, not a proof of zero)")


def main():
    try:
        req = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"engine": "none", "verdict": "UNKNOWN", "detail": f"bad input: {e}"})); return 1
    lhs, rhs, symbols = req.get("lhs", ""), req.get("rhs", ""), req.get("symbols", [])
    engines, verdict, details = [], "UNKNOWN", []
    # a rigorous NONZERO from any engine dominates: it is a proof of non-identity
    for name, fn in (("python-flint/Arb", _flint_opinion), ("symengine", _symengine_opinion)):
        try:
            out = fn(lhs, rhs, symbols)
        except ImportError:
            continue
        except Exception as e:
            details.append(f"{name}: error {type(e).__name__}"); continue
        if out is None:
            continue
        engines.append(name); v, d = out; details.append(f"{name}: {d}")
        if v == "NONZERO":
            verdict = "NONZERO"
        elif v == "ZERO" and verdict != "NONZERO":
            verdict = "ZERO"
    if not engines:
        print(json.dumps({"engine": "none", "verdict": "UNAVAILABLE",
                          "detail": "no independent CAS importable under this interpreter"})); return 2
    print(json.dumps({"engine": "+".join(engines), "verdict": verdict, "detail": " | ".join(details)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
