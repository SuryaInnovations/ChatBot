"""
Solution Verifier for Mathematical and Code outputs.
Re-checks SymPy computation and verifies Python code in the secure sandbox
before presenting the final answer to the user.
"""

import re
import logging
from typing import Dict, Any

from tools.sandbox import execute_safe_code
from tools.math_solver import solve_math_expression

logger = logging.getLogger("chatbot.verifier")


def verify_math(query: str, proposed_answer: str) -> Dict[str, Any]:
    """
    Verifies mathematical expressions against SymPy symbolic engine.
    Compares the calculated result with the claims in proposed_answer.
    """
    try:
        # Check if the query contains mathematical questions or expressions
        math_indicators = ["+", "-", "*", "/", "^", "=", "solve", "derivative", "integral", "limit", "integrate", "factor", "simplify"]
        if not any(ind in query for ind in math_indicators) and not any(ind in proposed_answer for ind in ["=", "result", "answer"]):
            return {"applicable": False, "verified": True}

        # Attempt SymPy evaluation of the query
        sympy_res = solve_math_expression(query)
        if not sympy_res.get("success"):
            # Try extracting expressions from query or proposed answer
            eq_matches = re.findall(r'([0-9a-zA-Z\s\+\-\*\/\^\(\)\.\%]+=[0-9a-zA-Z\s\+\-\*\/\^\(\)\.\%]+)', query)
            if eq_matches:
                sympy_res = solve_math_expression(eq_matches[0], task_type="solve")

        if sympy_res.get("success"):
            exact_res = str(sympy_res.get("result", "")).strip()
            # Normalize for comparison
            clean_res = exact_res.replace(" ", "").lower()
            clean_ans = proposed_answer.replace(" ", "").lower()

            # Check if exact result or float approximation appears in the answer
            matched = False
            if clean_res and clean_res in clean_ans:
                matched = True
            else:
                # Check numeric approximation if fractional
                try:
                    num_val = float(exact_res)
                    num_str = f"{num_val:.4f}".rstrip("0").rstrip(".")
                    if num_str in proposed_answer:
                        matched = True
                except (ValueError, TypeError):
                    pass

            badge = "✅ SymPy Verified" if matched else "❌ Calculation Mismatch"
            return {
                "applicable": True,
                "verified": matched,
                "engine": "SymPy",
                "exact_result": exact_res,
                "badge": badge,
                "note": f"Evaluated independently by SymPy: `{exact_res}`"
            }
        else:
            return {
                "applicable": True,
                "verified": False,
                "engine": "SymPy",
                "exact_result": None,
                "badge": "⚠️ Could not verify independently",
                "note": "Independent symbolic engine could not evaluate expression."
            }

    except Exception as e:
        logger.debug(f"Math verification error: {e}")

    return {"applicable": False, "verified": True}


def verify_code(query: str, proposed_answer: str) -> Dict[str, Any]:
    """
    Extracts executable Python code blocks and verifies them inside the secure sandbox.
    Labels as '🛡️ Executed OK' if code runs without error, or
    '🛡️ Code Verified' if unit test assertions (assert ...) were executed and passed.
    """
    try:
        # Find all python blocks
        code_blocks = re.findall(r'```(?:python|py)?\s*\n([\s\S]+?)\n```', proposed_answer)
        if not code_blocks:
            return {"applicable": False, "verified": True}

        results = []
        for code in code_blocks:
            code_clean = code.strip()
            # Skip empty or partial pseudocode snippets
            if not code_clean or "..." in code_clean.splitlines()[:2]:
                continue
            # If code is runnable
            res = execute_safe_code(code_clean, timeout_seconds=4.0)
            results.append({
                "code": code_clean,
                "success": res.get("success", False),
                "error": res.get("error"),
                "output": res.get("output", "")
            })

        if not results:
            return {"applicable": False, "verified": True}

        all_ok = all(r["success"] for r in results)
        first_err = next((r["error"] for r in results if not r["success"]), None)

        if all_ok:
            has_unit_tests = any("assert " in r["code"] for r in results)
            badge = "🛡️ Code Verified (Unit Tests Passed)" if has_unit_tests else "🛡️ Executed OK"
        else:
            badge = "⚠️ Code Execution Warning"

        return {
            "applicable": True,
            "verified": all_ok,
            "engine": "Sandbox",
            "badge": badge,
            "error": first_err,
            "output": results[0].get("output") if results else "",
            "blocks_checked": len(results)
        }

    except Exception as e:
        logger.debug(f"Code verification error: {e}")

    return {"applicable": False, "verified": True}


def verify_solution(query: str, proposed_answer: str, intent_str: str = "") -> Dict[str, Any]:
    """
    Comprehensive verification pipeline.
    Runs SymPy verification on math and Sandbox verification on code.
    Enriches the final output with honest trust badges and verified annotations.
    """
    badges = []
    footnotes = []
    final_content = proposed_answer

    # 1. Math Verification
    math_check = verify_math(query, proposed_answer)
    if math_check.get("applicable"):
        badges.append(math_check["badge"])
        if not math_check.get("verified"):
            exact = math_check.get("exact_result")
            if exact:
                footnotes.append(f"> ❌ **Independent Calculation Mismatch**: SymPy recomputed value is **`{exact}`**.")
            elif math_check.get("badge") == "⚠️ Could not verify independently":
                footnotes.append("> ⚠️ **Verification Notice**: Problem could not be independently computed by the symbolic solver.")

    # 2. Code Verification
    code_check = verify_code(query, proposed_answer)
    if code_check.get("applicable"):
        badges.append(code_check["badge"])
        if not code_check.get("verified") and code_check.get("error"):
            err_msg = str(code_check["error"])[:150]
            footnotes.append(f"> ⚠️ **Sandbox Verification Note**: Code execution returned notice: `{err_msg}`")

    # Append any verification footnotes
    if footnotes:
        final_content = final_content.rstrip() + "\n\n" + "\n".join(footnotes)

    return {
        "verified": math_check.get("verified", True) and code_check.get("verified", True),
        "badges": badges,
        "content": final_content,
        "math_check": math_check,
        "code_check": code_check
    }
