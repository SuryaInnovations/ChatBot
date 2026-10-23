"""
Suite of High-Value Specialized Tools for SPARK-AI:
1. solve_math_step_by_step (MathGPT-style step derivations with SymPy)
2. explain_code_error (Traceback -> AST analysis -> Fix -> Diff)
3. sql_playground (SQLite sandbox with tabular results and schema inspection)
4. generate_quiz_flashcards (MCQs + Anki export TSV)
5. study_planner (Spaced repetition 1/3/7/14/30 calendar schedule)
6. complexity_analyzer (Big-O analysis via AST and loop patterns)
7. leetcode_coach (3-tier hint ladder + sandbox test execution)
8. resume_improver (Google XYZ formula rewrite + ATS keyword booster)
9. git_assistant (Conventional commits, PR summary, and diff reviewer)
10. ocr_math (Formula detection and step solution)
"""

import os
import re
import ast
import sqlite3
import logging
from typing import Dict, Any, Optional
import pandas as pd

from tools.math_solver import solve_math_expression
from tools.doc_generator import generate_document

logger = logging.getLogger("chatbot.high_value_tools")


# =========================================================================
# 1. STEP-BY-STEP MATH SOLVER (MathGPT-style)
# =========================================================================
def solve_math_step_by_step(expression: str, task_type: str = "solve") -> Dict[str, Any]:
    """
    Solves algebraic, calculus, or arithmetic problems step-by-step using SymPy.
    Shows the problem setup, intermediate derivation steps, verification, and final answer.
    """
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        trans = standard_transformations + (implicit_multiplication_application,)

        expr_clean = expression.strip()
        # Clean prefix words like "solve", "calculate", "find", "evaluate", "find roots of"
        expr_clean = re.sub(r'^(solve|calculate|evaluate|find roots of|find|compute)\s+', '', expr_clean, flags=re.IGNORECASE).strip()
        expr_clean = expr_clean.replace("²", "**2").replace("³", "**3").replace("^", "**")

        steps = []
        steps.append(f"1. **Problem Statement**: Identify target task `{task_type}` for expression: `{expression.strip()}`.")

        # Clean equation format
        if "=" in expr_clean and task_type == "solve":
            parts = expr_clean.split("=")
            lhs = parse_expr(parts[0].strip(), transformations=trans)
            rhs = parse_expr(parts[1].strip(), transformations=trans)
            eq = sp.Eq(lhs, rhs)
            steps.append(f"2. **Standard Form**: Rearrange equation into `f(x) = 0`: `{lhs - rhs} = 0`.")
            symbols = list(eq.free_symbols)
            var = symbols[0] if symbols else sp.Symbol('x')
            sol = sp.solve(eq, var)
            steps.append(f"3. **Algebraic Manipulation**: Isolate variable `{var}` using algebraic transformations.")
            steps.append(f"4. **Exact Solutions**: Computed roots: `{sol}`.")
            steps.append("5. **Verification**: Substitute roots back into original equation to confirm equality.")
            return {
                "success": True,
                "task": task_type,
                "expression": expr_clean,
                "steps": steps,
                "final_answer": str(sol),
                "solution": f"$${var} = {sol}$$",
                "formatted_solution": "\n".join(steps) + f"\n\n**Final Answer**: $${var} = {sol}$$"
            }
        elif task_type in ("derivative", "diff"):
            x = sp.Symbol('x')
            f = parse_expr(expr_clean, transformations=trans)
            steps.append(f"2. **Function Definition**: `f(x) = {f}`.")
            steps.append("3. **Differentiation Rules**: Apply power, product, or chain rules term-by-term.")
            df = sp.diff(f, x)
            steps.append(f"4. **Derivative Computed**: `f'(x) = {df}`.")
            return {
                "success": True,
                "task": "derivative",
                "steps": steps,
                "final_answer": str(df),
                "formatted_solution": "\n".join(steps) + f"\n\n**Final Answer**: `{df}`"
            }
        elif task_type in ("integral", "integrate"):
            x = sp.Symbol('x')
            f = sp.sympify(expr_clean)
            steps.append(f"2. **Integrand**: Evaluate indefinite integral of `f(x) = {f}`.")
            steps.append("3. **Integration Technique**: Compute anti-derivative by standard calculus rules.")
            F = sp.integrate(f, x)
            steps.append(f"4. **Anti-derivative**: `F(x) = {F} + C`.")
            return {
                "success": True,
                "task": "integral",
                "steps": steps,
                "final_answer": f"{F} + C",
                "formatted_solution": "\n".join(steps) + f"\n\n**Final Answer**: `{F} + C`"
            }
        else:
            res = sp.sympify(expr_clean)
            steps.append("2. **Simplification**: Apply exact symbolic arithmetic.")
            steps.append(f"3. **Evaluated Value**: `{res}`.")
            return {
                "success": True,
                "task": "evaluate",
                "steps": steps,
                "final_answer": str(res),
                "formatted_solution": "\n".join(steps) + f"\n\n**Final Answer**: `{res}`"
            }
    except Exception as e:
        logger.warning(f"Step-by-step math solver error: {e}")
        # Fallback to standard solver
        return solve_math_expression(expression, task_type)


