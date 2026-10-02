"""
Deterministic local solver module.
Used when LLM providers are unavailable or when exact local execution
(math, code debugging, file analysis, verified definitions) is sufficient.
Strictly avoids artificial warning banners and has NO dependencies on core.
"""

import re
import ast
from typing import Dict, Any, Optional

from tools.math_solver import solve_math_expression, calculate_finance
from tools.code_executor import execute_python_code
from tools.file_analyzer import analyze_file
from tools.web_search import search_web

# Foundational domain definitions for offline verified fallback
FOUNDATIONAL_KNOWLEDGE = {
    "physics": (
        "Physics is the branch of science that studies matter, energy, motion, forces, space, and time, and how they interact.\n\n"
        "For example, physics explains why objects fall, how electricity flows, how light travels, and how planets move.\n\n"
        "Major areas include mechanics, thermodynamics, electromagnetism, optics, quantum physics, and relativity."
    ),
    "chemistry": (
        "Chemistry is the scientific discipline that studies the composition, structure, properties, and reactions of matter.\n\n"
        "It investigates how atoms combine to form molecules, chemical bonds, and the transformations substances undergo during chemical reactions.\n\n"
        "Key branches include organic, inorganic, physical, analytical, and biochemistry."
    ),
    "biology": (
        "Biology is the natural science that studies life and living organisms, including their structure, function, growth, evolution, and interactions with ecosystems.\n\n"
        "Key areas include cellular biology, genetics, ecology, physiology, and evolutionary biology."
    ),
    "recursion": (
        "Recursion is a programming and mathematical technique where a function calls itself directly or indirectly to solve a problem.\n\n"
        "A valid recursive function always consists of:\n"
        "1. **Base Case**: The termination condition that stops recursion without making further calls.\n"
        "2. **Recursive Case**: The logic that reduces the problem towards the base case."
    ),
    "gravity": (
        "Gravity is a fundamental natural phenomenon by which all things with mass or energy are attracted to one another.\n\n"
        "In classical mechanics (Newton's law), gravity is described as an attractive force proportional to mass and inversely proportional to the square of the distance. In general relativity (Einstein), gravity is the curvature of spacetime caused by mass and energy."
    )
}

def can_deterministic_tool_answer(intent_val: Any, query: str, attached_files: Optional[list] = None) -> bool:
    """
    Checks if a query can be answered accurately by local deterministic tools without an LLM.
    intent_val can be an IntentType enum or string.
    """
    intent_str = intent_val.value if hasattr(intent_val, "value") else str(intent_val).lower()
    q_lower = query.strip().lower()

    if "math" in intent_str:
        return True

    if "data" in intent_str or ("program" in intent_str and ("```" in query or "for " in query or "def " in query or "syntax error" in q_lower or "debug" in q_lower)):
        return True

    if "document" in intent_str and attached_files and len(attached_files) > 0:
        return True

    if "current" in intent_str:
        return True

    # Check foundational definitions
    for term in FOUNDATIONAL_KNOWLEDGE:
        if term in q_lower and any(kw in q_lower for kw in ["what is", "define", "explain", "meaning of"]):
            return True

    return False

