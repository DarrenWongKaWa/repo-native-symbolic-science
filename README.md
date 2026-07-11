# Repo-Native Symbolic Science

A repo-native framework for auditable human-agent symbolic science, with semantic escalation, independent verification, provenance governance, and traceable scientific reporting.

## Purpose

This project provides a repo-native framework for auditable human-agent symbolic science. It establishes a structured environment where human scientists define semantics and assumptions, agents manage planning and governance, CAS/numerical engines perform bounded computation, and independent verifiers replay and adjudicate results.

## Human-Agent Responsibility Split

- **Human scientist**: scientific semantics, assumptions, and authorization
- **Agent**: planning, orchestration, and claim governance
- **CAS/numerical engine**: bounded computation
- **Independent verifier**: replay, comparison, and adjudication

## Supported Backends

- **SymPy**: open-source exact symbolic baseline (required)
- **NumPy / SciPy / mpmath**: numerical and high-precision support (required)
- **Mathematica**: optional verified commercial backend (optional, not mandatory)

## Scientific Safeguards

- The framework does not invent scientific assumptions
- The framework does not automatically authorize IBP (Integration By Parts)
- The framework does not silently reorder scientific limits
- Numerical agreement does not establish symbolic equality
- Automatic canonical promotion is forbidden

## End-to-End Case Boundary

- An end-to-end scientific reference case exists (private, not included)
- Public examples are synthetic and redistributable
- Private sigma_xxx and sigma_abc research content is excluded

## Limitations

1. **ENGINE_003 VERIFICATION STATUS**: The multi-backend CAS adapter layer has been verified as MINIMUM_MULTI_BACKEND_CAS_ADAPTER_LAYER_VERIFIED_WITH_CAVEAT. See below for documented caveats.

2. **Mathematica Availability**: Mathematica path is optional; release success does not require Mathematica availability outside the verified local environment.

3. **Symbolic vs Numerical Claims**: Exact symbolic claims remain separate from numerical claims; numerical agreement does not establish symbolic equality.

4. **Capability Safety**: Unsupported capability fails safely; the capability resolver returns bounded failure for unrecognized operations.

5. **Cross-Engine Verification Boundary**: A contract form with repeated up index in cross-engine verification is documented as a usage boundary; it produced valid results in the run but is treated as a form error.

6. **Alternate E2 Naming Caveat**: An alternate naming convention for E2 (end-to-end) fixtures exists as a separately documented view. This does not affect functional correctness but should be noted when comparing fixture naming across environments.

## Quick Start: Work with the Framework through an Agent

Clone the repository:

```bash
git clone https://github.com/DarrenWongKaWa/repo-native-symbolic-science.git
cd repo-native-symbolic-science
```

Open the repository in an agent-enabled coding environment such as Codex or Claude Code. Then describe your scientific task in natural language.

Users do not need to manually select schemas.
Users do not need to manually select validators.
Users do not need to manually select computation backends.
Users do not need to run fixture suites before starting a project.

When computation is needed, the agent probes available capabilities and requests authorization before installing dependencies or changing the environment.

A useful first request is:

> Use the Repo-Native Symbolic Science workflow for this project. Read `AGENTS.md` and `REPO_POLICY.md` first. Ingest the raw expression as immutable input, audit its scientific semantics, and tell me what definitions or assumptions are missing. Do not guess undefined symbols, index roles, boundary conditions, or allowed transformations.

The agent should route the request through the appropriate repo-native skills:

```text
scientific request
→ scientific repo entry
→ immutable raw-expression ingestion
→ semantic completeness audit
→ human information request, when needed
→ task planning
→ bounded computation
→ independent verification
→ provenance-backed reporting
```

### What the Scientist Should Provide

For the most reliable result, provide as many of the following as are currently known:

```text
1. Raw expression or source file
2. Scientific definitions
3. Free, dummy, band, spatial, or external index roles
4. Assumptions and symmetry conditions
5. Desired target form
6. Allowed transformations
7. Forbidden transformations
8. Regression or comparison targets
9. Required order of limits or expansions
10. Publication or reporting goal
```

