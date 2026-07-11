# CLAUDE.md — Universal Repo Rules

This file holds **stable, universal** working rules for this repository.
It is intentionally minimal: it is a contract with the executor, not a dump of current state.

## 1. Think before acting
- Read the task spec end-to-end **before** writing any file.
- Identify forbidden / allowed write paths.

## 2. Surgical changes only
- Touch only the files explicitly authorized.

## 3. Model-specific files
- `CLAUDE.md` and `CODEX.md` are thin adapters to the model-neutral `REPO_POLICY.md`.
- When in doubt, refer to `REPO_POLICY.md` and the relevant skill documentation.
