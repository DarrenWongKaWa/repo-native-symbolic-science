# Claim Governance

## Allowed Claims (no human gate required)

- "Task T's report dir contains the listed artifacts."
- "Task T's verdict is X, as recorded in <file>."
- "Prototype is open" (only if verified by current review/verifier report)

## Forbidden Claims (require verifier + reviewer + human gate)

- "Scientific sector is closed."
- "Derivation is complete."
- "Basis construction is authorized."
- "Global Guard is lifted." (Human-only)
- "Benchmark result implies derivation result."

## Claim Types

| Type | Description | Promotion Requires |
|------|-------------|-------------------|
| `exact_symbolic` | Verified by symbolic algebra | Verifier |
| `bounded_numeric` | Verified by numerical evaluation | Verifier |
| `pending` | Awaiting verification | — |
| `blocked` | Blocked by explicit guard | Human gate |

## Automatic Promotion

Automatic promotion from lower to higher claim types is **forbidden**.
All promotions require explicit verification and authorization.
