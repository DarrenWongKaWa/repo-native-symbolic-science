# Object and Task Lifecycle

## Task Lifecycle

```
PLAN → EXECUTE → VERIFY → REVIEW → INTEGRATE → FREEZE
```

### Plan
- Define target, inputs, allowed operations, claim boundary
- Produce task contract and specification

### Execute
- Compute tables, reports, metrics, validation files
- Record provenance and SHAs

### Verify
- Check exact identities, regressions, row counts
- Run independent validators

### Review
- Audit review packets
- Return structured verdicts

### Integrate
- Freeze checkpoints
- Open next branches

## Object States

Objects in the system have explicit states:
- `raw` — ingested but not processed
- `normalized` — normalized but not transformed
- `candidate` — transformation proposed
- `verified` — transformation verified
- `canonical` — promoted to canonical (requires human gate)
