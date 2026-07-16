#!/usr/bin/env python3
"""
Geometric-basis reconstruction — a repo capability.

Given a TARGET rank-3 tensor T^{abc} (a function of a model + k) and a declared
CANDIDATE BASIS of geometric rank-3 tensors {B_1^{abc}, ...}, find coefficients c
such that  T = sum_i c_i B_i, and either

  * CLOSED   : residual ~ 0  -> report c (rationalized), a reconstruction proof, OR
  * NOT CLOSED: residual > tol -> FAIL CLOSED: report the residual magnitude and the
    largest-leftover component = the direction of a candidate NEW irreducible tensor.

This is the "prove OR refute" contract 嘉华 described. It never force-fits a basis
that does not close; non-closure is a first-class, reported outcome.

Design follows the framework's discipline:
  - numerical fit is EVIDENCE; if a symbolic checker is supplied it is run separately.
  - a declared basis that does not span the target is REFUTED, not silently truncated.
"""
import numpy as np
from fractions import Fraction


def _rationalize(x, max_den=32, tol=1e-6):
    """Nearest simple rational to x, or None if not close to one."""
    f = Fraction(x).limit_denominator(max_den)
    return f if abs(float(f) - x) < tol else None


def reconstruct(target_fn, basis, models, kpoints, tol=1e-6):
    """
    target_fn(H,k) -> tensor [.,3,3,3]-summable to a scalar per (a,b,c); here we take
        the f_n-band-summed rank-3 component array of shape (3,3,3).
    basis = list of (name, fn) where fn(H,k) -> the same (3,3,3) array.
    models = list of H (each with .N); kpoints = list of k arrays.
    Returns a structured verdict dict.
    """
    # assemble linear system: rows = (model,k,a,b,c) samples, cols = basis tensors
    rows_T, rows_B = [], []
    for H in models:
        for k in kpoints:
            T = np.asarray(target_fn(H, k)).real
            Bs = [np.asarray(fn(H, k)).real for _, fn in basis]
            for a in range(3):
                for b in range(3):
                    for c in range(3):
                        rows_T.append(T[a, b, c])
                        rows_B.append([B[a, b, c] for B in Bs])
    y = np.array(rows_T)
    X = np.array(rows_B)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = X @ coef - y
    rel = np.linalg.norm(resid)/(np.linalg.norm(y) + 1e-30)

    verdict = {
        "n_samples": len(y),
        "basis": [name for name, _ in basis],
        "raw_coef": coef.tolist(),
        "target_norm": float(np.linalg.norm(y)),
        "abs_residual": float(np.linalg.norm(resid)),
        "rel_residual": float(rel),
    }

    if rel < tol:
        rats = [_rationalize(c) for c in coef]
        if all(r is not None for r in rats):
            # verify the rationalized coefficients still close (guards against a lucky fit)
            cr = np.array([float(r) for r in rats])
            rel_rat = np.linalg.norm(X @ cr - y)/(np.linalg.norm(y)+1e-30)
            verdict["coefficients"] = {name: str(r) for (name, _), r in zip(basis, rats)}
            verdict["rational_rel_residual"] = float(rel_rat)
            verdict["status"] = "CLOSED_RATIONAL" if rel_rat < 1e-4 else "CLOSED_NUMERICAL"
        else:
            verdict["status"] = "CLOSED_NUMERICAL"
            verdict["coefficients"] = {name: round(c, 6) for (name, _), c in zip(basis, coef)}
    else:
        # FAIL CLOSED: basis does not span the target. Locate the biggest leftover.
        # residual reshaped back to (model,k,a,b,c); report the (a,b,c) with max mean |leftover|
        R = resid.reshape(len(models)*len(kpoints), 3, 3, 3)
        comp = np.mean(np.abs(R), axis=0)  # (3,3,3)
        idx = np.unravel_index(int(np.argmax(comp)), comp.shape)
        verdict["status"] = "NOT_CLOSED"
        verdict["message"] = ("declared basis does NOT span the target; residual is a "
                              "component outside the basis (candidate new irreducible tensor)")
        verdict["largest_leftover_component"] = {"abc": list(map(int, idx)),
                                                 "mean_abs": float(comp[idx])}
    return verdict


def print_verdict(title, v):
    print(f"\n=== {title} ===")
    print(f"  basis: {v['basis']}")
    print(f"  samples: {v['n_samples']}   target_norm: {v['target_norm']:.4f}")
    print(f"  rel_residual: {v['rel_residual']:.2e}   status: {v['status']}")
    if "coefficients" in v:
        print(f"  coefficients: {v['coefficients']}")
        if "rational_rel_residual" in v:
            print(f"  (rationalized residual: {v['rational_rel_residual']:.2e})")
    if v["status"] == "NOT_CLOSED":
        print(f"  {v['message']}")
        print(f"  largest leftover at abc={v['largest_leftover_component']['abc']} "
              f"(mean |leftover| {v['largest_leftover_component']['mean_abs']:.4f})")
