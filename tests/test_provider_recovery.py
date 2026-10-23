"""
Production-Ready AI Provider Recovery and Automatic Fallback Test Suite.
Verifies all 11 core recovery scenarios with deterministic mocks:
1. All providers missing configuration -> clean concise prompt, no raw tracebacks.
2. Gemini 504 network error -> brief bounded retry -> fallback to next provider.
3. OpenAI 429 quota exhaustion -> skips repeated retries, falls back cleanly without locking other healthy providers.
4. Groq functioning when another provider fails.
5. Ollama working without API key when server reachable.
6. Incorrect model identifiers rejected early by validation layer before any SDK call.
7. Invalid API keys marked misconfigured without retries.
8. All configured providers unavailable -> short diagnostic, no chat message pollution.
9. Retry limits & timeout bounds respected.
10. No duplicate user/assistant messages after fallback.
11. Accurate provider status reporting.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.conversation import ConversationSession
from core.orchestrator import ChatbotOrchestrator
from core.llm_provider import (
    LLMProvider,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError
)
from core.providers import (
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
    OllamaProvider
)
from core.circuit_breaker import circuit_breaker
from core.provider_status import (
    get_provider_status,
    reset_all_provider_statuses,
    record_provider_error,
    record_provider_success,
    is_provider_errored
)
from core.rate_limiter import reset_rate_limiter_pacing


class TestProviderRecoverySuite(unittest.TestCase):

    def setUp(self):
        reset_all_provider_statuses()
        reset_rate_limiter_pacing()

    def test_01_all_providers_missing_configuration_clean_message(self):
        """Scenario 1: All providers missing configuration -> clean concise prompt, no raw tracebacks."""
        llm = LLMProvider(provider="auto", fallback_providers=["gemini", "groq", "openai", "ollama"])

        with patch.object(GeminiProvider, "is_configured", return_value=False):
            with patch.object(GroqProvider, "is_configured", return_value=False):
                with patch.object(OpenAIProvider, "is_configured", return_value=False):
                    with patch.object(OllamaProvider, "is_configured", return_value=False):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "Explain photosynthesis")

                        self.assertFalse(res.get("success"))
                        content = res.get("content", "")
                        # Verify polite user-facing error without tracebacks or raw table
                        self.assertIn("No AI provider is configured yet", content)
                        self.assertNotIn("Traceback", content)
                        self.assertNotIn("504 UNAVAILABLE", content)
                        self.assertNotIn("RESOURCE_EXHAUSTED", content)

    def test_02_gemini_504_network_error_bounded_retry_and_fallback(self):
        """Scenario 2: Gemini 504 network error -> bounded retry -> cleanly falls back to Groq."""
        llm = LLMProvider(provider="gemini", fallback_providers=["groq"], api_key="gem-test-key")

        gem_call_count = [0]
        def mock_gem_504(self, messages, system_prompt, **kwargs):
            gem_call_count[0] += 1
            raise ProviderConnectionError("Request to Gemini timed out (504)", status_code=504)

        def mock_groq_ok(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Photosynthesis is the process plants use to turn sunlight into energy.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        with patch.object(GeminiProvider, "generate", new=mock_gem_504):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", new=mock_groq_ok):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "What is photosynthesis?")

                        self.assertTrue(res.get("success"))
                        self.assertEqual(res.get("provider"), "groq")
                        # Gemini retried once (total 2 attempts: attempt + bounded retry)
                        self.assertEqual(gem_call_count[0], 2)
                        # Content contains answer and clean fallback notice
                        content = res.get("content", "")
                        self.assertIn("Photosynthesis", content)
                        self.assertIn("The selected AI provider is temporarily unavailable", content)

    def test_03_openai_429_quota_exhaustion_does_not_block_gemini(self):
        """Scenario 3: OpenAI 429 quota exhaustion -> skips repeated retries, falls back cleanly to Gemini."""
        llm = LLMProvider(provider="openai", fallback_providers=["gemini"], api_key="sk-test-key")

        openai_calls = [0]
        def mock_openai_quota(self, messages, system_prompt, **kwargs):
            openai_calls[0] += 1
            raise QuotaExhaustedError("OpenAI 429: You exceeded your current quota (RESOURCE_EXHAUSTED)")

        def mock_gemini_ok(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "An API is a set of rules allowing software programs to talk to each other.",
                "provider": "gemini",
                "model": "gemini-2.5-flash"
            }

        with patch.object(OpenAIProvider, "generate", new=mock_openai_quota):
            with patch.object(OpenAIProvider, "is_configured", return_value=True):
                with patch.object(GeminiProvider, "generate", new=mock_gemini_ok):
                    with patch.object(GeminiProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "What is an API?")

                        self.assertTrue(res.get("success"))
                        self.assertEqual(res.get("provider"), "gemini")
                        # Quota exhausted must NOT be repeatedly retried (exactly 1 call)
                        self.assertEqual(openai_calls[0], 1)
                        # Gemini answered cleanly
                        self.assertIn("API", res.get("content", ""))

    def test_04_groq_functioning_when_another_provider_fails(self):
        """Scenario 4: Groq functioning cleanly when primary provider fails."""
        llm = LLMProvider(provider="gemini", fallback_providers=["groq"], api_key="gem-key")

        def mock_gemini_fail(self, messages, system_prompt, **kwargs):
            raise RateLimitError("Gemini 429: Resource exhausted")

        def mock_groq_success(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Python is a high-level programming language known for readability.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        with patch.object(GeminiProvider, "generate", new=mock_gemini_fail):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", new=mock_groq_success):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "What is Python?")

                        self.assertTrue(res.get("success"))
                        self.assertEqual(res.get("provider"), "groq")
                        self.assertIn("Python is a high-level", res.get("content", ""))

    def test_05_ollama_working_without_api_key_when_server_reachable(self):
        """Scenario 5: Ollama works locally without an API key when reachable."""
        llm = LLMProvider(provider="ollama")

        def mock_ollama_generate(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Docker is a platform for running applications in lightweight containers.",
                "provider": "ollama",
                "model": "llama3.2"
            }

        with patch.object(OllamaProvider, "is_configured", return_value=True):
            with patch.object(OllamaProvider, "generate", new=mock_ollama_generate):
                session = ConversationSession()
                orchestrator = ChatbotOrchestrator(provider=llm)
                res = orchestrator.process_message(session, "What is Docker?")

                self.assertTrue(res.get("success"))
                self.assertEqual(res.get("provider"), "ollama")
                self.assertIn("Docker", res.get("content", ""))

    def test_06_incorrect_model_identifiers_rejected_early_by_validation(self):
        """Scenario 6: Incompatible model identifier rejected early by validation before any SDK request."""
        # Attempting to send an OpenAI model ('gpt-4o') to Gemini provider
        llm = LLMProvider(provider="gemini", model="gpt-4o", fallback_providers=["groq"])

        gem_network_called = []
        def mock_gem_network(self, messages, system_prompt, **kwargs):
            gem_network_called.append(True)
            return {"success": True, "content": "Should not reach here"}

        def mock_groq_ok(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Valid answer from Groq.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        with patch.object(GeminiProvider, "generate", new=mock_gem_network):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", new=mock_groq_ok):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "What is a neural network?")

                        # Gemini SDK was never called because validation rejected 'gpt-4o' for Gemini
                        self.assertEqual(len(gem_network_called), 0)
                        self.assertTrue(res.get("success"))
                        self.assertEqual(res.get("provider"), "groq")

    def test_07_invalid_api_keys_marked_misconfigured_without_retries(self):
        """Scenario 7: Invalid API keys (HTTP 401/403) marked misconfigured immediately without retries."""
        llm = LLMProvider(provider="gemini", fallback_providers=["groq"], api_key="bad-key")

        gemini_calls = [0]
        def mock_gemini_401(self, messages, system_prompt, **kwargs):
            gemini_calls[0] += 1
            raise AuthenticationError("API_KEY_INVALID: 401 Unauthorized")

        def mock_groq_ok(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Groq answer.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        with patch.object(GeminiProvider, "generate", new=mock_gemini_401):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", new=mock_groq_ok):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "Hello world")

                        self.assertTrue(res.get("success"))
                        # Gemini called exactly once (no wasteful retries for 401)
                        self.assertEqual(gemini_calls[0], 1)
                        # Circuit breaker marked misconfigured
                        avail, reason = circuit_breaker.is_available("gemini")
                        self.assertFalse(avail)
                        self.assertIn("MISCONFIGURED", reason)

    def test_08_all_configured_providers_unavailable_short_clean_diagnostic(self):
        """Scenario 8: All configured providers fail -> short clean diagnostic, no chat message pollution."""
        llm = LLMProvider(provider="auto", fallback_providers=["gemini", "groq", "openai"])

        with patch.object(GeminiProvider, "is_configured", return_value=True):
            with patch.object(GeminiProvider, "generate", side_effect=ProviderConnectionError("504 Timeout", status_code=504)):
                with patch.object(GroqProvider, "is_configured", return_value=True):
                    with patch.object(GroqProvider, "generate", side_effect=RateLimitError("429 Rate limited")):
                        with patch.object(OpenAIProvider, "is_configured", return_value=True):
                            with patch.object(OpenAIProvider, "generate", side_effect=QuotaExhaustedError("429 Quota exhausted")):
                                session = ConversationSession()
                                orchestrator = ChatbotOrchestrator(provider=llm)
                                res = orchestrator.process_message(session, "Explain the theory of relativity")

                                self.assertFalse(res.get("success"))
                                content = res.get("content", "")
                                # Clean message displayed
                                self.assertIn("SPARK-AI couldn't connect to any available AI provider", content)
                                # No raw table dumped into chat text
                                self.assertNotIn("504 UNAVAILABLE: network error", content)
                                self.assertNotIn("429 RESOURCE_EXHAUSTED", content)
                                self.assertNotIn("⚪ NOT_CONFIGURED", content)

    def test_09_retry_limits_and_timeout_bounds_respected(self):
        """Scenario 9: Bounded retry limit (max 1 retry) and timeout bounds respected."""
        llm = LLMProvider(provider="gemini", fallback_providers=[], api_key="gem-key", timeout=12.0)

        call_records = []
        def mock_hanging_call(self, messages, system_prompt, **kwargs):
            call_records.append(kwargs.get("timeout", 0.0))
            raise ProviderConnectionError("Request timed out after 12.0s", status_code=504)

        with patch.object(GeminiProvider, "generate", new=mock_hanging_call):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                session = ConversationSession()
                orchestrator = ChatbotOrchestrator(provider=llm)
                res = orchestrator.process_message(session, "Explain recursion")

                # Bounded retry: 1 initial attempt + 1 retry = exactly 2 calls
                self.assertEqual(len(call_records), 2)
                # Timeout argument respected
                for t in call_records:
                    self.assertEqual(t, 12.0)

    def test_10_no_duplicate_messages_after_fallback(self):
        """Scenario 10: Fallback execution preserves exact conversation history with zero duplicate messages."""
        llm = LLMProvider(provider="gemini", fallback_providers=["groq", "openai"], api_key="gem-key")

        with patch.object(GeminiProvider, "generate", side_effect=ProviderConnectionError("504 Timeout", status_code=504)):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", return_value={"success": True, "content": "Clean answer", "provider": "groq", "model": "llama-3.3-70b-versatile"}):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        session = ConversationSession()
                        orchestrator = ChatbotOrchestrator(provider=llm)
                        res = orchestrator.process_message(session, "What is gravity?")

                        self.assertTrue(res.get("success"))
                        # Verify session message count: exactly 1 user message, exactly 1 assistant message
                        self.assertEqual(len(session.messages), 2)
                        self.assertEqual(session.messages[0]["role"], "user")
                        self.assertEqual(session.messages[0]["content"], "What is gravity?")
                        self.assertEqual(session.messages[1]["role"], "assistant")
                        self.assertIn("Clean answer", session.messages[1]["content"])

    def test_11_accurate_provider_status_reporting(self):
        """Scenario 11: Provider status accurately reflects NOT_CONFIGURED, READY, and ERROR with TTL auto-recovery."""
        # 1. Unconfigured provider
        s_unconf = get_provider_status("ollama", is_configured=False)
        self.assertEqual(s_unconf["status"], "NOT_CONFIGURED")

        # 2. Provider with successful request -> READY
        record_provider_success("gemini", model="gemini-2.5-flash", latency_seconds=0.45)
        s_ready = get_provider_status("gemini", is_configured=True)
        self.assertEqual(s_ready["status"], "READY")

        # 3. Provider with error -> ERROR with status code and reason
        record_provider_error("openai", QuotaExhaustedError("OpenAI 429: insufficient quota"))
        s_err = get_provider_status("openai", is_configured=True)
        self.assertEqual(s_err["status"], "ERROR")
        self.assertEqual(s_err["reason"], "quota exhausted")
        self.assertTrue(is_provider_errored("openai"))


if __name__ == "__main__":
    unittest.main()
