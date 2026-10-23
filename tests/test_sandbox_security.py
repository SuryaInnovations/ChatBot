"""
Security Test Suite for SPARK-AI Code Execution Sandbox.
Verifies that all known exploit payloads, introspection escapes, dangerous built-ins,
and file/network accesses are strictly blocked by the AST validator and sandbox environment.
"""

import os
import subprocess
import pytest
from tools.sandbox import (
    validate_code_safety,
    execute_safe_code,
    is_docker_available,
    _execute_in_docker,
)


KNOWN_EXPLOIT_PAYLOADS = [
    # 1. System calls & process execution
    ("import os\nos.system('echo pwned')", "import of 'os'"),
    ("import subprocess\nsubprocess.run(['dir'])", "import of 'subprocess'"),
    ("from os import system\nsystem('whoami')", "import from 'os'"),
    ("from subprocess import Popen\nPopen(['cmd'])", "import from 'subprocess'"),

    # 2. Reflection and __subclasses__ escape
    ("().__class__.__bases__[0].__subclasses__()", "Introspection attribute '__class__'"),
    ("().__class__.__mro__[1].__subclasses__()", "Introspection attribute '__class__'"),
    ("object.__subclasses__()", "attribute '__subclasses__'"),

    # 3. Dynamic evaluation and code execution
    ("eval(\"__import__('os').system('dir')\")", "Call to 'eval()'"),
    ("exec(\"import os; os.system('echo test')\")", "Call to 'exec()'"),
    ("compile('2+2', '', 'eval')", "Call to 'compile()'"),
    ("__import__('os').system('ls')", "Call to '__import__()'"),

    # 4. Introspection / Globals / Locals / Builtins
    ("globals()['__builtins__']", "Introspection attribute '__builtins__'"),
    ("getattr(int, '__class__')", "Call to 'getattr()'"),
    ("setattr(int, 'x', 1)", "Call to 'setattr()'"),
    ("delattr(int, 'x')", "Call to 'delattr()'"),
    ("vars()", "Call to 'vars()'"),
    ("locals()", "Call to 'locals()'"),

    # 5. File access
    ("open('/etc/passwd', 'r')", "Call to 'open()'"),
    ("open('secret.txt', 'w').write('leak')", "Call to 'open()'"),

    # 6. Network access
    ("import socket\ns = socket.socket()", "import of 'socket'"),
    ("import urllib.request\nurllib.request.urlopen('http://evil.com')", "import of 'urllib'"),
    ("import requests\nrequests.get('http://evil.com')", "import of 'requests'"),
    ("import httpx\nhttpx.get('http://evil.com')", "import of 'httpx'"),

    # 7. Unsafe deserialization and native code
    ("import pickle\npickle.loads(b'')", "import of 'pickle'"),
    ("import ctypes\nctypes.CDLL(None)", "import of 'ctypes'"),
    ("import importlib\nimportlib.import_module('os')", "import of 'importlib'"),
    ("import shutil\nshutil.rmtree('/')", "import of 'shutil'"),
]


@pytest.mark.parametrize("payload, expected_keyword", KNOWN_EXPLOIT_PAYLOADS)
def test_ast_blocks_all_known_exploits(payload, expected_keyword):
    """Verifies AST safety pre-screener detects and rejects each exploit."""
    is_safe, msg = validate_code_safety(payload)
    assert not is_safe, f"Exploit was NOT blocked by AST: {payload}"
    assert "Security Blocked" in msg


def test_sandbox_execution_blocks_dangerous_code():
    """Verifies execute_safe_code marks dangerous payload as security_blocked."""
    res = execute_safe_code("import os\nprint(os.listdir('.'))")
    assert not res["success"]
    assert res["security_blocked"] is True
    assert "Security Blocked" in res["error"]


def test_sandbox_allows_safe_math_and_data_code():
    """Verifies legitimate numerical and algorithmic code executes safely."""
    safe_code = """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print(fibonacci(10))
"""
    res = execute_safe_code(safe_code)
    assert res["success"] is True
    assert res["security_blocked"] is False
    assert "55" in res["output"]


def test_sandbox_timeout_halts_infinite_loops():
    """Verifies that an infinite loop is terminated by the sandbox timeout."""
    infinite_loop = """
while True:
    pass
"""
    res = execute_safe_code(infinite_loop, timeout_seconds=1.0)
    assert res["success"] is False
    assert "timed out" in res["error"].lower()


def test_string_built_attribute_access_blocked():
    """Verifies that dynamic string concatenation attempts to access attributes like __class__ are blocked."""
    is_safe1, msg1 = validate_code_safety("getattr((), '__cl' + 'ass__')")
    assert not is_safe1
    assert "getattr" in msg1

    is_safe2, msg2 = validate_code_safety("().__getattribute__('__cl' + 'ass__')")
    assert not is_safe2
    assert "__getattribute__" in msg2


