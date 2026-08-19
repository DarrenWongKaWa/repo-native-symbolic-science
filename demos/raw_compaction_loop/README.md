# Unknown raw-compaction loop

This public, synthetic fixture demonstrates the workflow for an **unknown raw
Wolfram expression**: an external model proposer sees only frozen raw text and
emits data-only compactification plans; a separate structural verifier decides
whether any plan can be replayed structurally from that raw text.

The supplied Guo full-tensor source remains local and is deliberately not
committed here: this repository's public examples must stay synthetic and
redistributable. You may pass an authorized local source with `--raw`; evidence
will label it `EXTERNAL_UNPINNED` unless you add a separate approved manifest.
For that external source, `compact_candidate.wl` is withheld by default; pass
`--emit-external-wolfram` only after you have authorized that local source for
Wolfram output.

It is intentionally narrower than the generic C0 compactification capability.
C0 verifies a restricted SymPy identity grammar, whereas this fixture uses
Wolfram `Sum`, indexed functions, `Piecewise`, and
coincidence branches.  Treating the latter as a C0 identity would be a false
claim of coverage, so this demo supplies its own constrained raw-text verifier.

## Start with the workflow map

Open the [interactive workflow map](raw_compaction.workflow.html) for the
shortest route through the demo, or inspect its editable
[Archify specification](raw_compaction.workflow.json). The map makes three
beginner-critical facts visible: the model is outside the trust boundary,
candidate plans are JSON data rather than code, and a rejected plan returns as
feedback instead of becoming a result.

## Trust boundary

```text
raw/synthetic_unknown_tensor.wl
        │ SHA-256 locked
        ▼
external proposer command (LLM in a real run)
        │ JSON grouping plans only — no code execution
        ▼
raw_text_structural_verifier_v1
        │ literal kernel / iterator / factor / coverage gates
        ├── DIAGNOSTIC feedback for a rejected proposal
        └── STRUCTURAL_CERTIFIED compact_candidate.wl
```

The verifier does not load a known compact formula, expected term positions, or
kernel hashes. It obtains all comparisons directly from the raw input. A
proposal succeeds only if its groups cover the raw source exactly, paired sums
have byte-identical iterator domains and final kernel factors, and any proposed
prefix factor is byte-identical in both terms. It also replays the emitted
Wolfram template against the source components. This is a structural
factorization artifact only—not an independent equality proof, a scientific
theorem, a weak-Gamma reduction, or canonical promotion.

## Target-architecture status

This demo now exports the shared scientific-compaction artifacts: its frozen
structural contract \(A_i\), current representation \(C_i\), proposal-only
\(\tilde C_{i+1}\), pending independent-verification record, blocked human-selection
gate, and hash-linked pending chain node. The local structural replay is useful
evidence, but it remains `UNKNOWN` for the target architecture until an
independent CAS verifier supplies a residual verdict. See the repository-wide
[target architecture](../../docs/scientific_compactification_target_architecture.md).

## Run

The included backend is an offline fixture, not an LLM. It deliberately emits
one bad plan and then a valid plan so the demo shows both fail-closed feedback
and loop completion:

```bash
python3 demos/raw_compaction_loop/run_demo.py \
  --proposer-cmd "python3 demos/raw_compaction_loop/fixtures/mock_proposer.py" \
  --proposer-id "offline-test-fixture" \
  --out-dir /tmp/raw_compaction_demo
```

For a real LLM, replace the command with a wrapper that reads one JSON object
from standard input and writes only a JSON array conforming to the protocol in
`run_demo.py`. The raw expression is supplied in that JSON envelope; the model
does not receive a compact answer key. Model output is parsed as data and is
never executed. The evidence records the model identifier (when provided), plus
hashes of the command, request envelope, and response. No credentials or model
command text are recorded.

The included fixture is not an LLM and has a known valid plan hard-coded. It
tests the trust boundary and failure/recovery path only; it does **not** show
blind model discovery. A real run also cannot establish that a model had no
prior training or developer knowledge of a source—only that no answer key was
passed through this protocol.

The evidence file records the raw hash, every proposal, each accepted/rejected
verdict, node hashes, and the selected candidate. Generated output is ignored
by Git under `out/`.

## Files

- `raw/` holds the public synthetic source; [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)
  pins its SHA-256, redistributability, and operation boundary.
- `run_demo.py` is the untrusted-proposer boundary and trusted verifier.
- `fixtures/mock_proposer.py` is a deterministic offline test fixture only.
