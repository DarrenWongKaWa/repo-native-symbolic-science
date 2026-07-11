# Architecture

## Overview

Repo-Native Symbolic Science is organized into layered modules:

1. **Schemas** — JSON Schema definitions for all artifact types
2. **Engines** — Multi-backend CAS adapter layer (SymPy, NumPy/SciPy/mpmath, Mathematica)
3. **Scripts** — Orchestration, validation, and verification scripts
4. **Skills** — Agent skills for specific symbolic workflow operations
5. **Task Templates** — Reusable task definition templates
6. **Policies** — Governance and operation policies
7. **Tests** — Public fixture suites and synthetic test cases

## Data Flow

```
Human Request → Entry Skill → Task Classification → Engine Orchestrator
    → Backend Selection → Bounded Execution → Verification → Reporting
```
