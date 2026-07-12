#!/usr/bin/env python3
"""Validate derivation_graph.json against the schema and structural rules."""
import json
import sys
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

VALID_NODE_TYPES = {
    "definition", "raw_equation", "decomposition", "identity",
    "transformation", "projection", "integration", "limiting_case",
    "verification", "physical_interpretation"
}

VALID_EDGE_TYPES = {
    "derived_from", "defined_by", "decomposed_into", "reconstructed_from",
    "equal_under_assumptions", "projected_to", "integrated_to",
    "numerically_supported_by", "interpreted_as"
}

VALID_STEP_IDS = {
    "step_def_R", "step_def_AB", "step_raw_eq", "step_product_rule",
    "step_reorganize", "step_decompose", "step_project",
    "step_integ_A", "step_integ_B", "step_combine",
    "step_limit", "step_numeric", "step_interpret"
}

VALID_EQUATION_LABELS = {
    "eq:def_R", "eq:def_AB", "eq:start", "eq:identity", "eq:reorganized",
    "eq:sector_A", "eq:sector_B", "eq:projected", "eq:integrated_A", "eq:integrated_B",
    "eq:final", "eq:limit_eps0", "eq:long_expr"
}


def validate_derivation_graph(graph_path: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, "derivation_graph.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(graph_path) as f:
        data = json.load(f)

    errors = []
    warnings = []
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    root_id = data.get("root_node_id", "")
    leaf_ids = set(data.get("leaf_node_ids", []))

    node_ids = set()
    node_type_map = {}
    equation_label_map = {}
    for node in nodes:
        nid = node.get("node_id", "")
        if nid in node_ids:
            errors.append(f"Duplicate node_id: {nid}")
        node_ids.add(nid)
        ntype = node.get("node_type", "")
        if ntype not in VALID_NODE_TYPES:
            errors.append(f"Unknown node_type '{ntype}' for node {nid}")
        node_type_map[nid] = ntype
        step = node.get("step_id", "")
        if step and step not in VALID_STEP_IDS:
            warnings.append(f"Non-INTERFACE-CONTRACT step_id '{step}' for node {nid}")
        eq_label = node.get("equation_label", "")
        if eq_label and eq_label not in VALID_EQUATION_LABELS:
            warnings.append(f"Non-INTERFACE-CONTRACT equation_label '{eq_label}' for node {nid}")
        equation_label_map[nid] = eq_label

    if root_id and root_id not in node_ids:
        errors.append(f"root_node_id '{root_id}' not found in nodes")

    for lid in leaf_ids:
        if lid not in node_ids:
            errors.append(f"leaf_node_id '{lid}' not found in nodes")

    edge_ids = set()
    adjacency = {nid: set() for nid in node_ids}
    for edge in edges:
        eid = edge.get("edge_id", "")
        if eid in edge_ids:
            errors.append(f"Duplicate edge_id: {eid}")
        edge_ids.add(eid)
        src = edge.get("source_node_id", "")
        tgt = edge.get("target_node_id", "")
        etype = edge.get("edge_type", "")
        if src not in node_ids:
            errors.append(f"Edge {eid}: source_node_id '{src}' not found in nodes")
        if tgt not in node_ids:
            errors.append(f"Edge {eid}: target_node_id '{tgt}' not found in nodes")
        if etype not in VALID_EDGE_TYPES:
            errors.append(f"Unknown edge_type '{etype}' for edge {eid}")
        if src in adjacency:
            adjacency[src].add(tgt)

    unreachable = set(node_ids)
    if root_id and root_id in node_ids:
        visited = set()
        stack = [root_id]
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            if nid in adjacency:
                stack.extend(adjacency[nid])
        unreachable = node_ids - visited
        if unreachable:
            errors.append(f"Unreachable nodes from root: {unreachable}")

    has_cycle = False
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}
    cycle_nodes = []
    def dfs(nid):
        nonlocal has_cycle
        color[nid] = GRAY
        for neighbor in adjacency.get(nid, set()):
            if color[neighbor] == GRAY:
                has_cycle = True
                cycle_nodes.append((nid, neighbor))
            elif color[neighbor] == WHITE:
                dfs(neighbor)
        color[nid] = BLACK

    for nid in node_ids:
        if color[nid] == WHITE:
            dfs(nid)

    if has_cycle:
        errors.append(f"Cycle detected: {cycle_nodes}")

    references_from_steps = set()
    for node in nodes:
        for dep in node.get("dependencies", []):
            references_from_steps.add(dep)

    for nid in node_ids:
        deps = [n for n in node_ids if n in references_from_steps]
        if nid not in references_from_steps and nid != root_id and nid not in leaf_ids:
            pass

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "unreachable_count": len(unreachable),
            "has_cycle": has_cycle,
            "node_type_counts": {nt: sum(1 for n in nodes if n.get("node_type") == nt) for nt in VALID_NODE_TYPES},
            "edge_type_counts": {et: sum(1 for e in edges if e.get("edge_type") == et) for et in VALID_EDGE_TYPES},
        }
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <derivation_graph.json>")
        sys.exit(2)
    result = validate_derivation_graph(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
