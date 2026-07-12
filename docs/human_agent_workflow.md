# Human-Agent Workflow

## Responsibility Split

| Role | Responsibility |
|------|---------------|
| Human Scientist | Scientific semantics, assumptions, authorization |
| Agent | Planning, orchestration, claim governance |
| CAS/Numerical Engine | Bounded computation |
| Independent Verifier | Replay, comparison, adjudication |

The ORCH controller routes these responsibilities through isolated contexts:
- Planner context: converts targets into staged plans
- Executor context: computes outputs from frozen inputs
- Verifier context: independently checks results (cannot edit executor outputs)
- Reviewer context: audits review packets, returns structured verdicts
- Integration context: freezes checkpoints, opens next branches

One human-facing controller coordinates these roles without conflating contexts.

## Semantic Escalation

When an agent encounters ambiguity or needs scientific authorization:
1. The agent formulates a structured question
2. The human scientist provides explicit authorization or clarification
3. The agent records the decision in provenance artifacts
4. The workflow resumes with the authorized scope

## Claim Governance

All claims are typed:
- `exact_symbolic`: verified by symbolic algebra
- `bounded_numeric`: verified by numerical evaluation within bounds
- `pending`: awaiting verification
- `blocked`: blocked by explicit guard