def test_sandbox_fail_closed_without_docker(monkeypatch):
    """Verifies sandbox refuses execution when Docker is absent and ALLOW_UNSAFE_SUBPROCESS is disabled, but allows when flag is 1."""
    # State 1: Disabled (fail closed)
    monkeypatch.setenv("ALLOW_UNSAFE_SUBPROCESS", "0")
    monkeypatch.setattr("tools.sandbox.is_docker_available", lambda: False)
    res_disabled = execute_safe_code("print('fail closed test')")
    assert res_disabled["success"] is False
    assert res_disabled["security_blocked"] is True
    assert "fail-closed policy" in res_disabled["error"]

    # State 2: Explicitly enabled for local dev
    monkeypatch.setenv("ALLOW_UNSAFE_SUBPROCESS", "1")
    res_enabled = execute_safe_code("print('hello dev sandbox')")
    assert res_enabled["success"] is True
    assert res_enabled["security_blocked"] is False
    assert "hello dev sandbox" in res_enabled["output"]


def test_sql_playground_blocks_destructive_mutations():
    """Verifies connection-level and pre-execution blocking of mutations and multi-statement SQL."""
    from tools.high_value_tools import sql_playground

    # Semicolon multi-statement
    res1 = sql_playground("SELECT 1; DROP TABLE employees;")
    assert res1["success"] is False
    assert "Multi-statement" in res1["error"]

    # Mutation keyword
    res2 = sql_playground("DELETE FROM employees WHERE emp_id = 1;")
    assert res2["success"] is False
    assert "Mutation commands" in res2["error"]

    # CTE with mutation (WITH ... DELETE)
    res3 = sql_playground("WITH victims AS (SELECT * FROM employees) DELETE FROM employees;")
    assert res3["success"] is False
    assert "Mutation commands" in res3["error"]


def test_web_search_logs_do_not_contain_raw_query(caplog):
    """Verifies search_web logs never include user query plaintext."""
    import logging
    from tools.web_search import search_web
    secret_text = "SECRET_USER_SEARCH_TOKEN_998811"
    with caplog.at_level(logging.INFO, logger="chatbot.web_search"):
        search_web(f"what is {secret_text}", max_results=1)
    assert secret_text not in caplog.text


def test_ssrf_rejects_internal_redirects():
    """Verifies fetch_webpage_content aborts on internal redirects."""
    from tools.web_search import is_safe_public_url
    assert is_safe_public_url("http://127.0.0.1:8080")[0] is False
    assert is_safe_public_url("http://10.0.0.1/admin")[0] is False
    assert is_safe_public_url("http://169.254.169.254/latest")[0] is False
    assert is_safe_public_url("http://[::1]:80")[0] is False


@pytest.mark.skipif(not is_docker_available(), reason="Docker daemon not accessible")
def test_docker_container_network_memory_and_timeout():
    """
    Integration test asserting that the real Docker container enforces:
    1. No network access (--network none)
    2. Memory limit (--memory 128m)
    3. Timeout enforcement
    """
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # 1. Assert no network access: socket connect fails immediately
        net_code = (
            "import socket\n"
            "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "s.settimeout(2.0)\n"
            "try:\n"
            "    s.connect(('1.1.1.1', 80))\n"
            "    print('CONNECTED')\n"
            "except Exception as e:\n"
            "    print('BLOCKED:', type(e).__name__)\n"
        )
        net_file = os.path.join(td, "net.py")
        with open(net_file, "w") as f:
            f.write(net_code)
        proc_net = _execute_in_docker(net_file, td, timeout=10.0)
        assert proc_net is not None
        assert "CONNECTED" not in proc_net.stdout
        assert "BLOCKED" in proc_net.stdout

        # 2. Assert memory limit (128MB limit triggers MemoryError or killed exit code)
        mem_code = (
            "try:\n"
            "    data = bytearray(512 * 1024 * 1024)\n"
            "    print('ALLOCATED')\n"
            "except MemoryError:\n"
            "    print('MEMORY_LIMIT_HIT')\n"
        )
        mem_file = os.path.join(td, "mem.py")
        with open(mem_file, "w") as f:
            f.write(mem_code)
        proc_mem = _execute_in_docker(mem_file, td, timeout=10.0)
        assert proc_mem is not None
        assert "ALLOCATED" not in proc_mem.stdout
        assert proc_mem.returncode != 0 or "MEMORY_LIMIT_HIT" in proc_mem.stdout

        # 3. Assert timeout enforcement
        timeout_code = "import time\ntime.sleep(10.0)\n"
        timeout_file = os.path.join(td, "timeout.py")
        with open(timeout_file, "w") as f:
            f.write(timeout_code)
        with pytest.raises(subprocess.TimeoutExpired):
            _execute_in_docker(timeout_file, td, timeout=1.5)



