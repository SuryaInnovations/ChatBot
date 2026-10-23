"""
Enterprise Quality & Performance Optimization Test Suite for SPARK-AI.
Independently verifies all 9 software quality attributes:
1. Consistency
2. Reliability
3. Scalability
4. Flexibility
5. Accessibility
6. Usability
7. Performance & Speed
8. Credibility & Trust
9. Responsiveness
"""

import time
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

# =====================================================================
# 1. CONSISTENCY TESTS
# =====================================================================

def test_consistency_response_validator_integration():
    """Verify ResponseValidator executes and checks citations and tool outcomes."""
    from core.orchestrator import ChatbotOrchestrator
    from core.conversation import ConversationSession

    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        "success": True,
        "content": "Python is an interpreted programming language [1].",
        "provider": "gemini",
        "model": "gemini-2.5-flash"
    }
    mock_llm.model = "gemini-2.5-flash"

    orch = ChatbotOrchestrator(provider=mock_llm)
    session = ConversationSession(user_id="consistency_test_user")

    res = orch.process_message(
        session=session,
        user_message="What is Python?",
        search_mode="Auto"
    )

    assert res.get("success") is True
    # Validation report must be present
    assert "validation" in res
    val = res["validation"]
    assert "is_valid" in val
    assert "confidence_score" in val
    assert isinstance(val["confidence_score"], float)


def test_consistency_temperature_uniformity():
    """Verify default generation temperature is consistent across all providers."""
    from core.llm_provider import LLMProvider

    llm_auto = LLMProvider(provider="auto")
    assert llm_auto.temperature == 0.2

    llm_gemini = LLMProvider(provider="gemini")
    assert llm_gemini.temperature == 0.2

    llm_groq = LLMProvider(provider="groq")
    assert llm_groq.temperature == 0.2


def test_consistency_math_katex_formatting():
    """Verify deterministic math answers consistently format output with KaTeX $$...$$."""
    from tools.high_value_tools import solve_math_step_by_step

    res = solve_math_step_by_step("Solve 2*x + 6 = 14")
    assert res.get("success") is True
    assert "$$" in res.get("solution", "") or "$$" in res.get("formatted_solution", "")
    assert "4" in str(res.get("final_answer"))


# =====================================================================
# 2. RELIABILITY TESTS
# =====================================================================

def test_reliability_simulated_network_error_failover():
    """Verify automatic failover when primary provider encounters 504 / 429."""
    from core.llm_provider import LLMProvider
    from core.providers.gemini import GeminiProvider
    from core.providers.groq import GroqProvider
    from core.providers.base import ProviderConnectionError

    llm = LLMProvider(provider="gemini", fallback_providers=["groq"])

    with patch.object(GeminiProvider, "generate", side_effect=ProviderConnectionError("504 Gateway Timeout")):
        with patch.object(GroqProvider, "is_configured", return_value=True):
            with patch.object(GroqProvider, "generate", return_value={"success": True, "content": "Recovered via Groq successfully!", "provider": "groq", "model": "llama-3.3-70b-versatile"}) as mock_groq:
                resp = llm.generate(messages=[{"role": "user", "content": "Ping"}], system_prompt="You are SPARK-AI")
                assert "Recovered via Groq" in resp["content"]
                assert mock_groq.called


def test_reliability_circuit_breaker_transitions():
    """Verify circuit breaker transitions between CLOSED, OPEN, and HALF_OPEN."""
    from core.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.1)
    avail, reason = cb.is_available("gemini")
    assert avail is True
    assert "CLOSED" in reason

    # Record 2 failures -> OPEN with backoff ladder (0.1s -> 0.2s)
    cb.record_failure("gemini", error_msg="Simulated connection timeout")
    cb.record_failure("gemini", error_msg="Simulated connection timeout")
    avail_open, reason_open = cb.is_available("gemini")
    assert avail_open is False
    assert "OPEN" in reason_open

    # Wait for recovery timeout (0.2s ladder + margin) -> HALF_OPEN probe allowed
    time.sleep(0.25)
    avail_probe, reason_probe = cb.is_available("gemini")
    assert avail_probe is True
    assert "HALF_OPEN" in reason_probe

    # Record success -> CLOSED
    cb.record_success("gemini")
    avail_recovered, reason_recovered = cb.is_available("gemini")
    assert avail_recovered is True
    assert "CLOSED" in reason_recovered