Missing information does not need to be invented. The framework is designed to stop safely and generate a structured request for the human scientist.

## Example: Start a New Symbolic Project

> My raw expression is stored in `input/raw_expression.txt`. Treat the original bytes as immutable. The indices \(a,b,c\) are external tensor indices and \(m,n,l\) are internal band indices. My target is an exact finite-parameter closed form. First inventory the symbols, indices, denominators, special functions, and assumptions. Do not perform integration by parts, discard boundary terms, reorder limits, or expand protected parameters without explicit authorization.

Expected routing:

```text
scientific_symbolic_repo_entry
→ generic_raw_expression_ingestion
→ semantic audit
→ plan materialization
```

## Example: Missing Scientific Definitions

> Audit whether all symbols in the raw expression have authoritative definitions. If definitions such as \(h_1\), \(h_2\), or \(h_3\) are missing, do not infer them from notation. Materialize a human information request specifying exactly what definitions, signs, prefactors, index orientations, and source evidence are required.

Expected routing:

```text
human_scientist_semantic_escalation
```

The output should distinguish:

```text
not found in the declared search universe
external source not supplied
definition rejected
definition contradicted
definition accepted by a human gate
```

“Not found” must never be converted into “does not exist.”

## Example: Normalize and Decompose an Expression

> Use the normalization and decomposition workflow. Preserve free and dummy index roles, noncommutative multiplication order, coefficients, and source provenance. Every child sector must reconstruct the exact parent expression. Term-count agreement alone is not sufficient.

Expected routing:

```text
generic_expression_normalization_and_decomposition
```

## Example: Request a Candidate Transformation

> Search for a more compact candidate representation using only exact algebra and the scientific identities already authorized in the project adapter. Do not use integration by parts, boundary assumptions, or integrated cancellation. Record every transformation and its claim scope.

Expected routing:

```text
candidate_symbolic_transformation
```

## Example: Select a Computation Backend

> Determine which computation capabilities this task requires. Prefer an open-source exact backend when sufficient. Use Mathematica only as an optional backend when its additional capabilities are needed. Do not replace an exact symbolic requirement with numerical sampling.

Expected routing:

```text
computational_backend_selection
→ bounded_computation_backend_execution
```

The backend resolver may select:

```text
SymPy
    exact symbolic baseline

NumPy / SciPy / mpmath
    numerical and high-precision support

Mathematica
    optional commercial exact backend
```

Backend selection is a technical routing decision. It does not authorize new scientific assumptions.

## Example: Request Independent Verification

> Independently verify the candidate result from frozen inputs. Reconstruct the parent expression, compute exact differences where possible, and use high-precision numerical sampling only as supporting evidence. Keep exact equality, structural replay, and numerical regression as separate claim types.

Expected routing:

```text
exact_and_bounded_symbolic_verification
→ cross_engine_symbolic_and_numeric_verification
```

Possible result types include:

```text
EXACT_SYMBOLIC_RESULT
EXACT_RECONSTRUCTION_PASS
STRUCTURAL_REPLAY_PASS
NUMERICAL_REGRESSION_PASS
HIGH_PRECISION_SUPPORT_PASS
COUNTEREXAMPLE_FOUND
INCONCLUSIVE
TIMEOUT
UNSUPPORTED_CAPABILITY
ENGINE_UNAVAILABLE
POLICY_VIOLATION
```

A numerical regression pass does not establish symbolic equality.

## Example: Authorize a Scientific Gate

A human scientist may explicitly authorize a new scientific level:

> I authorize use of the following definition-level identities under the stated complete-basis, nondegenerate, smooth-frame assumptions. This authorization does not include integration by parts, integrated cancellation, closure, or canonical promotion.

The agent should materialize this as a repo-native human decision before dependent execution continues.

A chat statement alone must not silently modify canonical project state.

