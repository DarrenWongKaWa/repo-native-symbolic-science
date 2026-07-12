# Repo-Native Symbolic Science

A repo-native framework for auditable human-agent symbolic science, with semantic escalation, independent verification, provenance governance, and traceable scientific reporting.

This repository provides both:

- a **repo-native symbolic-science workflow framework** for agent-assisted scientific derivation and verification
- an **executable, fail-closed ORCH controller runtime** with a registered SUPP derivation-validation layer

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

- A public finite-Gamma `sigma_xxx` replay benchmark is included at `benchmarks/sigma_xxx_finite_gamma_replay/`
- Public examples are synthetic and redistributable
- Private source snapshots, unrelated historical reports, and private sigma_abc research content are excluded

## Public Sigma_xxx Replay Benchmark

The finite-Gamma `sigma_xxx` benchmark is a `HUMAN_SPECIFIED_PREVIOUSLY_VERIFIED_NONINTERACTIVE_REPLAY_BENCHMARK`. It demonstrates framework ingestion of structured scientific semantics, derivation-DAG replay, sector reconstruction checks, symbolic-oracle comparison, numerical and Gamma-scaling regressions, scoped closure evaluation, and provenance-backed reporting.

It does not demonstrate autonomous mathematical discovery, independent verification, a general tensorial `sigma_abc` solution, or canonical scientific promotion.

Run the benchmark-local public validation:

```bash
python3 benchmarks/sigma_xxx_finite_gamma_replay/tests/validate_public_benchmark.py benchmarks/sigma_xxx_finite_gamma_replay
```

The scientific boundary is: DC limit first; Gamma finite and exact in the raw one-dimensional `sigma_xxx` object; then normalization, decomposition, simplification, closed-form construction, and model-specific validation. The raw object must not be described as resulting from a prior Gamma-order expansion.

Secondary conversation-derived decision provenance and the benchmark-local scoped pair-sector IBP authority record are documented under `benchmarks/sigma_xxx_finite_gamma_replay/docs/`.

## Limitations

1. **ENGINE_003 VERIFICATION STATUS**: The multi-backend CAS adapter layer has been verified as MINIMUM_MULTI_BACKEND_CAS_ADAPTER_LAYER_VERIFIED_WITH_CAVEAT. See below for documented caveats.

2. **Mathematica Availability**: Mathematica path is optional; release success does not require Mathematica availability outside the verified local environment.

3. **Symbolic vs Numerical Claims**: Exact symbolic claims remain separate from numerical claims; numerical agreement does not establish symbolic equality.

4. **Capability Safety**: Unsupported capability fails safely; the capability resolver returns bounded failure for unrecognized operations.

5. **Cross-Engine Verification Boundary**: A contract form with repeated up index in cross-engine verification is documented as a usage boundary; it produced valid results in the run but is treated as a form error.

6. **Alternate E2 Naming Caveat**: An alternate naming convention for E2 (end-to-end) fixtures exists as a separately documented view. This does not affect functional correctness but should be noted when comparing fixture naming across environments.

7. **Runtime Bounded by Declared Adapters**: The executable controller works through declared adapters and contracts. Unsupported roles or validators fail closed. Synthetic adapters are demonstrations, not claims of universal scientific automation. Human authorization remains required at scientific gates. The framework does not guarantee that every scientific task can be solved.

---

## Two Supported User Pathways

### Agent-First Pathway

Works through an agent-enabled coding environment. No CLI knowledge required.

Clone the repository:

```bash
git clone https://github.com/DarrenWongKaWa/repo-native-symbolic-science.git
cd repo-native-symbolic-science
```

Open the repository in an agent-enabled coding environment such as Codex or Claude Code. Ask the agent to read `AGENTS.md` and `REPO_POLICY.md` first. Then describe your scientific task in natural language. The agent routes through repo-native skills and controller contracts.

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

### Executable Controller Pathway

Run the orchestration controller directly from the command line. Four subcommands are available:

```bash
python3 scripts/orch_controller.py list-roles
python3 scripts/orch_controller.py validate-task <contract_path>
python3 scripts/orch_controller.py check-transition --from <state> --to <state>
python3 scripts/orch_controller.py run-workflow <fixture_path>
```

Add `--verbose` to any command for detailed output.

**Full CLI surface:**

```
usage: orch_controller.py [-h] [--verbose]
  {validate-task,check-transition,list-roles,run-workflow} ...

positional arguments:
  validate-task       Validate a task contract JSON file
  check-transition    Check if a state transition is valid
  list-roles          List all registered roles
  run-workflow        Run a workflow fixture
```

**Subcommand summary:**

| Command | Purpose | Exit 0 |
|---------|---------|--------|
| `list-roles` | List all registered roles | Always |
| `validate-task <path>` | Validate a task contract JSON | Contract passes |
| `check-transition --from X --to Y` | Check state transition validity | Transition allowed |
| `run-workflow <path>` | Run a workflow fixture | Workflow passes |

**Minimal example using public synthetic fixtures:**

```bash
# List registered roles (12 roles: executor, global_planner, verifier, etc.)
python3 scripts/orch_controller.py list-roles
# {"roles": ["executor", "global_planner", ...]}

# Run the synthetic demo workflow (3 stages: plan, execute, verify)
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
# {"passed": true, "blocking_findings": [], "errors": []}

# Check a valid state transition
python3 scripts/orch_controller.py check-transition --from EXECUTING --to EXECUTION_COMPLETE
# {"allowed": true, "reason": "...", "from": "EXECUTING", "to": "EXECUTION_COMPLETE"}

# Invalid transitions fail closed
python3 scripts/orch_controller.py check-transition --from RECEIVED --to EXECUTING
# {"allowed": false, "reason": "Transition from 'RECEIVED' to 'EXECUTING' is not allowed...", ...}
# exit code: 1
```

---

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

"Not found" must never be converted into "does not exist."

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

---

## Skill Map

The repository contains 18 public skills. Refer to the skill directories under `skills/` and the [Skill Cookbook](docs/SKILL_COOKBOOK.md) for the current inventory.

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
| Orchestrate multi-agent workflows | `multi_agent_scientific_workflow_orchestration` |
| Map equations to claim-level evidence | `equation_level_claim_and_evidence_mapping` |
| Present and manage long expressions | `long_expression_presentation_and_omission` |
| Map physical interpretation and limiting cases | `physical_interpretation_and_limiting_cases` |
| Build and audit supplementary material | `supplementary_material_build_and_audit` |
| Write theoretical physics derivation narratives | `theoretical_physics_derivation_narrative` |
| Build verified derivation graphs from artifacts | `verified_artifact_to_derivation_graph` |

---

## ORCH Controller: Collaboration Model

The controller coordinates multiple logical roles through isolated contexts. One human-facing controller does **not** mean one model context silently performs every role.

Planner, executor, and verifier roles remain logically isolated and communicate through:

```text
task contracts
artifact paths
complete SHA-256 values
manifests
structured validation results
workflow states
human gates
```

**Verified runtime architecture:**

```text
human-facing request
→ executable ORCH controller
→ role/adapter registry
→ planner / executor / verifier isolation
→ actual SUPP validator plugin
→ structured validation result
→ fail-closed controller decision
→ provenance-backed reporting
```

The default verdict is FAIL. A PASS requires positive evidence: at least one check executed, all checks passed, and no blocking findings. Invalid required inputs fail closed.

---

## ORCH-to-SUPP Integration

The verified integration path from the ORCH controller to the SUPP validator plugin:

```text
ORCH controller
→ registry.json
→ SUPP validator plugin
→ derivation-step JSON Schema validation
→ derivative-semantics validation
→ cross-record provenance checks
→ structured controller verdict
```

Invalid required inputs fail closed. Examples of blocked conditions:

```text
unknown or missing relation_type
malformed or empty required JSONL
undeclared additional properties
zero semantic checks
missing validators
validator exceptions
```

