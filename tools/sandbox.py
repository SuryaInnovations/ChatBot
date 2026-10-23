"""
Isolated Subprocess Sandbox for Python Code Execution.
Enforces:
1. Hard execution timeout (default 5.0 seconds).
2. Clean environment (strips sensitive credentials, API keys, and os.environ).
3. Process isolation (child subprocess cannot crash the main server).
4. Matplotlib chart rendering to artifacts directory.
"""

import sys
import os
import ast
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("chatbot.sandbox")

# Timeout in seconds
SANDBOX_TIMEOUT = float(os.getenv("SANDBOX_TIMEOUT_SECONDS", "6.0"))

# Startup check: warn if unisolated subprocess execution is enabled for development
if os.getenv("ALLOW_UNSAFE_SUBPROCESS", "0").strip().lower() in ("1", "true", "yes"):
    logger.warning(
        "[SECURITY WARNING] ALLOW_UNSAFE_SUBPROCESS=1 is active. "
        "Code execution is running without container virtualization. "
        "Do not enable this in production environments."
    )


# Blocked modules and calls for strict security
BLOCKED_MODULES = {
    "os", "subprocess", "socket", "shutil", "sys", "pty", "commands",
    "multiprocessing", "ctypes", "winreg", "msvcrt", "platform",
    "urllib", "requests", "httpx", "aiohttp", "ftplib", "smtplib",
    "telnetlib", "poplib", "imaplib", "http", "xmlrpc", "webbrowser",
    "pathlib", "importlib", "pickle", "shelve", "marshal", "inspect",
    "builtins", "posix", "nt", "gc", "signal", "_posixsubprocess", "resource",
    "codecs", "fcntl", "pwd", "grp"
}

BLOCKED_CALLS = {
    "eval", "exec", "compile", "__import__", "breakpoint",
    "getattr", "setattr", "delattr", "globals", "locals", "vars", "open"
}

BLOCKED_ATTRIBUTES = {
    "__builtins__", "__class__", "__bases__", "__subclasses__",
    "__mro__", "__globals__", "__code__", "__closure__",
    "__dict__", "__getattribute__", "__getattr__", "__setattr__", "__delattr__", "__dir__",
    "gi_frame", "f_globals", "f_locals", "f_builtins",
    "system", "popen", "spawn", "fork", "remove", "rmdir", "unlink"
}


def sanitize_traceback(text: str) -> str:
    """
    Sanitizes tracebacks and stderr to prevent internal path and host credential leakage.
    Replaces real temp file paths (e.g. C:\\Users\\... or /tmp/...) with generic virtual labels.
    """
    if not text:
        return ""
    import re
    # Mask user home directories and user names
    text = re.sub(r'[A-Za-z]:\\[Uu]sers\\[^\\]+\\', r'C:\\Users\\[REDACTED]\\', text)
    text = re.sub(r'/home/[^/\s\n\r]+/', r'/home/[REDACTED]/', text)
    # Mask temp directories and runner filenames
    text = re.sub(r'File ".*?[\\/](user_code|code|runner)\.py"', r'File "main.py"', text)
    text = re.sub(r'File ".*?[\\/]AppData[\\/]Local[\\/]Temp[\\/][^"]+"', r'File "main.py"', text)
    text = re.sub(r'File "/tmp/[^"]+"', r'File "main.py"', text)
    return text