def solve_deterministically(intent_val: Any, query: str, attached_files: Optional[list] = None) -> Optional[Dict[str, Any]]:
    """
    Executes the appropriate local deterministic tool and formats a clean response.
    """
    intent_str = intent_val.value if hasattr(intent_val, "value") else str(intent_val).lower()
    q_lower = query.strip().lower()

    # 1. Math / Financial Calculation
    if "math" in intent_str:
        # Check financial interest
        if any(term in q_lower for term in ["compound interest", "simple interest", "emi", "interest for"]):
            p_match = re.search(r'(?:₹|\$|rs\.?|principal\s*of)?\s*(\d[\d,]*(?:\.\d+)?)', query, re.I)
            r_match = re.search(r'(\d+(?:\.\d+)?)\s*%', query)
            t_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|months?)', query, re.I)

            p = float(p_match.group(1).replace(",", "")) if p_match else 10000.0
            r = float(r_match.group(1)) if r_match else 8.0
            t = float(t_match.group(1)) if t_match else 3.0
            calc_type = "emi" if "emi" in q_lower else ("simple" if "simple" in q_lower else "compound")

            res = calculate_finance(calc_type, p, r, t)
            amt = res.get("total_amount", 0)
            interest = res.get("total_interest", 0)
            formula = res.get("formula", "")

            content = (
                f"**Formula:**\n`{formula}`\n\n"
                f"**Substitution:**\n"
                f"- Principal: ₹{p:,.2f}\n"
                f"- Rate: {r}%\n"
                f"- Time: {t} years\n\n"
                f"**Calculation:**\n"
                f"- Accrued Amount: ₹{amt:,.2f}\n"
                f"- Interest: ₹{interest:,.2f}\n\n"
                f"**Final Answer:**\n"
                f"The total amount after {t} years is **₹{amt:,.2f}** (interest: **₹{interest:,.2f}**)."
            )
            return {"content": content, "tool": "calculate_finance", "result": res}

        # Symbolic / Arithmetic Math (e.g., "2 + 5 * 10", "solve x^2 - 5x + 6 = 0")
        task_type = "derivative" if "derivative" in q_lower else ("integral" if "integral" in q_lower else ("solve_equation" if "=" in query else "eval"))
        clean_expr = query
        for prefix in ["solve", "calculate", "find", "evaluate", "what is"]:
            if clean_expr.lower().startswith(prefix):
                clean_expr = clean_expr[len(prefix):].strip()

        res = solve_math_expression(clean_expr, task_type)
        if res.get("success"):
            exact_val = res.get("exact")
            numeric_val = res.get("numeric")
            solutions = res.get("solutions")
            
            # Format clean output
            if exact_val is not None:
                final_val = exact_val
            elif numeric_val is not None:
                final_val = str(int(numeric_val) if isinstance(numeric_val, (int, float)) and numeric_val == int(numeric_val) else numeric_val)
            elif solutions is not None:
                final_val = f"Solutions: {', '.join(solutions)}"
            else:
                final_val = str(res.get("result"))

            # For simple pure arithmetic like "2 + 5 * 10", return direct concise answer
            if re.match(r'^[\d\s\+\-\*\/\^\(\)\.\%]+$', clean_expr):
                content = f"**Calculation:**\n`{clean_expr}` = **{final_val}**"
            else:
                content = f"**Problem:**\n${clean_expr}$\n\n**Final Answer:**\n{final_val}"

            return {"content": content, "tool": "solve_math", "result": res}

    # 2. Python Code Debugging & Execution
    if "program" in intent_str or "data" in intent_str:
        # Check if code block or raw code
        raw_code = ""
        if "```" in query:
            raw_code = query.split("```")[1]
            if raw_code.startswith("python"):
                raw_code = raw_code[6:].strip()
        elif "for " in query or "def " in query:
            # Extract code lines after debug/fix
            lines = query.splitlines()
            code_lines = [l for l in lines if not any(l.lower().startswith(p) for p in ["debug", "fix", "check", "run"])]
            raw_code = "\n".join(code_lines).strip()

        if raw_code and ("debug" in q_lower or "fix" in q_lower or "error" in q_lower):
            # Deterministic Python Syntax Diagnostic via AST
            try:
                ast.parse(raw_code)
                # If syntax is valid, test execution
                exec_res = execute_python_code(raw_code)
                if exec_res.get("success"):
                    content = f"**Code Analysis:**\nNo syntax errors found.\n\n**Output:**\n```text\n{exec_res.get('stdout', '(Executed with no output)')}\n```"
                else:
                    content = f"**Runtime Error Detected:**\n```text\n{exec_res.get('stderr')}\n```"
                return {"content": content, "tool": "code_executor", "result": exec_res}
            except SyntaxError as syn_err:
                # Identify missing colon or syntax issue
                msg_err = syn_err.msg
                lineno = syn_err.lineno or 1
                lines = raw_code.splitlines()
                problematic_line = lines[lineno - 1] if lineno <= len(lines) else ""
                
                # Propose fix
                fixed_lines = list(lines)
                if "expected ':'" in msg_err and problematic_line and not problematic_line.strip().endswith(":"):
                    fixed_lines[lineno - 1] = problematic_line + ":"
                corrected_code = "\n".join(fixed_lines)

                content = (
                    f"**Syntax Error Identified:**\n"
                    f"- Error: `{msg_err}` on line {lineno}: `{problematic_line}`\n"
                    f"- **Fix**: Add a colon (`:`) at the end of line {lineno}.\n\n"
                    f"**Corrected Code:**\n"
                    f"```python\n{corrected_code}\n```"
                )
                return {"content": content, "tool": "code_syntax_analyzer", "result": {"syntax_error": str(syn_err)}}

        elif raw_code:
            res = execute_python_code(raw_code)
            stdout = res.get("stdout", "")
            stderr = res.get("stderr", "")
            imgs = res.get("generated_images", [])

            content = "```text\n" + (stdout if stdout else "(Code executed successfully with no output)") + "\n```"
            if stderr:
                content += f"\n\n**Diagnostic output:**\n```text\n{stderr}\n```"
            return {"content": content, "tool": "execute_python_code", "result": res, "images": imgs}

    # 3. Document Analysis
    if "document" in intent_str and attached_files:
        f = attached_files[-1]
        analysis = analyze_file(f["path"])
        if analysis.get("success"):
            ftype = analysis.get("file_type")
            fname = analysis.get("filename")
            if ftype == "CSV/Tabular":
                content = (
                    f"**File Analysis: {fname}**\n\n"
                    f"- **Type:** {ftype}\n"
                    f"- **Rows:** {analysis.get('rows')}\n"
                    f"- **Columns ({len(analysis.get('columns', []))}):** {', '.join(analysis.get('columns', []))}\n\n"
                    f"**Sample Preview:**\n```json\n{analysis.get('head', [])}\n```"
                )
            elif ftype == "PDF":
                content = (
                    f"**PDF Document: {fname}**\n\n"
                    f"- **Total Pages:** {analysis.get('total_pages')}\n\n"
                    f"**Content Preview:**\n\n{analysis.get('preview_text')}"
                )
            else:
                content = f"**File: {fname}**\n\n{analysis.get('preview_text') or analysis.get('content')}"
            return {"content": content, "tool": "analyze_file", "result": analysis}

    # 4. Web Search (live factual snippets)
    if "current" in intent_str:
        res = search_web(query, max_results=4)
        if res and isinstance(res, list) and len(res) > 0 and res[0].get("title"):
            lines = []
            for item in res:
                lines.append(f"• **[{item.get('title')}]({item.get('href')})**: {item.get('body')}")
            content = "\n\n".join(lines)
            return {"content": content, "tool": "search_web", "result": res}

    # 5. Foundational Definitions
    for term, definition in FOUNDATIONAL_KNOWLEDGE.items():
        if term in q_lower and any(kw in q_lower for kw in ["what is", "define", "explain", "meaning of"]):
            return {"content": definition, "tool": "foundational_knowledge", "result": {}}

    return None
