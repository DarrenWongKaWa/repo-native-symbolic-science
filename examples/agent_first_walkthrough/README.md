# Agent-First Walkthrough

This redistributable synthetic example demonstrates a complete Repo-Native Symbolic Science workflow from raw expression to traceable report, using only public, synthetic content.

It demonstrates:
- One missing-definition blocker
- One exact symbolic transformation
- One numerical-support result
- One invalid claim promotion rejection
- One human authorization gate

## Project Overview

The walkthrough processes a synthetic expression:

```
G(x, y, z, n) = (x + 1)^n * exp(-x) + gamma(n+1, x) + sin(pi*z) * H_n(y)
```

Where:
- `x, y, z` are real scalar variables
- `n` is a positive integer parameter
- `H_n(y)` is the Hermite polynomial of degree n
- `gamma(n+1, x)` is the upper incomplete gamma function
- `pi` is the mathematical constant

## Directory Structure

```
agent_first_walkthrough/
├── README.md
├── input/
│   ├── raw_expression.md
│   └── scientific_context.md
└── expected/
    ├── human_information_request.md
    ├── plan.md
    ├── decomposition.md
    ├── backend_selection.md
    ├── execution_truth.md
    ├── verification.md
    └── report_mapping.md
```

## How to Use

Open this repository in an agent-enabled coding environment and say:

> I want to process the expression in `examples/agent_first_walkthrough/input/raw_expression.md`. Read the scientific context first, then follow the Repo-Native Symbolic Science workflow.

The agent will route through `scientific_symbolic_repo_entry` and walk through the complete workflow, encountering each demonstrated gate.
