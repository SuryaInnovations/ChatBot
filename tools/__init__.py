"""
Tools package for All-in-One AI Assistant.
"""
from tools.registry import TOOL_DEFINITIONS, dispatch_tool
from tools.web_search import search_web, fetch_webpage_content
from tools.code_executor import execute_python_code
from tools.math_solver import solve_math_expression, calculate_finance
from tools.file_analyzer import analyze_file
from tools.doc_generator import generate_document

__all__ = [
    "TOOL_DEFINITIONS",
    "dispatch_tool",
    "search_web",
    "fetch_webpage_content",
    "execute_python_code",
    "solve_math_expression",
    "calculate_finance",
    "analyze_file",
    "generate_document",
]