## Example: Generate a Traceable Report

> Generate a human-readable LaTeX report from verified artifacts. Every important equation and claim must map to its source task, artifact, SHA, verifier verdict, assumptions, human decision, caveats, and canonical status.

Expected routing:

```text
verified_provenance_to_latex_pdf
```

The reporting workflow should preserve distinctions such as:

```text
candidate
verified candidate
integrated result
canonical result
historical result
rejected result
```

## Skill Map

| Scientific intention | Primary skill |
|---|---|
| Start or route a project | `scientific_symbolic_repo_entry` |
| Freeze and inventory a raw expression | `generic_raw_expression_ingestion` |
| Request missing definitions from a scientist | `human_scientist_semantic_escalation` |
| Normalize and decompose | `generic_expression_normalization_and_decomposition` |
| Search for a compact candidate | `candidate_symbolic_transformation` |
| Verify exact or bounded claims | `exact_and_bounded_symbolic_verification` |
| Manage provenance and canonical status | `provenance_claim_and_canonical_state` |
| Produce a traceable report | `verified_provenance_to_latex_pdf` |
| Select SymPy, numerical tools, or Mathematica | `computational_backend_selection` |
| Run an authorized backend | `bounded_computation_backend_execution` |
| Compare exact and numerical evidence | `cross_engine_symbolic_and_numeric_verification` |

## Developer and Local Validation

The following commands are for contributors, CI, or users who want to verify the installation manually. They are not required simply to start a scientific task through an agent.

```bash
python3 -m pip install sympy numpy scipy mpmath jsonschema

python3 tests/engine_fixtures/run_fixture_suite.py
python3 scripts/run_reuse_fixture_suite.py
```

Mathematica is optional and is not required for the open-source core workflow.

## Documentation

| Document | Purpose |
|----------|---------|
| [Getting Started with an Agent](docs/GETTING_STARTED_WITH_AN_AGENT.md) | First-time user guide for agent-based interaction |
| [Skill Cookbook](docs/SKILL_COOKBOOK.md) | Complete reference of all 11 public skills |
| [End-to-End Workflow](docs/END_TO_END_WORKFLOW.md) | Synthetic walkthrough from raw input to report |
| [Human Scientist Guide](docs/HUMAN_SCIENTIST_GUIDE.md) | Scientist responsibilities and best practices |
| [Claim Types and Gates](docs/CLAIM_TYPES_AND_GATES.md) | Relation types, verification gates, and forbidden promotions |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and resolutions |
| [Architecture](docs/architecture.md) | Repository architecture and data flow |
| [CAS Backends](docs/cas_backends.md) | Multi-backend adapter details |
| [Human-Agent Workflow](docs/human_agent_workflow.md) | Responsibility split and escalation protocol |
| [Limitations](docs/limitations.md) | Known limitations and caveats |
| [Object and Task Lifecycle](docs/object_and_task_lifecycle.md) | Task and object state machine |
| [Reporting Contract](docs/reporting_contract.md) | Required artifact formats and claim boundaries |
| [Semantic Escalation](docs/semantic_escalation.md) | When and how the agent requests human input |

## Project Structure

```
├── README.md
├── LICENSE
├── pyproject.toml
├── engines/           # Multi-backend CAS adapter layer
├── schemas/           # JSON schemas for artifacts
├── scripts/           # Orchestration and validation scripts
├── skills/            # Agent skills for symbolic workflows
├── task_templates/    # Task definition templates
├── policies/          # Governance policies
├── tests/             # Public fixture suites
├── examples/          # Synthetic end-to-end examples
├── fixtures/          # Synthetic reporting fixtures
└── docs/              # Architectural and workflow documentation
```

## Acknowledgements

The framework was developed and stress-tested during nonlinear-transport research undertaken in collaboration with Zhichao Guo.

## License

Apache-2.0 — see [LICENSE](./LICENSE)

Copyright 2026 Kawa Wong. All rights reserved.
