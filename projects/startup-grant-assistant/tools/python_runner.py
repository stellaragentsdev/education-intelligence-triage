#!/usr/bin/env python3
"""Safe Local Python Code Runner Tool."""
import sys
import json
import subprocess

def run_code(code):
    try:
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.returncode
        }
    except Exception as e:
        return {"error": str(e), "exit_code": -1}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = "print('Hello from Python Runner Tool!')"
    print(json.dumps(run_code(code), indent=2))