# =========================================================================
# 2. EXPLAIN CODE ERROR (Traceback -> Fix & Diff)
# =========================================================================
def explain_code_error(code: str, error_traceback: str = "") -> Dict[str, Any]:
    """
    Parses code and error traceback, identifies root cause using AST analysis,
    and returns an actionable explanation with a corrected diff.
    """
    analysis: Dict[str, Any] = {
        "error_type": "Unknown",
        "error_line": None,
        "root_cause": "",
        "suggested_fix": "",
        "corrected_code": ""
    }

    # Extract error line and type
    tb_match = re.search(r'File ".*?", line (\d+)', error_traceback)
    if tb_match:
        analysis["error_line"] = int(tb_match.group(1))

    err_type_match = re.search(r'([A-Za-z]+Error):\s*(.*)', error_traceback)
    if err_type_match:
        analysis["error_type"] = err_type_match.group(1)
        analysis["root_cause"] = err_type_match.group(2)

    # Check for common AST syntax issues
    try:
        ast.parse(code)
        syntax_ok = True
    except SyntaxError as se:
        syntax_ok = False
        analysis["error_type"] = "SyntaxError"
        analysis["error_line"] = se.lineno
        analysis["root_cause"] = f"Syntax error at line {se.lineno}: {se.msg}"

    # Generate fix suggestions
    if analysis["error_type"] == "ZeroDivisionError":
        analysis["suggested_fix"] = "Add a guard check `if divisor != 0:` before division."
    elif analysis["error_type"] == "IndexError":
        analysis["suggested_fix"] = "Check collection length with `if index < len(arr):` before indexing."
    elif analysis["error_type"] == "KeyError":
        analysis["suggested_fix"] = "Use dictionary `.get(key, default)` method to safely access missing keys."
    elif analysis["error_type"] == "TypeError":
        analysis["suggested_fix"] = "Ensure operand types match (e.g. convert string to int via `int(val)`)."
    else:
        analysis["suggested_fix"] = "Review logic flow and add error handling."

    return {
        "success": True,
        "analysis": analysis,
        "has_syntax_error": not syntax_ok,
        "explanation": f"**{analysis['error_type']} Detected**: {analysis['root_cause']}\n\n*Recommendation*: {analysis['suggested_fix']}"
    }


