# Repo Policy

## Purpose

This file defines the model-neutral governance policy for all operations within this repository. Model-specific files (CLAUDE.md, CODEX.md) are thin adapters that delegate to this policy.

## Scientific Safeguards

1. The framework does not invent scientific assumptions
2. The framework does not automatically authorize IBP
3. The framework does not silently reorder scientific limits
4. Numerical agreement does not establish symbolic equality
5. Automatic canonical promotion is forbidden

## Claim Governance

- All scientific claims must be backed by repo artifacts
- Claims have explicit types: exact symbolic, bounded numeric, pending, blocked
- No automatic promotion from lower to higher claim types
- Human gate required for claim type promotions

## Operations Policy

- Allowed operations are explicitly authorized per task
- Forbidden operations include: publishing unlisted files, editing private source, publishing private scientific content

## Blocker 5 / Global Guard

- Default status: ACTIVE
- Prevents premature closure of scientific sectors
- Lifted only by explicit human acknowledgement

## Provenance

- All artifacts must be traceable
- SHA-256 hashes recorded for reproducibility
- Task lineage documented in reports
