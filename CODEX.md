# Codex / Superpowers Rules

This file is a thin adapter to the model-neutral `REPO_POLICY.md` and skills.

## Loop Discipline
- Do not edit symbolic output by hand without rerunning validation.
- Do not skip structured reviewer packet generation.
- Use isolated stages or git worktrees for active derivation work.
- Never replace a validated checkpoint in place; create a new checkpoint version.

## Symbolic Rules
- Do not claim simplification unless validated.
- Do not discard terms by intuition.
- Always record convention maps.
- Always distinguish general identities from model-specific parity or symmetry reductions.

## Roles
- Human scientist: defines target, basis, allowed operations, and claim boundary.
- Planner: converts the target into staged plans.
- Executor: computes tables, reports, metrics, and validation files.
- Verifier: checks exact identities, regressions, row counts, and benchmark gates.
- Reviewer: audits review packets and returns structured verdicts.

## Model-specific note
This file delegates to `REPO_POLICY.md` and listed skills for detailed rules.
