"""
Unit tests for SPARK-AI Stage 1 Features:
1. Multi-document comparison & PPTX parsing
2. Study Mode with exam patterns & NPTEL MCQs
3. Coding Lab workspace with test cases & Big-O
4. AutoML data quality & cleaning suggestions
5. Personal memory granular editing
"""

import os
import pytest
import pandas as pd
from tools.study_engine import generate_exam_pattern_answers, generate_nptel_mcqs, parse_mock_test_submission
from tools.coding_lab import run_coding_workspace
from tools.automl import analyze_data_quality, compute_eda_dashboard_data
from tools.rag import SemanticRAGIndex
from core.memory import add_user_topic_weakness, add_user_topic_strength, get_user_memory


def test_study_engine_exam_patterns():
    res = generate_exam_pattern_answers("Deadlocks in Operating Systems", pattern="all")
    assert res["topic"] == "Deadlocks in Operating Systems"
    assert "two_mark" in res["sections"]
    assert "five_mark" in res["sections"]
    assert "ten_mark" in res["sections"]
    assert res["sections"]["two_mark"]["marks"] == 2
    assert res["sections"]["ten_mark"]["marks"] == 10


def test_study_engine_nptel_mcqs():
    mcqs = generate_nptel_mcqs("Binary Search Trees", num_questions=3)
    assert mcqs["num_questions"] == 3
    assert "NPTEL" in mcqs["style"]


def test_mock_test_scoring_and_memory():
    questions = [
        {"question": "What is 2+2?", "correct_option": "A", "explanation": "2+2=4", "topic": "Math"},
        {"question": "Capital of France?", "correct_option": "B", "explanation": "Paris", "topic": "Geography"}
    ]
    submission = {"1": "A", "2": "C"}
    res = parse_mock_test_submission(submission, questions)
    assert res["score"] == 1
    assert res["total"] == 2
    assert res["percentage"] == 50.0
    assert "Math" in res["strong_topics"]
    assert "Geography" in res["weak_topics"]


def test_coding_lab_workspace_execution():
    code = """def add(a, b): return a + b\nprint(add(3, 4))"""
    res = run_coding_workspace(code)
    assert res["success"] is True
    assert "7" in res["stdout"]
    assert res["execution_time_ms"] > 0
    assert res["complexity"] is not None


def test_coding_lab_test_cases():
    code = """inp = input().strip()\nprint(f"Hello, {inp}")"""
    tcs = [{"input": "World", "expected": "Hello, World"}]
    res = run_coding_workspace(code, stdin_input="World", test_cases=tcs)
    assert res["success"] is True
    assert res["all_tests_passed"] is True
    assert len(res["test_results"]) == 1
    assert res["test_results"][0]["passed"] is True


def test_automl_data_quality():
    df = pd.DataFrame({
        "age": [20, 25, 30, None, 20],
        "city": ["NY", "SF", "LA", "NY", "NY"],
        "constant_col": [1, 1, 1, 1, 1]
    })
    quality = analyze_data_quality(df)
    assert quality["total_rows"] == 5
    assert quality["total_cols"] == 3
    assert "constant_col" in quality["constant_columns"]
    assert "age" in quality["missing_columns"]
    assert len(quality["cleaning_suggestions"]) > 0


def test_personal_memory_topic_helpers():
    test_user = "test_eval_user@example.com"
    add_user_topic_weakness(test_user, "Dynamic Programming")
    mem = get_user_memory(test_user)
    assert "Dynamic Programming" in mem["weak_topics"]

    add_user_topic_strength(test_user, "Dynamic Programming")
    mem2 = get_user_memory(test_user)
    assert "Dynamic Programming" in mem2["strong_topics"]
    assert "Dynamic Programming" not in mem2["weak_topics"]


def test_detect_target_workspace():
    from workspaces import detect_target_workspace
    assert detect_target_workspace("run this code in python") == "💻 Coding Lab"
    assert detect_target_workspace("give me a 5-mark answer for deadlocks") == "📖 Study Mentor"
    assert detect_target_workspace("run automl on this csv") == "📊 Data Science / AutoML"
    assert detect_target_workspace("solve this handwritten math equation") == "🖼️ Vision & Screenshots"
    assert detect_target_workspace("compare documents across slides") == "📄 Document Chat"
    assert detect_target_workspace("what is quantum computing?") is None

