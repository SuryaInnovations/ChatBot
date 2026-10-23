"""
Intent Detector module for Intelligent Query Understanding & Routing.
Classifies user requests into specific task categories for optimal tool selection and execution.
Supports Auto, Web, and Files search modes, conversation context tracking, and robust fallbacks.
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
    STUDY_QUESTION = "study_question"
    WEATHER = "weather"
    FOLLOW_UP = "follow_up"
    IMAGE_GENERATION = "image_generation"
    WRITING = "writing"
    INTERVIEW = "interview"
    AMBIGUOUS = "ambiguous"

def detect_intent(
    message: str,
    attached_files: Optional[List[Dict[str, Any]]] = None,
    in_interview: bool = False,
    search_mode: Optional[str] = "Auto",
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> IntentType:
    """
    Analyzes the user message, search mode, attached files, and conversation history
    to automatically determine what the user actually needs.
    """
    msg = message.strip()
    msg_lower = msg.lower()

    if not msg:
        return IntentType.AMBIGUOUS

    # 0. EXPLICIT SEARCH MODE OVERRIDE
    mode = (search_mode or "Auto").strip().lower()
    if mode == "web":
        return IntentType.CURRENT_INFO
    elif mode == "files":
        return IntentType.DOCUMENT_ANALYSIS

    # 1. Interview Session Active (unless user explicitly ends it)
    if in_interview and not any(kw in msg_lower for kw in ["end interview", "exit interview", "stop interview", "quit interview"]):
        return IntentType.INTERVIEW

    # 2. Weather Inquiries
    weather_keywords = [
        "weather in", "weather for", "weather of", "what is the weather", "what's the weather",
        "current weather", "forecast in", "temperature in", "temperature of", "is it raining in",
        "how cold is it in", "how hot is it in", "humidity in", "weather today in", "live weather",
        "weather forecast"
    ]
    if any(kw in msg_lower for kw in weather_keywords) or (
        "weather" in msg_lower and any(prep in msg_lower for prep in [" in ", " at ", " for ", " today", " tomorrow"])
    ):
        return IntentType.WEATHER

    # 3. Study & Exam Pattern Questions (2-mark, 5-mark, 10-mark, NPTEL)
    study_markers = [
        "2-mark", "2 mark", "5-mark", "5 mark", "10-mark", "10 mark",
        "two-mark", "two mark", "five-mark", "five mark", "ten-mark", "ten mark",
        "2mark", "5mark", "10mark", "exam format", "exam pattern", "university format",
        "university answer", "nptel mcq", "nptel questions", "syllabus format"
    ]
    if any(marker in msg_lower for marker in study_markers):
        return IntentType.STUDY_QUESTION

    # 4. Contextual Follow-Up Questions (referencing prior turn)
    follow_up_patterns = [
        r"^(what|how) about (the )?(first|second|third|fourth|fifth|last|next|other|previous|1st|2nd|3rd|4th|5th) (point|one|part|item|step|reason|method)",
        r"^why is that( so)?\??$",
        r"^(can you )?explain (that|this|it) (more|further|in detail|again)",
        r"^(show|give) me (a |an )?(code )?example( of (that|this))?",
        r"^how does (that|this) work\??$",
        r"^(what|how) about (that|this)\??$",
        r"^(and )?(the )?(second|2nd|first|1st|third|3rd) one\??$",
        r"^what do you mean by (that|this)\??$"
    ]
    if any(re.search(pat, msg_lower) for pat in follow_up_patterns):
        return IntentType.FOLLOW_UP

    # 5. Data Analysis & Tabular Datasets (CSV, Excel, EDA, charts, statistics)
    has_dataset_file = any(
        kw in msg_lower for kw in [".csv", ".xlsx", ".xls", "sales.csv", "iris.csv", "dataset", "dataframe"]
    )
    has_data_keywords = any(kw in msg_lower for kw in [
        "data analysis", "analyze data", "analyze dataset", "analyze this csv", "clean data",
        "data quality", "missing values", "correlation matrix", "summary statistics",
        "plot chart", "create chart", "bar chart", "scatter plot", "histogram", "eda report"
    ])
    if has_dataset_file or has_data_keywords:
        return IntentType.DATA_ANALYSIS

    # 6. Document / PDF / File Analysis (if files attached or explicitly mentioned)
    if (attached_files and len(attached_files) > 0) or any(
        kw in msg_lower for kw in ["uploaded file", "this pdf", "attached file", "this document", "in the pdf", "heart.pdf", "read file", "from the file"]
    ):
        # If the user specifically asks to find bugs or write code in an uploaded python file
        if any(kw in msg_lower for kw in ["find bugs", "debug", "fix bugs", "syntax error", "inspect code"]) and any(
            kw in msg_lower for kw in [".py", "python file", "code file", "uploaded file", "script"]
        ):
            return IntentType.PROGRAMMING
        return IntentType.DOCUMENT_ANALYSIS

    # 7. Image Generation
    if any(phrase in msg_lower for phrase in [
        "generate image", "create image", "draw an image", "draw a", "make a logo",
        "generate a logo", "design a poster", "create illustration", "create a picture"
    ]):
        return IntentType.IMAGE_GENERATION

    # 8. Interview Preparation / Mock Interview
    if any(phrase in msg_lower for phrase in [
        "mock interview", "interview me", "start interview", "start an interview",
        "begin interview", "prepare for interview", "interview preparation",
        "practice interview", "conduct an interview"
    ]):
        return IntentType.INTERVIEW

    # 9. Mathematical & Step-by-Step Problem Solving
    # Pure arithmetic (e.g., '2 + 5 * 10', '(100 - 20) / 4')
    is_pure_arithmetic = bool(
        re.match(r'^[\d\s\+\-\*\/\^\(\)\.\%]+$', msg) and
        re.search(r'[\+\-\*\/\^\%]', msg) and
        re.search(r'\d', msg)
    )
    # Algebraic equations: e.g. 'Solve x² - 5x + 6 = 0', 'x^2 - 5x + 6 = 0', '2x + 5 = 15'
    has_equation = bool(
        re.search(r'[a-zA-Z]\s*[\^²³]\s*\d', msg) or # polynomial degree (x^2, x²)
        (re.search(r'[a-zA-Z]\s*[\+\-\*\/]\s*\d+', msg) and "=" in msg) or # linear/algebraic eq with =
        ("=" in msg and any(kw in msg_lower for kw in ["solve", "find x", "find y", "calculate", "equation"]))
    )
    has_finance = any(term in msg_lower for term in [
        "compound interest", "simple interest", "calculate emi", "annual interest", "interest rate"
    ])
    has_math_keywords = any(kw in msg_lower for kw in [
        "calculate", "solve", "equation", "derivative", "integral", "simplify",
        "square root", "factorize", "find x", "eval", "derive", "integrate"
    ])
    has_math_ops = bool(re.search(r'[\d\w]+\s*[\+\-\*\/\^=]\s*[\d\w]+', msg))

    if is_pure_arithmetic or has_equation or has_finance or (has_math_keywords and has_math_ops):
        return IntentType.MATH_CALCULATION

    # 10. Programming (code generation, debugging, error identification, algorithms)
    programming_terms = [
        "write code", "debug", "find bugs", "fix this code", "fix bugs", "syntax error",
        "python function", "write a function", "implement algorithm", "compile error",
        "traceback", "in python", "in javascript", "in c++", "in java", "in sql",
        "write a script", "explain the logic", "identify errors", "refactor",
        "explain this code", "explain code", "code step by step", "analyze this code",
        "def ", "class ", "return "
    ]
    if any(term in msg_lower for term in programming_terms) or "```" in msg:
        return IntentType.PROGRAMMING

    # 11. Current / Fresh Information & Latest News (Requires Live Web Search)
    current_news_terms = [
        "latest", "today", "yesterday", "recently", "2026", "2025",
        "current price", "current version", "current news", "who won", "live score",
        "official syllabus", "what happened today", "release date", "latest ai news",
        "news today", "breaking news", "stock price of", "search the web", "search web for"
    ]
    if any(term in msg_lower for term in current_news_terms):
        return IntentType.CURRENT_INFO

    # 12. Writing / Drafting / Translation / Summarization
    if any(term in msg_lower for term in [
        "write an email", "draft a letter", "write an essay", "translate this",
        "summarize this", "rewrite", "proofread", "create a resume", "cover letter"
    ]):
        return IntentType.WRITING

    # 13. General Knowledge & Conceptual Explanation (e.g. "What is Python?")
    # Answer directly via LLM without unnecessary web searches or heavy tools
    return IntentType.KNOWLEDGE
