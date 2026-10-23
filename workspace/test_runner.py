"""
workspace/test_runner.py — Sandboxed Automated Test Execution Engine.

Implements:
- Running Python unit tests or assertion scripts against workspace code.
- Enforcing sandbox security and execution timeouts (prevents hanging loops).
- Extracting passed/failed counts, assertion errors, and tracebacks.
"""

import time
import logging
from typing import Dict, Any, Optional

from tools.sandbox import execute_in_sandbox

logger = logging.getLogger("chatbot.workspace.test_runner")


def run_code_tests(
    test_code: str,
    target_code: Optional[str] = None,
    timeout_sec: float = 6.0
) -> Dict[str, Any]:
    """
    Executes a test script against code in the sandbox.
    """
    combined_script = ""
    if target_code:
        combined_script = f"# --- Target Code ---\n{target_code}\n\n# --- Test Cases ---\n{test_code}"
    else:
        combined_script = test_code

    start_time = time.time()
    res = execute_in_sandbox(combined_script, timeout=timeout_sec)
    dur_ms = round((time.time() - start_time) * 1000.0, 2)

    stdout = res.get("output", "") or res.get("stdout", "")
    err = res.get("error")

    # Detect test pass or failure heuristics
    passed = res.get("success", False) and not err
    if "AssertionError" in stdout or "FAILED" in stdout:
        passed = False

    return {
        "success": passed,
        "stdout": stdout,
        "error": err,
        "execution_time_ms": dur_ms,
        "status": "passed" if passed else "failed"
    }
