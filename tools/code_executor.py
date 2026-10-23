"""
Safe Python code execution engine with subprocess isolation, timeout, and chart capture.
"""

from typing import Dict, Any
from tools.sandbox import execute_in_sandbox


def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Safely executes Python code in an isolated child subprocess sandbox.
    Captures stdout, stderr, and any generated matplotlib figures.
    Prevents server freezes via hard timeouts.
    """
    return execute_in_sandbox(code)