The combined integration registry is at `loop_engine/orch_adapters/registry.json`. It contains accepted ORCH runtime registrations plus SUPP plugin registrations. This combined registry is functional and verified for the release; it is not byte-identical to earlier ORCH_005 artifact versions.

---

## SUPP Capability Summary

Public SUPP (supplementary material) functions at a capability level:

```text
typed derivation graph
explicit mathematical reconstruction
derivative-semantic provenance
long-expression presentation modes
omission ledger
equation-level evidence mapping
algebra / physics / software / authority review
reporting_handoff_package
```

Authority boundary: `verified_provenance_to_latex_pdf` remains the sole final TeX/PDF rendering authority. SUPP does not automatically establish physical interpretation, canonical equivalence, or integrated cancellation.

---

## Developer and Local Validation

### Starting a project (minimal commands)

```bash
python3 -m pip install sympy numpy scipy mpmath jsonschema
```

### Validating the framework (contributor/CI commands)

```bash
# Install test dependencies
python3 -m pip install pytest sympy numpy scipy mpmath jsonschema

# Run the full regression suite (91 tests)
python3 -m pytest tests/

# Run specific test files
python3 -m pytest tests/test_orch002_synthetic_fixtures.py
python3 -m pytest tests/test_orch004_controller_runtime.py
python3 -m pytest tests/test_supp002r2_validator.py

# Verify controller CLI is functional
python3 scripts/orch_controller.py --help
python3 scripts/orch_controller.py list-roles
python3 scripts/orch_controller.py run-workflow fixtures/synthetic_workflow_demo.json
```

Mathematica is optional and is not required for the open-source core workflow.

---

## Verified Release Status

```text
verified release commit:
08a5ba15c645954badad1f94decd9286252cd868

independent remote verdict:
CLASS A

verified candidate paths:
110

remote regression:
91/91 PASS
```

No GitHub Release or version tag was created. Private scientific sigma research is excluded. Scientific canonical state is not part of this public release. Blocker 5 belongs to private scientific governance and was not changed.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [Getting Started with an Agent](docs/GETTING_STARTED_WITH_AN_AGENT.md) | First-time user guide for agent-based interaction |
| [Agent-First Controller Usage](docs/agent_first_controller_usage.md) | Complete executable controller guide |
| [Skill Cookbook](docs/SKILL_COOKBOOK.md) | Reference of all public skills |
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
| [Sigma XXX Repair Lineage Case Study](docs/case_studies/sigma_xxx_repair_lineage.md) | Public case study of a real repair lineage |

## Benchmarks

The `benchmarks/` directory contains public, repository-native benchmarks. The flagship benchmark exercises an end-to-end sigma_xxx repair lineage:

```bash
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile fast
```

See [benchmarks/README.md](benchmarks/README.md) for details.

## Project Structure

```
├── README.md
├── LICENSE
├── AGENTS.md
├── REPO_POLICY.md
├── pyproject.toml
├── engines/                # Multi-backend CAS adapter layer
├── loop_engine/            # Executable controller runtime
│   ├── orch_dispatcher.py  #   Dispatcher with role routing and validation
│   ├── orch_registry.py    #   Role and adapter registry
│   └── orch_adapters/      #   Adapter/plugin registry
├── scripts/                # Orchestration, validation, and controller CLI
│   └── orch_controller.py  #   Controller CLI entry point
├── schemas/                # JSON schemas (ORCH and SUPP artifacts)
├── validators/             # Validator implementations
│   └── supplement_validator.py  #   SUPP derivation-validation plugin
├── skills/                 # Symbolic, orchestration, and supplement skills
├── templates/              # Task and artifact templates
├── policies/               # Governance policies
├── tests/                  # Public fixture suites (91 tests)
├── fixtures/               # Public synthetic ORCH/SUPP fixtures
├── examples/               # Synthetic end-to-end examples
└── docs/                   # Architectural and workflow documentation
```

## Acknowledgements

The framework was developed and stress-tested during nonlinear-transport research undertaken in collaboration with Zhichao Guo.

## License

Apache-2.0 — see [LICENSE](./LICENSE)

Copyright 2026 Kawa Wong. All rights reserved.