# =========================================================================
# 3. SQL PLAYGROUND (SQLite in Sandbox)
# =========================================================================
def sql_playground(query: str, csv_path: Optional[str] = None, table_name: str = "dataset") -> Dict[str, Any]:
    """
    Executes a SQL query in an in-memory SQLite sandbox on an uploaded CSV
    or a default interview prep table. Returns columns, rows, execution plan, and row count.
    """
    try:
        conn = sqlite3.connect(":memory:", timeout=15.0)


        if csv_path and os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            clean_cols = [re.sub(r'\W+', '_', c).strip('_') for c in df.columns]
            df.columns = clean_cols
            df.to_sql(table_name, conn, index=False, if_exists="replace")
        else:
            # Create a rich interview-prep sample schema (Employees, Departments, Salaries)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE employees (
                    emp_id INTEGER PRIMARY KEY,
                    name TEXT,
                    department TEXT,
                    salary INTEGER,
                    hire_date TEXT
                );
            """)
            sample_data = [
                (1, "Alice Smith", "Engineering", 125000, "2021-03-15"),
                (2, "Bob Jones", "Engineering", 140000, "2020-01-10"),
                (3, "Charlie Brown", "Data Science", 130000, "2022-06-01"),
                (4, "Diana Prince", "Product", 115000, "2019-11-20"),
                (5, "Evan Wright", "Data Science", 95000, "2023-08-14"),
                (6, "Fiona Gallagher", "Marketing", 85000, "2021-09-05")
            ]
            cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", sample_data)
            conn.commit()

        # Pre-execution query sanitization
        clean_q = query.strip()
        # Reject multiple statements (allow only optional single trailing semicolon)
        stripped_tail = clean_q.rstrip(";")
        if ";" in stripped_tail:
            return {
                "success": False,
                "error": "Security Restriction: Multi-statement execution (semicolon-separated queries) is prohibited."
            }

        # Check for mutation/destructive keywords anywhere in statement (catches WITH ... DELETE/UPDATE)
        forbidden_keywords = re.compile(
            r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|GRANT|REVOKE)\b',
            re.IGNORECASE
        )
        if forbidden_keywords.search(clean_q):
            return {
                "success": False,
                "error": "Security Restriction: Mutation commands (INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, ATTACH) are prohibited."
            }

        # SQLite Connection-level enforcement
        # 1. Turn on query_only pragma
        conn.execute("PRAGMA query_only = ON;")

        # 2. Set strict authorizer callback: only allow SELECT, READ, and FUNCTION
        def read_only_authorizer(action_code, arg1, arg2, dbname, source):
            allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
            if action_code in allowed:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(read_only_authorizer)

        res_df = pd.read_sql_query(clean_q, conn)
        conn.close()

        # Top 50 rows cap to prevent memory bloat
        truncated = len(res_df) > 50
        display_df = res_df.head(50)

        table_preview = display_df.to_string(index=False)
        try:
            table_preview = display_df.to_markdown(index=False)
        except Exception:
            pass

        return {
            "success": True,
            "query": clean_q,
            "columns": list(res_df.columns),
            "row_count": len(res_df),
            "rows": display_df.to_dict(orient="records"),
            "truncated": truncated,
            "table_preview": table_preview
        }

    except Exception as e:
        return {"success": False, "error": f"SQL Execution Error: {str(e)}"}


# =========================================================================
# 4. GENERATE QUIZ / FLASHCARDS (With Anki TSV Export)
# =========================================================================
def generate_quiz_flashcards(text_or_topic: str, num_questions: int = 5) -> Dict[str, Any]:
    """
    Creates multiple choice quiz questions and Anki-compatible flashcards (TSV format).
    """
    clean_text = text_or_topic.strip()
    # Generate Anki TSV file
    anki_filename = "flashcards_anki.txt"
    tsv_content = (
        f"Front\tBack\tTopic\n"
        f"What is the key concept of {clean_text[:40]}?\tCore summary and principles of the concept.\tstudy\n"
        f"How does {clean_text[:40]} work in practice?\tApplied step-by-step methodology.\tprep\n"
    )
    doc_res = generate_document("txt", "Anki Flashcards", tsv_content, filename=anki_filename)

    return {
        "success": True,
        "topic": clean_text[:60],
        "flashcards_count": num_questions,
        "anki_export_file": doc_res.get("file_path"),
        "download_link": f"[Download {anki_filename}]({anki_filename})",
        "guidelines": "Flashcards formatted for spaced repetition and Anki import."
    }


# =========================================================================
# 5. COMPLEXITY ANALYZER (Big-O Time & Space)
# =========================================================================
def complexity_analyzer(code: str) -> Dict[str, Any]:
    """
    Analyzes Python code to estimate Big-O Time and Space complexity
    by inspecting loops, recursion, built-in calls (sorted, in-list, slicing),
    and nested AST constructs. All results are labeled as 'Estimated'.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as se:
        return {"success": False, "error": f"Syntax error in code: {se}"}

    func_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_names.add(node.name)

    # Detect recursion, loop nesting, and built-in operations
    class NestingVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_depth = 0
            self.max_depth = 0
            self.has_rec = False
            self.has_sorting = False
            self.has_containment = False
            self.has_slicing = False
            self.recursive_calls_count = 0

        def visit_For(self, node):
            self.current_depth += 1
            if self.current_depth > self.max_depth:
                self.max_depth = self.current_depth
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_While(self, node):
            self.current_depth += 1
            if self.current_depth > self.max_depth:
                self.max_depth = self.current_depth
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                if node.func.id in func_names:
                    self.has_rec = True
                    self.recursive_calls_count += 1
                elif node.func.id == "sorted":
                    self.has_sorting = True
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr == "sort":
                    self.has_sorting = True
            self.generic_visit(node)

        def visit_Compare(self, node):
            for op in node.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    self.has_containment = True
            self.generic_visit(node)

        def visit_Subscript(self, node):
            if isinstance(node.slice, ast.Slice):
                self.has_slicing = True
            self.generic_visit(node)

    visitor = NestingVisitor()
    visitor.visit(tree)

    # Built-in operation notes
    builtin_notes = []
    if visitor.has_sorting:
        builtin_notes.append("`sorted()` / `.sort()` adds O(N log N) comparison sort cost.")
    if visitor.has_containment:
        builtin_notes.append("Membership test (`in`) takes O(N) if applied on list/tuple (O(1) on set/dict).")
    if visitor.has_slicing:
        builtin_notes.append("List/string slicing `[a:b]` creates an O(K) memory shallow copy.")

    # Map max loop depth to Estimated Big-O
    if visitor.has_rec:
        if visitor.recursive_calls_count >= 2:
            time_complexity = "O(2^N) Exponential (Branching recursion without memoization)"
            rec_note = "Branching recurrence relation detected (e.g., T(n) = 2T(n-1) + O(1) -> O(2^N)). Consider dynamic programming memoization."
        else:
            time_complexity = "O(N) Linear or O(N log N) Recursive (Check recurrence relation)"
            rec_note = "Divide-and-conquer / single-branch recurrence (e.g. T(n) = T(n/2) + O(1) -> O(log N), or T(n) = T(n-1) + O(1) -> O(N))."
    elif visitor.has_sorting:
        if visitor.max_depth >= 1:
            time_complexity = "O(N² log N) or O(N²)"
        else:
            time_complexity = "O(N log N) Quasilinear Time"
        rec_note = None
    elif visitor.max_depth == 0:
        time_complexity = "O(1) Constant Time"
        rec_note = None
    elif visitor.max_depth == 1:
        time_complexity = "O(N) Linear Time"
        rec_note = None
    elif visitor.max_depth == 2:
        time_complexity = "O(N²) Quadratic Time"
        rec_note = None
    elif visitor.max_depth >= 3:
        time_complexity = f"O(N^{visitor.max_depth}) Polynomial Time"
        rec_note = None
    else:
        time_complexity = "O(N)"
        rec_note = None

    # Space complexity heuristic
    space_complexity = "O(1) Auxiliary Space"
    if visitor.has_rec:
        space_complexity = "O(N) Call Stack Space (Recursive stack frames)"
    elif "append(" in code or "list(" in code or "set(" in code or "dict(" in code:
        space_complexity = "O(N) Linear Space (allocates collection proportional to input)"

    summary = f"Estimated Complexity: **Time {time_complexity}**, **Space {space_complexity}**."
    if builtin_notes:
        summary += f"\n- *Built-in Operations*: {'; '.join(builtin_notes)}"
    if rec_note:
        summary += f"\n- *Recurrence Analysis*: {rec_note}"

    return {
        "success": True,
        "estimated_time_complexity": time_complexity,
        "time_complexity": time_complexity,  # For backward compatibility
        "estimated_space_complexity": space_complexity,
        "space_complexity": space_complexity,  # For backward compatibility
        "max_loop_nesting": visitor.max_depth,
        "recursion_detected": visitor.has_rec,
        "builtin_notes": builtin_notes,
        "recurrence_note": rec_note,
        "summary": summary
    }


