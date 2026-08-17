# Changelog

This changelog is generated from the Git history of `main`. No GitHub Release
or version tag exists for any of these entries; the dates below are commit dates.

## Unreleased — main @ 52e1045 (2026-08-16)

Repository-native development continues on `main` without a formal release.
Recent evolution (newest first), with merge SHAs:

- **PR #9** (52e1045, 2026-08-16) — `work/demo-literal-anan-d3-bridge`:
  literal Anan D^(3) bridge demo (notation provenance, f_+ convention collision,
  thermal coefficient derivation, M/T/K kernels, six-orbit reduction, reality,
  literal Anan D3 six-orbit closure with clarified frozen contract, claim
  containment, mutation/adversarial controls); exploratory probe scratch files
  removed before merge (d46020c).
- **PR #8** (db5475f, 2026-08-16) — `work/viper-c0-minimal-compactification-loop`:
  minimal certified C0 compactification loop (Stage 1, Python/SymPy only):
  certified seed, LLM proposer, machine residual, independent verifier,
  fail-closed ZERO/NONZERO/UNKNOWN semantics, re-verifiable chain records;
  independent-review findings F-01..F-08 closed (62a8dd3).
- **PR #7** (bfb5bb4, 2026-08-16) — `fix/viper-b5-postmerge-review-blockers-v2`:
  B5 post-merge correction recorded (1bfc470) and reconciled onto main (a6891be).
- **Trusted Wolfram runtime hardening** (2026-07-31–2026-08-16): pin and verify
  the B3 Wolfram runtime (38a595f), reject redirected Wolfram trust boundaries
  (4b852dc), restore root-suite trusted-runtime isolation (a7c68de), stabilize
  the trusted Wolfram verification runtime (cbae6a8).
- **PR #6** (ff96fc7, 2026-07-31) — `feat/viper-b5-multivariable-t3`: bounded
  multivariable T3 certificate contract (ee4ea3c), multivariable T3 adversarial
  matrix (c838449), bounded multivariable T3 scope documentation (11b3a47),
  B5 attack-fixture isolation from leaked engine state (b5f7b69).
- **PR #5** (702b9f9, 2026-07-30) — `feat/viper-b4-domain-obligations`:
  first-class domain obligation graphs (8634135), B4 review packet
  (6f888df), obligation-graph review blockers (45bc523), hash-complete B4
  recovery packet (2066a69), B1-composite graph binding (2414a99), B4 packet
  canonical-hash correction (9bd1cff), multistep/componentwise graph blockers
  (51e5089), nonrecursive packet coverage (12c15d7), complete nonrecursive B4
  packet (5d185d4), O17 child/base binding (ae54e49), final B4 packet boundary
  (9b6a97f).
- **B3 independent second engine** (f774f16, 2026-07-30): independent
  second-engine ZERO confirmation required before an identity certificate is
  issued; a rigorous second-engine NONZERO conflicts fail closed.
- **B2 connected-subdomain identities** (923e6c5, 2026-07-30): governed
  conditional subdomain certificates (only the log-product route, explicit
  positive real subdomains), exp transformation hashes stabilized (a73fae7),
  exp subdomain transformations bound (71fb8a4), B2 independent review
  recorded (b48b344).
- **B1 composite T3 certificates** (16dbb83, 2026-07-30): recheckable composite
  T3 certificates with pinned second-engine confirmation.
- **PR #4** (1d37b9a, 2026-07-30) — `fix/second-cas-command-path-portability`:
  quoted configured stub commands in portability tests (e858c20).
- **PR #3** (7a5beee, 2026-07-29) — `feat/viper-llmsr-fusion-stage1` (LLM-SR ×
  Viper fusion): general symbolic identity verification capability (18567a6),
  evidence-sound symbolic identity judge (9de261a), governed proposer
  capability (61c8af3), searcher-cannot-reach-judge isolation (c76646f),
  audit-the-auditor cross-checked certificates + metamorphic fuzz (ce8b64b),
  re-checkable certificates (d9e1a32), differential canonicalization
  (b3432dc), re-checkable trig/exp certificates T1/T2 (18cbd34), domain guard +
  T3 derivative proofs + Gate 5 attacks + second CAS (43b26c), certificate-kind
  evidence honesty (d97766).
- **PR #2** (6c2d065, 2026-07-17) — Viper geometric-basis verification workflow:
  registered geometric basis verification adapter (159952f), extractable
  geometric-basis routing seam (4498315), Gate 4 orchestration governance
  attacks (8191ea6), frozen Gate 1-2 conformance bundle (b00bb44), declared
  verification runtime dependencies (c0f0c19).
- **2026-07-16** — safe-main release candidate recorded (250c849) and external
  safe-main replay recorded (94f1980).

## v0.1.0 — Initial Release (historical)

- Initial verified framework release (private staging)
- Multi-backend CAS adapter layer (SymPy, NumPy/SciPy/mpmath, Mathematica)
- 107 public files at that time: schemas, engines, skills, task templates, policies, tests, fixtures
- Apache-2.0 licensed
- Copyright 2026 Kawa Wong
