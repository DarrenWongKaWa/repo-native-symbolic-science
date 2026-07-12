#!/usr/bin/env python3
"""Pytest wrapper for the public sigma_xxx benchmark validator."""

from pathlib import Path

from validate_public_benchmark import validate


def test_sigma_xxx_public_benchmark_contract():
    root = Path(__file__).resolve().parents[1]
    result = validate(root)
    assert result["passed"] is True
