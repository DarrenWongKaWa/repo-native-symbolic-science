# Getting Started with an Agent

This guide explains how to use the Repo-Native Symbolic Science framework through an agent-enabled coding environment such as Codex or Claude Code. No manual schema selection, validator invocation, or fixture execution is required to begin a scientific project.

Two entry paths are available:

- **Agent-first**: ask the agent in natural language to read the repo policies and route your request (recommended for most users)
- **Executable controller**: run the CLI directly with `python3 scripts/orch_controller.py` (see [Agent-First Controller Usage](agent_first_controller_usage.md) for the full guide)

## Clone and Open

```bash
git clone https://github.com/DarrenWongKaWa/repo-native-symbolic-science.git
cd repo-native-symbolic-science
```

Open the repository directory in your agent-enabled coding environment. The agent will automatically discover the repository policy (`REPO_POLICY.md`), agent configuration (`AGENTS.md` or `CLAUDE.md`), and available skills.

## First Natural-Language Request

A useful first request for any new project is:

> Use the Repo-Native Symbolic Science workflow for this project. Read `AGENTS.md` and `REPO_POLICY.md` first. Ingest the raw expression as immutable input, audit its scientific semantics, and tell me what definitions or assumptions are missing. Do not guess undefined symbols, index roles, boundary conditions, or allowed transformations.

This instructs the agent to:
1. Load the repository governance rules
2. Route through `scientific_symbolic_repo_entry`
3. Freeze your raw expression via `generic_raw_expression_ingestion`
4. Audit completeness via `human_scientist_semantic_escalation`

## What Files the Agent Should Read

When first activated, the agent should read at minimum:

| File | Purpose |
|------|---------|
| `REPO_POLICY.md` | Model-neutral governance rules |
| `AGENTS.md` or `CLAUDE.md` | Agent-specific adapter policies |
| `skills/*/SKILL.md` | Available skill definitions |
| `docs/architecture.md` | Repository architecture overview |
| `docs/human_agent_workflow.md` | Responsibility split and escalation protocol |

The agent reads additional files on demand as each skill is activated.

## What the Human Scientist Should Provide

For the most reliable and complete result, provide as many of the following as are currently known:

1. **Raw expression or source file** — the expression as raw bytes or file path
2. **Scientific definitions** — what each symbol, operator, and function means
3. **Index roles** — which indices are free, dummy, band, spatial, or external
4. **Assumptions and symmetry conditions** — nondegeneracy, real/complex fields, parity
5. **Desired target form** — expanded, factorized, series-expanded, or closed form
6. **Allowed transformations** — exact algebra, substitution, differentiation, series expansion
7. **Forbidden transformations** — integration by parts, boundary term discard, limit reordering
8. **Regression or comparison targets** — known special cases, limits, or numerical values
9. **Required order of limits or expansions** — which limit is taken first
10. **Publication or reporting goal** — what deliverable is expected

## What Happens When Information Is Missing

The framework is designed to stop safely when information is missing. The agent will:

1. Audit all symbols, indices, and assumptions against declared definitions
2. Produce a structured `human_information_request.md` listing exactly what is missing
3. Halt and wait for the human scientist to provide the missing information
4. Resume only after the human response is recorded in provenance artifacts

The framework distinguishes:

- **Not found in the declared search universe** — the symbol appears in the expression but has no definition
- **External source not supplied** — the definition requires an external reference that has not been provided
- **Definition rejected** — a definition was proposed but rejected by a verifier
- **Definition contradicted** — two definitions conflict
- **Definition accepted by a human gate** — a definition was explicitly authorized by the human scientist

"Not found" is never silently converted into "does not exist."

## What Happens When a Backend Is Unavailable

The framework probes available computation backends automatically:

| Backend | Status | Behavior When Unavailable |
|---------|--------|---------------------------|
| SymPy | Required (open source) | Framework will not operate; install SymPy |
| NumPy/SciPy/mpmath | Required (open source) | Numerical support unavailable; exact-only mode |
| Mathematica | Optional (proprietary) | Framework operates with open-source backends only |

When Mathematica is unavailable, the capability resolver returns `ENGINE_UNAVAILABLE` for Mathematica-only requests. The agent may offer a fallback or escalate to the human for a decision. Required open-source backends must be installed; the agent will request authorization before installing dependencies.

## What Artifacts Are Generated

A complete workflow generates the following artifact types:

| Stage | Artifacts |
|-------|-----------|
| Ingestion | `raw_object.json`, `raw_sha256.txt`, `ingestion_report.md` |
| Semantic Audit | `human_information_request.md`, `scientific_context.json` |
| Normalization | `normalized_parent.json`, `child_expressions.json`, `reconstruction_result.json` |
| Transformation | `candidate_transformation.json`, `rule_application_trace.json`, `transformation_report.md` |
| Backend Execution | `execution_truth.json`, `engine_output.json` |
| Verification | `claim_relation.json`, `verification_report.md`, `numerical_evidence.json` |
| Provenance | `checkpoint_manifest.json`, `canonical_state.json` |
| Reporting | `latex_evidence_mapping.json`, generated `.tex` and `.pdf` files |

All artifacts are stored with SHA-256 hashes and traceable provenance. No artifact is promoted from candidate to verified or from verified to canonical without an explicit human gate.

## No Manual Configuration Required

Users do not need to:

- Manually select schemas — the skills select the correct schema for each artifact
- Manually select validators — verification is routed through skill logic
- Manually select computation backends — the capability resolver selects backends automatically
- Run fixture suites before starting a project — fixtures exist for framework validation, not user workflow

When computation is needed, the agent probes available capabilities and requests authorization before installing dependencies or changing the environment.
