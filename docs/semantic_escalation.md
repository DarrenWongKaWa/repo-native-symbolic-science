# Semantic Escalation

## Overview

Semantic escalation is the process by which an agent requests human guidance when encountering ambiguity beyond its authorized scope.

## Escalation Triggers

- Missing semantic definitions
- Ambiguous operation scope
- Insufficient authorization for a transformation
- Conflict between task specification and observed state

## Escalation Protocol

1. Agent formulates a structured information request
2. Human scientist provides explicit clarification
3. Agent records the decision as a provenance artifact
4. Workflow resumes with updated scope

## Non-Escalatable Operations

Some operations require explicit pre-authorization and cannot be escalated at runtime:
- IBP (Integration By Parts)
- Canonical promotion
- Publishing of private scientific content
