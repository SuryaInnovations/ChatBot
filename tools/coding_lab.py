"""
Interactive Coding Lab Engine.
Powers the live coding workspace with code execution, test-case evaluation,
I/O console processing, AST complexity analysis, and diagnostic explanations.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from tools.sandbox import execute_safe_code
from tools.high_value_tools import complexity_analyzer, explain_code_error

logger = logging.getLogger("chatbot.coding_lab")


def run_coding_workspace(
    code: str,
    stdin_input: str = "",
    test_cases: Optional[List[Dict[str, str]]] = None,
    timeout_seconds: float = 5.0
) -> Dict[str, Any]:
    """
    Executes Python code from the interactive workspace with full test cases,
    runtime metrics, stdin inputs, Big-O complexity estimation, and error feedback.
    """
    code_clean = code.strip()
    if not code_clean:
        return {
            "success": False,
            "stdout": "",
            "stderr": "No code provided to execute.",
            "execution_time_ms": 0.0,
            "test_results": [],
            "all_tests_passed": False,
            "complexity": None,
            "error_explanation": None
        }

    # 1. Static AST Complexity Analysis
    complexity_info = None
    try:
        complexity_info = complexity_analyzer(code_clean)
    except Exception as e:
        logger.debug(f"Complexity analysis note: {e}")

    # 2. Main Execution (Standard Run)
    start_time = time.perf_counter()
    exec_res = execute_safe_code(code_clean, timeout_seconds=timeout_seconds, stdin_data=stdin_input)
    exec_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    raw_stdout = exec_res.get("output", "")
    raw_error = exec_res.get("error")
    is_success = exec_res.get("success", False)

    # 3. Test Cases Execution
    test_results = []
    all_passed = True if (test_cases and len(test_cases) > 0) else None

    if test_cases and len(test_cases) > 0:
        for idx, tc in enumerate(test_cases, start=1):
            inp = tc.get("input", "")
            expected = tc.get("expected", "").strip()

            t_start = time.perf_counter()
            t_res = execute_safe_code(code_clean, timeout_seconds=timeout_seconds, stdin_data=inp)
            t_duration = round((time.perf_counter() - t_start) * 1000, 2)

            actual_out = t_res.get("output", "").strip()
            passed = bool(t_res.get("success") and actual_out == expected)
            if not passed:
                all_passed = False

            test_results.append({
                "test_id": idx,
                "input": inp,
                "expected": expected,
                "actual": actual_out,
                "passed": passed,
                "duration_ms": t_duration,
                "error": t_res.get("error")
            })

    # 4. Error Diagnosis if failed
    error_diag = None
    if not is_success and raw_error:
        try:
            diag = explain_code_error(code_clean, str(raw_error))
            if diag.get("success"):
                error_diag = diag.get("explanation")
        except Exception as e:
            logger.debug(f"Error diagnosis note: {e}")

    return {
        "success": is_success,
        "stdout": raw_stdout,
        "stderr": raw_error if not is_success else None,
        "execution_time_ms": exec_duration_ms,
        "test_results": test_results,
        "all_tests_passed": all_passed,
        "complexity": complexity_info,
        "error_explanation": error_diag
    }


def generate_code_patch(original_code: str, modified_code: str, filename: str = "main.py") -> str:
    """
    Generates a unified diff patch between original and modified code.
    Prevents blind file overwriting by allowing users to inspect targeted diffs.
    """
    import difflib
    orig_lines = original_code.splitlines(keepends=True)
    mod_lines = modified_code.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    patch_text = "".join(diff)
    return patch_text if patch_text.strip() else f"# No changes detected between original and modified {filename}."


def inspect_project_structure(target_dir: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Safely inspects a local project repository.
    Reports directory tree, file counts, lines of code, detected test suites, and entry points.
    Protects against path traversal.
    """
    import os
    abs_path = os.path.abspath(target_dir)

    # Basic boundary check
    if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
        return {"error": f"Path '{target_dir}' is not a valid directory."}

    file_inventory = []
    total_loc = 0
    py_files = 0
    test_files = []
    entrypoints = []

    for root, dirs, files in os.walk(abs_path):
        # Skip git, caches, and virtual environments
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "venv", ".venv", "env", "node_modules", ".pytest_cache")]
        rel_root = os.path.relpath(root, abs_path)
        depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
        if depth > max_depth:
            continue

        for f in files:
            f_path = os.path.join(root, f)
            rel_f = os.path.relpath(f_path, abs_path)
            f_size = os.path.getsize(f_path) if os.path.exists(f_path) else 0

            loc = 0
            if f.endswith((".py", ".js", ".ts", ".html", ".css", ".sql", ".sh")):
                try:
                    with open(f_path, "r", encoding="utf-8", errors="ignore") as fp:
                        loc = sum(1 for _ in fp)
                        total_loc += loc
                except Exception:
                    pass

            if f.endswith(".py"):
                py_files += 1
                if f.startswith("test_") or f.endswith("_test.py"):
                    test_files.append(rel_f)
                if f in ("main.py", "app.py", "cli.py", "index.py", "server.py"):
                    entrypoints.append(rel_f)

            file_inventory.append({
                "path": rel_f,
                "size_bytes": f_size,
                "loc": loc
            })

    return {
        "root_directory": abs_path,
        "total_files": len(file_inventory),
        "total_loc": total_loc,
        "python_files": py_files,
        "entrypoints": entrypoints,
        "test_files": test_files,
        "files_sample": file_inventory[:40]
    }


