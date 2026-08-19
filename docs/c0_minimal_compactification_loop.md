# C0 — Minimal Certified Compactification Loop (Stage 1)

**Status:** merged to `main` via PR #8 (merge `db5475f`, 2026-08-16).
**Development branch:** `work/viper-c0-minimal-compactification-loop`
**Base:** `main @ bfb5bb4b817162fdf87aee7a9c41bacca3e898b1` (B5 frozen authority)
**Calculations:** Python / SymPy only — no Wolfram in this capability.
**Scope guard:** no repository cleanup, no candidate ranking, no e-graph, no
automatic termination search. This stage only makes one minimal loop step
executable, auditable, and regression-locked.

## 1. The loop

```
            ┌──────────────────────────────────────────────┐
            │                                              ▼
    certified C_i ──► LLM proposer ──► candidate C̃_{i+1} ──► machine residual R_i
            ▲                                              │
            │                                              ▼
            │                                   independent Python verifier
            │                                              │
            │                          ┌───────────────────┴──────────────────┐
            │                          ▼                                      ▼
            │                   R_i == 0  (ZERO)                     R_i ≠ 0 (NONZERO)
            │                          │                        / UNKNOWN (fail-closed)
            │                          ▼                                      │
            │                 certified C_{i+1}                        diagnostic feedback
            └──────────────── (chain node appended) ◄────────────────────────┘
```

- **C_i** — a certified identity claim `lhs == rhs` over declared symbols, with a
  chain record (parent edge, residual evidence, certificate).
- **LLM proposer** — the existing `propose_equation_candidates` adapter
  (LLM-SR fusion Stage 2). It emits UNVERIFIED candidates only; its backend is a
  config-driven subprocess (`VIPER_PROPOSER_CMD`); output is DATA, never executed;
  candidates are whitelist-parsed with the judge's own strict parser.
- **Machine residual R_i** — *no LLM in this step.* Given certified parent
  `C_i = (lhs_i, rhs_i)` and candidate `C̃_{i+1} = (lhs_{i+1}, rhs_{i+1})`, the
  machine constructs the difference-of-differences claim

  ```
  R_i :   (lhs_{i+1} − rhs_{i+1})  ==  (lhs_i − rhs_i)
  ```

  by pure string composition of already-validated sub-expressions, followed by
  strict re-validation with the shared whitelist parser.
- **Independent Python verifier** — exact SymPy adjudication, fail-closed
  semantics mirroring the B3 engine:
  - parse both sides with the strict whitelist (symbols honour their declared
    real/complex/nonzero assumptions);
  - `diff = expand(lhs − rhs)` then bounded simplification;
  - `simplify(diff) == 0`  →  **ZERO** (identity certified);
  - else exact rational (and ±i for complex symbols) counterexample probes;
    an exact nonzero value  →  **NONZERO** (identity refuted, counterexample
    evidence recorded);
  - otherwise  →  **UNKNOWN** (fail-closed; never guessed).
- **Chain record** — every node stores claim, parent id, residual, verdict,
  evidence, certificate references, SHA-256 hashes, timestamps; an independent
  process can re-verify any node from the record alone.

## Target-architecture bridge

C0's `ZERO` verdict certifies the identity relation, but it does **not** choose
the next scientific representation automatically. `scripts/run_c0_loop_demo.py`
now maps C0 nodes into the shared
[scientific compactification target architecture](scientific_compactification_target_architecture.md):
the frozen contract (A_i), (C_i), candidate, independent residual evidence,
and a `HUMAN_SELECTION_REQUIRED` gate are recorded together. A human must still
select or reject the verified candidate before it becomes (C_{i+1}).

## 2. Why this is sound

For certified parent `C_i` (i.e. `lhs_i − rhs_i = 0`):

```
R_i == 0  ⇔  (lhs_{i+1} − rhs_{i+1}) − (lhs_i − rhs_i) = 0  ⇒  lhs_{i+1} − rhs_{i+1} = 0
```

so `R_i == 0 ∧ C_i` certifies `C_{i+1}`. Conversely, if `C_{i+1}` holds then
`R_i` holds trivially. Certifying the residual therefore certifies the next
claim, and the certificate of `C_{i+1}` is *the pair* (certificate of `C_i`,
certificate of `R_i`) — the delta is explicit and auditable.

If `R_i` is **NONZERO**, the verifier's simplified residual with its exact
counterexample is the machine-constructed diagnostic fed back to the LLM.

## 3. Seed

`C_0` is taken from the frozen geobasis corpus family `METRIC_true`
(`verification/viper/corpus/expected_results/families_results.json`), whose
symbolic gold oracle is `loop_engine/orch_adapters/geobasis_verify/families.py`
(`symbolic_gold("METRIC")`, per-summand identity):

```
( v^a v^b + v^b v^a ) / ε²  ==  2 Re( A^a_nm A^b_mn )
```

with `A^a_nm = v^a/(iε)`, `A^b_mn = conj(v^b)/(−iε)`, i.e. exactly

```
(va*conjugate(vb) + vb*conjugate(va))/eps^2  ==
(va*conjugate(vb) + conjugate(va)*vb)/eps^2
```

over complex `va, vb` and real nonzero `eps`. The seed record lives in
`loop_engine/orch_adapters/compactification_loop/seeds/METRIC_true_seed.json`
and is itself verified (must adjudicate ZERO) before any loop step runs.

## 4. Files

- `loop_engine/orch_adapters/compactification_loop/` — core capability
  - `core.py` — seed loading, residual construction, Python verifier, chain records
  - `seeds/METRIC_true_seed.json` — certified C_0
  - `schemas/claim_chain.schema.json` — chain-node contract
- `loop_engine/orch_adapters/compactification_loop_adapter.py` — thin ORCH adapter
- `loop_engine/orch_adapters/registry.json` — role + adapter registration
- `tests/test_c0_compactification_loop.py` — regression tests (pure Python)
- `scripts/run_c0_loop_demo.py` — end-to-end demo (real LLM proposer + Python verifier)
- this document

## 5. Explicitly out of scope (Stage 1)

- repository cleanup / unrelated history
- candidate ranking or scoring (proposer explicitly cannot score)
- e-graph / term-rewriting search
- automatic termination search / loop scheduling
- Wolfram-backed verification (B5 remains for the B-series; C0 is Python-only)
- assumption-based residual acceleration (verifying R_i with C_i as a rewrite
  assumption is future work; Stage 1 verifies R_i independently)
