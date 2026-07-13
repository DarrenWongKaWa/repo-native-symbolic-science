# Theoretical Supplement Pipeline Example

This example uses only the public synthetic two-sector supplement fixture.

Plan the workflow without executing stages:

```bash
python3 scripts/build_theoretical_supplement.py \
  --request examples/theoretical_supplement_request.json \
  --dry-run
```

Run the facade workflow:

```bash
python3 scripts/build_theoretical_supplement.py \
  --request examples/theoretical_supplement_request.json
```

The command writes `pipeline_plan.json`, `pipeline_state.json`, `pipeline_event_log.jsonl`, `skill_execution_manifest.json`, `missing_prerequisites.json`, and `final_result.json` to the request output directory.

The renderer is not invoked directly. Rendering is authorized only after `reporting_handoff_package.json` validates.
