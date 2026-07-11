#!/usr/bin/env python3
"""
Engine orchestration script for ENGINE_002.
Loads the engine registry, probes availability, resolves capabilities,
executes bounded requests, and captures execution truth.
"""
import json
import sys
import os
import hashlib
import time
import subprocess
import traceback
import platform as _platform

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def probe_engine(engine_id: str) -> dict:
    probe = {
        "engine": engine_id,
        "executable_found": False,
        "version_detected": "unknown",
        "license_or_activation_state_if_observable": "unknown",
        "probe_command": "",
        "probe_exit_code": -1,
        "platform": _platform.platform(),
        "required_dependencies": [],
        "missing_dependencies": [],
        "safe_to_execute": False,
        "caveats": []
    }

    if engine_id == "sympy":
        probe["probe_command"] = f"{sys.executable} -c 'import sympy; print(sympy.__version__)'"
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import sympy; print(sympy.__version__)"],
                capture_output=True, text=True, timeout=10
            )
            probe["probe_exit_code"] = result.returncode
            if result.returncode == 0:
                probe["executable_found"] = True
                probe["version_detected"] = result.stdout.strip()
                probe["safe_to_execute"] = True
                probe["license_or_activation_state_if_observable"] = "open_source"
            else:
                probe["missing_dependencies"].append("sympy")
                probe["executable_found"] = True
        except Exception as e:
            probe["missing_dependencies"].append("sympy")
            probe["caveats"].append(str(e))

    elif engine_id == "python_numeric":
        probe["probe_command"] = f"{sys.executable} -c 'import numpy,scipy,mpmath; print(numpy.__version__,scipy.__version__,mpmath.__version__)'"
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import numpy,scipy,mpmath; print(numpy.__version__,scipy.__version__,mpmath.__version__)"],
                capture_output=True, text=True, timeout=10
            )
            probe["probe_exit_code"] = result.returncode
            if result.returncode == 0:
                probe["executable_found"] = True
                probe["version_detected"] = result.stdout.strip()
                probe["safe_to_execute"] = True
                probe["license_or_activation_state_if_observable"] = "open_source"
            else:
                probe["missing_dependencies"].extend(["numpy", "scipy", "mpmath"])
                probe["executable_found"] = True
        except Exception as e:
            probe["missing_dependencies"].extend(["numpy", "scipy", "mpmath"])
            probe["caveats"].append(str(e))

    elif engine_id == "mathematica":
        import shutil
        candidates = ["wolframscript",
                      os.path.expanduser("~/.local/bin/wolframscript"),
                      "/usr/local/bin/wolframscript"]
        found = None
        for c in candidates:
            if shutil.which(c):
                found = c
                break
        if found is None:
            probe["missing_dependencies"].append("wolframscript")
            probe["caveats"].append("Mathematica is optional; absence is not a failure.")
        else:
            probe["executable_found"] = True
            probe["probe_command"] = f"{found} -code 'Print[$VersionNumber]'"
            try:
                result = subprocess.run(
                    [found, "-code", "Print[$VersionNumber]"],
                    capture_output=True, text=True, timeout=10
                )
                probe["probe_exit_code"] = result.returncode
                probe["version_detected"] = result.stdout.strip() if result.returncode == 0 else "unknown"
                probe["license_or_activation_state_if_observable"] = (
                    "license_active" if result.returncode == 0 else "unknown"
                )
                probe["safe_to_execute"] = result.returncode == 0
            except subprocess.TimeoutExpired:
                probe["probe_exit_code"] = -2
            except Exception as e:
                probe["caveats"].append(str(e))

    return probe


def run_engine_bounded(request: dict, selection: dict) -> dict:
    """Execute a bounded request on the selected backend."""
    primary = selection.get("selected_primary_backend")
    if primary is None:
        return {
            "request_id": request.get("request_id", "unknown"),
            "engine_id": "none",
            "result_type": "UNSUPPORTED_CAPABILITY",
            "errors": ["no_backend_satisfies_request"],
            "capability_gaps": selection.get("capability_gaps", [])
        }

    runner_path = os.path.join(REPO_ROOT, "engines", primary, "runner.py")
    if not os.path.exists(runner_path):
        return {
            "request_id": request.get("request_id", "unknown"),
            "engine_id": primary,
            "result_type": "EXECUTION_FAILED",
            "errors": [f"runner_not_found: {runner_path}"]
        }

    try:
        request_json = json.dumps(request)
        proc = subprocess.run(
            [sys.executable, runner_path],
            input=request_json,
            capture_output=True, text=True,
            timeout=request.get("timeout", 60),
            cwd=REPO_ROOT
        )
        if proc.returncode != 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout.strip())
            except json.JSONDecodeError:
                pass

        if proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        else:
            return {
                "request_id": request.get("request_id", "unknown"),
                "engine_id": primary,
                "result_type": "EXECUTION_FAILED",
                "exit_code": proc.returncode,
                "errors": [proc.stderr[:1000] if proc.stderr else "no_output"],
                "warnings": []
            }
    except subprocess.TimeoutExpired:
        return {
            "request_id": request.get("request_id", "unknown"),
            "engine_id": primary,
            "result_type": "TIMEOUT",
            "timeout_state": True,
            "errors": ["timeout_expired"]
        }
    except Exception as e:
        return {
            "request_id": request.get("request_id", "unknown"),
            "engine_id": primary,
            "result_type": "EXECUTION_FAILED",
            "errors": [f"{type(e).__name__}: {str(e)}"]
        }


def main():
    """Probe all engines and optionally execute a request."""
    if len(sys.argv) > 1 and sys.argv[1] == "--probe-only":
        probes = {}
        for engine_id in ["sympy", "python_numeric", "mathematica"]:
            probes[engine_id] = probe_engine(engine_id)
        print(json.dumps(probes, indent=2))
    elif len(sys.argv) > 1:
        request = json.loads(sys.argv[1])
        from scripts.resolve_backend_capabilities import resolve_capabilities
        selection = resolve_capabilities(request)
        result = run_engine_bounded(request, selection)
        print(json.dumps({"selection": selection, "result": result}, indent=2))
    else:
        request = json.load(sys.stdin)
        from scripts.resolve_backend_capabilities import resolve_capabilities
        selection = resolve_capabilities(request)
        result = run_engine_bounded(request, selection)
        print(json.dumps({"selection": selection, "result": result}, indent=2))


if __name__ == "__main__":
    main()
