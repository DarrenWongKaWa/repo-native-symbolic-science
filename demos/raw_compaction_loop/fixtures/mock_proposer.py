#!/usr/bin/env python3
"""Offline fixture only: simulates an untrusted proposer response.

It intentionally supplies one invalid plan before one valid plan.  It is not an
LLM and is never described as one; use --proposer-cmd with a model backend for
a real proposal run.
"""

import json
import sys


json.load(sys.stdin)  # The fixture consumes, but does not inspect, the raw envelope.
json.dump([
    {
        "candidate_id": "bad-prefix",
        "groups": [
            {"term_indices": [0, 1], "kernel_factor_index": 2,
             "common_prefix_factor_count": 0},
            {"term_indices": [2, 3], "kernel_factor_index": 3,
             "common_prefix_factor_count": 2},
        ],
        "note": "deliberately invalid: the two leading factors are not identical",
    },
    {
        "candidate_id": "shared-piecewise-kernels",
        "groups": [
            {"term_indices": [0, 1], "kernel_factor_index": 2,
             "common_prefix_factor_count": 0},
            {"term_indices": [2, 3], "kernel_factor_index": 3,
             "common_prefix_factor_count": 1},
        ],
        "note": "group byte-identical Piecewise kernel bodies",
    },
], sys.stdout)
