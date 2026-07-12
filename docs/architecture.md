# Architecture

## Overview

Repo-Native Symbolic Science is organized into layered modules:

1. **Schemas** — JSON Schema definitions for all artifact types (ORCH and SUPP)
2. **Engines** — Multi-backend CAS adapter layer (SymPy, NumPy/SciPy/mpmath, Mathematica)
3. **Loop Engine** — Executable controller runtime (dispatcher, registry, adapters)
4. **Scripts** — Orchestration, validation, verification scripts, and controller CLI
5. **Skills** — Agent skills for symbolic, orchestration, and supplement workflows
6. **Validators** — Validator implementations including the SUPP derivation-validation plugin
7. **Templates** — Reusable task and artifact templates
8. **Policies** — Governance and operation policies
9. **Tests** — Public fixture suites and synthetic test cases (91 tests)

## Data Flow

### Agent-first pathway

```
Human Request → Entry Skill → Task Classification → Engine Orchestrator
    → Backend Selection → Bounded Execution → Verification → Reporting
```

### Executable controller pathway

```
human-facing request
→ executable ORCH controller (scripts/orch_controller.py)
→ role/adapter registry (loop_engine/orch_registry.py)
→ dispatcher (loop_engine/orch_dispatcher.py)
→ planner / executor / verifier isolated contexts
→ SUPP validator plugin (validators/supplement_validator.py)
→ structured validation result
→ fail-closed controller decision
→ provenance-backed reporting
```

## Controller Component Map

| Component | Path | Purpose |
|-----------|------|---------|
| CLI entry point | `scripts/orch_controller.py` | Four subcommands: validate-task, check-transition, list-roles, run-workflow |
| Dispatcher | `loop_engine/orch_dispatcher.py` | Role routing, validation orchestration, workflow execution |
| Registry | `loop_engine/orch_registry.py` | Role definitions, adapter mappings, claim boundaries |
| Adapter registry | `loop_engine/orch_adapters/registry.json` | Combined ORCH + SUPP adapter configuration |
| SUPP validator | `validators/supplement_validator.py` | Derivation-step and cross-record validation |
| Synthetic adapters | `loop_engine/orch_adapters/synthetic_*.py` | Demonstration adapters for testing |
