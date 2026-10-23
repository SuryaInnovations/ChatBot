"""
Comprehensive Test Suite for SPARK-AI Final Master Upgrades.
Verifies all 10 architectural phases:
1. Sandbox path sanitization & newly blocked modules
2. Query complexity classification & dynamic model routing
3. Autonomous Plan-Act-Verify agent execution & Orchestrator delegation
4. RAG retrieval relevance evaluation & insufficient context detection
5. Calibrated 16-mark university blueprint generation
6. Memory privacy compliance (GDPR deletion & data export)
7. Production API endpoints (/healthz, /readyz, /api/observability, X-Request-ID)
8. Observability latency percentiles & token cost estimation
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

# 1. Sandbox Path Sanitization & AST Checks
def test_sandbox_path_sanitization():
    from tools.sandbox import sanitize_traceback

    raw_tb = """Traceback (most recent call last):
  File "C:\\Users\\SURYA PRAKASH\\AppData\\Local\\Temp\\tmp12345.py", line 4, in <module>
    raise ValueError("Something went wrong")
ValueError: Something went wrong"""

    cleaned = sanitize_traceback(raw_tb)
    assert "SURYA PRAKASH" not in cleaned
    assert 'File "main.py"' in cleaned or '[REDACTED]' in cleaned
    assert "ValueError: Something went wrong" in cleaned

    # Linux-style path sanitization
    raw_linux_tb = """Traceback (most recent call last):
  File "/home/john_doe/app/temp/runner.py", line 12, in <module>
    1 / 0
