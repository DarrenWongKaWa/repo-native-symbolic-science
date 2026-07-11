# Synthetic End-to-End Example

This directory contains synthetic, redistributable examples demonstrating the end-to-end workflow of the framework.

## Overview

The synthetic end-to-end example walks through:
1. Ingestion of a synthetic expression
2. Normalization and decomposition
3. Candidate transformation
4. Cross-engine verification (SymPy + NumPy/SciPy)
5. Provenance recording
6. Report generation

## Running

```bash
# This is a synthetic example showing the workflow structure.
# Actual execution requires the full framework.

python3 scripts/engine_orchestrator.py --expression synthetic_example.json
```

## Note

The original end-to-end scientific reference case exists in the private source repository.
Public examples are synthetic and redistributable.
Private sigma_xxx and sigma_abc research content is excluded.
