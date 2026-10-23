"""
Comprehensive Unit Tests for High-Value Reliability, Tools, and Interview Features.
Covers:
- Verifier (Math with SymPy & Code in Sandbox)
- Step-by-Step Math Solver
- AST Error Explainer
- SQL Playground
- Big-O Complexity Analyzer
- LeetCode Hint Ladder
- Resume Improver (XYZ Formula)
- Git Assistant
- Semantic RAG and Citations
- SQLite Long-Term Memory
- Interview Question Bank and 4-Dimension Rubric
- Pydantic Tool Schemas
- Response Cache
"""

import os
import unittest
import tempfile

from core.verifier import verify_math, verify_code
from tools.high_value_tools import (
    solve_math_step_by_step,
    explain_code_error,
    sql_playground,
    complexity_analyzer,
    leetcode_coach,
    resume_improver,
    git_assistant
)
from tools.rag import SemanticRAGIndex
from core.memory import get_user_memory, update_user_memory, record_topic_score
from core.interview_bank import get_questions_by_category
from core.interview import InterviewSession
from core.cache import get_cached_response, store_cached_response, clear_cache
from tools.schemas import validate_tool_arguments


class TestHighValueFeatures(unittest.TestCase):

    def test_01_verify_math_with_sympy(self):
        """Verifier correctly verifies valid mathematical statements with SymPy."""
        res = verify_math("2*x + 5 = 15", "The solution to 2*x + 5 = 15 is x = 5.")
        self.assertTrue(res["applicable"])
        self.assertTrue(res["verified"])
        self.assertIn("5", res["exact_result"])
        self.assertEqual(res["badge"], "✅ SymPy Verified")

    def test_02_verify_code_in_sandbox(self):
        """Verifier tests valid Python snippet in sandbox without error and with unit tests."""
        code_answer = "Here is the code:\n```python\na = [1, 2, 3]\nb = sum(a)\nprint(b)\n```"
        res = verify_code("sum of list", code_answer)
        self.assertTrue(res["applicable"])
        self.assertTrue(res["verified"])
        self.assertEqual(res["badge"], "🛡️ Executed OK")

        # Code with unit test assertions
        assert_answer = "```python\ndef add(a, b): return a + b\nassert add(2, 3) == 5\n```"
        res_test = verify_code("test adder", assert_answer)
        self.assertEqual(res_test["badge"], "🛡️ Code Verified (Unit Tests Passed)")

    def test_03_verify_code_catches_runtime_error(self):
        """Verifier catches division by zero or runtime error."""
        bad_code = "```python\nx = 1 / 0\n```"
        res = verify_code("divide", bad_code)
        self.assertTrue(res["applicable"])
        self.assertFalse(res["verified"])
        self.assertIn("ZeroDivisionError", str(res["error"]))

    def test_04_solve_math_step_by_step(self):
        """Step-by-step math solver returns problem setup, derivations, and roots."""
        res = solve_math_step_by_step("x**2 - 9 = 0")
        self.assertTrue(res["success"])
        self.assertTrue(len(res["steps"]) >= 4)
        self.assertIn("-3, 3", res["final_answer"])

    def test_05_explain_code_error(self):
        """AST debugger parses traceback and identifies error line and fix."""
        code = "def calc():\n    return 10 / 0\ncalc()"
        tb = 'File "test.py", line 2, in calc\n    return 10 / 0\nZeroDivisionError: division by zero'
        res = explain_code_error(code, tb)
        self.assertTrue(res["success"])
        self.assertEqual(res["analysis"]["error_type"], "ZeroDivisionError")
        self.assertIn("guard check", res["analysis"]["suggested_fix"].lower())

    def test_06_sql_playground_execution(self):
        """SQL playground executes read-only query on sample schema."""
        res = sql_playground("SELECT name, department, salary FROM employees WHERE salary > 100000 ORDER BY salary DESC")
        self.assertTrue(res["success"])
        self.assertTrue(res["row_count"] >= 3)
        self.assertIn("Bob Jones", str(res["rows"]))

    def test_07_sql_playground_security_blocks_mutation(self):
        """SQL playground strictly blocks DROP / DELETE / INSERT statements."""
        res = sql_playground("DROP TABLE employees")
        self.assertFalse(res["success"])
        self.assertIn("Security Restriction", res["error"])

    def test_08_complexity_analyzer(self):
        """Complexity analyzer identifies O(N^2) quadratic time from nested loops."""
        code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
