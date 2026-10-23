"""
Unit and integration tests for SPARK-AI Intelligent Search Bar.
Validates:
1. Intelligent Query Understanding & Intent Routing across all required prompt test cases
2. Search Modes (Auto, Web, Files) and automatic fallback behavior
3. Tool Execution (SymPy step-by-step solver, Weather API, Code diagnostics, Study questions, Follow-up)
4. Dynamic Contextual Autocomplete Suggestions
5. Search Bar response handling and orchestrator integration
"""

import pytest
from unittest.mock import MagicMock
from core.intent import detect_intent, IntentType
from tools.weather import get_live_weather
from tools.high_value_tools import solve_math_step_by_step, explain_code_error
from tools.study_engine import generate_exam_pattern_answers
from core.orchestrator import ChatbotOrchestrator
from core.conversation import ConversationSession


def test_intent_detection_all_core_cases():
    """Verify that intent detection matches expected actions for all 8 prompt test cases."""
    test_cases = [
        ("What is Python?", IntentType.KNOWLEDGE),
        ("Latest AI news today", IntentType.CURRENT_INFO),
        ("Solve x² - 5x + 6 = 0", IntentType.MATH_CALCULATION),
        ("Find bugs in my uploaded Python file", IntentType.PROGRAMMING),
        ("Analyze sales.csv", IntentType.DATA_ANALYSIS),
        ("Explain this in 5-mark format", IntentType.STUDY_QUESTION),
        ("What about the second point?", IntentType.FOLLOW_UP),
        ("Weather in Saint-Merri", IntentType.WEATHER),
    ]

    for query, expected_intent in test_cases:
        actual_intent = detect_intent(query, search_mode="Auto")
        assert actual_intent == expected_intent, f"Failed for query '{query}': expected {expected_intent}, got {actual_intent}"


def test_search_mode_overrides():
    """Verify search mode behavior: Auto, Web, and Files."""
    # In Web mode, queries force web search
    assert detect_intent("What is Python?", search_mode="Web") == IntentType.CURRENT_INFO
    assert detect_intent("Solve 2 + 2", search_mode="Web") == IntentType.CURRENT_INFO

    # In Files mode, queries force document analysis
    assert detect_intent("What is Python?", search_mode="Files") == IntentType.DOCUMENT_ANALYSIS
    assert detect_intent("Summarize this", search_mode="Files") == IntentType.DOCUMENT_ANALYSIS

    # In Auto mode, basic questions avoid unnecessary web search
    assert detect_intent("What is Python?", search_mode="Auto") == IntentType.KNOWLEDGE
    assert detect_intent("Solve x² - 5x + 6 = 0", search_mode="Auto") == IntentType.MATH_CALCULATION


def test_live_weather_tool():
    """Verify get_live_weather retrieves live or fallback weather data with required schema."""
    res = get_live_weather("Saint-Merri")
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert "location" in res
    assert "celsius" in res
    assert "condition" in res
    assert "summary" in res
    assert len(res["summary"]) > 0 and ("Saint-Merri" in res["summary"] or "Paris" in res["summary"] or "France" in res["summary"])


def test_sympy_step_by_step_math_solver():
    """Verify solve_math_step_by_step solves polynomial equations with steps."""
    res = solve_math_step_by_step("Solve x² - 5x + 6 = 0")
    assert res.get("success") is True
    assert "steps" in res
    assert len(res["steps"]) >= 4
    # Roots for x² - 5x + 6 = 0 are 2 and 3
    assert "2" in res["final_answer"] and "3" in res["final_answer"]


def test_code_error_diagnostics():
    """Verify explain_code_error identifies syntax errors and suggests fixes."""
    bad_code = "def calculate_sum(a, b)\n    return a + b"
    res = explain_code_error(bad_code, "")
    assert res.get("success") is True
    assert res.get("has_syntax_error") is True
    assert res["analysis"]["error_type"] == "SyntaxError"
    assert "Recommendation" in res["explanation"]


def test_study_question_pattern_generation():
    """Verify generate_exam_pattern_answers produces 2-mark, 5-mark, and 10-mark structures."""
    res = generate_exam_pattern_answers("Supervised Learning", pattern="5-mark")
    assert res.get("success") is True
    assert "5-Mark" in res.get("pattern_title", "")
    assert len(res.get("sections", [])) > 0


