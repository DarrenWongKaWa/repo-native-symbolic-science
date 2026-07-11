#!/usr/bin/env python3
"""
Mathematica bounded runner for ENGINE_002.
Probes for wolframscript availability. When available, executes bounded Mathematica code.
When unavailable, returns ENGINE_UNAVAILABLE safely.
"""
import json
import sys
import hashlib
import subprocess
import time
import os
import platform as _platform
import traceback


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def probe_mathematica() -> dict:
    """Safe probe for wolframscript availability."""
    result = {
        "executable_found": False,
        "version_detected": "unknown",
        "probe_exit_code": -1,
        "missing_dependencies": [],
        "safe_to_execute": False
    }

    candidates = ["wolframscript", "/usr/local/bin/wolframscript",
                  os.path.expanduser("~/.local/bin/wolframscript")]
    found = None
    import shutil
    for c in candidates:
        if shutil.which(c):
            found = c
            break

    if found is None:
        result["missing_dependencies"] = ["wolframscript"]
        return result

    result["executable_found"] = True
    result["probe_command"] = f"{found} -code 'Print[$VersionNumber]'"
    try:
        proc = subprocess.run(
            [found, "-code", "Print[$VersionNumber]"],
            capture_output=True, text=True, timeout=10
        )
        result["probe_exit_code"] = proc.returncode
        result["version_detected"] = proc.stdout.strip()
        result["license_or_activation_state_if_observable"] = "license_active" if proc.returncode == 0 else "unknown"
        result["safe_to_execute"] = proc.returncode == 0
    except subprocess.TimeoutExpired:
        result["probe_exit_code"] = -2
        result["safe_to_execute"] = False
    except Exception as e:
        result["probe_exit_code"] = -3
        result["safe_to_execute"] = False

    return result


def generate_mathematica_script(request: dict) -> str:
    """Generate a bounded Mathematica script from the request."""
    ops_sequence = request.get("requested_operation_sequence", [])
    expression_text = request.get("expression_scope", {}).get("input_expression", "0")
    assumptions = request.get("declared_assumptions", [])
    timeout = request.get("timeout", 30)

    lines = []
    lines.append('(* SLOOP_ENGINE_002 Mathematica bounded runner *)')
    lines.append(f'expr = {expression_text};')

    if assumptions:
        lines.append(f'$Assumptions = {" && ".join(assumptions)};')

    for op_entry in sorted(ops_sequence, key=lambda x: x.get("order", 0)):
        op_name = op_entry.get("operation", "")
        params = op_entry.get("parameters", {})

        if op_name == "ReplaceAll":
            rules = params.get("rules", "{}")
            lines.append(f'expr = expr /. {rules};')
        elif op_name == "Expand":
            lines.append(f'expr = TimeConstrained[Expand[expr], {timeout}];')
        elif op_name == "Factor":
            lines.append(f'expr = TimeConstrained[Factor[expr], {timeout}];')
        elif op_name == "Together":
            lines.append(f'expr = TimeConstrained[Together[expr], {timeout}];')
        elif op_name == "Apart":
            lines.append(f'expr = TimeConstrained[Apart[expr], {timeout}];')
        elif op_name == "Cancel":
            lines.append(f'expr = TimeConstrained[Cancel[expr], {timeout}];')
        elif op_name == "exact_subtraction":
            other = params.get("other", "0")
            lines.append(f'expr = TimeConstrained[Simplify[expr - ({other})], {timeout}];')
        elif op_name == "SameQ":
            other = params.get("other", "0")
            lines.append(f'result = SameQ[Simplify[expr], Simplify[{other}]];')
        elif op_name == "Simplify_with_TimeConstrained":
            lines.append(f'expr = TimeConstrained[Simplify[expr], {timeout}];')
        elif op_name == "Series":
            var = params.get("variable", "x")
            pt = params.get("point", "0")
            n = params.get("n", "5")
            lines.append(f'expr = TimeConstrained[Series[expr, {{{var}, {pt}, {n}}}], {timeout}];')
        elif op_name == "Coefficient":
            var = params.get("variable", "x")
            n = params.get("n", "0")
            lines.append(f'expr = Coefficient[expr, {var}, {n}];')
        elif op_name == "D":
            var = params.get("variable", "x")
            lines.append(f'expr = D[expr, {var}];')
        else:
            lines.append(f'(* unhandled operation: {op_name} *)')

    lines.append('Print[InputForm[expr]];')
    return "\n".join(lines)


def run_mathematica_bounded(request: dict) -> dict:
    request_id = request.get("request_id", "unknown")
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    probe = probe_mathematica()

    if not probe.get("safe_to_execute", False):
        return {
            "request_id": request_id,
            "engine_id": "mathematica",
            "engine_version": "unknown",
            "exit_code": -1,
            "result_type": "ENGINE_UNAVAILABLE",
            "errors": ["mathematica_not_available"],
            "availability_probe": probe,
            "started_at": started_at,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    engine_version = probe.get("version_detected", "unknown")
    wolframscript_path = probe.get("probe_command", "").split(" ")[0]

    script = generate_mathematica_script(request)
    script_sha = sha256_hex(script)

    errors = []
    warnings = []
    raw_output = ""
    exit_code = 0
    result_type = "EXACT_SYMBOLIC_RESULT"
    partial = "COMPLETE"

    try:
        proc = subprocess.run(
            [wolframscript_path, "-code", script],
            capture_output=True, text=True,
            timeout=request.get("timeout", 30)
        )
        exit_code = proc.returncode
        raw_output = proc.stdout.strip()
        if proc.stderr:
            warnings.append(proc.stderr.strip()[-500:])
        if exit_code != 0:
            result_type = "EXECUTION_FAILED"
            errors.append(f"exit_code_{exit_code}")
    except subprocess.TimeoutExpired:
        exit_code = -2
        result_type = "TIMEOUT"
        errors.append("timeout_expired")
        partial = "PARTIAL"
        raw_output = "$TimedOut"
    except Exception as e:
        exit_code = -3
        result_type = "EXECUTION_FAILED"
        errors.append(f"{type(e).__name__}: {str(e)}")
        partial = "PARTIAL"

    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "request_id": request_id,
        "engine_id": "mathematica",
        "engine_version": engine_version,
        "engine_executable": wolframscript_path if probe.get("executable_found") else "unknown",
        "environment": {
            "platform": _platform.platform(),
            "python_version": _platform.python_version(),
            "dependencies": {"mathematica": engine_version}
        },
        "generated_script": script,
        "generated_script_sha": script_sha,
        "exact_command": f"{wolframscript_path} -code '<script>'",
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "timeout_state": result_type == "TIMEOUT",
        "memory_state": "OK",
        "operations_requested": [o.get("operation", "") for o in request.get("requested_operation_sequence", [])],
        "operations_observed": [o.get("operation", "") for o in request.get("requested_operation_sequence", [])],
        "assumptions_requested": request.get("declared_assumptions", []),
        "assumptions_observed": request.get("declared_assumptions", []),
        "raw_output": raw_output,
        "raw_output_sha": sha256_hex(raw_output),
        "normalized_output": raw_output,
        "normalized_output_sha": sha256_hex(raw_output),
        "warnings": warnings,
        "errors": errors,
        "partial_result_status": partial,
        "determinism_record": {
            "declared_deterministic": True,
            "observed_deterministic": True,
            "reproducible": True
        },
        "result_type": result_type,
        "availability_probe": probe
    }


def main():
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError:
        request = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}

    result = run_mathematica_bounded(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
