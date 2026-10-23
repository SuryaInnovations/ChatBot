"""
tools/python_interpreter.py — Hardened Python Code Interpreter.

Implements Capability 04:
- Executes Python code in a hardened isolated container or subprocess sandbox.
- Checks for Docker daemon; falls back cleanly to the hardened sandbox in tools/sandbox.py.
- Captures stdout, stderr, execution time, and generated artifacts (plots, tables).
- Never runs arbitrary code in the web server process.
"""

import time
import logging
from typing import Dict, Any, Optional

from tools.sandbox import execute_in_sandbox, validate_code_safety

logger = logging.getLogger("chatbot.tools.python_interpreter")


def execute_python_interpreter(
    code: str,
    timeout: float = 6.0,
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes Python code in a hardened sandbox.
    Attempts Docker isolation if available; otherwise uses strict subprocess sandbox.
    """
    clean_code = code.strip()
    if not clean_code:
        return {"success": False, "error": "No Python code provided for execution."}

    # 1. AST Safety check first
    is_safe, safety_err = validate_code_safety(clean_code)
    if not is_safe:
        return {
            "success": False,
            "error": f"Code safety violation: {safety_err}",
            "stdout": "",
            "execution_time_ms": 0.0
        }

    # 2. Try Docker SDK if installed and daemon is running
    docker_available = False
    try:
        import docker
        client = docker.from_env(timeout=2)
        client.ping()
        docker_available = True
    except Exception:
        docker_available = False

    start_time = time.time()

    if docker_available:
        try:
            logger.info("Executing Python code inside Docker container sandbox...")
            container = client.containers.run(
                image="python:3.11-slim",
                command=["python", "-c", clean_code],
                network_mode="none",  # No internet inside container
                mem_limit="256m",
                nano_cpus=1000000000, # Max 1 CPU
                remove=True,
                stdout=True,
                stderr=True,
                timeout=int(timeout)
            )
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            stdout = container.decode("utf-8", errors="replace")
            return {
                "success": True,
                "stdout": stdout,
                "execution_time_ms": duration_ms,
                "backend": "docker"
            }
        except Exception as e:
            logger.warning(f"Docker execution failed, falling back to subprocess sandbox: {e}")

    # Fallback to existing hardened subprocess sandbox
    logger.info("Executing Python code in hardened subprocess sandbox...")
    res = execute_in_sandbox(clean_code, timeout=timeout)
    duration_ms = round((time.time() - start_time) * 1000.0, 2)

    return {
        "success": res.get("success", False),
        "stdout": res.get("output", "") or res.get("stdout", ""),
        "error": res.get("error", None),
        "artifacts": res.get("artifacts", []),
        "execution_time_ms": duration_ms,
        "backend": "subprocess_sandbox"
    }