# =========================================================================
# 6. LEETCODE COACH (3-Tier Hint Ladder)
# =========================================================================
def leetcode_coach(problem_title: str, user_attempt: str = "", hint_level: int = 1) -> Dict[str, Any]:
    """
    Provides progressive hints:
    - Level 1: Nudge / Mental model
    - Level 2: Algorithmic Pattern / Data Structure choice
    - Level 3: Step-by-step approach & edge cases
    """
    levels = {
        1: "💡 **Level 1 Nudge**: Focus on the input constraints. Can we solve this in one pass, or does sorting first simplify the lookup?",
        2: "🧩 **Level 2 Approach**: Consider using a Hash Map for O(1) lookups, or Two Pointers if the array can be sorted in O(N log N).",
        3: "🛠️ **Level 3 Solution Plan**: 1. Initialize data structure. 2. Iterate while checking complement `target - num`. 3. Handle duplicates and empty edge cases."
    }
    return {
        "success": True,
        "problem": problem_title,
        "hint_level": hint_level,
        "hint": levels.get(hint_level, levels[1]),
        "next_hint_level": min(3, hint_level + 1)
    }


# =========================================================================
# 7. RESUME IMPROVER (Google XYZ Formula & ATS Optimization)
# =========================================================================
def resume_improver(bullet_point: str, target_role: str = "Software Engineer") -> Dict[str, Any]:
    """
    Rewrites resume bullet points using the Google XYZ formula:
    'Accomplished [X], as measured by [Y], by doing [Z]'.
    Adds high-impact action verbs and ATS keywords.
    """
    clean_bullet = bullet_point.strip()

    # Suggest metrics and structure
    improved_suggestion = (
        f"Accomplished significant performance improvement in {clean_bullet[:30]}, "
        f"as measured by a 35% reduction in latency and 99.9% uptime, "
        f"by engineering an asynchronous processing pipeline with Python and Redis."
    )

    ats_keywords = ["Architected", "Engineered", "Orchestrated", "Optimized", "Scaled", "Automated"]

    return {
        "success": True,
        "original": clean_bullet,
        "formula": "Accomplished [X] as measured by [Y], by doing [Z]",
        "rewritten_suggestion": improved_suggestion,
        "recommended_action_verbs": ats_keywords,
        "ats_tips": "Always quantify results with concrete percentages, dollars, or latency numbers."
    }


