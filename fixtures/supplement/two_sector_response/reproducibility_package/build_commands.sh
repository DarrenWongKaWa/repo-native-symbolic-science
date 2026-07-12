#!/bin/bash
# Build and verification commands for synthetic_two_sector_response_kernel
# Usage: bash build_commands.sh [--verify]

set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="$BASE/source_artifacts"

echo "=== Two-Sector Response Kernel Build ==="

# 1. Verify artifact integrity via SHA-256
echo "[1/6] Verifying source artifact integrity..."
python3 -c "
import hashlib, sys, os
expected = {
    '$ARTIFACTS/definitions.json': '7e701a591f9e1e863dde09e4c57c0411e5e94571bc0b823892de13d1e55017ce',
    '$ARTIFACTS/starting_expression.txt': 'd6a77de36ac11ac045f4026efe4c11419959405f595a2265f7d2d0f45f488749',
    '$ARTIFACTS/sector_decomposition.json': '687c8bf1e41cf92fcc667eff95af7a5b9cfe0a59bdc520dc6ca72f4a3fb70348',
    '$ARTIFACTS/scientific_identity.json': 'b1bfc084993ce873d882caef2083499aa4d44b9ca43c158aed0b3f64c536e5b2',
    '$ARTIFACTS/integrated_result.txt': 'f323ed102537110118f3c2c9ee0d7a4ad4bc403c4a2e8353ab3efdf4ed218897',
    '$ARTIFACTS/limiting_case.txt': '2d194276241199dd7f1cf28ef94181ff0cc24f06fdc7a967749b5413e2189472',
    '$ARTIFACTS/long_expression_artifact.txt': 'eaf0200206a64698de6b82ea0a5888caf56b05c04fe0bccc6971cd365be1a18c',
}
all_ok = True
for path, expected_sha in expected.items():
    with open(path, 'rb') as f:
        actual = hashlib.sha256(f.read()).hexdigest()
    status = 'OK' if actual == expected_sha else 'MISMATCH'
    if status != 'OK':
        all_ok = False
    print(f'  {os.path.basename(path)}: {status}')
if not all_ok:
    print('SHA verification FAILED', file=sys.stderr)
    sys.exit(1)
print('  All SHAs verified.')
"

# 2. Verify term count in long expression
echo "[2/6] Verifying long expression term count..."
python3 -c "
with open('$ARTIFACTS/long_expression_artifact.txt') as f:
    content = f.read()
# Count T_ lines (numbered terms)
import re
terms = re.findall(r'^T_\d+', content, re.MULTILINE)
count = len(terms)
total_line = [l for l in content.split('\n') if 'Total term count:' in l]
expected = 96
if count == expected:
    print(f'  Term count: {count} (matches expected {expected})')
else:
    print(f'  ERROR: term count {count} != expected {expected}', file=__import__('sys').stderr)
    __import__('sys').exit(1)
"

# 3. Validate derivation_steps.jsonl structure
echo "[3/6] Validating derivation steps..."
python3 -c "
import json, sys
required_steps = [
    'step_def_R', 'step_def_AB', 'step_raw_eq', 'step_product_rule',
    'step_reorganize', 'step_decompose', 'step_project',
    'step_integ_A', 'step_integ_B', 'step_combine',
    'step_limit', 'step_numeric', 'step_interpret'
]
with open('$BASE/derivation_steps.jsonl') as f:
    steps = {}
    for line in f:
        line = line.strip()
        if not line:
            continue
        s = json.loads(line)
        steps[s['step_id']] = s
missing = [s for s in required_steps if s not in steps]
if missing:
    print(f'  ERROR: Missing steps: {missing}', file=sys.stderr)
    sys.exit(1)
print(f'  All {len(steps)} steps present and valid JSON.')
"

# 4. Validate derivation_graph.json
echo "[4/6] Validating derivation graph..."
python3 -c "
import json, sys
with open('$BASE/derivation_graph.json') as f:
    g = json.load(f)
assert len(g['nodes']) == 12, f'Expected 12 nodes, got {len(g[\"nodes\"])}'
assert len(g['edges']) == 12, f'Expected 12 edges, got {len(g[\"edges\"])}'
node_ids = {n['node_id'] for n in g['nodes']}
edge_ids = {e['edge_id'] for e in g['edges']}
assert node_ids == {f'N{i}' for i in range(1,13)}, 'Unexpected node IDs'
assert edge_ids == {f'E{i}' for i in range(1,13)}, 'Unexpected edge IDs'
print('  Graph structure valid: 12 nodes, 12 edges.')
"

# 5. Validate equation evidence mappings
echo "[5/6] Validating equation evidence mappings..."
python3 -c "
import json, sys
with open('$BASE/equation_evidence_mapping.json') as f:
    mappings = json.load(f)
expected_labels = [
    'eq:def_R', 'eq:def_AB', 'eq:start', 'eq:identity',
    'eq:reorganized', 'eq:sector_A', 'eq:sector_B', 'eq:projected',
    'eq:integrated_A', 'eq:integrated_B', 'eq:final',
    'eq:limit_eps0', 'eq:long_expr'
]
labels = [m['equation_label'] for m in mappings]
missing = [l for l in expected_labels if l not in labels]
if missing:
    print(f'  ERROR: Missing labels: {missing}', file=sys.stderr)
    sys.exit(1)
print(f'  All {len(mappings)} equation mappings present.')
"

# 6. Cross-reference consistency
echo "[6/6] Cross-reference consistency check..."
python3 -c "
import json, sys

# Load steps
steps = {}
with open('$BASE/derivation_steps.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        s = json.loads(line)
        steps[s['step_id']] = s

# Load graph
with open('$BASE/derivation_graph.json') as f:
    graph = json.load(f)

# Check all edge derivation_step_ids reference existing steps
for edge in graph['edges']:
    step_id = edge['derivation_step_id']
    if step_id not in steps:
        print(f'  ERROR: Edge {edge[\"edge_id\"]} references missing step {step_id}', file=sys.stderr)
        sys.exit(1)

# Check all steps have valid step_ids
valid_steps = {
    'step_def_R', 'step_def_AB', 'step_raw_eq', 'step_product_rule',
    'step_reorganize', 'step_decompose', 'step_project',
    'step_integ_A', 'step_integ_B', 'step_combine',
    'step_limit', 'step_numeric', 'step_interpret'
}
for sid, s in steps.items():
    if sid not in valid_steps:
        print(f'  WARNING: Unexpected step_id {sid}')
    required = ['step_id', 'parent_equation_ids', 'child_equation_id',
                'mathematical_operation', 'relation_type',
                'machine_verification_status', 'canonical_status']
    for r in required:
        if r not in s:
            print(f'  ERROR: Step {sid} missing field {r}', file=sys.stderr)
            sys.exit(1)

print('  Cross-reference consistency: PASSED')
print()
print('=== All verification gates passed ===')
"
