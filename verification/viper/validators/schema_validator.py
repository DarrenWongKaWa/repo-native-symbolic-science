"""Independent structural validator: uses the standard jsonschema library only."""
import json, jsonschema
from pathlib import Path
SCH = Path(__file__).resolve().parent.parent / "schemas"
def _load(name): return json.loads((SCH/name).read_text())
def validate_claim(obj):
    jsonschema.validate(obj, _load("condition_d_claim.schema.json"))
def validate_result(obj):
    jsonschema.validate(obj, _load("verifier_result.schema.json"))
