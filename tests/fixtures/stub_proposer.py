#!/usr/bin/env python3
"""Deterministic stub proposer backend for Stage-2 tests (no LLM, no machine paths).
Reads the prompt on stdin (ignored), prints a fixed JSON array incl. one malicious
candidate that MUST be dropped by the proposer's strict validation."""
import sys
sys.stdin.read()
print('[{"lhs":"(x+y)**2","rhs":"x**2+2*x*y+y**2","note":"binomial"},'
      '{"lhs":"x*(y+1)","rhs":"x*y+x","note":"distributive"},'
      '{"lhs":"__import__(\\"os\\").system(\\"id\\")","rhs":"0","note":"attack"},'
      '{"lhs":"x+z","rhs":"x","note":"undeclared symbol z"}]')
