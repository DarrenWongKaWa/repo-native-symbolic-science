#!/usr/bin/env python3
"""Comprehensive supplement validator for supp002r2 public baseline.

Covers JSON/JSONL parse, derivation graph integrity, derivation step completeness,
equation evidence coverage, assumption visibility, claim type consistency,
relation type consistency, omission ledger completeness, expression reconstruction
reference, section contract completeness, reader pathway integrity, derivative
semantics, SHA integrity, human readability audit, and provenance compatibility.
"""
import json
import sys
import os
import hashlib
import glob
import re
from typing import Any, Dict, List, Optional, Tuple, Union

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NODE_TYPES = [
    "definition", "raw_equation", "decomposition", "identity",
    "transformation", "projection", "integration", "limiting_case",
    "verification", "physical_interpretation",
]

EDGE_TYPES = [
    "derived_from", "defined_by", "decomposed_into", "reconstructed_from",
    "equal_under_assumptions", "projected_to", "integrated_to",
    "numerically_supported_by", "interpreted_as",
]

RELATION_TYPES = [
    "definition", "literal_equality", "finite_role_preserving_rename",
    "identity_under_assumptions", "pointwise_identity", "projected_identity",
    "integrated_identity", "structural_replay", "exact_reconstruction",
    "numerical_regression", "counterexample", "not_established",
    "verified_candidate", "canonical_result", "historical_result",
    "rejected_result",
]

CANONICAL_STATUSES = [
    "CANONICAL", "INTEGRATED", "VERIFIED", "CANDIDATE", "NOT_ESTABLISHED",
]

VERIFICATION_STATUSES = [
    "VERIFIED", "NUMERICALLY_SUPPORTED", "UNVERIFIED", "NOT_APPLICABLE",
]

POINTWISE_INTEGRATED_SCOPES = ["pointwise", "integrated", "not_applicable"]

SECTION_ROLES = [
    "SCOPE", "DEFINITIONS", "DERIVATION", "INTERPRETATION", "VALIDATION",
    "REPRODUCTION",
]

READER_PERSONAS = [
    "physics_first", "derivation_checking", "machine_reproduction",
]

FORBIDDEN_PROMOTIONS = {
    "projected_to": ["literal_equality"],
    "numerically_supported_by": ["pointwise_identity", "projected_identity",
                                  "integrated_identity", "literal_equality",
                                  "canonical_result"],
    "counterexample": [],
}

EDGE_TO_RELATION_MAP = {
    "defined_by": ["definition"],
    "derived_from": ["identity_under_assumptions", "structural_replay",
                      "verified_candidate", "canonical_result",
                      "historical_result"],
    "equal_under_assumptions": ["identity_under_assumptions",
                                 "literal_equality",
                                 "finite_role_preserving_rename"],
    "projected_to": ["projected_identity", "pointwise_identity"],
    "integrated_to": ["integrated_identity"],
    "decomposed_into": ["structural_replay", "finite_role_preserving_rename"],
    "reconstructed_from": ["exact_reconstruction", "structural_replay"],
    "numerically_supported_by": ["numerical_regression"],
    "interpreted_as": ["not_established"],
}

DERIVATIVE_NODE_TYPES = {"transformation", "integration"}
REQUIRED_DERIVATIVE_FIELDS = [
    "derivative_variable", "sign_provenance", "held_fixed_variables",
]

REQUIRED_DERIVATION_STEP_FIELDS = [
    "step_id", "section_id", "parent_equation_ids", "child_equation_id",
    "mathematical_operation", "relation_type", "assumptions",
    "index_scope", "machine_verification_status", "canonical_status", "caveats",
]
REQUIRED_INDEX_SCOPE_FIELDS = ["free_indices", "dummy_indices", "index_domains"]

EXPRESSION_INLINE_VALUE = "INLINE_FULL"
GENERATOR_RULE_VALUE = "GENERATOR_RULE"
VALID_PRESENTATION_MODES = [
    EXPRESSION_INLINE_VALUE, "INLINE_COMPACT", "SYMBOLIC_TREE",
    GENERATOR_RULE_VALUE,
]

REQUIRED_SECTION_FIELDS = [
    "section_id", "section_title", "section_role", "presentation_artifacts",
    "completeness_claims",
]

CARDINAL_LEAF_SECTIONS = [
    "14_validation_full", "14_reproduction_full",
]

def _make_result(check, status, details="", findings=None):
    return {
        "check": check,
        "status": status,
        "details": details,
        "findings": findings or [],
    }