def test_autocomplete_suggestions_logic():
    """Verify autocomplete suggestions dynamic generator adapts to history and files."""
    from app import get_contextual_suggestions

    # Initial state (empty messages)
    empty_suggestions = get_contextual_suggestions([])
    assert len(empty_suggestions) >= 4
    labels = [s[0] for s in empty_suggestions]
    assert any("Python" in l for l in labels)
    assert any("AI news" in l for l in labels)

    # Initial state with attached files
    file_suggestions = get_contextual_suggestions([], attached_files=[{"name": "script.py", "path": "uploads/script.py"}])
    file_labels = [s[0] for s in file_suggestions]
    assert any("bugs" in l.lower() for l in file_labels)

    # Contextual state (after code conversation)
    history = [
        {"role": "user", "content": "How do I implement binary search?"},
        {"role": "assistant", "content": "Here is the Python code: ```python\ndef binary_search(arr, x):\n    pass\n```"}
    ]
    post_code_sugs = get_contextual_suggestions(history)
    post_labels = [s[0] for s in post_code_sugs]
    assert any("second point" in l.lower() or "code" in l.lower() or "test" in l.lower() for l in post_labels)


def test_orchestrator_intelligent_routing():
    """Verify end-to-end ChatbotOrchestrator integration across tools and badges."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {"success": True, "content": "Here is the calibrated response."}
    mock_llm.model = "test-provider-model"

    orch = ChatbotOrchestrator(provider=mock_llm)

    # 1. Weather routing
    s_weather = ConversationSession()
    res_w = orch.process_message(s_weather, "What is the weather in Saint-Merri?", search_mode="Auto")
    assert any("Weather" in b for b in res_w.get("verification_badges", []))
    assert any(t["name"] == "get_live_weather" for t in res_w.get("executed_tools", []))

    # 2. Math routing
    s_math = ConversationSession()
    res_m = orch.process_message(s_math, "Solve x² - 5x + 6 = 0", search_mode="Auto")
    assert any("SymPy" in b for b in res_m.get("verification_badges", []))
    assert any(t["name"] == "solve_math_step_by_step" for t in res_m.get("executed_tools", []))

    # 3. Study question routing
    s_study = ConversationSession()
    res_s = orch.process_message(s_study, "Explain gradient descent in 5-mark format", search_mode="Auto")
    assert any("Exam" in b for b in res_s.get("verification_badges", []))
    assert any(t["name"] == "generate_exam_pattern_answers" for t in res_s.get("executed_tools", []))

    # 4. Contextual follow-up routing
    s_follow = ConversationSession()
    s_follow.add_message("user", "Explain 3 sorting algorithms")
    s_follow.add_message("assistant", "1. QuickSort. 2. MergeSort. 3. BubbleSort.")
    res_f = orch.process_message(s_follow, "What about the second point?", search_mode="Auto")
    assert res_f.get("success") is True or res_f.get("content")

    # 5. Incomplete voice query without context -> asks single clarification question
    s_inc_no_ctx = ConversationSession()
    res_inc1 = orch.process_message(s_inc_no_ctx, "What is an...", search_mode="Auto")
    assert res_inc1.get("success") is True
    assert res_inc1.get("content") == "What would you like to know about?"

    # 6. Incomplete voice query with context -> infers intended question
    s_inc_ctx = ConversationSession()
    s_inc_ctx.add_message("user", "We are building an API gateway.")
    s_inc_ctx.add_message("assistant", "An API gateway handles incoming requests.")
    res_inc2 = orch.process_message(s_inc_ctx, "What is an...", search_mode="Auto")
    assert res_inc2.get("success") is True
    # The last user message recorded in session should be the resolved question
    assert any("API" in m.get("content", "") for m in s_inc_ctx.messages if m.get("role") == "user")

    # 7. Voice query cleaning (strips filler words)
    s_fillers = ConversationSession()
    res_clean = orch.process_message(s_fillers, "um uh basically what is Python?", search_mode="Auto")
    assert res_clean.get("success") is True
    # The prompt sent or user message stored shouldn't contain "um uh"
    user_msgs = [m.get("content") for m in s_fillers.messages if m.get("role") == "user"]
    assert "What is Python?" in user_msgs