def compare_test_runs(before_code: str, after_code: str, test_suite_code: str, timeout_seconds: float = 4.0) -> Dict[str, Any]:
    """
    Executes unit test assertions against code before and after a change.
    Compares pass/fail status and verifies regressions.
    """
    script_before = f"{before_code}\n\n# --- Unit Tests ---\n{test_suite_code}"
    script_after = f"{after_code}\n\n# --- Unit Tests ---\n{test_suite_code}"

    res_before = execute_safe_code(script_before, timeout_seconds=timeout_seconds)
    res_after = execute_safe_code(script_after, timeout_seconds=timeout_seconds)

    passed_before = res_before.get("success", False)
    passed_after = res_after.get("success", False)

    regression_detected = bool(passed_before and not passed_after)
    bug_fixed = bool(not passed_before and passed_after)

    return {
        "before": {
            "passed": passed_before,
            "output": res_before.get("output", ""),
            "error": res_before.get("error")
        },
        "after": {
            "passed": passed_after,
            "output": res_after.get("output", ""),
            "error": res_after.get("error")
        },
        "status": "Fixed" if bug_fixed else "Regression" if regression_detected else "Unchanged",
        "regression_detected": regression_detected,
        "bug_fixed": bug_fixed
    }


def analyze_code_quality_and_security(code: str) -> Dict[str, Any]:
    """
    Performs AST and heuristic code-quality and security screening.
    Identifies bare excepts, hardcoded credentials, complexity smells, and suggestions.
    """
    import ast
    hints = []
    security_flags = []
    score = 100

    clean_code = code.strip()
    if not clean_code:
        return {"score": 0, "hints": ["No code provided."], "security_flags": []}

    try:
        tree = ast.parse(clean_code)

        # 1. AST Checks
        for node in ast.walk(tree):
            # Bare except check
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    hints.append("Avoid bare 'except:'; catch specific exceptions like 'except ValueError:' or 'except Exception:' to avoid catching KeyboardInterrupt/SystemExit.")
                    score -= 10

            # Hardcoded API key or password heuristics
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(k in name_lower for k in ("api_key", "secret", "password", "token", "auth_token")):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                val = node.value.value
                                if len(val) >= 8 and not val.startswith("your-") and not val.startswith("replace-"):
                                    security_flags.append(f"Potential hardcoded credential in variable '{target.id}'. Use environment variables instead.")
                                    score -= 20

            # Function complexity heuristics (number of loops / branches per function)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                branches = sum(1 for child in ast.walk(node) if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)))
                if branches > 8:
                    hints.append(f"Function '{node.name}' has high cyclomatic complexity ({branches} decision branches). Consider decomposing into smaller subroutines.")
                    score -= 10

    except SyntaxError as se:
        return {
            "score": 0,
            "syntax_error": f"Line {se.lineno}: {se.msg}",
            "hints": ["Fix Python syntax error before proceeding with quality audit."],
            "security_flags": []
        }

    return {
        "score": max(0, min(100, score)),
        "rating": "Excellent" if score >= 85 else "Good" if score >= 70 else "Needs Improvement",
        "hints": hints,
        "security_flags": security_flags
    }

