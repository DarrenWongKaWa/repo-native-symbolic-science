# Codex / Superpowers Rules

Always use a Superpowers-style workflow for nontrivial symbolic-simplification tasks.

## Loop Discipline

- Do not edit symbolic output by hand without rerunning validation.
- Do not skip structured reviewer packet generation.
- Do not freeze a checkpoint without `validation_summary.json` and `review_result.json`.
- Use isolated stages or git worktrees for active derivation work when available.
- Preserve raw provenance tables.
- Never replace a validated checkpoint in place; create a new checkpoint version.

## Symbolic Rules

- Do not claim simplification unless `old - new` or `old - new - dF` validates.
- Do not discard terms by intuition.
- Do not mix pre-IBP and post-IBP tables.
- Do not reuse stale output.
- Always record convention maps.
- Always distinguish general identities from model-specific parity or symmetry reductions.
- Do not claim a tensorial formula is correct until the protected projection benchmark passes.
- Reviewer agents must not edit code, symbolic outputs, validation files, or checkpoints.
- Reviewer agents audit exactness gates, stale inputs, regressions, claim boundary, and next action; they do not replace verifier scripts.
- Routine branch review should use read-only Codex subagents: `AlgebraReviewer`, `PhysicsReviewer`, and `SoftwareReviewer`.
- Major checkpoints, paper claims, final scientific audits, and next-branch scientific-route decisions should receive a separate web-GPT audit.
- Do not confuse Codex app `/review` for code diffs with symbolic reviewer-agent audit.

## Roles

- Human scientist: defines target, basis, allowed operations, and claim boundary.
- Planner: converts the target into staged plans.
- Executor: computes tables, reports, metrics, and validation files.
- Verifier: checks exact identities, regressions, row counts, and benchmark gates.
- Reviewer: audits review packets and returns structured verdicts.
- Integrator: freezes checkpoints and opens next branches.
