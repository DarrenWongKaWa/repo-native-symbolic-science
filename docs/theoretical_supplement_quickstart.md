# Theoretical Supplement Quickstart

To generate a complete theoretical supplement, use:

```bash
python3 scripts/build_theoretical_supplement.py --request request.json
```

The internal supplement skills are implementation stages and normally should not be invoked manually. The pipeline facade plans dependencies, validates native artifacts, persists resumable state, enforces the renderer authorization gate, and returns one machine-readable final result envelope.

| Layer | Responsibility | Direct user invocation |
|---|---|---|
| Derivation graph | Formal dependency DAG | Usually no |
| Narrative | Step-by-step explanation | Usually no |
| Interpretation | Mathematical and physical term meaning | Usually no |
| Assembly | Section assembly, audit, handoff | Usually no |
| Renderer | Traceable TeX/PDF from validated handoff | Usually no |
| End-to-end pipeline | Runs the complete workflow | Yes |

Warning:

```text
Do not invoke verified_provenance_to_latex_pdf directly unless a validated
reporting_handoff_package.json already exists.
```

## Minimal Request

```json
{
  "request_id": "example_theoretical_supplement",
  "source_manifest": "fixtures/supplement/two_sector_response/source_artifact_manifest.json",
  "output_directory": "output/example_theoretical_supplement",
  "audience": "theoretical_physicist",
  "output_formats": ["latex", "pdf"],
  "pipeline_mode": "full",
  "require_term_level_interpretation": true,
  "require_long_expression_reconstruction": true,
  "require_independent_readability_review": true
}
```

## Dry Run

```bash
python3 scripts/build_theoretical_supplement.py \
  --request examples/theoretical_supplement_request.json \
  --dry-run
```

## Resume

```bash
python3 scripts/build_theoretical_supplement.py \
  --request examples/theoretical_supplement_request.json \
  --resume
```

Resume reuses only SHA-valid prior outputs. Stale or partial artifacts are not silently accepted.