ZeroDivisionError: division by zero"""
    cleaned_linux = sanitize_traceback(raw_linux_tb)
    assert "john_doe" not in cleaned_linux
    assert "ZeroDivisionError: division by zero" in cleaned_linux


def test_sandbox_blocked_modules_ast():
    from tools.sandbox import validate_code_safety

    # Test newly blocked internal modules
    forbidden_snippets = [
        "import _posixsubprocess",
        "import resource",
        "import codecs",
        "import fcntl",
        "from codecs import open",
    ]
    for snippet in forbidden_snippets:
        is_safe, error = validate_code_safety(snippet)
        assert not is_safe, f"Expected '{snippet}' to be blocked by AST validator"
        assert error is not None


# 2. Query Complexity Classification & Model Routing
def test_query_complexity_classification():
    from core.llm_provider import classify_query_complexity, select_model_for_complexity

    # Level 1: Deterministic greetings / simple ping
    lvl1 = classify_query_complexity("hi")
    assert lvl1 == 1
    assert select_model_for_complexity(lvl1, "groq") == "llama-3.1-8b-instant"

    # Level 2: General definition
    lvl2 = classify_query_complexity("What is Python?")
    assert lvl2 == 2
    assert select_model_for_complexity(lvl2, "gemini") == "gemini-3.5-flash-lite"

    # Level 3: Coding / Math
    lvl3 = classify_query_complexity("def fibonacci(n): calculate derivative")
    assert lvl3 == 3

    # Level 4: Document / 16-mark
    lvl4 = classify_query_complexity("Provide a 16-mark essay and compare documents")
    assert lvl4 == 4
    assert select_model_for_complexity(lvl4, "gemini") == "gemini-3.8-flash"

    # Level 5: Autonomous agent / full-stack system design
    lvl5 = classify_query_complexity("Execute autonomous full-stack architecture design with comprehensive research")
    assert lvl5 == 5
    assert select_model_for_complexity(lvl5, "groq") == "llama-3.3-70b-versatile"


# 3. Autonomous Plan-Act-Verify Agent & Orchestrator Delegation
def test_bounded_agent_execution():
    from core.agent import BoundedAutonomousAgent, ActionStatus

    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        "content": "Result: 15 * 12 is verified to be 180."
    }

    agent = BoundedAutonomousAgent(
        llm_provider=mock_llm,
        max_steps=3,
        max_tool_budget=3,
        timeout_seconds=5.0
    )

    result = agent.execute_bounded_run("calculate 15 * 12")
    assert result.status == "success"
    assert "180" in result.content
    assert len(result.timeline.actions) > 0


def test_orchestrator_agent_mode_delegation():
    from core.orchestrator import ChatbotOrchestrator
    from core.conversation import ConversationSession

    session = ConversationSession(user_id="test_user")
    orchestrator = ChatbotOrchestrator(provider="auto")

    with patch("core.orchestrator.BoundedAutonomousAgent") as MockAgentClass:
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "Autonomous Agent successfully resolved the objective: [Result 42]"
        mock_result.timeline.to_dict.return_value = {"actions": [], "budget_used": 1}
        mock_instance.execute_bounded_run.return_value = mock_result
        MockAgentClass.return_value = mock_instance

        # Test with /agent prefix
        result = orchestrator.process_message(
            session=session,
            user_message="/agent calculate optimal hyperparameters"
        )
        assert MockAgentClass.called
        assert "Autonomous Agent" in result["content"]


# 4. RAG Retrieval Relevance & Insufficient Context Detection
def test_rag_retrieval_relevance_evaluation():
    from tools.rag import evaluate_retrieval_relevance

    # Case 1: High relevance match
    good_results = [
        {"text": "Python was conceived in the late 1980s by Guido van Rossum.", "score": 0.85},
        {"text": "Python supports multiple programming paradigms.", "score": 0.72}
    ]
    eval_good = evaluate_retrieval_relevance("Who created Python and when?", good_results)
    assert eval_good["is_sufficient"] is True
    assert eval_good["confidence_score"] > 0

    # Case 2: Empty results
    empty_results = []
    eval_empty = evaluate_retrieval_relevance("What is quantum computing?", empty_results)
    assert eval_empty["is_sufficient"] is False
    assert "No document passages were retrieved." in eval_empty["message"]

    # Case 3: Zero lexical overlap and tiny score
    bad_results = [
        {"text": "The recipe for strawberry shortcake involves flour and sugar.", "score": 0.0001}
    ]
    eval_bad = evaluate_retrieval_relevance("Explain Byzantine Fault Tolerance in distributed databases", bad_results)
    assert eval_bad["is_sufficient"] is False
    assert "do not contain sufficient information" in eval_bad["message"]


# 5. Calibrated 16-Mark University Blueprint
def test_study_engine_16_mark_blueprint():
    from tools.study_engine import generate_exam_pattern_answers

    res = generate_exam_pattern_answers("Transformer Attention Architecture", pattern="16-mark")
    assert res["success"] is True
    assert "sixteen_mark" in res["sections"]
    section_16 = res["sections"]["sixteen_mark"]
    assert section_16["marks"] == 16
    assert "Part C standard" in section_16["prompt_template"]
    assert "System Architecture" in section_16["prompt_template"]
    assert "Enterprise Industrial Case Study" in section_16["prompt_template"]


# 6. Memory Privacy & GDPR Compliance
def test_memory_privacy_compliance():
    from core.memory import (
        update_user_memory,
        get_user_memory,
        delete_user_data,
        export_user_data,
        clear_user_history
    )

    test_uid = "privacy_test_user@example.com"
    # Create test data
    update_user_memory(test_uid, {
        "user_level": "Undergraduate",
        "target_role": "Data Scientist",
        "weak_topics": ["Fourier Transform", "Eigenvalues"]
    })

    mem = get_user_memory(test_uid)
    assert mem.get("target_role") == "Data Scientist"

    # Export user data
    exported = export_user_data(test_uid)
    assert exported["user_id"] == test_uid
    assert "profile" in exported
    assert exported["profile"].get("target_role") == "Data Scientist"

    # Delete user data
    del_ok = delete_user_data(test_uid)
    assert del_ok is True

    # Verify cleared
    fresh_mem = get_user_memory(test_uid)
    assert fresh_mem.get("weak_topics") == []


# 7. Production API Endpoints & Observability
def test_api_production_endpoints():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # 1. /healthz Liveness Probe
    resp_liveness = client.get("/healthz")
    assert resp_liveness.status_code == 200
    data_live = resp_liveness.json()
    assert data_live["status"] == "healthy"
    assert "uptime_seconds" in data_live

    # 2. /readyz Readiness Probe
    resp_ready = client.get("/readyz")
    assert resp_ready.status_code == 200
    data_ready = resp_ready.json()
    assert data_ready["status"] in ("ready", "degraded")
    assert "providers" in data_ready
    assert "database" in data_ready

    # 3. /api/observability Endpoint
    resp_obs = client.get("/api/observability")
    assert resp_obs.status_code == 200
    data_obs = resp_obs.json()
    assert "latency_percentiles" in data_obs
    assert "total_estimated_cost_usd" in data_obs
    assert "p50" in data_obs["latency_percentiles"]

    # 4. Tracing Header Middleware
    resp_trace = client.get("/healthz")
    assert "X-Request-ID" in resp_trace.headers


# 8. Observability Percentile Calculations
def test_observability_percentiles():
    from core.observability import record_request_metrics, get_observability_summary

    # Record sample latency entries
    for lat in [100.0, 150.0, 200.0, 300.0, 500.0, 1000.0]:
        record_request_metrics(
            endpoint="/chat",
            latency_ms=lat,
            tokens_in=50,
            tokens_out=150,
            provider="groq",
            model="llama-3.3-70b-versatile"
        )

    summary = get_observability_summary()
    assert summary["total_requests"] >= 6
    lat_p = summary["latency_percentiles"]
    assert "p50" in lat_p
    assert "p95" in lat_p
    assert "p99" in lat_p
    assert lat_p["p50"] <= lat_p["p95"] <= lat_p["p99"]