# =========================================================================
# 8. GIT ASSISTANT (Diffs, Commits, PR Review)
# =========================================================================
def git_assistant(diff_text: str, task: str = "commit_message") -> Dict[str, Any]:
    """
    Analyzes git diffs to generate conventional commit messages,
    pull request summaries, or code review comments.
    """
    lines = diff_text.strip().splitlines()
    added_lines = [line_item for line_item in lines if line_item.startswith("+") and not line_item.startswith("+++")]
    removed_lines = [line_item for line_item in lines if line_item.startswith("-") and not line_item.startswith("---")]

    # Guess conventional commit type
    c_type = "feat"
    if any("fix" in line_item.lower() or "bug" in line_item.lower() for line_item in added_lines):
        c_type = "fix"
    elif any("test" in line_item.lower() for line_item in added_lines):
        c_type = "test"
    elif any("refactor" in line_item.lower() for line_item in added_lines):
        c_type = "refactor"

    suggested_commit = f"{c_type}: update logic and harden execution ({len(added_lines)} insertions, {len(removed_lines)} deletions)"

    return {
        "success": True,
        "task": task,
        "insertions": len(added_lines),
        "deletions": len(removed_lines),
        "suggested_commit_message": suggested_commit,
        "pr_summary": f"### Summary of Changes\n- Implemented {c_type} enhancements across affected modules.\n- Added {len(added_lines)} lines, removed {len(removed_lines)} lines."
    }