def validate_code_safety(code: str) -> Tuple[bool, str]:
    """
    Parses code into an AST and verifies that no dangerous imports,
    system calls, reflection/introspection escapes, or network requests are present.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {e}"

    for node in ast.walk(tree):
        # 1. Check imports (import os, import subprocess, etc.)
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0].lower()
                if root_pkg in BLOCKED_MODULES:
                    return False, f"Security Blocked: Import of '{root_pkg}' is prohibited in the execution sandbox."
        # 2. Check from imports (from os import path, etc.)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0].lower()
                if root_pkg in BLOCKED_MODULES:
                    return False, f"Security Blocked: Import from '{root_pkg}' is prohibited in the execution sandbox."
        # 3. Check forbidden built-in calls (eval, exec, __import__, getattr, open)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_CALLS:
                    return False, f"Security Blocked: Call to '{node.func.id}()' is prohibited in the execution sandbox."
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in BLOCKED_ATTRIBUTES or node.func.attr in BLOCKED_CALLS:
                    return False, f"Security Blocked: Method or attribute '{node.func.attr}' is prohibited in the execution sandbox."
        # 4. Check forbidden attribute lookups (e.g. ().__class__.__bases__[0].__subclasses__())
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_ATTRIBUTES:
                return False, f"Security Blocked: Introspection attribute '{node.attr}' is prohibited in the execution sandbox."

    return True, ""


RUNNER_SCRIPT = """
import sys
import io
import os
import uuid
import traceback

artifacts_dir = sys.argv[1]
code_file = sys.argv[2]

with open(code_file, 'r', encoding='utf-8') as f:
    code = f.read()

# Setup matplotlib headless
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Restrict builtins in execution environment
safe_builtins = dict(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)
_orig_import = __import__
for blocked in ["eval", "exec", "compile", "breakpoint", "open", "getattr", "setattr", "delattr", "globals", "locals", "vars"]:
    safe_builtins.pop(blocked, None)

BLOCKED_PKGS = {"os", "subprocess", "socket", "sys", "shutil", "importlib", "ctypes", "pickle", "pty", "commands"}
def _safe_import(name, *args, **kwargs):
    root = name.split(".")[0].lower()
    if root in BLOCKED_PKGS:
        raise ImportError(f"Security: import of '{root}' is prohibited in the sandbox.")
    return _orig_import(name, *args, **kwargs)

safe_builtins["__import__"] = _safe_import

exec_globals = {
    "__builtins__": safe_builtins,
}

try:
    if plt:
        import numpy as np
        import pandas as pd
        exec_globals["np"] = np
        exec_globals["pd"] = pd
        exec_globals["plt"] = plt
        exec_globals["matplotlib"] = matplotlib
        plt.close("all")

    exec(code, exec_globals)

    if plt and plt.get_fignums():
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            img_path = os.path.join(artifacts_dir, f"chart_{uuid.uuid4().hex[:8]}.png")
            fig.savefig(img_path, bbox_inches="tight", dpi=150)
            print(f"[IMAGE_GENERATED]:{img_path}")
        plt.close("all")

except Exception:
    traceback.print_exc()
