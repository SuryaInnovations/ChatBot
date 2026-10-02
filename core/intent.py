"""
Intent Detector module.
Classifies user requests into specific task categories for optimal routing.
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional

class IntentType(Enum):
    KNOWLEDGE = "knowledge"
    CURRENT_INFO = "current_info"
    MATH_CALCULATION = "math_calculation"
    PROGRAMMING = "programming"
    DOCUMENT_ANALYSIS = "document_analysis"
    DATA_ANALYSIS = "data_analysis"
    IMAGE_GENERATION = "image_generation"
    WRITING = "writing"
    INTERVIEW = "interview"
    AMBIGUOUS = "ambiguous"

def detect_intent(message: str, attached_files: Optional[List[Dict[str, Any]]] = None, in_interview: bool = False) -> IntentType:
    """
    Analyzes the user message and context to determine what the user actually needs.
    """
    msg = message.strip()
    msg_lower = msg.lower()

    if not msg:
        return IntentType.AMBIGUOUS

    # If already in an interview session
    if in_interview:
        return IntentType.INTERVIEW

    # 1. Document / File Analysis (if files are attached or explicitly mentioned)
    if attached_files and len(attached_files) > 0 and any(kw in msg_lower for kw in ["file", "pdf", "csv", "excel", "document", "sheet", "this data", "attached", "upload"]):
        return IntentType.DOCUMENT_ANALYSIS

    # 2. Image Generation
    if any(phrase in msg_lower for phrase in [
        "generate image", "create image", "draw an image", "draw a", "make a logo",
        "generate a logo", "design a poster", "create illustration", "create a picture"
    ]):
        return IntentType.IMAGE_GENERATION

    # 3. Interview Preparation / Mock Interview
    if any(phrase in msg_lower for phrase in [
        "mock interview", "interview me", "prepare for interview", "interview preparation",
        "practice interview", "conduct an interview"
    ]):
        return IntentType.INTERVIEW

    # 4. Mathematical & Financial Calculations
    # Check for pure arithmetic (e.g., '2 + 5 * 10', '(100 - 20) / 4')
    is_pure_arithmetic = bool(
        re.match(r'^[\d\s\+\-\*\/\^\(\)\.\%]+$', msg) and
        re.search(r'[\+\-\*\/\^\%]', msg) and
        re.search(r'\d', msg)
    )

    has_finance = any(term in msg_lower for term in [
        "compound interest", "simple interest", "emi", "interest rate",
        "principal", "annual interest", "calculate emi"
    ])
    has_math_ops = bool(re.search(r'[\d\w]+\s*[\+\-\*\/\^=]\s*[\d\w]+', msg))
    has_math_keywords = any(kw in msg_lower for kw in [
        "calculate", "solve", "equation", "derivative", "integral", "simplify",
        "square root", "factorize", "find x", "eval"
    ])

    if is_pure_arithmetic or has_finance or (has_math_keywords and has_math_ops):
        return IntentType.MATH_CALCULATION

    # 5. Data Analysis (tabular datasets, statistics, charts)
    if any(term in msg_lower for term in [
        "data analysis", "analyze data", "plot chart", "create chart",
        "bar chart", "scatter plot", "correlation", "missing values", "dataframe"
    ]):
        return IntentType.DATA_ANALYSIS

    # 6. Current / Fresh Information (requires web search)
    if any(term in msg_lower for term in [
        "latest", "current", "today", "yesterday", "recently", "2026", "2025",
        "current price", "current version", "current news", "who won", "live score",
        "current weather", "official syllabus", "what happened today", "release date"
    ]):
        return IntentType.CURRENT_INFO

    # 7. Programming (code writing, debugging, testing, refactoring)
    if any(term in msg_lower for term in [
        "write code", "debug", "fix this code", "syntax error", "python function",
        "write a function", "implement algorithm", "compile error", "traceback",
        "in python", "in javascript", "in c++", "in java", "in sql"
    ]) or "```" in msg:
        return IntentType.PROGRAMMING

    # 8. Writing / Drafting / Translation / Summarization
    if any(term in msg_lower for term in [
        "write an email", "draft a letter", "write an essay", "translate this",
        "summarize this", "rewrite", "proofread", "create a resume", "cover letter"
    ]):
        return IntentType.WRITING

    # 9. Simple General Knowledge (definitions, concepts, history, science, etc.)
    # e.g. "what is physics", "explain recursion", "who was newton", "how does gravity work"
    if any(msg_lower.startswith(prefix) for prefix in [
        "what is", "what are", "who is", "who was", "explain", "describe",
        "why do", "why does", "how does", "tell me about", "define"
    ]) or len(msg.split()) < 10:
        return IntentType.KNOWLEDGE

    # Default to general knowledge
    return IntentType.KNOWLEDGE
