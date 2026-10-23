"""
Tools package for All-in-One AI Assistant.
"""
from tools.registry import TOOL_DEFINITIONS, dispatch_tool
from tools.web_search import search_web, fetch_webpage_content
from tools.code_executor import execute_python_code
from tools.math_solver import solve_math_expression, calculate_finance
from tools.file_analyzer import analyze_file
from tools.doc_generator import generate_document

from tools.python_interpreter import execute_python_interpreter
from tools.file_parser import parse_document
from tools.image_vision import analyze_image
from tools.browser_tool import browse_webpage
from tools.github_tool import default_github_tool
from tools.document_generator import create_document
from tools.chart_generator import generate_chart
from tools.image_generation import generate_image_sync
from tools.speech_to_text import transcribe_audio, transcribe_audio_file
from tools.text_to_speech import synthesize_speech
from tools.translator import translate_text
from tools.ocr_vision import extract_ocr_text, screenshot_to_code
from tools.calendar_tool import create_calendar_event
from tools.weather import get_live_weather

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
    "execute_python_interpreter",
    "parse_document",
    "analyze_image",
    "browse_webpage",
    "default_github_tool",
    "create_document",
    "generate_chart",
    "generate_image_sync",
    "transcribe_audio",
    "transcribe_audio_file",
    "synthesize_speech",
    "translate_text",
    "extract_ocr_text",
    "screenshot_to_code",
    "create_calendar_event",
    "get_live_weather",
]