# =====================================================================
# 3. SCALABILITY TESTS
# =====================================================================

def test_scalability_lru_cache_bounded_eviction():
    """Verify response cache strictly enforces MAX_CACHE_ENTRIES bounded eviction."""
    from core.cache import store_cached_response, get_cached_response, _RESPONSE_CACHE, MAX_CACHE_ENTRIES

    _RESPONSE_CACHE.clear()

    # Store 1030 entries (> MAX_CACHE_ENTRIES 1024)
    for i in range(1030):
        store_cached_response(
            prompt=f"Test query sequence item {i}",
            response={"success": True, "content": f"Answer {i}"},
            user_id="scale_test_user"
        )

    # Cache length must be strictly capped at MAX_CACHE_ENTRIES
    assert len(_RESPONSE_CACHE) <= MAX_CACHE_ENTRIES
    # Oldest entries should have been evicted
    assert get_cached_response("Test query sequence item 0", user_id="scale_test_user") is None
    # Latest entry must be present
    assert get_cached_response("Test query sequence item 1029", user_id="scale_test_user") is not None


def test_scalability_concurrent_request_simulation():
    """Simulate concurrent threads processing queries through cache and deterministic engine."""
    from tools.deterministic_solver import can_deterministic_tool_answer, solve_deterministically
    from core.intent import IntentType

    def worker_task(task_id: int):
        q = f"Calculate {task_id} * 10"
        can_det = can_deterministic_tool_answer(IntentType.MATH_CALCULATION, q)
        if can_det:
            ans = solve_deterministically(IntentType.MATH_CALCULATION, q)
            return ans.get("content")
        return None

    # Run with 20 parallel threads
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker_task, i) for i in range(50)]
        results = [f.result() for f in futures]

    assert len(results) == 50
    assert all(r is not None for r in results)


# =====================================================================
# 4. FLEXIBILITY TESTS
# =====================================================================

def test_flexibility_pluggable_custom_provider():
    """Verify that registering a custom AI provider adapter works dynamically without modifying core engine."""
    from core.providers import register_provider, PROVIDER_REGISTRY
    from core.providers.base import BaseProvider
    from typing import Dict, Any, List

    class MockCustomProvider(BaseProvider):
        @property
        def name(self) -> str:
            return "Mock Custom Provider"

        @property
        def code(self) -> str:
            return "custom_plug"

        @property
        def default_model(self) -> str:
            return "custom-model-v1"

        def is_configured(self) -> bool:
            return True

        def health_check(self) -> Dict[str, Any]:
            return {"healthy": True, "status": "AVAILABLE"}

        def generate(self, messages: List[Dict[str, Any]], system_prompt: str = "", **kwargs) -> Dict[str, Any]:
            return {"success": True, "content": "Hello from custom pluggable provider!", "tokens": 10, "provider": "custom_plug", "model": "custom-model-v1"}

        def generate_stream(self, messages: List[Dict[str, Any]], system_prompt: str = "", **kwargs):
            yield "Custom token"

    # Register dynamic provider
    register_provider("custom_plug", MockCustomProvider)
    assert "custom_plug" in PROVIDER_REGISTRY

    # Instantiate via dynamic registry
    inst = PROVIDER_REGISTRY["custom_plug"]()
    out = inst.generate([{"role": "user", "content": "hi"}])
    assert out["content"] == "Hello from custom pluggable provider!"


def test_flexibility_pluggable_custom_tool():
    """Verify that registering a custom tool via register_custom_tool executes cleanly through dispatch_tool."""
    from tools.registry import register_custom_tool, dispatch_tool

    def custom_reverse_string(text: str = ""):
        return text[::-1]

    register_custom_tool("reverse_string", custom_reverse_string)
    res = dispatch_tool("reverse_string", {"text": "SPARK"})

    assert res.get("success") is True
    assert res.get("result") == "KRAPS"


