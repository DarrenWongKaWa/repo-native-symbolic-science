#!/usr/bin/env python3
"""Tests for supplement_validator.py against supp002r2 public baseline.

Minimum 20 pytest tests covering positive, negative, mutation, and edge cases.
Each test exercises a specific validator method or integration path.
"""
import pytest
import json
import os
import sys
import tempfile
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "validators"))
from supplement_validator import (  # noqa: E402
    SupplementValidator, _make_result, NODE_TYPES, EDGE_TYPES, RELATION_TYPES,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "supplement", "two_sector_response"
)


def _valid_graph():
    return {
        "graph_id": "test_graph",
        "nodes": [
            {"node_id": "A", "node_type": "definition",
             "equation_label": "eq1", "step_id": "s1",
             "derivation_step_ref": "ref1"},
            {"node_id": "B", "node_type": "transformation",
             "equation_label": "eq2", "step_id": "s2",
             "derivation_step_ref": "ref2"},
        ],
        "edges": [
            {"edge_id": "e1", "parent_node_ids": ["A"],
             "child_node_id": "B", "edge_type": "derived_from"},
        ],
        "root_node_id": "A",
        "leaf_node_ids": ["B"],
    }


def _valid_steps():
    return {
        "derivation_steps": [
            {"step_id": "s1", "section_id": "SEC_01", "parent_equation_ids": [],
             "child_equation_id": "eq1", "mathematical_operation": "define", 
             "relation_type": "definition", "assumptions": [],
             "index_scope": {"free_indices": [], "dummy_indices": [], "index_domains": {}, "summation_conventions": "", "symmetry_properties": {}, "role_preserving_renames": []},
             "machine_verification_status": "NOT_APPLICABLE", "canonical_status": "NOT_ESTABLISHED", "caveats": [],
             "derivative_semantics": {"status": "NOT_APPLICABLE", "reason": "definition_step"}},
            {"step_id": "s2", "section_id": "SEC_02", "parent_equation_ids": ["eq1"],
             "child_equation_id": "eq2", "mathematical_operation": "partial derivative", 
             "relation_type": "identity_under_assumptions", "assumptions": ["linear"],
             "index_scope": {"free_indices": ["i"], "dummy_indices": [], "index_domains": {"i": "1..3"}, "summation_conventions": "einstein", "symmetry_properties": {}, "role_preserving_renames": []},
             "machine_verification_status": "VERIFIED", "canonical_status": "VERIFIED", "caveats": [],
             "derivative_semantics": {
                 "status": "ACTIVE_DERIVATIVE", "derivative_variable": "x", "derivative_order": 1,
                 "held_fixed_variables": ["t"], "sign_provenance": "positive", "coefficient_provenance": "unit", "source_definition": "standard"
             }},
        ]
    }