"""
        res = complexity_analyzer(code)
        self.assertTrue(res["success"])
        self.assertIn("O(N²)", res["time_complexity"])
        self.assertEqual(res["max_loop_nesting"], 2)

    def test_09_leetcode_coach(self):
        """LeetCode coach provides progressive hints 1, 2, and 3."""
        h1 = leetcode_coach("Two Sum", hint_level=1)
        self.assertIn("Level 1 Nudge", h1["hint"])
        h2 = leetcode_coach("Two Sum", hint_level=2)
        self.assertIn("Level 2 Approach", h2["hint"])
        h3 = leetcode_coach("Two Sum", hint_level=3)
        self.assertIn("Level 3 Solution Plan", h3["hint"])

    def test_10_resume_improver_xyz_formula(self):
        """Resume improver formats bullets using Google XYZ formula."""
        res = resume_improver("worked on optimizing database queries", target_role="Data Engineer")
        self.assertTrue(res["success"])
        self.assertIn("Accomplished", res["rewritten_suggestion"])
        self.assertIn("as measured by", res["rewritten_suggestion"])
        self.assertIn("by engineering", res["rewritten_suggestion"])
        self.assertIn("by doing", res["formula"])

    def test_11_git_assistant_diff_parser(self):
        """Git assistant produces conventional commit messages from git diff."""
        diff = "--- a/app.py\n+++ b/app.py\n@@ -1 +1,2 @@\n+def fix_bug():\n+    return True\n"
        res = git_assistant(diff)
        self.assertTrue(res["success"])
        self.assertIn("fix:", res["suggested_commit_message"])
        self.assertEqual(res["insertions"], 2)

    def test_12_semantic_rag_index(self):
        """Semantic RAG chunks documents and returns top hits with page citations."""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("Artificial intelligence and deep learning transformers have revolutionized natural language processing.\n\n"
                    "Database systems use B-trees and write-ahead logging to guarantee ACID compliance.")
            temp_path = f.name

        try:
            rag = SemanticRAGIndex()
            rag.add_file(temp_path, "tech_notes.txt")
            hits = rag.search("transformers and deep learning", top_k=1)
            self.assertTrue(len(hits) > 0)
            self.assertEqual(hits[0]["file_name"], "tech_notes.txt")
            self.assertIn("Page 1", hits[0]["citation"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_13_user_memory_sqlite_persistence(self):
        """User memory persists level, goals, and tracks weak topics."""
        uid = "test_user_42"
        update_user_memory(uid, {
            "user_level": "Undergraduate",
            "target_role": "Backend Engineer",
            "goals": ["Master FAANG DSA"]
        })
        mem = get_user_memory(uid)
        self.assertEqual(mem["target_role"], "Backend Engineer")
        self.assertIn("Master FAANG DSA", mem["goals"])

        # Record a low score on dynamic programming -> adds to weak_topics
        record_topic_score(uid, "Dynamic Programming", 5.0, "Missed memoization table")
        mem_updated = get_user_memory(uid)
        self.assertIn("Dynamic Programming", mem_updated["weak_topics"])

    def test_14_interview_bank_and_session(self):
        """Interview question bank and 4-dimension scoring rubric prompt."""
        dsa_qs = get_questions_by_category("DSA")
        self.assertTrue(len(dsa_qs) >= 2)

        session = InterviewSession(role="Software Engineer", category="DSA", company="Google")
        start_p = session.start_prompt()
        self.assertIn("Question 1", start_p)
        self.assertIn("Google", start_p)

        eval_p = session.evaluate_and_next_prompt("I would use a two-pointer sliding window with a hash set.")
        self.assertIn("Scoring Rubric", eval_p)
        self.assertIn("Correctness (/10)", eval_p)
        self.assertIn("Clarity (/10)", eval_p)
        self.assertIn("Structure (/10)", eval_p)
        self.assertIn("Depth (/10)", eval_p)
        self.assertIn("Ideal Model Answer", eval_p)

    def test_15_response_cache(self):
        """Response cache returns cached payload and avoids redundant compute."""
        clear_cache()
        prompt = "Explain quantum computing briefly"
        resp_mock = {"success": True, "content": "Quantum computing uses qubits."}
        store_cached_response(prompt, resp_mock)

        hit = get_cached_response(prompt)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["content"], "Quantum computing uses qubits.")

    def test_16_pydantic_tool_validation(self):
        """Pydantic schemas validate good arguments and cleanly reject malformed ones."""
        valid, args, err = validate_tool_arguments("solve_math", {"expression": "integrate(x**2, x)"})
        self.assertTrue(valid)
        self.assertIsNone(err)

        # Invalid arguments (missing required expression)
        valid_bad, _, err_bad = validate_tool_arguments("solve_math", {})
        self.assertFalse(valid_bad)
        self.assertIn("expression", err_bad)


if __name__ == "__main__":
    unittest.main()