"""


def is_docker_available() -> bool:
    """Checks whether Docker CLI is available and reachable."""
    import shutil
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
        return res.returncode == 0
    except Exception:
        return False


def _execute_in_docker(code_file: str, artifacts_dir: str, timeout: float) -> Optional[subprocess.CompletedProcess]:
    """Executes code file inside an isolated unprivileged Docker container with resource limits."""
    if not is_docker_available():
        return None
    try:
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--read-only",
            "--cpus", "0.5",
            "--memory", "128m",
            "--pids-limit", "64",
            "-v", f"{artifacts_dir}:/artifacts:rw",
            "-v", f"{code_file}:/app/code.py:ro",
            "python:3.11-slim",
            "python", "/app/code.py"
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise
    except Exception as e:
        logger.debug(f"Docker sandbox run skipped: {e}")
        return None


def execute_in_sandbox(code: str, timeout: float = SANDBOX_TIMEOUT, stdin_data: str = "") -> Dict[str, Any]:
    """
    Executes Python code in an isolated environment.
    Uses Docker container when available, falling back to a hardened child subprocess
    with stripped environment and AST inspection.
    """
    # 1. AST Security Pre-screener
    is_safe, security_msg = validate_code_safety(code)
    if not is_safe:
        logger.warning(f"[SANDBOX BLOCKED] {security_msg}")
        return {
            "success": False,
            "stdout": "",
            "stderr": security_msg,
            "security_blocked": True,
            "generated_images": []
        }

    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        code_file = os.path.join(temp_dir, "user_code.py")
        runner_file = os.path.join(temp_dir, "runner.py")

        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        with open(runner_file, "w", encoding="utf-8") as f:
            f.write(RUNNER_SCRIPT)

        # Build clean environment: strip all API keys and credentials
        clean_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join(sys.path),
            "APPDATA": os.environ.get("APPDATA", ""),
            "USERPROFILE": os.environ.get("USERPROFILE", ""),
            "TMP": temp_dir,
            "TEMP": temp_dir,
        }

        cmd = [sys.executable, runner_file, artifacts_dir, code_file]

        try:
            # Attempt Docker isolation if running, else subprocess with fail-closed check
            proc = _execute_in_docker(code_file, artifacts_dir, timeout=timeout)
            if proc is None:
                allow_unsafe = os.getenv("ALLOW_UNSAFE_SUBPROCESS", "0").strip().lower() in ("1", "true", "yes")
                if not allow_unsafe:
                    logger.warning("[SANDBOX FAIL-CLOSED] Docker is unavailable and ALLOW_UNSAFE_SUBPROCESS is not set.")
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": (
                            "Sandbox execution disabled (fail-closed policy): Docker isolation is unavailable. "
                            "In public cloud environments without container virtualization, unisolated execution is blocked. "
                            "For local development testing only, set ALLOW_UNSAFE_SUBPROCESS=1 in your .env."
                        ),
                        "security_blocked": True,
                        "generated_images": []
                    }

                proc = subprocess.run(
                    cmd,
                    input=stdin_data if stdin_data else None,
                    capture_output=True,
                    text=True,
                    env=clean_env,
                    timeout=timeout
                )

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            # Extract generated images
            generated_images: List[str] = []
            clean_stdout_lines = []
            for line in stdout.splitlines():
                if line.startswith("[IMAGE_GENERATED]:"):
                    img_path = line.split("[IMAGE_GENERATED]:", 1)[1].strip()
                    if os.path.exists(img_path):
                        generated_images.append(img_path)
                else:
                    clean_stdout_lines.append(line)

            clean_stdout = "\n".join(clean_stdout_lines).strip()
            
            # Enforce output length limits (max 50,000 chars)
            MAX_OUTPUT_CHARS = 50_000
            if len(clean_stdout) > MAX_OUTPUT_CHARS:
                clean_stdout = clean_stdout[:MAX_OUTPUT_CHARS] + "\n... [Output truncated at 50,000 characters]"
            clean_stderr = sanitize_traceback(stderr.strip())
            if len(clean_stderr) > MAX_OUTPUT_CHARS:
                clean_stderr = clean_stderr[:MAX_OUTPUT_CHARS] + "\n... [Stderr truncated at 50,000 characters]"

            success = proc.returncode == 0 and not ("Traceback" in clean_stderr and not clean_stdout)

            return {
                "success": success,
                "stdout": clean_stdout,
                "stderr": clean_stderr,
                "generated_images": generated_images
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds. Infinite loops or long operations are prevented.",
                "generated_images": []
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox execution error: {str(e)}",
                "generated_images": []
            }


def execute_safe_code(code: str, timeout_seconds: float = SANDBOX_TIMEOUT, stdin_data: str = "") -> Dict[str, Any]:
    """Alias for execute_in_sandbox returning unified output dict."""
    res = execute_in_sandbox(code, timeout=timeout_seconds, stdin_data=stdin_data)
    return {
        "success": res.get("success", False),
        "output": res.get("stdout", ""),
        "error": res.get("stderr", ""),
        "images": res.get("generated_images", []),
        "security_blocked": res.get("security_blocked", False)
    }


execute_code_in_sandbox = execute_in_sandbox