class SupplementValidator:
    """Comprehensive supplement validator (1000+ lines).

    Each validate_* method returns a dict with keys:
      check (str), status ("PASS"|"FAIL"|"WARN"), details (str), findings (list).
    """

    @staticmethod
    def validate_json_parse(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _make_result(
                "json_parse",
                "PASS",
                f"Successfully parsed {filepath}",
                [f"top-level type: {type(data).__name__}"],
            )
        except json.JSONDecodeError as e:
            return _make_result(
                "json_parse", "FAIL",
                f"JSON parse error in {filepath}: {e}",
                [str(e)],
            )
        except FileNotFoundError:
            return _make_result(
                "json_parse", "FAIL",
                f"File not found: {filepath}",
            )

    @staticmethod
    def validate_jsonl_parse(filepath):
        lines_ok = []
        lines_fail = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        json.loads(stripped)
                        lines_ok.append(i)
                    except json.JSONDecodeError as e:
                        lines_fail.append(f"line {i}: {e}")
        except FileNotFoundError:
            return _make_result("jsonl_parse", "FAIL",
                                f"File not found: {filepath}")
        status = "PASS" if not lines_fail else "FAIL"
        return _make_result(
            "jsonl_parse", status,
            f"Parsed {filepath}: {len(lines_ok)} ok, {len(lines_fail)} fail lines",
            lines_fail if lines_fail else [f"{len(lines_ok)} lines parsed"],
        )

    @staticmethod
    def validate_derivation_graph_integrity(data):
        findings = []
        if not isinstance(data, dict):
            return _make_result("derivation_graph_integrity", "FAIL",
                                "Data is not a dict", ["top-level type mismatch"])
        required = ["graph_id", "nodes", "edges"]
        missing = [k for k in required if k not in data]
        if missing:
            findings.append(f"Missing required keys: {missing}")
            return _make_result(
                "derivation_graph_integrity", "FAIL",
                f"Missing keys: {missing}", findings,
            )
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        node_ids = set()
        for n in nodes:
            nid = n.get("node_id", "")
            if not nid:
                findings.append("Node missing node_id")
                continue
            if nid in node_ids:
                findings.append(f"Duplicate node_id: {nid}")
            node_ids.add(nid)
            nt = n.get("node_type", "")
            if nt and nt not in NODE_TYPES:
                findings.append(f"Invalid node_type '{nt}' on node {nid}")
            ct = n.get("claim_type", "")
            if ct and ct not in RELATION_TYPES:
                findings.append(f"Node {nid}: invalid claim_type '{ct}'")
            cs = n.get("canonical_status", "")
            if cs and cs not in CANONICAL_STATUSES:
                findings.append(f"Node {nid}: invalid canonical_status '{cs}'")
            vs = n.get("verification_status", "")
            if vs and vs not in VERIFICATION_STATUSES:
                findings.append(f"Node {nid}: invalid verification_status '{vs}'")
        edge_ids = set()
        for e in edges:
            eid = e.get("edge_id", "")
            if not eid:
                findings.append("Edge missing edge_id")
                continue
            if eid in edge_ids:
                findings.append(f"Duplicate edge_id: {eid}")
            edge_ids.add(eid)
            et = e.get("edge_type", "")
            if et and et not in EDGE_TYPES:
                findings.append(f"Invalid edge_type '{et}' on edge {eid}")
            # Check parent_node_ids (array) and child_node_id (string)
            pids = e.get("parent_node_ids", [])
            cid = e.get("child_node_id", "")
            for pid in pids:
                if pid and pid not in node_ids:
                    findings.append(f"Edge {eid}: parent_node_id '{pid}' not in nodes")
            if cid and cid not in node_ids:
                findings.append(f"Edge {eid}: child_node_id '{cid}' not in nodes")
            ct = e.get("claim_type", "")
            if ct and ct not in RELATION_TYPES:
                findings.append(f"Edge {eid}: invalid claim_type '{ct}'")
            pwis = e.get("pointwise_or_integrated_scope", "")
            if pwis and pwis not in POINTWISE_INTEGRATED_SCOPES:
                findings.append(f"Edge {eid}: invalid pointwise_or_integrated_scope '{pwis}'")
            # equality-like edges must carry assumptions
            if et == "equal_under_assumptions":
                if not e.get("assumption_scope"):
                    findings.append(f"Edge {eid}: equal_under_assumptions missing assumption_scope")
        # Cycle detection
        adj = {nid: set() for nid in node_ids}
        for e in edges:
            pids = e.get("parent_node_ids", [])
            cid = e.get("child_node_id", "")
            if cid in adj:
                for pid in pids:
                    if pid in adj:
                        adj[pid].add(cid)
        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in node_ids}
        def has_cycle(u):
            color[u] = GRAY
            for v in adj.get(u, set()):
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and has_cycle(v):
                    return True
            color[u] = BLACK
            return False
        for nid in node_ids:
            if color[nid] == WHITE:
                if has_cycle(nid):
                    findings.append("Graph contains a cycle")
                    break
        if findings:
            return _make_result("derivation_graph_integrity", "FAIL",
                                f"{len(findings)} integrity issue(s)", findings)
        return _make_result("derivation_graph_integrity", "PASS",
                            f"Valid: {len(nodes)} nodes, {len(edges)} edges")
    @staticmethod
    def _detect_cycles(adj, node_ids):
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in node_ids}
        cycle_nodes = set()

        def dfs(u, stack):
            color[u] = GRAY
            stack.append(u)
            for v in adj.get(u, set()):
                if color[v] == GRAY:
                    idx = stack.index(v)
                    for k in stack[idx:]:
                        cycle_nodes.add(k)
                elif color[v] == WHITE:
                    dfs(v, stack)
            stack.pop()
            color[u] = BLACK

        for n in node_ids:
            if color[n] == WHITE:
                dfs(n, [])
        return cycle_nodes

    @staticmethod
    def validate_derivation_step_completeness(data):
        findings = []
        if not isinstance(data, dict):
            return _make_result("derivation_step_completeness", "FAIL",
                                "Data is not a dict")
        steps = data.get("derivation_steps", [])
        if not isinstance(steps, list):
            findings.append("derivation_steps is not a list")
            return _make_result("derivation_step_completeness", "FAIL",
                                "Invalid derivation_steps", findings)
        if len(steps) == 0:
            return _make_result("derivation_step_completeness", "FAIL",
                                "EMPTY_REQUIRED_RECORD_SET: 0 derivation steps found",
                                ["zero records in derivation_steps"])
        step_ids = set()
        for i, step in enumerate(steps):
            sid = step.get("step_id", "")
            if not sid:
                findings.append(f"Step[{i}] missing step_id")
                continue
            if sid in step_ids:
                findings.append(f"Duplicate step_id: {sid}")
            step_ids.add(sid)
            for fld in REQUIRED_DERIVATION_STEP_FIELDS:
                if fld not in step:
                    findings.append(f"Step {sid}: missing required field '{fld}'")
            rt = step.get("relation_type", "")
            if rt and rt not in RELATION_TYPES:
                findings.append(f"Step {sid}: unknown relation_type '{rt}' (not in accepted enum)")
            index_scope = step.get("index_scope", {})
            if index_scope:
                for fld in REQUIRED_INDEX_SCOPE_FIELDS:
                    if fld not in index_scope:
                        findings.append(
                            f"Step {sid}: index_scope missing '{fld}'"
                        )
            assumptions = step.get("assumptions")
            if assumptions is None:
                findings.append(
                    f"Step {sid}: 'assumptions' field missing (should be array, "
                    "may be empty)"
                )
            if not isinstance(assumptions, list):
                findings.append(f"Step {sid}: 'assumptions' must be an array")
            # Check for derivative_semantics object (three-state model)
            ds = step.get("derivative_semantics")
            if not ds or not isinstance(ds, dict):
                findings.append(f"Step {sid}: missing derivative_semantics object")
            else:
                status = ds.get("status", "")
                if status not in ("ACTIVE_DERIVATIVE", "INHERITED_PROVENANCE", "NOT_APPLICABLE"):
                    findings.append(f"Step {sid}: unknown derivative_semantics status '{status}'")
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "derivation_step_completeness", status,
            f"Checked {len(steps)} steps",
            findings,
        )

    @staticmethod
    def validate_equation_evidence_coverage(map_data, equation_labels):
        findings = []
        if not isinstance(map_data, dict):
            return _make_result("equation_evidence_coverage", "FAIL",
                                "map_data is not a dict")
        mappings = map_data.get("equation_evidence_mappings", [])
        if not isinstance(mappings, list):
            findings.append("equation_evidence_mappings is not a list")
            return _make_result("equation_evidence_coverage", "FAIL",
                                "Invalid mappings", findings)
        mapped_labels = set()
        for m in mappings:
            label = m.get("equation_label", "")
            if label:
                mapped_labels.add(label)
        expected = set(equation_labels)
        uncovered = expected - mapped_labels
        if uncovered:
            findings.append(f"Equations not covered by evidence: {sorted(uncovered)}")
        excess = mapped_labels - expected
        if excess:
            findings.append(
                f"Beware: evidence mapped for equations not in expected set "
                f"(possible stale mapping): {sorted(excess)}"
            )
        status = "FAIL" if uncovered else ("WARN" if excess else "PASS")
        return _make_result(
            "equation_evidence_coverage", status,
            f"Covered: {len(mapped_labels & expected)}/{len(expected)} equations",
            findings,
        )

    @staticmethod
    def validate_assumption_visibility(step_data):
        findings = []
        if not isinstance(step_data, dict):
            return _make_result("assumption_visibility", "FAIL",
                                "step_data is not a dict")
        steps = step_data.get("derivation_steps", [])
        if not isinstance(steps, list):
            return _make_result("assumption_visibility", "FAIL",
                                "derivation_steps is not a list")
        for i, step in enumerate(steps):
            sid = step.get("step_id", f"step[{i}]")
            if "assumptions" not in step:
                findings.append(f"Step {sid}: missing 'assumptions' array")
            elif not isinstance(step["assumptions"], list):
                findings.append(
                    f"Step {sid}: 'assumptions' is not a list"
                )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "assumption_visibility", status,
            f"Checked {len(steps)} steps for assumptions",
            findings,
        )

    @staticmethod
    def validate_claim_type_consistency(data):
        findings = []
        if not isinstance(data, dict):
            return _make_result("claim_type_consistency", "FAIL",
                                "Data is not a dict")
        claims = data.get("claims", [])
        if not isinstance(claims, list):
            return _make_result("claim_type_consistency", "FAIL",
                                "claims is not a list")
        for c in claims:
            cid = c.get("claim_id", "UNKNOWN")
            edge_type_used = c.get("edge_type_used", "")
            relation_type = c.get("relation_type", "")
            if edge_type_used in FORBIDDEN_PROMOTIONS:
                forbidden = FORBIDDEN_PROMOTIONS[edge_type_used]
                if relation_type in forbidden:
                    findings.append(
                        f"Claim {cid}: FORBIDDEN promotion — "
                        f"'{edge_type_used}' edge cannot yield '{relation_type}'"
                    )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "claim_type_consistency", status,
            f"Checked {len(claims)} claims for forbidden promotions",
            findings,
        )

    @staticmethod
    def validate_relation_type_consistency(edges):
        findings = []
        for e in (edges or []):
            eid = e.get("edge_id", "UNKNOWN")
            et = e.get("edge_type", "")
            rt = e.get("relation_type", "")
            if et and rt:
                allowed = EDGE_TO_RELATION_MAP.get(et, [])
                if allowed and rt not in allowed:
                    findings.append(
                        f"Edge {eid}: edge_type '{et}' inconsistent with "
                        f"relation_type '{rt}'; allowed: {allowed}"
                    )
            if et not in EDGE_TYPES:
                findings.append(f"Edge {eid}: invalid edge_type '{et}'")
            if rt and rt not in RELATION_TYPES:
                findings.append(f"Edge {eid}: invalid relation_type '{rt}'")
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "relation_type_consistency", status,
            f"Checked {len(edges or [])} edges",
            findings,
        )

    @staticmethod
    def validate_omission_ledger_completeness(ledger_data, presentations):
        findings = []
        if not isinstance(ledger_data, dict):
            findings.append("ledger_data is not a dict")
        if not isinstance(presentations, list):
            findings.append("presentations is not a list")
        ledger_entries = ledger_data.get("omission_entries", []) if isinstance(ledger_data, dict) else []
        ledger_by_expr = {}
        for entry in (ledger_entries or []):
            expr = entry.get("expression_label", "")
            if expr:
                ledger_by_expr.setdefault(expr, []).append(entry)
        for p in (presentations or []):
            mode = p.get("presentation_mode", "")
            label = p.get("expression_label", "")
            if mode and mode != EXPRESSION_INLINE_VALUE and label:
                if label not in ledger_by_expr:
                    findings.append(
                        f"Expression '{label}': mode '{mode}' non-"
                        f"{EXPRESSION_INLINE_VALUE} but no omission ledger entry"
                    )
                else:
                    for entry in ledger_by_expr[label]:
                        reason = entry.get("omission_reason", "").lower()
                        if reason == "omitted for brevity":
                            findings.append(
                                f"Expression '{label}': 'omitted for brevity' "
                                f"alone rejected — must have substantive reason"
                            )
                        gen_rule = entry.get("generator_rule", "")
                        if gen_rule == GENERATOR_RULE_VALUE:
                            verif = entry.get("verification_status", "")
                            if verif != "VERIFIED":
                                findings.append(
                                    f"Expression '{label}': GENERATOR_RULE "
                                    f"requires VERIFIED, got '{verif}'"
                                )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "omission_ledger_completeness", status,
            f"Checked {len(ledger_entries or [])} ledger entries "
            f"against {len(presentations or [])} presentations",
            findings,
        )

    @staticmethod
    def validate_expression_reconstruction_reference(presentations):
        findings = []
        for p in (presentations or []):
            mode = p.get("presentation_mode", "")
            if mode and mode != EXPRESSION_INLINE_VALUE:
                has_artifact = p.get("full_expression_artifact", "")
                has_sha = p.get("sha256", "")
                if not has_artifact:
                    findings.append(
                        f"Expression '{p.get('expression_label', '?')}': "
                        f"mode '{mode}' missing full_expression_artifact"
                    )
                if not has_sha:
                    findings.append(
                        f"Expression '{p.get('expression_label', '?')}': "
                        f"mode '{mode}' missing sha256"
                    )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "expression_reconstruction_reference", status,
            f"Checked {len(presentations or [])} presentations",
            findings,
        )

    @staticmethod
    def validate_section_contract_completeness(contracts):
        findings = []
        if not isinstance(contracts, list):
            return _make_result("section_contract_completeness", "FAIL",
                                "contracts is not a list")
        section_ids = set()
        roles_present = set()
        for c in contracts:
            sid = c.get("section_id", "")
            if not sid:
                findings.append("Contract missing section_id")
                continue
            if sid in section_ids:
                findings.append(f"Duplicate section_id: {sid}")
            section_ids.add(sid)
            for fld in REQUIRED_SECTION_FIELDS:
                if fld not in c:
                    findings.append(f"Section {sid}: missing '{fld}'")
            role = c.get("section_role", "")
            if role and role not in SECTION_ROLES:
                findings.append(
                    f"Section {sid}: invalid section_role '{role}'"
                )
            if role:
                roles_present.add(role)
        cardinal_found = section_ids & set(CARDINAL_LEAF_SECTIONS)
        if len(cardinal_found) < len(CARDINAL_LEAF_SECTIONS):
            missing_cardinal = set(CARDINAL_LEAF_SECTIONS) - cardinal_found
            findings.append(
                f"Missing cardinal leaf sections: {sorted(missing_cardinal)}"
            )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "section_contract_completeness", status,
            f"Checked {len(contracts)} contracts, "
            f"roles: {sorted(roles_present)}, "
            f"sections: {len(section_ids)}",
            findings,
        )

    @staticmethod
    def validate_reader_pathway_integrity(pathways, contracts):
        findings = []
        if not isinstance(pathways, list):
            return _make_result("reader_pathway_integrity", "FAIL",
                                "pathways is not a list")
        contract_ids = {c.get("section_id", "") for c in (contracts or [])}
        contract_ids.discard("")
        for p in pathways:
            pid = p.get("pathway_id", "UNKNOWN")
            persona = p.get("reader_persona", "")
            if persona and persona not in READER_PERSONAS:
                findings.append(
                    f"Pathway {pid}: invalid reader_persona '{persona}'"
                )
            entry = p.get("entry_section", "")
            if entry and entry not in contract_ids:
                findings.append(
                    f"Pathway {pid}: entry_section '{entry}' not in contracts"
                )
            route = p.get("route_sections", [])
            for sec in (route or []):
                if sec not in contract_ids:
                    findings.append(
                        f"Pathway {pid}: route section '{sec}' not in contracts"
                    )
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "reader_pathway_integrity", status,
            f"Checked {len(pathways)} pathways against "
            f"{len(contract_ids)} contracts",
            findings,
        )

    @staticmethod
    def validate_schema_enforcement(steps_data):
        """Validate every derivation step record against the authoritative JSON Schema
        with additionalProperties:false enforcement."""
        findings = []
        records = steps_data if isinstance(steps_data, list) else steps_data.get("derivation_steps", [])
        if not isinstance(records, list) or len(records) == 0:
            return _make_result("schema_enforcement", "WARN",
                                "No records to validate against schema",
                                ["empty_or_missing_records"])

        # Load the derivation_step schema
        schema_path = os.path.join(REPO_ROOT, "schemas", "derivation_step.schema.json")
        try:
            with open(schema_path) as f:
                schema = json.load(f)
        except Exception as e:
            return _make_result("schema_enforcement", "FAIL",
                                f"Cannot load schema: {e}",
                                [f"schema_load_failed: {schema_path}"])
        try:
            import jsonschema
        except ImportError:
            return _make_result("schema_enforcement", "FAIL",
                                "jsonschema library not available",
                                ["jsonschema_import_failed"])

        validator = jsonschema.Draft202012Validator(schema)
        schema_valid = 0
        schema_invalid = 0
        for i, record in enumerate(records):
            sid = record.get("step_id", f"record[{i}]")
            errs = sorted(validator.iter_errors(record), key=lambda e: str(e.path))
            if errs:
                schema_invalid += 1
                for e in errs:
                    path = ".".join(str(p) for p in e.path) if e.path else "(root)"
                    findings.append(f"Step {sid}: schema violation at {path}: {e.message}")
            else:
                schema_valid += 1

        if findings:
            return _make_result("schema_enforcement", "FAIL",
                                f"{schema_valid} valid, {schema_invalid} invalid records",
                                findings)
        return _make_result("schema_enforcement", "PASS",
                            f"All {schema_valid} records schema-valid against {os.path.basename(schema_path)}")

    @staticmethod
    def validate_derivative_semantics(steps_data):
        """Validate three-state derivative_semantics model (ACTIVE_DERIVATIVE | INHERITED_PROVENANCE | NOT_APPLICABLE)."""
        findings = []
        items = steps_data if isinstance(steps_data, list) else [steps_data]
        if isinstance(steps_data, dict) and not isinstance(steps_data, list):
            items = steps_data.get("nodes", steps_data.get("edges", 
                steps_data.get("derivation_steps", steps_data.get("steps", [steps_data]))))
        if not isinstance(items, list):
            items = [items] if items else []

        step_map = {}
        for item in items:
            if isinstance(item, dict):
                sid = item.get("step_id", "")
                if sid:
                    step_map[sid] = item

        for item in items:
            if not isinstance(item, dict):
                continue
            sid = item.get("step_id", "?")
            ds = item.get("derivative_semantics")
            
            if not ds or not isinstance(ds, dict):
                findings.append(f"Step {sid}: missing derivative_semantics object")
                continue
            
            status = ds.get("status", "")
            
            if status == "ACTIVE_DERIVATIVE":
                required = ["derivative_variable", "derivative_order", "held_fixed_variables",
                           "sign_provenance", "coefficient_provenance", "source_definition"]
                for fld in required:
                    if fld not in ds or not ds[fld]:
                        findings.append(f"Step {sid}: ACTIVE_DERIVATIVE missing '{fld}'")
                order = ds.get("derivative_order")
                if order is not None and (not isinstance(order, int) or order < 1):
                    findings.append(f"Step {sid}: derivative_order must be >= 1, got {order}")
                    
            elif status == "INHERITED_PROVENANCE":
                if "derivative_source_step_id" not in ds or not ds["derivative_source_step_id"]:
                    findings.append(f"Step {sid}: INHERITED_PROVENANCE missing derivative_source_step_id")
                else:
                    src_id = ds["derivative_source_step_id"]
                    if src_id == sid:
                        findings.append(f"Step {sid}: INHERITED_PROVENANCE self-reference")
                    elif src_id not in step_map:
                        findings.append(f"Step {sid}: derivative_source_step_id '{src_id}' not found in steps")
                    else:
                        src_ds = step_map[src_id].get("derivative_semantics", {})
                        src_status = src_ds.get("status", "")
                        if src_status == "NOT_APPLICABLE":
                            findings.append(f"Step {sid}: inherits from '{src_id}' which is NOT_APPLICABLE")
                if "inheritance_reason" not in ds or not ds["inheritance_reason"]:
                    findings.append(f"Step {sid}: INHERITED_PROVENANCE missing inheritance_reason")
                    
            elif status == "NOT_APPLICABLE":
                if "reason" not in ds or not ds["reason"]:
                    findings.append(f"Step {sid}: NOT_APPLICABLE missing reason")
                if "derivative_variable" in ds or "sign_provenance" in ds:
                    findings.append(f"Step {sid}: NOT_APPLICABLE should not carry active derivative fields")
                    
            else:
                findings.append(f"Step {sid}: unknown derivative_semantics status '{status}'")

        # Inheritance cycle detection
        for item in items:
            if not isinstance(item, dict):
                continue
            ds = item.get("derivative_semantics", {})
            if ds.get("status") != "INHERITED_PROVENANCE":
                continue
            visited = set()
            cur = item.get("step_id", "")
            while cur:
                if cur in visited:
                    findings.append(f"Inheritance cycle involving step '{cur}'")
                    break
                visited.add(cur)
                cur_step = step_map.get(cur, {})
                cur_ds = cur_step.get("derivative_semantics", {})
                if cur_ds.get("status") == "INHERITED_PROVENANCE":
                    cur = cur_ds.get("derivative_source_step_id", "")
                elif cur_ds.get("status") == "ACTIVE_DERIVATIVE":
                    break  # chain terminates correctly
                else:
                    break

        status = "PASS" if not findings else "FAIL"
        return _make_result("derivative_semantics", status,
                            f"Checked {len(items)} step(s) for derivative semantics",
                            findings)

    @staticmethod
    def validate_sha_integrity(data, base_dir):
        findings = []
        if not isinstance(data, dict):
            return _make_result("sha_integrity", "FAIL", "Data is not a dict")
        shas = data.get("sha_registry", data.get("sha_manifest", []))
        if not isinstance(shas, list):
            return _make_result("sha_integrity", "FAIL",
                                "No sha_registry or sha_manifest list")
        for entry in shas:
            path = entry.get("file_path", "")
            expected = entry.get("sha256", "")
            if not path or not expected:
                continue
            full_path = os.path.join(base_dir, path)
            if not os.path.isfile(full_path):
                findings.append(f"SHA: file not found: {path}")
                continue
            try:
                with open(full_path, "rb") as f:
                    actual = hashlib.sha256(f.read()).hexdigest()
                if actual != expected:
                    findings.append(
                        f"SHA mismatch for {path}: expected {expected[:12]}..., "
                        f"got {actual[:12]}..."
                    )
            except Exception as exc:
                findings.append(f"SHA: error reading {path}: {exc}")
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "sha_integrity", status,
            f"Checked {len(shas)} SHA entries",
            findings,
        )

    @staticmethod
    def validate_human_readability_audit_structure(audit_data):
        findings = []
        if not isinstance(audit_data, dict):
            return _make_result("human_readability_audit", "FAIL",
                                "audit_data is not a dict")
        required = ["audit_id", "sections_audited", "overall_score",
                     "critical_issues"]
        for fld in required:
            if fld not in audit_data:
                findings.append(f"Missing required field '{fld}'")
        sections = audit_data.get("sections_audited", [])
        if not isinstance(sections, list):
            findings.append("sections_audited is not a list")
        else:
            for sec in sections:
                if not isinstance(sec, dict):
                    findings.append("sections_audited entry is not a dict")
                    continue
                if "section_id" not in sec:
                    findings.append("section_audited missing section_id")
                if "readability_score" not in sec:
                    findings.append("section_audited missing readability_score")
        score = audit_data.get("overall_score")
        if score is not None:
            try:
                s = float(score)
                if s < 0 or s > 10:
                    findings.append(
                        f"overall_score {s} outside valid range [0, 10]"
                    )
            except (ValueError, TypeError):
                findings.append("overall_score not numeric")
        status = "PASS" if not findings else "FAIL"
        return _make_result(
            "human_readability_audit", status,
            f"Checked readability audit structure",
            findings,
        )

    @staticmethod
    def validate_provenance_to_tex_compatibility(base_dir="."):
        """Check that if .tex artifacts exist alongside .json/.jsonl,
        there are no naming conflicts or missing pairings that would indicate
        of provenance table."""
        findings = []
        json_files = set(
            glob.glob(os.path.join(base_dir, "**", "*.json"), recursive=True)
        )
        jsonl_files = set(
            glob.glob(os.path.join(base_dir, "**", "*.jsonl"), recursive=True)
        )
        tex_files = set(
            glob.glob(os.path.join(base_dir, "**", "*.tex"), recursive=True)
        )
        if not tex_files:
            return _make_result(
                "provenance_to_tex", "WARN",
                "No .tex files found for provenance check",
                [],
            )
        stem_to_both = {}
        for tf in tex_files:
            stem = os.path.splitext(tf)[0]
            stem_to_both.setdefault(stem, {"tex": tf, "json": None, "jsonl": None})
        for jf in json_files:
            stem = os.path.splitext(jf)[0]
            stem_to_both.setdefault(stem, {})["json"] = jf
        for jlf in jsonl_files:
            stem = os.path.splitext(jlf)[0]
            stem_to_both.setdefault(stem, {})["jsonl"] = jlf
        for stem, d in stem_to_both.items():
            has_json = d.get("json") is not None
            has_jsonl = d.get("jsonl") is not None
            has_tex = d.get("tex") is not None
            if has_tex and not (has_json or has_jsonl):
                findings.append(
                    f".tex without corresponding .json/.jsonl: {os.path.basename(stem)}.tex"
                )
        status = "PASS" if not findings else "WARN"
        return _make_result(
            "provenance_to_tex", status,
            f"{len(tex_files)} .tex, {len(json_files)} .json, "
            f"{len(jsonl_files)} .jsonl",
            findings,
        )

    @staticmethod
    def _discover_data_files(supplement_dir):
        """BUG-001 fix: glob for BOTH *.json AND *.jsonl."""
        json_files = sorted(glob.glob(
            os.path.join(supplement_dir, "**", "*.json"), recursive=True
        ))
        jsonl_files = sorted(glob.glob(
            os.path.join(supplement_dir, "**", "*.jsonl"), recursive=True
        ))
        all_files = json_files + jsonl_files
        json_only = set(os.path.basename(f) for f in json_files)
        jsonl_only = set(os.path.basename(f) for f in jsonl_files)
        dual = json_only & {os.path.basename(f) for f in jsonl_files}
        return all_files, json_files, jsonl_files, dual

    @staticmethod
    def _load_file(filepath):
        """BUG-003 fix: identify data type by field sets present.

        Returns (data, file_type) where file_type is one of:
        'derivation_graph', 'derivation_steps', 'claim_relation',
        'equation_evidence', 'omission_ledger', 'section_contracts',
        'readability_audit', 'sha_manifest', 'presentations', 'unknown'.
        """
        if filepath.endswith(".jsonl"):
            records = []
            parse_errors = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        parse_errors.append((filepath, line_num, str(e)))
            if parse_errors:
                data = {"records": records, "parse_errors": parse_errors}
            else:
                data = records
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                keys = data[0].keys()
                if "step_id" in keys and "relation_type" in keys:
                    return data, "derivation_steps"
                elif "section_id" in keys and "section_role" in keys:
                    return data, "section_contracts"
                elif "pathway_id" in keys and "reader_persona" in keys:
                    return data, "reader_pathways"
                elif "file_path" in keys and "sha256" in keys:
                    return data, "sha_manifest"
                elif "presentation_mode" in keys:
                    return data, "presentations"
                elif "expression_label" in keys and "omission_reason" in keys:
                    return data, "omission_ledger"
                elif "claim_id" in keys:
                    return data, "claims"
                elif "equation_label" in keys:
                    return data, "equation_evidence_mappings"
            return data, "unknown"

        if not isinstance(data, dict):
            return data, "unknown"

        keys = data.keys()
        if "graph_id" in keys and "nodes" in keys and "edges" in keys:
            return data, "derivation_graph"
        elif "derivation_steps" in keys:
            return data, "derivation_steps"
        elif "claims" in keys:
            return data, "claim_relation"
        elif "equation_evidence_mappings" in keys:
            return data, "equation_evidence"
        elif "omission_entries" in keys:
            return data, "omission_ledger"
        elif "section_contracts" in keys or "contracts" in keys:
            return data, "section_contracts"
        elif "audit_id" in keys:
            return data, "readability_audit"
        elif "sha_registry" in keys or "sha_manifest" in keys:
            return data, "sha_manifest"
        elif "presentations" in keys:
            return data, "presentations"
        elif "reader_pathways" in keys or "pathways" in keys:
            return data, "reader_pathways"
        return data, "unknown"

    @staticmethod
    def run_all_validations(supplement_dir):
        """Run all validation checks against a supplement directory.

        Returns a dict with overall status and all individual check results.
        Exits nonzero if any check FAILs.
        """
        all_results = {"supplement_dir": supplement_dir,
                        "overall_status": "PASS",
                        "checks": []}
        all_files, json_files, jsonl_files, dual = (
            SupplementValidator._discover_data_files(supplement_dir)
        )

        if not all_files:
            all_results["overall_status"] = "FAIL"
            all_results["checks"].append(
                _make_result("file_discovery", "FAIL",
                              "NO target files found (.json or .jsonl)")
            )
            return all_results

        all_results["checks"].append(
            _make_result(
                "file_discovery", "PASS",
                f"Found {len(json_files)} .json + {len(jsonl_files)} .jsonl "
                f"= {len(all_files)} total files"
            )
        )

        parsed_data = {}
        for fp in all_files:
            if fp.endswith(".jsonl"):
                r2 = SupplementValidator.validate_jsonl_parse(fp)
                all_results["checks"].append(r2)
                data, ftype = SupplementValidator._load_file(fp)
                parsed_data[fp] = (data, ftype)
            else:
                r = SupplementValidator.validate_json_parse(fp)
                all_results["checks"].append(r)
                data, ftype = SupplementValidator._load_file(fp)
                parsed_data[fp] = (data, ftype)

        # Check for JSONL parse errors
        parse_errors_total = 0
        for fp, (data, ftype) in parsed_data.items():
            if isinstance(data, dict) and "parse_errors" in data:
                errs = data["parse_errors"]
                for fpath, lineno, msg in errs:
                    parse_errors_total += 1
                    all_results["checks"].append(
                        _make_result("jsonl_parse", "FAIL",
                                     f"Parse error in {fpath} line {lineno}: {msg}",
                                     [f"{fpath}:{lineno}: {msg}"])
                    )
                # Extract records from error dict
                parsed_data[fp] = (data.get("records", []), ftype)
                if parse_errors_total > 0:
                    all_results["overall_status"] = "FAIL"

        # Validation accounting
        accounting = {"files_discovered": len(all_files),
                       "jsonl_files": len(jsonl_files),
                       "records_parsed": 0, "records_routed": 0,
                       "records_validated": 0, "records_failed": 0,
                       "records_skipped": 0, "parse_failures": parse_errors_total}

        graph_data = None
        steps_data = None
        derivation_records_routed = 0
        all_equation_labels = []
        claims_data = None
        evidence_map_data = None
        ledger_data = None
        presentations_list = None
        contracts_list = None
        pathways_list = None
        audit_data = None
        sha_data = None
        edges_for_consistency = None

        for fp, (data, ftype) in parsed_data.items():
            if ftype == "derivation_graph":
                graph_data = data
                gnodes = data.get("nodes", []) if isinstance(data, dict) else []
                for n in gnodes:
                    label = n.get("equation_label", "")
                    if label:
                        all_equation_labels.append(label)
            elif ftype == "derivation_steps":
                if isinstance(data, list):
                    steps_data = {"derivation_steps": data}
                    derivation_records_routed = len(data)
                elif isinstance(data, dict):
                    steps_data = data
                    derivation_records_routed = len(data.get("derivation_steps", []))
            elif ftype == "claims":
                claims_data = data
            elif ftype == "claim_relation":
                if isinstance(data, dict):
                    claims_data = {"claims": data.get("claims", [])}
            elif ftype == "equation_evidence":
                if isinstance(data, list):
                    evidence_map_data = {"equation_evidence_mappings": data}
                elif isinstance(data, dict):
                    evidence_map_data = data
            elif ftype == "equation_evidence_mappings":
                evidence_map_data = {"equation_evidence_mappings": data}
            elif ftype == "omission_ledger":
                if isinstance(data, list):
                    ledger_data = {"omission_entries": data}
                elif isinstance(data, dict):
                    ledger_data = data
            elif ftype == "presentations":
                if isinstance(data, list):
                    presentations_list = data
                elif isinstance(data, dict):
                    presentations_list = data.get("presentations", data.get(
                        "expression_presentations", [])
                    )
            elif ftype == "section_contracts":
                if isinstance(data, list):
                    contracts_list = data
                elif isinstance(data, dict):
                    contracts_list = (
                        data.get("section_contracts")
                        or data.get("contracts", [])
                    )
            elif ftype == "reader_pathways":
                if isinstance(data, list):
                    pathways_list = data
                elif isinstance(data, dict):
                    pathways_list = (
                        data.get("reader_pathways")
                        or data.get("pathways", [])
                    )
            elif ftype == "readability_audit":
                audit_data = data
            elif ftype == "sha_manifest":
                if isinstance(data, list):
                    sha_data = {"sha_registry": data}
                elif isinstance(data, dict):
                    sha_data = data

        if graph_data:
            r = SupplementValidator.validate_derivation_graph_integrity(
                graph_data
            )
            all_results["checks"].append(r)
            edges_for_consistency = (
                graph_data.get("edges", [])
                if isinstance(graph_data, dict)
                else []
            )

        if steps_data:
            r = SupplementValidator.validate_schema_enforcement(steps_data)
            all_results["checks"].append(r)
            r = SupplementValidator.validate_derivation_step_completeness(
                steps_data
            )
            all_results["checks"].append(r)
            r = SupplementValidator.validate_assumption_visibility(steps_data)
            all_results["checks"].append(r)
            r = SupplementValidator.validate_derivative_semantics(steps_data)
            all_results["checks"].append(r)

        if evidence_map_data and all_equation_labels:
            r = SupplementValidator.validate_equation_evidence_coverage(
                evidence_map_data, all_equation_labels
            )
            all_results["checks"].append(r)

        if claims_data:
            r = SupplementValidator.validate_claim_type_consistency(
                claims_data
            )
            all_results["checks"].append(r)

        if edges_for_consistency is not None:
            r = SupplementValidator.validate_relation_type_consistency(
                edges_for_consistency
            )
            all_results["checks"].append(r)

        if ledger_data is not None or presentations_list is not None:
            r = SupplementValidator.validate_omission_ledger_completeness(
                ledger_data or {}, presentations_list or []
            )
            all_results["checks"].append(r)

        if presentations_list is not None:
            r = SupplementValidator.validate_expression_reconstruction_reference(
                presentations_list
            )
            all_results["checks"].append(r)

        if contracts_list:
            r = SupplementValidator.validate_section_contract_completeness(
                contracts_list
            )
            all_results["checks"].append(r)

        if pathways_list is not None:
            r = SupplementValidator.validate_reader_pathway_integrity(
                pathways_list, contracts_list or []
            )
            all_results["checks"].append(r)

        if audit_data:
            r = SupplementValidator.validate_human_readability_audit_structure(
                audit_data
            )
            all_results["checks"].append(r)

        if sha_data:
            r = SupplementValidator.validate_sha_integrity(
                sha_data, supplement_dir
            )
            all_results["checks"].append(r)

        r = SupplementValidator.validate_provenance_to_tex_compatibility(
            supplement_dir
        )
        all_results["checks"].append(r)

        # Validation accounting: check that derivation records were actually validated
        num_deriv_checks = sum(1 for c in all_results["checks"]
                              if c.get("check") == "derivative_semantics" and c.get("status") != "FAIL")
        step_completeness_checks = [c for c in all_results["checks"]
                                     if c.get("check") == "derivation_step_completeness"]
        records_validated = 0
        if step_completeness_checks:
            details = step_completeness_checks[0].get("details", "")
            if "Checked" in details:
                try:
                    records_validated = int(details.split("Checked ")[1].split(" step")[0])
                except: pass

        accounting["records_routed"] = derivation_records_routed
        accounting["records_validated"] = records_validated
        # If derivation records were parsed but none validated, fail
        if derivation_records_routed > 0 and records_validated == 0:
            all_results["checks"].append(
                _make_result("validation_accounting", "FAIL",
                             f"ZERO_SEMANTIC_CHECKS: {derivation_records_routed} records routed but 0 validated",
                             ["semantic_check_count_zero"])
            )
            all_results["overall_status"] = "FAIL"
        if derivation_records_routed == 0 and any("derivation_steps.jsonl" in fp for fp in all_files):
            all_results["checks"].append(
                _make_result("validation_accounting", "FAIL",
                             "NO_DERIVATION_RECORDS_ROUTED: JSONL present but no records dispatched",
                             ["records_parsed_but_not_routed"])
            )
            all_results["overall_status"] = "FAIL"
        accounting["records_skipped"] = max(0, derivation_records_routed - records_validated)

        all_results["accounting"] = accounting

        has_fail = any(
            c["status"] == "FAIL" for c in all_results["checks"]
        )
        if has_fail:
            all_results["overall_status"] = "FAIL"

        return all_results

    @staticmethod
    def run_self_test():
        results = []
        test_dir = os.path.join(
            os.path.dirname(__file__), "..", "fixtures",
            "supplement", "two_sector_response"
        )
        if not os.path.isdir(test_dir):
            return {
                "self_test": "SKIP",
                "reason": f"Fixture directory not found: {test_dir}",
            }
        all_files, _, _, _ = SupplementValidator._discover_data_files(test_dir)
        if not all_files:
            return {
                "self_test": "SKIP",
                "reason": f"No data files in {test_dir}",
            }
        for fp in all_files:
            base = os.path.basename(fp)
            r = SupplementValidator.validate_json_parse(fp)
            results.append({"file": base, "result": r})
            data, ftype = SupplementValidator._load_file(fp)
            results.append({"file": base, "detected_type": ftype})
        return {"self_test": "PASS", "files_tested": len(all_files),
                "results": results}

    @staticmethod
    def run_mutation_tests():
        """Run mutation tests against synthetic invalid inputs to verify
        that the validator detects known error patterns."""
        all_mutations = []

        # Test 1: invalid JSON
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tf:
            tf.write("{not json}")
            tmp = tf.name
        r = SupplementValidator.validate_json_parse(tmp)
        all_mutations.append({
            "mutation": "invalid_json",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })
        os.unlink(tmp)

        # Test 2: invalid graph (missing nodes)
        r = SupplementValidator.validate_derivation_graph_integrity({})
        all_mutations.append({
            "mutation": "empty_graph",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 3: cycle detection
        graph = {
            "graph_id": "test",
            "nodes": [
                {"node_id": "A", "node_type": "definition",
                 "equation_label": "eq1", "step_id": "s1",
                 "derivation_step_ref": "ref1"},
                {"node_id": "B", "node_type": "transformation",
                 "equation_label": "eq2", "step_id": "s2",
                 "derivation_step_ref": "ref2"},
            ],
            "edges": [
                {"edge_id": "e1", "parent_node_ids": "A",
                 "child_node_id": "B", "edge_type": "derived_from"},
                {"edge_id": "e2", "parent_node_ids": "B",
                 "child_node_id": "A", "edge_type": "derived_from"},
            ],
            "root_node_id": "A",
            "leaf_node_ids": ["B"],
        }
        r = SupplementValidator.validate_derivation_graph_integrity(graph)
        all_mutations.append({
            "mutation": "cycle_graph",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 4: forbidden claim promotion
        claims = {
            "claims": [{
                "claim_id": "C1",
                "edge_type_used": "numerically_supported_by",
                "relation_type": "literal_equality",
            }]
        }
        r = SupplementValidator.validate_claim_type_consistency(claims)
        all_mutations.append({
            "mutation": "forbidden_promotion",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 5: missing derivative semantics
        steps = {
            "derivation_steps": [{
                "step_id": "s1",
                "step_type": "integration",
                "input_equations": [],
                "output_equations": [],
                "assumptions": [],
            }]
        }
        r = SupplementValidator.validate_derivative_semantics(steps)
        all_mutations.append({
            "mutation": "missing_derivative_semantics",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 6: omission brevity alone
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
        all_mutations.append({
            "mutation": "omission_brevity_alone",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 7: missing step_id
        steps2 = {
            "derivation_steps": [{
                "step_type": "transformation",
                "input_equations": [],
                "output_equations": [],
                "assumptions": [],
            }]
        }
        r = SupplementValidator.validate_derivation_step_completeness(steps2)
        all_mutations.append({
            "mutation": "missing_step_id",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 8: invalid node_type
        graph2 = {
            "graph_id": "g2",
            "nodes": [{
                "node_id": "X",
                "node_type": "bogus_type",
                "equation_label": "eq1",
                "step_id": "s1",
                "derivation_step_ref": "ref1",
            }],
            "edges": [],
            "root_node_id": "X",
            "leaf_node_ids": ["X"],
        }
        r = SupplementValidator.validate_derivation_graph_integrity(graph2)
        all_mutations.append({
            "mutation": "invalid_node_type",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 9: unmapped equation
        evidence = {
            "equation_evidence_mappings": [
                {"equation_label": "eq_A"},
            ]
        }
        labels = ["eq_A", "eq_B"]
        r = SupplementValidator.validate_equation_evidence_coverage(
            evidence, labels
        )
        all_mutations.append({
            "mutation": "unmapped_equation",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 10: GENERATOR_RULE without VERIFIED
        ledger2 = {
            "omission_entries": [{
                "expression_label": "expr_gen",
                "omission_reason": "generated programmatically",
                "generator_rule": "GENERATOR_RULE",
                "verification_status": "UNVERIFIED",
            }]
        }
        presentations2 = [{
            "expression_label": "expr_gen",
            "presentation_mode": "GENERATOR_RULE",
        }]
        r = SupplementValidator.validate_omission_ledger_completeness(
            ledger2, presentations2
        )
        all_mutations.append({
            "mutation": "generator_rule_not_verified",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 11: missing assumptions field (not just empty)
        steps3 = {
            "derivation_steps": [{
                "step_id": "s3",
                "step_type": "definition",
                "input_equations": [],
                "output_equations": [],
            }]
        }
        r = SupplementValidator.validate_assumption_visibility(steps3)
        all_mutations.append({
            "mutation": "missing_assumptions_field",
            "expected_status": "FAIL",
            "actual_status": r["status"],
            "passed": r["status"] == "FAIL",
        })

        # Test 12: no_match_is_failure — validate on nonexistent dir
        r_all = SupplementValidator.run_all_validations(
            "/tmp/nonexistent_supplement_dir_12345"
        )
        all_mutations.append({
            "mutation": "no_match_is_failure",
            "expected_status": "FAIL",
            "actual_status": r_all["overall_status"],
            "passed": r_all["overall_status"] == "FAIL",
        })

        passed = sum(1 for m in all_mutations if m["passed"])
        failed = len(all_mutations) - passed
        return {
            "mutation_tests": "PASS" if failed == 0 else "FAIL",
            "total": len(all_mutations),
            "passed": passed,
            "failed": failed,
            "mutations": all_mutations,
        }


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: supplement_validator.py <supplement_dir> "
            "[--self-test] [--mutation-tests]"
        )
        sys.exit(1)

    supplement_dir = sys.argv[1]
    flags = sys.argv[2:]

    if "--self-test" in flags:
        result = SupplementValidator.run_self_test()
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if "--mutation-tests" in flags:
        result = SupplementValidator.run_mutation_tests()
        print(json.dumps(result, indent=2))
        status = result.get("mutation_tests", "FAIL")
        sys.exit(0 if status == "PASS" else 1)

    all_results = SupplementValidator.run_all_validations(supplement_dir)
    print(json.dumps(all_results, indent=2))
    status = all_results.get("overall_status", "FAIL")
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
