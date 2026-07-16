# Viper — Frozen Release-Verification Bundle

This bundle is a frozen release-verification corpus.
It is not runtime gold data and is not accessible to the production verifier.

It exists so that a clean checkout of a fixed release commit can prove — from its own
contents alone, with no experiment-tree or working-tree state — that the frozen
geometric-basis verification workflow and its Gate 1–4 governance chain hold.

## What is here

```
verification/viper/
├── README.md                     ← this file
├── manifest.json                 ← bundle metadata, locks, provenance, scope caveat
├── schemas/                      ← frozen I/O contract
│   ├── condition_d_claim.schema.json
│   ├── verifier_result.schema.json
│   └── SCHEMA_LOCK.sha256.json
├── corpus/
│   ├── expected_results/families_results.json   ← frozen family ground truth (7 cases)
│   └── CORPUS_LOCK.sha256.json                   ← locks expected_results + fixtures
├── evidence/
│   ├── frozen_evidence_package.json              ← frozen F-23 task ground truth (7 tasks)
│   └── EVIDENCE_LOCK.sha256                       ← raw-file SHA-256 of the package
├── fixtures/{valid,invalid}/     ← hand-authored contract conformance fixtures
├── validators/                   ← independent structural + semantic validators
├── gate1_contract.py             ← Gate 1: frozen I/O contract conformance
├── gate2_conformance.py          ← Gate 2: 6-group conformance against the frozen corpus
└── run_release_verification.py   ← the single release-verification entry point
```

Notes on faithful mapping (no fabricated files, no regenerable duplicates):
- The "claims" corpus is the structured inputs embedded in `fixtures/` and in the frozen
  `expected_results` / `evidence` packages. No separately-regenerable claim files are
  committed, per the "do not commit files a script can regenerate" rule.
- `verifier_result.schema.json` is the frozen v1.x result contract; `manifest.json`
  records its version and lock.

## Runtime isolation (enforced by an automated test)

The production verifier and ORCH adapter MUST NOT import from `verification/`, and MUST
NOT be able to look a task up in this corpus by task ID. That would let gold answers leak
into the runtime and defeat the independent-oracle design. `tests/test_release_bundle_isolation.py`
asserts this: no shipped module references `verification.viper`, the frozen task IDs, or
the frozen evidence/corpus files.

## How to run

```
python verification/viper/run_release_verification.py
```

It performs, in order: record commit → verify schema/corpus/evidence locks → verify
runtime gold isolation → Gate 1 contract → Gate 2 conformance → real-CLI Gate 3 → real-CLI
Gate 4 → full pytest → secret/switch/alias scan → emit a machine-readable release report.
Any failed step exits nonzero and no success label is produced.

## Scope caveat

"Full" refers to the frozen geometric-basis verification workflow and its Gate 1–4
governance chain, not universal coverage of all symbolic-physics claims.