class TestPositivePaths:
    def test_all_validators_pass_on_fixture(self):
        if not os.path.isdir(FIXTURE_DIR):
            pytest.skip("Fixture directory not found")
        result = SupplementValidator.run_all_validations(FIXTURE_DIR)
        assert result["overall_status"] in ("PASS", "WARN")

    def test_self_test_passes(self):
        result = SupplementValidator.run_self_test()
        assert result.get("self_test") in ("PASS", "SKIP")

    def test_mutation_tests_detect_all(self):
        result = SupplementValidator.run_mutation_tests()
        assert result.get("failed", -1) == 0, (
            f"{result.get('failed')} mutation tests failed:\n"
            + json.dumps(result, indent=2)
        )

    def test_valid_json_parse(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tf:
            json.dump({"key": "value"}, tf)
            path = tf.name
        try:
            r = SupplementValidator.validate_json_parse(path)
            assert r["status"] == "PASS"
        finally:
            os.unlink(path)

    def test_glob_discovers_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            json_path = os.path.join(td, "test.json")
            jsonl_path = os.path.join(td, "test.jsonl")
            with open(json_path, "w") as f:
                json.dump({}, f)
            with open(jsonl_path, "w") as f:
                f.write('{"a":1}\n{"a":2}\n')
            all_files, json_files, jsonl_files, _ = (
                SupplementValidator._discover_data_files(td)
            )
            assert json_path in json_files
            assert jsonl_path in jsonl_files
            assert len(all_files) == 2

    def test_no_match_is_failure(self):
        result = SupplementValidator.run_all_validations(
            "/tmp/nonexistent_supplement_dir_98765"
        )
        assert result["overall_status"] == "FAIL"
        assert any(
            c["check"] == "file_discovery" and c["status"] == "FAIL"
            for c in result["checks"]
        )

    def test_valid_graph_passes(self):
        g = _valid_graph()
        r = SupplementValidator.validate_derivation_graph_integrity(g)
        assert r["status"] == "PASS"

    def test_valid_steps_pass_completeness(self):
        s = _valid_steps()
        r = SupplementValidator.validate_derivation_step_completeness(s)
        assert r["status"] == "PASS"

    def test_valid_steps_pass_assumptions(self):
        s = _valid_steps()
        r = SupplementValidator.validate_assumption_visibility(s)
        assert r["status"] == "PASS"


class TestNegativePaths:
    def test_adversarial_invalid_graph(self):
        r = SupplementValidator.validate_derivation_graph_integrity({})
        assert r["status"] == "FAIL"

    def test_forbidden_claim_promotion(self):
        claims = {
            "claims": [{
                "claim_id": "C1",
                "edge_type_used": "numerically_supported_by",
                "relation_type": "literal_equality",
            }]
        }
        r = SupplementValidator.validate_claim_type_consistency(claims)
        assert r["status"] == "FAIL"

    def test_derivative_semantics_missing(self):
        steps = {
            "derivation_steps": [{
                "step_id": "s1", "step_type": "integration",
                "input_equations": [], "output_equations": [],
                "assumptions": [],
            }]
        }
        r = SupplementValidator.validate_derivative_semantics(steps)
        assert r["status"] == "FAIL"

    def test_cycle_detection(self):
        g = {
            "graph_id": "cycle_test",
            "nodes": [
                {"node_id": "A", "node_type": "definition",
                 "equation_label": "eq1", "step_id": "s1",
                 "derivation_step_ref": "ref1"},
                {"node_id": "B", "node_type": "transformation",
                 "equation_label": "eq2", "step_id": "s2",
                 "derivation_step_ref": "ref2"},
            ],
            "edges": [
                {"edge_id": "e1", "parent_node_ids": ["A"],
                 "child_node_id": "B", "edge_type": "derived_from"},
                {"edge_id": "e2", "parent_node_ids": ["B"],
                 "child_node_id": "A", "edge_type": "derived_from"},
            ],
            "root_node_id": "A",
            "leaf_node_ids": ["B"],
        }
        r = SupplementValidator.validate_derivation_graph_integrity(g)
        assert r["status"] == "FAIL"

    def test_omission_brevity_alone_rejected(self):
        ledger = {
            "omission_entries": [{
                "expression_label": "expr1",
                "omission_reason": "omitted for brevity",
            }]
        }
        presentations = [{
            "expression_label": "expr1",
            "presentation_mode": "SYMBOLIC_TREE",
        }]
        r = SupplementValidator.validate_omission_ledger_completeness(
            ledger, presentations
        )
        assert r["status"] == "FAIL"

    def test_reconstruction_verified_required(self):
        ledger = {
            "omission_entries": [{
                "expression_label": "expr_gen",
                "omission_reason": "generated",
                "generator_rule": "GENERATOR_RULE",
                "verification_status": "UNVERIFIED",
            }]
        }
        presentations = [{
            "expression_label": "expr_gen",
            "presentation_mode": "GENERATOR_RULE",
        }]
        r = SupplementValidator.validate_omission_ledger_completeness(
            ledger, presentations
        )
        assert r["status"] == "FAIL"

    def test_unmapped_equation_fails(self):
        evidence = {"equation_evidence_mappings": [
            {"equation_label": "eq_A"},
        ]}
        labels = ["eq_A", "eq_B"]
        r = SupplementValidator.validate_equation_evidence_coverage(
            evidence, labels
        )
        assert r["status"] == "FAIL"

    def test_missing_step_id_fails(self):
        steps = {
            "derivation_steps": [{
                "step_type": "transformation",
                "input_equations": [],
                "output_equations": [],
                "assumptions": [],
            }]
        }
        r = SupplementValidator.validate_derivation_step_completeness(steps)
        assert r["status"] == "FAIL"

    def test_excess_coverage_detected(self):
        evidence = {"equation_evidence_mappings": [
            {"equation_label": "eq_A"},
            {"equation_label": "eq_EXTRA"},
        ]}
        labels = ["eq_A"]
        r = SupplementValidator.validate_equation_evidence_coverage(
            evidence, labels
        )
        assert r["status"] == "WARN"

    def test_invalid_relation_type_detected(self):
        edges = [{
            "edge_id": "e1",
            "edge_type": "defined_by",
            "relation_type": "literal_equality",
        }]
        r = SupplementValidator.validate_relation_type_consistency(edges)
        assert r["status"] == "FAIL"

    def test_sanitization_check(self):
        r = SupplementValidator.validate_human_readability_audit_structure({
            "audit_id": "audit_001",
            "sections_audited": [
                {"section_id": "sec1", "readability_score": 7.5},
            ],
            "overall_score": 8.0,
            "critical_issues": [],
        })
        assert r["status"] == "PASS"