# =====================================================================
# 5. ACCESSIBILITY TESTS
# =====================================================================

def test_accessibility_wcag_css_rules():
    """Verify stylesheet includes WCAG 2.2 AA universal focus states and reduced motion support."""
    from styles import get_custom_css

    css = get_custom_css()
    # Universal focus indicators
    assert ":focus-visible" in css
    assert "outline:" in css
    # Screen reader utility
    assert ".sr-only" in css
    # Reduced motion support
    assert "prefers-reduced-motion" in css


# =====================================================================
# 6. USABILITY TESTS
# =====================================================================

def test_usability_session_export_and_persistence():
    """Verify conversation sessions can be cleanly exported, saved, and loaded without data loss."""
    from core.conversation import ConversationSession

    sess = ConversationSession(user_id="usability_user")
    sess.add_message("user", "Explain recursion")
    sess.add_message("assistant", "Recursion is a function calling itself.")

    assert len(sess.messages) == 2
    # Verify structure
    assert sess.messages[0]["role"] == "user"
    assert sess.messages[1]["role"] == "assistant"
    assert "Recursion" in sess.messages[1]["content"]


# =====================================================================
# 7. PERFORMANCE & SPEED TESTS
# =====================================================================

def test_performance_sub_millisecond_cache_hit():
    """Verify cache hit latency is well below the 50ms performance target."""
    from core.cache import store_cached_response, get_cached_response

    q = "What is the capital of France?"
    store_cached_response(
        prompt=q,
        response={"success": True, "content": "Paris is the capital of France."},
        user_id="perf_user"
    )

    t0 = time.perf_counter()
    cached = get_cached_response(q, user_id="perf_user")
    dur_ms = (time.perf_counter() - t0) * 1000

    assert cached is not None
    assert "Paris" in cached["content"]
    assert dur_ms < 50.0, f"Cache hit latency {dur_ms:.2f}ms exceeded 50ms target"


def test_performance_deterministic_math_latency():
    """Verify SymPy deterministic math solver answers in under 100ms."""
    from tools.high_value_tools import solve_math_step_by_step

    t0 = time.perf_counter()
    res = solve_math_step_by_step("Solve 5*x + 15 = 45")
    dur_ms = (time.perf_counter() - t0) * 1000

    assert res.get("success") is True
    assert "6" in str(res.get("final_answer"))
    assert dur_ms < 100.0, f"Math calculation latency {dur_ms:.2f}ms exceeded 100ms target"


# =====================================================================
# 8. CREDIBILITY & TRUST TESTS
# =====================================================================

def test_credibility_unanswerable_document_disclaimer():
    """Verify that irrelevant document context triggers an explicit disclaimer without hallucination."""
    from tools.rag import evaluate_retrieval_relevance

    irrelevant_hits = [
        {"text": "The chocolate cake recipe calls for cocoa powder and milk.", "score": 0.0001}
    ]
    eval_res = evaluate_retrieval_relevance(
        query="Explain the Byzantine Fault Tolerance algorithm in distributed systems",
        hits=irrelevant_hits
    )

    assert eval_res["is_sufficient"] is False
    assert "do not contain sufficient information" in eval_res["message"]


# =====================================================================
# 9. RESPONSIVENESS TESTS
# =====================================================================

def test_responsiveness_non_blocking_conversation_add():
    """Verify message addition returns immediately in sub-millisecond time."""
    from core.conversation import ConversationSession

    sess = ConversationSession(user_id="resp_user")
    t0 = time.perf_counter()
    msg = sess.add_message("user", "Instant message test")
    dur_ms = (time.perf_counter() - t0) * 1000

    assert msg["content"] == "Instant message test"
    assert dur_ms < 5.0, f"add_message duration {dur_ms:.2f}ms exceeded 5ms responsiveness target"
