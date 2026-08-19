# Scientific Compactification Target Architecture

This is the repository-wide target for turning a current representation
Σᵢ into a compact next representation Σᵢ₊₁. It is deliberately
broader than either existing executable slice:

- C0 supplies an exact SymPy residual chain for a restricted identity grammar.
- The raw-compaction demo supplies a structural Wolfram replay for a restricted
  `Sum`/factor grammar.

Neither is allowed to silently stand in for the complete architecture.

Open the [interactive target workflow](scientific_compactification_target.workflow.html)
or inspect its editable [Archify specification](scientific_compactification_target.workflow.json).

## Required state transition

```text
human scientific contract A_i + immutable C_i
  -> untrusted proposal C~_(i+1)
  -> independent residual verdict {ZERO, NONZERO, UNKNOWN}
  -> human compactness-and-meaning selection
  -> selected C_(i+1), or a preserved diagnostic / blocked node
```

The new shared implementation is
[`loop_engine/scientific_compactification/core.py`](../loop_engine/scientific_compactification/core.py).
It supplies the contract and provenance artifacts and never trusts an external
residual assertion. The bundled C0 bridge is the current trusted exception: it
recomputes the hash-bound (C_i\to\tilde C_{i+1}) SymPy residual itself.

## Contracts and roles

| Target role | Repository component | Hard boundary |
|---|---|---|
| Human scientific contract | `scientific_compactification_contract.schema.json` | Declares scope, operations, assumptions, preferences, and stopping rule. |
| Structure proposer | Configured `--proposer-cmd` or `propose_equation_candidates` | Emits proposal data only; cannot verify or select. |
| Independent CAS verifier | Registered rechecker / C0 SymPy bridge | External CAS JSON is recorded as a pending attestation; only a registered recheck can open selection. |
| Diagnostic residual packet | `NONZERO` / `UNKNOWN` verifier record | Preserved; never converted into a success. |
| Human selection | `apply_human_selection` | A verified candidate remains unselected until a recorded `SELECT` or `REJECT` decision. |
| Proof-carrying edge | `build_chain_node` | Hash-binds A_i, C_i, proposal, verifier result, selection, and parent node. |

## Current migration status

### Raw Wolfram compaction demo

The demo now freezes a structural-only contract, current raw representation,
candidate carrier definitions, and a hash-linked pending node. Its local replay
is explicitly `PENDING_INDEPENDENT_VERIFICATION`, so it cannot open the human
selection gate. A future external Mathematica/Wolfram result is first recorded
as an attestation; a registered independent rechecker must bind its immutable
artifact before a human can select the compact form.

### C0 exact identity loop

`scripts/run_c0_loop_demo.py` now bridges every C0 node into the shared target
contract. A C0 `ZERO` residual is eligible for human selection, not automatic
promotion. `NONZERO` and `UNKNOWN` nodes remain blocked/diagnostic.

## ORCH entry point

```bash
python3 scripts/orch_controller.py scientific-compactification
```

The request schema is
[`scientific_compactification_request.schema.json`](../schemas/scientific_compactification_request.schema.json).
Supported actions are `bootstrap`, `adjudicate`, `select`, and `bridge_c0`.
`adjudicate` records an external attestation as pending; `bridge_c0` is the
currently bundled trusted recheck path.
The capability exists only in the full ORCH profile; proposer and judge profiles
cannot create contracts or make selections.

## Non-negotiable claim boundary

- `UNKNOWN` never becomes `ZERO` through structural replay or numerical support.
- A candidate is never selected, canonical, or terminal without a human decision.
- The framework does not infer missing definitions, assumptions, symmetry, IBP,
  boundary conditions, or scientific preference from notation.
- The human may reject a mathematically verified candidate for poor compactness
  or absent scientific meaning; that decision is part of the chain provenance.
- `human_scientist` is a recorded decision-role attestation and SHA integrity
  binding, not cryptographic identity authentication. Deployments requiring
  authenticated sign-off must attach an organization-specific signed decision
  artifact before invoking `select`.
