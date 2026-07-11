# Session Capabilities

## Capability Matrix

Each session has an explicit capability matrix defining:
- Allowed transformation levels
- Authorized backends
- Permitted operation types
- Maximum claim type

## Capability Enforcement

- All operations checked against capability matrix before execution
- Exceeding capabilities triggers semantic escalation
- No implicit capability expansion

## Capability Types

- `ingestion` — read and parse expressions
- `transformation` — apply transformations at authorized levels
- `verification` — verify identities and regressions
- `reporting` — generate reports and artifacts
- `integration` — freeze checkpoints
