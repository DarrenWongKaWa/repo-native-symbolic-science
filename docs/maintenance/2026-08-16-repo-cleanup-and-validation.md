# Repository Cleanup + Scientific Validation — 2026-08-16

Maintenance report for `DarrenWongKaWa/repo-native-symbolic-science`.
Work performed on the isolated maintenance branch
`maintenance/repo-cleanup-docs-physics-validation-20260816`. Nothing was pushed.

## A. Authority

| Field | Value |
|---|---|
| origin/main baseline SHA | `52e104559d9ff2448193f03403e47fefe98718cb` (merge of PR #9, 2026-08-16) |
| Pre-fetch observation from request | `52e104559d9ff2448193f03403e47fefe98718cb` (identical — no movement) |
| Maintenance branch | `maintenance/repo-cleanup-docs-physics-validation-20260816` |
| Final HEAD SHA | FINAL_HEAD_PLACEHOLDER |
| Date / environment | 2026-08-16 (+08:00); macOS aarch64 (darwin); git 2.50.1 (Apple Git-155) |
| Python | CPython 3.12.13 in disposable venv `/tmp/rnss-maintenance-venv` (no global installs) |
| SymPy | 1.14.0 |
| NumPy / SciPy | 1.26.x / 1.18.0 |
| pytest | 9.1.1 |
| Wolfram | AVAILABLE — pinned `/Applications/Wolfram Engine.app` 15.0.0 resolves, hashes and codesign verified by `tools/wolfram_runtime.py`; B3 second engine exercised live |

## B. Cleanup

| Metric | Before | After |
|---|---|---|
| Tracked files | 495 | TRACKED_AFTER_PLACEHOLDER |
| Tracked `.md` files | 126 | MD_AFTER_PLACEHOLDER |
| Repository size (`du -sh .`) | 3.9M | SIZE_AFTER_PLACEHOLDER |
| Untracked / ignored junk removed | 0 (fresh worktree; none present) | — |
| Tracked files deleted | 0 | — |

No tracked file met the deletion bar (unreferenced AND superseded AND outside every
manifest/hash/fixture/claim contract). Three byte-identical manifest pairs and two empty
`__init__.py` files were examined and RETAINED (see section C).

The last exploratory scratch files had already been removed from the repository before
this maintenance run (`chore(demo): remove exploratory probe scratch files`,
`d46020c`, merged via PR #9).

## C. Preserved suspicious files

| Path | Why retained |
|---|---|
| `benchmarks/sigma_xxx_finite_gamma_replay/manifests/credential_scan.json` ≙ `public_path_sanitization.json` (byte-identical) | Distinct provenance slots referenced by name in `scripts/materialize_sigma_xxx_public_benchmark.py` / `validate_decision_provenance.py`; public-benchmark manifest contract |
| `benchmarks/.../manifests/output_sha_manifest.json` ≙ `public_file_inventory.json` (byte-identical) | Referenced by `run_case003r1_replay.py`, docs, and materialize scripts; hash-manifest contract |
| `benchmarks/.../manifests/git_state_before.json` ≙ `github002_git_state_before.json` (byte-identical) | Referenced by name in materialize scripts; provenance record of distinct runs |
| `loop_engine/orch_adapters/compactification_loop/__init__.py` ≙ `validators/__init__.py` (both empty) | Legitimate Python package markers |
| `benchmarks/.../inputs/*` vs `provenance/conversation_extraction/*` (near-duplicates, contents DIFFER) | Two distinct provenance layers (canonical inputs vs extraction record); both referenced |
| `demos/literal_anan_d3_bridge/claims/*` vs `proofs/out/*` (same names, contents DIFFER) | Claims are declarations; proofs/out are certificates. Both part of the demo contract |
| `schemas/engine_environment_probe.schema.json` | "probe" is the schema's subject (engine environment probing), not scratch |
| `demos/literal_anan_d3_bridge/sources/provenance.md` (two `/Users/kawawong/...` paths) | Deliberate provenance records ("recorded by the controller at demo build time"); modifying them would tamper with provenance. Flagged in G as a residual risk |

## D. Markdown audit

126 tracked `.md` files (plus 4 new files added by this run) inspected. Classification:
`CURRENT` / `STALE — UPDATE` / `HISTORICAL — PRESERVE VERBATIM` /
`REDUNDANT — REMOVE`. No file was removed.

MD_TABLE_PLACEHOLDER

## E. Verification

| Check | Result |
|---|---|
| Root `pytest -q` (baseline, before changes, commit 52e1045) | PASS — 528 passed, 0 failed, 0 skipped, 13 warnings in 4599.04s (EXIT 0) |
| Root `pytest -q` (after changes, final HEAD) | AFTER_PYTEST_PLACEHOLDER |
| `verification/viper/run_release_verification.py` | RELEASE_PLACEHOLDER |
| Controller smoke (`--help`, `list-roles`, `run-workflow`, transitions) | PASS (see below) |
| Invalid transition `RECEIVED → EXECUTING` | EXPECTED_REJECTION (`allowed: false`, exit 1) |
| sigma_xxx public benchmark replay | PASS (24/24 checks) |
| Literal Anan D3 demo (`run_all.sh`) | PASS (all gates; mutations red-flag; exit 0) |
| C0 compactification tests | PASS — `tests/test_c0_compactification_loop.py` + `tests/test_demo_literal_anan_d3.py`: 35 passed in 8.96s |
| Physics stress examples (`examples/physics_stress/run_all.py`) | PHYSICS_PLACEHOLDER |
| Clean-clone replay | CLEANCLONE_PLACEHOLDER |
| Repair-lineage benchmark | fast: 24/24 PASS · standard: 37/37 PASS · full: 38 PASS / 1 FAIL (`wolfram_12x12_rank`, environment: local Wolfram binary reports `Get::noopen: Cannot open -.` on stdin script — the documented 38/39 caveat; fail-closed, not a scientific failure; with Wolfram hidden from PATH the Wolfram stage SKIPs) |

## F. Physics stress cases

| Example | Scientific identity | Domain | Claim type | Verification route | Positive result | Mutation | Negative-control result |
|---|---|---|---|---|---|---|---|
| A — Dirac Berry curvature | `Ω_xy = −½ n·(∂_x n × ∂_y n) = −m/(2(kx²+ky²+m²)^{3/2})` | `kx,ky∈ℝ`; `m∈ℝ, m≠0` (gapped; `R=√(R²)>0` declared) | `identity_under_assumptions`, `real_scalars` | `symbolic-identity-verify` CLI; projector-trace + unit-vector mechanical strings | A1/A2: `VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS` (L3); A0 (long projector string): `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` (fail-closed boundary) | `Ω_xy` sign flip | `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` |
| B — Quantum metric | `g_xx=(ky²+m²)/4R⁴`, `g_yy=(kx²+m²)/4R⁴`, `g_xy=−kxky/4R⁴`, `det(g)=Ω_xy²/4=m²/16R⁶` | same gapped real domain | `identity_under_assumptions`, `real_scalars` | `symbolic-identity-verify` CLI; mechanical dot products + unsimplified determinant | B1–B5: `VERIFIED_SYMBOLIC_IDENTITY_WITH_SIDE_CONDITIONS` (L3) | `g_xy` sign flip; `Ω²/2` instead of `Ω²/4` | both `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` |
| C — finite-Γ resolvent | `1/(x+iΓ)−1/(x−iΓ)=−2iΓ/(x²+Γ²)`; `1/((x+iΓ)(x−iΓ))=1/(x²+Γ²)` | `x∈ℝ`; `Γ∈ℝ, Γ>0` (finite lifetime; retarded `+iΓ`, advanced `−iΓ`) | `identity_under_assumptions`, `real_scalars` (complex values only via `I`) | `symbolic-identity-verify` CLI (direct complex form; `re/im` decomposition also probed) | primary canonicalizers prove both; pinned second engine declines complex-valued confirmation → `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` (honest fail-closed: complex finite-Γ semantics not silently flattened) | advanced `x−iΓ → x+iΓ`; double-retarded product | both `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` |
| D — gauge equivalence | `A_L−A_sym=∇χ` componentwise; `∂_x A_y−∂_y A_x=B` for both gauges; pointwise `A_L≠A_sym` | `B,x,y∈ℝ`; `B` constant | `identity_under_assumptions`, `real_scalars` | `symbolic-identity-verify` CLI; derivation layer verifies the gauge relation exactly in SymPy before claim submission | D1–D4: `VERIFIED_SYMBOLIC_IDENTITY` (L3, clean) | `χ → Bxy` (1/2 dropped) | D5 (illegal pointwise equality) + mutation: `DISPROVED_BY_REPRODUCIBLE_NUMERICAL_COUNTEREXAMPLE` |
| Capability boundary | — | — | — | direct `cross(...)` / `matrix(...)` / `curl(...)` submissions | `UNSUPPORTED_BY_CURRENT_CONTRACT` (whitelist rejects with `UNDECLARED_OR_DISALLOWED_NAME`, exit 1) | — | — |

Final `run_all.py` verdict (definitive solo run, no concurrency, 2026-08-16):
**PASS — 25/25 claims met their expectation (EXIT 0)**. Certified at evidence level 3:
A1, A2, B1–B5, D1–D4 (A/B with recorded side conditions, D clean).
Fail-closed pending-second-engine (capability boundaries, never fake passes):
A0 (1369-char mechanical projector string) and C1/C2 (complex-valued `I` forms —
the pinned Wolfram engine declines confirmation within its bounds).
Refuted with reproducible numeric counterexamples: Am, Bm×2, Cm×2, D5, Dm.
Unsupported grammar rejected fail-closed: Au, Bu, Cu, Du.

## G. Residual risks

- Vector/matrix mechanics (Pauli traces, cross products, gradients, curls) live in the
  trusted derivation layer; the whitelist judge certifies the resulting scalar pointwise
  identities only. Direct matrix/cross/curl syntax is `UNSUPPORTED_BY_CURRENT_CONTRACT`
  (demonstrated fail-closed).
- The pinned Wolfram second engine declines confirmation on some claim shapes
  (very long mechanical strings, complex-valued `I` forms, `re/im` forms); the
  framework then reports `SYMBOLIC_ZERO_PENDING_SECOND_ENGINE` — honest, never a fake
  PASS. Such claims remain at evidence level 1 with an unresolved B3 obligation.
- Historical documents and frozen evidence were intentionally preserved verbatim
  (benchmark manifests, extraction summaries, Viper reviews, demo certificates).
- `demos/literal_anan_d3_bridge/sources/provenance.md` records two absolute host paths
  as provenance metadata; `docs/TROUBLESHOOTING.md` says public files must not contain
  absolute paths. Both left intact (provenance immutability); tension documented here.
- No GitHub Actions workflow exists on `main` (only issue/PR templates); release
  verification is the repo-local `verification/viper/run_release_verification.py`.
- Demo certificates regenerate `commit`/`timestamp_utc` provenance fields on each run;
  scientific content is deterministic. Restored to the committed frozen state after the
  replay so the maintenance branch carries no regeneration noise.
