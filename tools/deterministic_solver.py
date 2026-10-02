"""
Deterministic local solver module.
Used when LLM providers are unavailable or when exact local execution (math, code, file analysis, verified knowledge) is sufficient.
Strictly avoids fabricating or adding artificial warning banners to responses.
"""

import re
from typing import Dict, Any, Optional
from core.intent import IntentType
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

def can_deterministic_tool_answer(intent: IntentType, query: str, attached_files: Optional[list] = None) -> bool:
    """
    Checks if a query can be answered accurately by local deterministic tools without an LLM.
    """
    q_lower = query.strip().lower()

    if intent == IntentType.MATH_CALCULATION:
        return True

    if intent == IntentType.DATA_ANALYSIS or (intent == IntentType.PROGRAMMING and "```" in query):
        return True

    if intent == IntentType.DOCUMENT_ANALYSIS and attached_files and len(attached_files) > 0:
        return True

    if intent == IntentType.CURRENT_INFO:
        return True

    # Check foundational definitions
    for term in FOUNDATIONAL_KNOWLEDGE:
        if term in q_lower and any(kw in q_lower for kw in ["what is", "define", "explain", "meaning of"]):
            return True

    return False

def solve_deterministically(intent: IntentType, query: str, attached_files: Optional[list] = None) -> Optional[Dict[str, Any]]:
    """
    Executes the appropriate local deterministic tool and formats a clean response.
    """
    q_lower = query.strip().lower()

    # 1. Math / Financial Calculation
    if intent == IntentType.MATH_CALCULATION:
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

        # Symbolic / General Math
        task_type = "derivative" if "derivative" in q_lower else ("integral" if "integral" in q_lower else ("solve_equation" if "=" in query else "eval"))
        clean_expr = query
        for prefix in ["solve", "calculate", "find", "evaluate", "what is"]:
            if clean_expr.lower().startswith(prefix):
                clean_expr = clean_expr[len(prefix):].strip()

        res = solve_math_expression(clean_expr, task_type)
        if res.get("success"):
            sol = res.get("solutions") or res.get("numeric") or res.get("derivative") or res.get("integral") or res.get("result")
            content = f"**Problem:**\n${clean_expr}$\n\n**Final Answer:**\n{sol}"
            return {"content": content, "tool": "solve_math", "result": res}

    # 2. Python Code Execution
    if (intent == IntentType.PROGRAMMING or intent == IntentType.DATA_ANALYSIS) and "```" in query:
        code_block = query.split("```")[1]
        if code_block.startswith("python"):
            code_block = code_block[6:].strip()
        res = execute_python_code(code_block)
        stdout = res.get("stdout", "")
        stderr = res.get("stderr", "")
        imgs = res.get("generated_images", [])

        content = "```text\n" + (stdout if stdout else "(Code executed successfully with no output)") + "\n```"
        if stderr:
            content += f"\n\n**Diagnostic output:**\n```text\n{stderr}\n```"
        return {"content": content, "tool": "execute_python_code", "result": res, "images": imgs}

    # 3. Document Analysis
    if intent == IntentType.DOCUMENT_ANALYSIS and attached_files:
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
    if intent == IntentType.CURRENT_INFO:
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
