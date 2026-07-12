#!/usr/bin/env python3
"""Tests for sigma_xxx conversation provenance and scoped operation authority."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from validate_decision_provenance import validate, validate_authority_record


ROOT = Path(__file__).resolve().parents[1]


def _authority() -> dict:
    return json.loads((ROOT / "manifests" / "scoped_operation_authority.json").read_text(encoding="utf-8"))


def test_decision_provenance_contract_passes():
    result = validate(ROOT)
    assert result["passed"] is True


def test_pair_authorization_rejects_center_sector_application():
    record = copy.deepcopy(_authority())
    record["scope"]["parent_sector"] = "center_sector"
    with pytest.raises(AssertionError):
        validate_authority_record(record)


def test_pair_authorization_rejects_loop_sector_application():
    record = copy.deepcopy(_authority())
    record["scope"]["parent_sector"] = "loop_sector"
    with pytest.raises(AssertionError):
        validate_authority_record(record)


def test_pair_authorization_rejects_unauthorized_ibp_stage():
    record = copy.deepcopy(_authority())
    record["scope"]["permitted_stages"].append("center_sector_ibp")
    with pytest.raises(AssertionError):
        validate_authority_record(record)


def test_pair_authorization_requires_periodicity_evidence_precondition():
    record = copy.deepcopy(_authority())
    record["preconditions"].remove("periodic_boundary_convention_defined")
    with pytest.raises(AssertionError):
        validate_authority_record(record)


def test_numerical_only_evidence_cannot_verify_exact_ibp():
    record = copy.deepcopy(_authority())
    with pytest.raises(AssertionError):
        validate_authority_record(record, exact_evidence_basis="NUMERICAL_ONLY")
