# Computational Backend Selection

Role: Technical-routing skill that selects computation backends by capability, not by filename or arbitrary preference.

## Parent skill
`scientific_symbolic_repo_entry`

## Must do

1. Read the task package and scientific adapter.
2. Derive required technical capabilities from the request.
3. Probe available engines using `scripts/engine_orchestrator.py --probe-only`.
4. Select primary, supporting, and verifier backends based on capability matching.
5. Record unresolved capability gaps explicitly.
6. Refuse unsafe fallback — return `UNSUPPORTED_CAPABILITY` when no safe backend exists.
7. Generate an `engine_selection` artifact conforming to `schemas/engine_selection.schema.json`.

## Must not do

- Infer scientific definitions.
- Invent scientific assumptions.
- Promote backend routing to a scientific claim.
- Silent downgrade from exact symbolic to numerical sampling.
- Route by filename or arbitrary preference rather than declared capabilities.

## Capability resolution

Read `engines/engine_registry.json` and each adapter's `capability.json` to match requested capabilities.

The resolver must distinguish:
- `exact symbolic requirement` → only EXACT_SYMBOLIC engine types
- `structural replay requirement` → compatible expression representation
- `numerical support requirement` → NUMERICAL or HIGH_PRECISION_NUMERICAL types
- `high-precision requirement` → mpmath-capable backends
- `unsupported requirement` → explicit gap report
- `optional-backend unavailable` → safe EngineUnavailable result

## Fallback policy

| Fallback Policy | Behavior |
|---|---|
| `STRICT` | No backend without exact capability match; return `UNSUPPORTED_CAPABILITY` or require human decision |
| `ALLOW_NUMERICAL_FALLBACK` | Allow numerical backend for exact requests ONLY with explicit human authorization |
| `ALLOW_ANY_AVAILABLE` | Accept any available backend matching safety constraints |

## Unsafe fallback rule

- Never silently downgrade `exact symbolic verification` to `finite numerical sampling`.
- If no safe backend satisfies the request, return `UNSUPPORTED_CAPABILITY` and set `human_decision_required=true`.

## Output artifact

`engine_selection` conforming to `schemas/engine_selection.schema.json`, with:
- candidate_backends with match/gap analysis
- selected primary/supporting/verification backends
- selection reason referencing specific capabilities
- availability evidence from probe results
- capability gaps list
- human_decision_required flag

## Integration

Uses `engines/engine_registry.json` for registry.
Uses `scripts/engine_orchestrator.py` for probing.
Extends `session_capability_matrix` roles.
