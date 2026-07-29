#!/usr/bin/env python3
"""Stub second engine that always reports a rigorous NONZERO — used to test that the judge
FAILS CLOSED when an independent engine contradicts its certificate."""
import json, sys
sys.stdin.read()
print(json.dumps({"engine": "stub", "verdict": "NONZERO", "detail": "stub contradiction"}))
