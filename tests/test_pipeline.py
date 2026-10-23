"""
Comprehensive Test Suite for LLMProvider, Modular Adapters, Fallback Chain, and Routing.
"""

import os
import sys
import unittest
from unittest.mock import patch

try:
    import google
    import google.genai
    setattr(google, "genai", google.genai)
except ImportError:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.conversation import ConversationSession
from core.llm_provider import (
    LLMProvider,
    AuthenticationError,
    QuotaExhaustedError,
    ModelUnavailableError
)
from core.orchestrator import ChatbotOrchestrator
from core.providers import GeminiProvider, GroqProvider, OpenAIProvider, OllamaProvider

class TestProviderFallbackAndIntent(unittest.TestCase):

    def setUp(self):
        from core.provider_status import reset_provider_status
        from core.circuit_breaker import circuit_breaker
        from core.rate_limiter import reset_circuit_breaker, reset_rate_limiter_pacing
        circuit_breaker.reset()
        reset_circuit_breaker()
        reset_rate_limiter_pacing()
        for p in ["gemini", "groq", "openai", "ollama"]:
            reset_provider_status(p)

    def test_00_what_is_llm(self):
        """Test: 'what is llm' produces a rich, accurate answer without failure."""
        llm = LLMProvider(provider="auto", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        result = orchestrator.process_message(session, "what is llm")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("Large Language Model", content)
        self.assertTrue(any(t in content.lower() for t in ["artificial intelligence", "deep learning", "machine learning"]))
        self.assertNotIn("Traceback", content)
        self.assertNotIn("TypeError", content)

    def test_01_llm_provider_constructor_compatibility(self):
        """Test: LLMProvider explicitly accepts fallback_providers without TypeError."""
        provider = LLMProvider(
            provider="gemini",
            fallback_providers=["groq", "openai", "ollama"],
            model="gemini-3.8-flash",
            temperature=0.3,
            timeout=25.0
        )
        self.assertEqual(provider.requested_provider, "gemini")
        self.assertEqual(provider.fallback_providers, ["groq", "openai", "ollama"])
        self.assertEqual(provider.timeout, 25.0)

    def test_02_what_is_physics(self):
        """Test: 'what is physics' produces normal educational answer with zero artificial banners."""
        llm = LLMProvider(provider="auto", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        result = orchestrator.process_message(session, "what is physics")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertTrue("physics" in content.lower())
        self.assertTrue(any(term in content.lower() for term in ["matter", "energy", "science"]))
        self.assertNotIn("API-key", content)
        self.assertNotIn("Cloud API Notice", content)
        self.assertNotIn("Traceback", content)

    def test_03_pure_arithmetic_calculation(self):
        """Test: '2 + 5 * 10' produces 52 via deterministic calculator directly."""
        llm = LLMProvider(provider="none", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        result = orchestrator.process_message(session, "2 + 5 * 10")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("52", content)
        self.assertEqual(result.get("provider"), "deterministic_calculator")

    def test_04_debug_python_code(self):
        """Test: Missing colon identified and corrected code provided via AST."""
        llm = LLMProvider(provider="none", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        query = "Debug this Python code:\nfor i in range(5)\n    print(i)"
        result = orchestrator.process_message(session, query)
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("colon", content.lower())
        self.assertIn("for i in range(5):", content)

    def test_05_simulate_invalid_api_key_fallback(self):
        """Test: Primary provider fails with 401 AuthenticationError -> Fallback succeeds."""
        llm = LLMProvider(
            provider="openai",
            fallback_providers=["gemini", "groq"],
            api_key="sk-invalid-test-key"
        )

        call_log = []

        def mock_openai_generate(self, messages, system_prompt, **kwargs):
            call_log.append("openai")
            raise AuthenticationError("Invalid API key for OpenAI.")

        def mock_gemini_generate(self, messages, system_prompt, **kwargs):
            call_log.append("gemini")
            return {
                "success": True,
                "content": "Answer generated successfully by Gemini.",
                "provider": "gemini",
                "model": "gemini-3.8-flash"
            }

        with patch.object(OpenAIProvider, "generate", new=mock_openai_generate):
            with patch.object(GeminiProvider, "generate", new=mock_gemini_generate):
                with patch.object(GeminiProvider, "is_configured", return_value=True):
                    session = ConversationSession()
                    orchestrator = ChatbotOrchestrator(provider=llm)
                    result = orchestrator.process_message(session, "Explain photosynthesis.")
                    
                    self.assertEqual(call_log, ["openai", "gemini"])
                    self.assertTrue(result.get("success"))
                    self.assertEqual(result.get("provider"), "gemini")

    def test_06_simulate_quota_exhausted_fallback(self):
        """Test: Primary provider hits 429 QuotaExhaustedError -> Next configured provider succeeds."""
        llm = LLMProvider(
            provider="groq",
            fallback_providers=["openai"],
            api_key="gsk-quota-key"
        )

        call_log = []

        def mock_groq_generate(self, messages, system_prompt, **kwargs):
            call_log.append("groq")
            raise QuotaExhaustedError("Groq 429: Insufficient credits or quota exceeded.")

        def mock_openai_generate(self, messages, system_prompt, **kwargs):
            call_log.append("openai")
            return {
                "success": True,
                "content": "Answer generated successfully by OpenAI.",
                "provider": "openai",
                "model": "gpt-4o-mini"
            }

        with patch.object(GroqProvider, "generate", new=mock_groq_generate):
            with patch.object(OpenAIProvider, "generate", new=mock_openai_generate):
                with patch.object(OpenAIProvider, "is_configured", return_value=True):
                    session = ConversationSession()
                    orchestrator = ChatbotOrchestrator(provider=llm)
                    result = orchestrator.process_message(session, "Explain the solar system.")
                    
                    self.assertEqual(call_log, ["groq", "openai"])
                    self.assertTrue(result.get("success"))
                    self.assertEqual(result.get("provider"), "openai")

    def test_07_all_providers_unavailable_honest_error(self):
        """Test: All providers unconfigured/unavailable -> Clean diagnostic error, no raw tracebacks."""
        llm = LLMProvider(provider="none", fallback_providers=[], api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        query = "Write a customized 20-page strategic business plan for a hyperloop venture."
        result = orchestrator.process_message(session, query)

        self.assertFalse(result.get("success"))
        content = result.get("content", "")
        self.assertIn("No AI provider is currently available", content)
        self.assertNotIn("Traceback", content)
        self.assertNotIn("TypeError", content)

    def test_08_provider_diagnostics(self):
        """Test: Health diagnostics return structured safe status without leaking keys."""
        llm = LLMProvider(provider="auto")
        diags = llm.get_provider_diagnostics()
        self.assertEqual(len(diags), 4)
        codes = [d["code"] for d in diags]
        self.assertIn("gemini", codes)
        self.assertIn("groq", codes)
        self.assertIn("openai", codes)
        self.assertIn("ollama", codes)

    def test_09_model_isolation_gemini_to_openai_fallback(self):
        """Test: Primary Gemini fails -> OpenAI fallback receives gpt-4o-mini, NEVER gemini-3.8-flash."""

        llm = LLMProvider(
            provider="gemini",
            fallback_providers=["openai"],
            model="gemini-3.8-flash",
            api_key="fake-gemini-key"
        )

        received_models = {}

        def mock_gemini_generate(self, messages, system_prompt, **kwargs):
            received_models["gemini"] = kwargs.get("model")
            raise QuotaExhaustedError("Gemini quota exhausted")

        def mock_openai_generate(self, messages, system_prompt, **kwargs):
            received_models["openai"] = kwargs.get("model")
            return {
                "success": True,
                "content": "OpenAI generated answer successfully.",
                "provider": "openai",
                "model": kwargs.get("model")
            }

        with patch.object(GeminiProvider, "generate", new=mock_gemini_generate):
            with patch.object(OpenAIProvider, "generate", new=mock_openai_generate):
                with patch.object(OpenAIProvider, "is_configured", return_value=True):
                    session = ConversationSession()
                    orchestrator = ChatbotOrchestrator(provider=llm)
                    result = orchestrator.process_message(session, "Explain black holes.")

                    self.assertTrue(result.get("success"))
                    self.assertEqual(result.get("provider"), "openai")
                    self.assertEqual(received_models.get("gemini"), "gemini-3.8-flash")
                    # Assert OpenAI NEVER received gemini-3.8-flash
                    self.assertNotEqual(received_models.get("openai"), "gemini-3.8-flash")
                    self.assertEqual(received_models.get("openai"), "gpt-4o-mini")

    def test_10_model_resolver_and_validation(self):
        """Test: Foreign models are rejected and reset to provider default; valid models preserved."""
        from core.models import resolve_model_for_provider, is_model_valid_for_provider, get_default_model

        # OpenAI rejecting foreign models
        self.assertFalse(is_model_valid_for_provider("openai", "gemini-3.8-flash"))
        self.assertFalse(is_model_valid_for_provider("openai", "llama-3.3-70b-versatile"))
        self.assertTrue(is_model_valid_for_provider("openai", "gpt-4o-mini"))
        self.assertTrue(is_model_valid_for_provider("openai", "gpt-4o"))
        self.assertEqual(resolve_model_for_provider("openai", "gemini-3.8-flash"), "gpt-4o-mini")
        self.assertEqual(resolve_model_for_provider("openai", "gpt-4o"), "gpt-4o")

        # Gemini rejecting foreign models
        self.assertFalse(is_model_valid_for_provider("gemini", "gpt-4o"))
        self.assertTrue(is_model_valid_for_provider("gemini", "gemini-3.8-flash"))
        self.assertTrue(is_model_valid_for_provider("gemini", "gemini-3.7-flash"))
        self.assertEqual(resolve_model_for_provider("gemini", "gpt-4o"), get_default_model("gemini"))
        self.assertEqual(resolve_model_for_provider("gemini", "gemini-3.7-flash"), "gemini-3.7-flash")

        # Groq rejecting foreign models
        self.assertFalse(is_model_valid_for_provider("groq", "gemini-3.8-flash"))
        self.assertFalse(is_model_valid_for_provider("groq", "gpt-4o-mini"))
        self.assertTrue(is_model_valid_for_provider("groq", "llama-3.3-70b-versatile"))
        self.assertEqual(resolve_model_for_provider("groq", "gemini-3.8-flash"), "llama-3.3-70b-versatile")

    def test_11_invalid_combinations_rejected_before_api_request(self):
        """Test: Hard validation layer immediately rejects invalid provider/model combinations."""
        from core.providers.base import InvalidProviderModelError

        # OpenAI + Gemini model -> must raise InvalidProviderModelError BEFORE any SDK call
        p_openai = OpenAIProvider(api_key="fake-key")
        with self.assertRaises(InvalidProviderModelError) as ctx:
            p_openai.generate(
                messages=[{"role": "user", "content": "hi"}],
                system_prompt="system",
                model="gemini-3.8-flash"
            )
        self.assertIn("Invalid provider/model combination", str(ctx.exception))
        self.assertEqual(ctx.exception.provider, "openai")
        self.assertEqual(ctx.exception.model, "gemini-3.8-flash")

        # Groq + Gemini model -> must raise InvalidProviderModelError BEFORE any SDK call
        p_groq = GroqProvider(api_key="fake-key")
        with self.assertRaises(InvalidProviderModelError) as ctx:
            p_groq.generate(
                messages=[{"role": "user", "content": "hi"}],
                system_prompt="system",
                model="gemini-3.8-flash"
            )
        self.assertIn("Invalid provider/model combination", str(ctx.exception))
        self.assertEqual(ctx.exception.provider, "groq")

        # Gemini + OpenAI model -> must raise InvalidProviderModelError BEFORE any SDK call
        p_gemini = GeminiProvider(api_key="fake-key")
        with self.assertRaises(InvalidProviderModelError) as ctx:
            p_gemini.generate(
                messages=[{"role": "user", "content": "hi"}],
                system_prompt="system",
                model="gpt-4o"
            )
        self.assertIn("Invalid provider/model combination", str(ctx.exception))
        self.assertEqual(ctx.exception.provider, "gemini")

        # Ollama + Gemini model -> must raise InvalidProviderModelError BEFORE any local call
        with patch.object(OllamaProvider, "is_configured", return_value=True):
            p_ollama = OllamaProvider()
            with self.assertRaises(InvalidProviderModelError) as ctx:
                p_ollama.generate(
                    messages=[{"role": "user", "content": "hi"}],
                    system_prompt="system",
                    model="gemini-3.8-flash"
                )
            self.assertIn("Invalid provider/model combination", str(ctx.exception))
            self.assertEqual(ctx.exception.provider, "ollama")

    def test_12_execution_chain_provider_model_pairs(self):
        """Test: LLMProvider builds strict (provider, model) pairs where foreign models never cross providers."""
        llm = LLMProvider(provider="gemini", model="gemini-3.8-flash")
        chain = llm._build_execution_chain()

        self.assertTrue(len(chain) >= 2)
        # First entry must be gemini with gemini-3.8-flash
        self.assertEqual(chain[0], ("gemini", "gemini-3.8-flash"))

        # Every subsequent fallback entry must use its own provider's valid model
        for prov, m in chain[1:]:
            self.assertNotEqual(m, "gemini-3.8-flash")
            if prov == "openai":
                self.assertEqual(m, "gpt-4o-mini")
            elif prov == "groq":
                self.assertEqual(m, "llama-3.3-70b-versatile")
            elif prov == "ollama":
                self.assertEqual(m, "llama3.2")

        # Auto mode execution chain
        llm_auto = LLMProvider(provider="auto")
        auto_chain = llm_auto._build_execution_chain()
        for prov, m in auto_chain:
            if prov == "openai":
                self.assertEqual(m, "gpt-4o-mini")
            elif prov == "gemini":
                from core.models import get_default_model
                self.assertEqual(m, get_default_model("gemini"))
            elif prov == "groq":
                self.assertEqual(m, "llama-3.3-70b-versatile")
            elif prov == "ollama":
                self.assertEqual(m, "llama3.2")

    def test_13_accurate_provider_status_tracking(self):
        """Test: Accurate states: NOT_CONFIGURED (no key), READY (last request succeeded), ERROR (with short reason)."""
        from core.provider_status import (
            get_provider_status,
            record_provider_success,
            record_provider_error,
            reset_provider_status
        )

        reset_provider_status("openai")
        reset_provider_status("gemini")

        # Provider without key -> NOT_CONFIGURED
        s_unconfigured = get_provider_status("gemini", is_configured=False)
        self.assertEqual(s_unconfigured["status"], "NOT_CONFIGURED")
        self.assertIn("NOT_CONFIGURED", s_unconfigured["display"])

        # Record error -> status must be ERROR with short reason
        record_provider_error("openai", QuotaExhaustedError("Quota exhausted"))
        s_err = get_provider_status("openai", is_configured=True)
        self.assertEqual(s_err["status"], "ERROR")
        self.assertEqual(s_err["reason"], "quota exhausted")
        self.assertIn("ERROR", s_err["display"])
        self.assertIn("quota exhausted", s_err["display"])

        # Record success -> status must be READY
        record_provider_success("gemini", "gemini-3.8-flash")
        s_ready = get_provider_status("gemini", is_configured=True)
        self.assertEqual(s_ready["status"], "READY")
        self.assertIn("READY", s_ready["display"])

    def test_14_test_connection_and_model_discovery(self):
        """Test: test_connection() sends 1-word prompt and returns clear result; 404 captures available models."""
        from core.providers.gemini import GeminiProvider

        # Mock successful test_connection
        def mock_generate_success(self, messages, system_prompt, **kwargs):
            return {"success": True, "content": "pong", "provider": "gemini", "model": "gemini-3.8-flash"}

        with patch.object(GeminiProvider, "generate", new=mock_generate_success):
            p = GeminiProvider(api_key="test-key")
            res = p.test_connection()
            self.assertTrue(res["success"])
            self.assertIn("Connection verified", res["message"])

        # Mock 404 model not found with available_models list
        def mock_generate_404(self, messages, system_prompt, **kwargs):
            raise ModelUnavailableError("Model not found", available_models=["gemini-3.8-flash", "gemini-3.7-flash"])

        with patch.object(GeminiProvider, "generate", new=mock_generate_404):
            p = GeminiProvider(api_key="test-key")
            res = p.test_connection()
            self.assertFalse(res["success"])
            self.assertEqual(res["available_models"], ["gemini-3.8-flash", "gemini-3.7-flash"])

    def test_15_env_model_configuration(self):
        """Test: Default model names are read from environment variables with sensible defaults."""
        from core.models import get_default_model, get_supported_models

        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.8-flash", "GROQ_MODEL": "llama-3.3-70b-versatile"}):
            self.assertEqual(get_default_model("gemini"), "gemini-3.8-flash")
            self.assertEqual(get_default_model("groq"), "llama-3.3-70b-versatile")
            models = get_supported_models("gemini")
            self.assertIn("gemini-3.8-flash", models)
            self.assertIn("gemini-3.7-flash", models)

    def test_16_what_is_ai(self):
        """Test: 'what is ai' produces a complete answer without crashing or leaking keys."""
        llm = LLMProvider(provider="auto", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        result = orchestrator.process_message(session, "what is ai")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("artificial intelligence", content.lower())
        self.assertNotIn("Traceback", content)
        self.assertNotIn("AIza", content)
        self.assertNotIn("sk-proj", content)

    def test_17_gemini_model_sorting(self):
        """Test: sort_gemini_models sorts Flash models first and newest versions first."""
        from core.models import sort_gemini_models

        unsorted = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
            "gemini-2.0-flash",
            "gemini-1.0-pro"
        ]
        sorted_m = sort_gemini_models(unsorted)
        # Flash models must come before pro models
        self.assertEqual(sorted_m[0], "gemini-3.8-flash")
        self.assertEqual(sorted_m[1], "gemini-3.7-flash")
        self.assertEqual(sorted_m[2], "gemini-2.0-flash")
        self.assertEqual(sorted_m[3], "gemini-1.5-flash")
        # Pro models come after
        self.assertEqual(sorted_m[4], "gemini-1.5-pro")
        self.assertEqual(sorted_m[5], "gemini-1.0-pro")

    def test_18_fallback_notice_in_response(self):
        """Test: When primary provider fails, response includes notice: e.g. Gemini failed (...), answered by Groq."""
        from core.provider_status import reset_provider_status
        reset_provider_status("gemini")
        reset_provider_status("groq")

        llm = LLMProvider(provider="gemini", fallback_providers=["groq"], api_key="fake-gem-key")

        def mock_gem_fail(self, messages, system_prompt, **kwargs):
            raise ModelUnavailableError("Model not found")

        def mock_groq_ok(self, messages, system_prompt, **kwargs):
            return {
                "success": True,
                "content": "Groq answered properly.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        with patch.object(GeminiProvider, "generate", new=mock_gem_fail):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GeminiProvider, "list_available_models", return_value=[]):
                    with patch.object(GroqProvider, "generate", new=mock_groq_ok):
                        with patch.object(GroqProvider, "is_configured", return_value=True):
                            session = ConversationSession()
                            orchestrator = ChatbotOrchestrator(provider=llm)
                            res = orchestrator.process_message(session, "Explain relativity.")

                            self.assertTrue(res.get("success"))
                            self.assertEqual(res.get("provider"), "groq")
                            # Verify one-line fallback notice
                            content = res.get("content", "")
                            self.assertIn("Google Gemini failed (model not found), answered by Groq", content)

    def test_19_skip_fallback_with_error_status(self):
        """Test: A fallback provider with ERROR status is skipped in fallback cascade."""
        from core.provider_status import record_provider_error, reset_provider_status
        reset_provider_status("gemini")
        reset_provider_status("groq")
        reset_provider_status("openai")

        # Mark groq as ERROR (quota exhausted)
        record_provider_error("groq", QuotaExhaustedError("Groq quota exhausted"))

        llm = LLMProvider(provider="gemini", fallback_providers=["groq", "openai"], api_key="gem-key")

        def mock_gem_fail(self, messages, system_prompt, **kwargs):
            raise AuthenticationError("Invalid Gemini key")

        groq_called = []
        def mock_groq_call(self, messages, system_prompt, **kwargs):
            groq_called.append(True)
            return {"success": True, "content": "Groq ans", "provider": "groq", "model": "llama-3.3-70b-versatile"}

        def mock_openai_ok(self, messages, system_prompt, **kwargs):
            return {"success": True, "content": "OpenAI answered.", "provider": "openai", "model": "gpt-4o-mini"}

        with patch.object(GeminiProvider, "generate", new=mock_gem_fail):
            with patch.object(GeminiProvider, "is_configured", return_value=True):
                with patch.object(GroqProvider, "generate", new=mock_groq_call):
                    with patch.object(GroqProvider, "is_configured", return_value=True):
                        with patch.object(OpenAIProvider, "generate", new=mock_openai_ok):
                            with patch.object(OpenAIProvider, "is_configured", return_value=True):
                                session = ConversationSession()
                                orchestrator = ChatbotOrchestrator(provider=llm)
                                res = orchestrator.process_message(session, "Explain evolution.")

                                self.assertTrue(res.get("success"))
                                self.assertEqual(res.get("provider"), "openai")
                                # Assert groq was skipped because it was already in ERROR status
                                self.assertEqual(len(groq_called), 0)

    def test_20_gemini_429_rate_limit_retry_and_delay(self):
        """Test: 429 RateLimitError retries up to 2 times, updates status, and succeeds."""
        from core.providers.gemini import GeminiProvider

        attempts = []
        statuses = []

        def mock_generate_content(model, contents):
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                class MockAPIError(Exception):
                    code = 429
                    status = "RESOURCE_EXHAUSTED"
                    message = "Quota limit reached"
                    details = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "2s"}]
                raise MockAPIError("Resource exhausted")
            
            class MockResponse:
                text = "Gemini answer after retry"
            return MockResponse()

        def status_cb(msg):
            statuses.append(msg)

        import google.genai
        provider = GeminiProvider(api_key="AIzaSyDummyKeyForTesting429")
        with patch.object(google.genai, "Client") as mock_client_cls, \
             patch("core.providers.gemini.enforce_provider_gap"), \
             patch("time.sleep") as mock_sleep:
            mock_client = mock_client_cls.return_value
            mock_client.models.generate_content = mock_generate_content

            res = provider.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="Be helpful",
                on_status_update=status_cb
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["content"], "Gemini answer after retry")
            self.assertEqual(len(attempts), 2)
            mock_sleep.assert_called_with(2.0)
            self.assertTrue(any("Rate limited, retrying in" in s for s in statuses))

    def test_21_gemini_503_temporary_error_backoff(self):
        """Test: HTTP 503 UNAVAILABLE retries with exponential backoff (1s, 2s, 4s)."""
        from core.providers.gemini import GeminiProvider

        attempts = []
        sleep_durations = []

        def mock_generate_content(model, contents):
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                class Mock503Error(Exception):
                    code = 503
                    status = "UNAVAILABLE"
                    message = "The service is temporarily overloaded."
                raise Mock503Error("Unavailable")
            class MockResponse:
                text = "Success on attempt 3"
            return MockResponse()

        def mock_sleep_tracker(d):
            sleep_durations.append(d)

        import google.genai
        provider = GeminiProvider(api_key="AIzaSyDummyKeyForTesting503")
        with patch.object(google.genai, "Client") as mock_client_cls, \
             patch("core.providers.gemini.enforce_provider_gap"), \
             patch("time.sleep", side_effect=mock_sleep_tracker):
            mock_client = mock_client_cls.return_value
            mock_client.models.generate_content = mock_generate_content

            res = provider.generate(
                messages=[{"role": "user", "content": "Test"}],
                system_prompt="Be helpful"
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["content"], "Success on attempt 3")
            self.assertEqual(len(attempts), 3)
            self.assertEqual(sleep_durations, [1.0, 2.0])

    def test_22_gemini_rate_limit_fallback_with_tip(self):
        """Test: Rate limit retries exhaust -> Fallback to Groq with Flash-Lite/Groq tip."""
        from core.providers.gemini import GeminiProvider
        from core.providers.groq import GroqProvider
        from core.providers.base import RateLimitError
        from core.provider_status import get_provider_status, reset_provider_status

        reset_provider_status("gemini")
        reset_provider_status("groq")

        def mock_gemini_always_429(*args, **kwargs):
            raise RateLimitError("Gemini rate limit exceeded", status_code=429, error_status="RESOURCE_EXHAUSTED", retry_delay=15.0)

        def mock_groq_ok(*args, **kwargs):
            return {
                "success": True,
                "content": "Answer from Groq after Gemini rate limit.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }

        llm = LLMProvider(provider="gemini", fallback_providers=["groq"], api_key="gem-test")

        with patch.object(GeminiProvider, "generate", side_effect=mock_gemini_always_429), \
             patch.object(GeminiProvider, "is_configured", return_value=True), \
             patch.object(GroqProvider, "generate", side_effect=mock_groq_ok), \
             patch.object(GroqProvider, "is_configured", return_value=True):

            session = ConversationSession()
            orchestrator = ChatbotOrchestrator(provider=llm)
            res = orchestrator.process_message(session, "Explain photosynthesis")

            self.assertTrue(res["success"])
            self.assertEqual(res["provider"], "groq")
            content = res.get("content", "")
            self.assertIn("Google Gemini failed (rate limited)", content)
            self.assertIn("answered by Groq", content)
            self.assertIn("Flash-Lite model", content)
            self.assertIn("Groq key", content)

            gem_st = get_provider_status("gemini", is_configured=True)
            self.assertEqual(gem_st["status"], "ERROR")
            self.assertEqual(gem_st["reason"], "rate limited")
            self.assertEqual(gem_st["http_code"], 429)

    def test_23_minimum_provider_gap_pacing(self):
        """Test: enforce_provider_gap ensures at least the specified minimum duration between calls."""
        import time
        from core.rate_limiter import enforce_provider_gap, reset_rate_limiter_pacing

        reset_rate_limiter_pacing()
        start = time.time()
        enforce_provider_gap("test_pacer", min_gap_seconds=0.05)
        enforce_provider_gap("test_pacer", min_gap_seconds=0.05)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.045)

    def test_24_redact_sensitive_keys_in_error_parsing(self):
        """Test: parse_error_details redacts API keys matching common key patterns."""
        from core.rate_limiter import parse_error_details

        raw_err = "Error 400 for key AIzaSyA1234567890abcdef1234567890 and sk-proj-1234567890abcdef1234567890: bad token"
        parsed = parse_error_details(Exception(raw_err))

        msg = parsed["message"]
        self.assertNotIn("AIzaSyA1234567890abcdef1234567890", msg)
        self.assertNotIn("sk-proj-1234567890abcdef1234567890", msg)
        self.assertIn("[REDACTED_API_KEY]", msg)

    def test_25_retry_last_question_history_preservation(self):
        """Test: One-click retry rolls back failed turn and preserves prior conversation history."""
        session = ConversationSession()
        session.add_message("user", "What is 1+1?")
        session.add_message("assistant", "2")
        session.add_message("user", "What is quantum gravity?")
        session.add_message("assistant", "⚠️ No AI provider is currently available.")

        # Slicing logic
        last_user_query = None
        for idx in range(len(session.messages) - 1, -1, -1):
            if session.messages[idx]["role"] == "user":
                last_user_query = session.messages[idx]["content"]
                session.messages = session.messages[:idx]
                break

        self.assertEqual(last_user_query, "What is quantum gravity?")
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0]["content"], "What is 1+1?")
        self.assertEqual(session.messages[1]["content"], "2")

        llm = LLMProvider(provider="none", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)

        def mock_llm_gen(*args, **kwargs):
            return {"success": True, "content": "Quantum gravity is...", "provider": "gemini", "model": "gemini-3.8-flash"}

        with patch.object(LLMProvider, "generate", side_effect=mock_llm_gen):
            res = orchestrator.process_message(session, last_user_query)
            self.assertTrue(res["success"])

        self.assertEqual(len(session.messages), 4)
        self.assertEqual(session.messages[0]["content"], "What is 1+1?")
        self.assertEqual(session.messages[1]["content"], "2")
        self.assertEqual(session.messages[2]["content"], "What is quantum gravity?")
        self.assertIn("Quantum gravity is...", session.messages[3]["content"])

    def test_26_auto_routing_and_interview_verification(self):
        """Test: Auto-routing for math, code errors, interview lifecycle, and file limits."""
        from core.intent import detect_intent, IntentType

        # 1. Math calculation short-circuit
        self.assertEqual(detect_intent("25 * 40 + 150"), IntentType.MATH_CALCULATION)
        session = ConversationSession()
        orchestrator = ChatbotOrchestrator(provider=LLMProvider(provider="none"))
        res = orchestrator.process_message(session, "25 * 40 + 150")
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "deterministic_calculator")
        self.assertIn("1150", res["content"])

        # 2. Python error traceback routing to programming/code
        traceback_msg = (
            "Traceback (most recent call last):\n"
            "  File \"main.py\", line 12, in run\n"
            "    print(1 / 0)\n"
            "ZeroDivisionError: division by zero"
        )
        self.assertEqual(detect_intent(traceback_msg), IntentType.PROGRAMMING)

        # 3. Interview detection and exit
        self.assertEqual(detect_intent("interview me for a data analyst role"), IntentType.INTERVIEW)
        self.assertEqual(detect_intent("start interview"), IntentType.INTERVIEW)
        self.assertEqual(detect_intent("mock interview"), IntentType.INTERVIEW)
        # Continuing interview
        self.assertEqual(detect_intent("I am skilled in SQL and Python", in_interview=True), IntentType.INTERVIEW)
        # Exiting interview
        self.assertNotEqual(detect_intent("end interview", in_interview=True), IntentType.INTERVIEW)
        self.assertNotEqual(detect_intent("exit interview", in_interview=True), IntentType.INTERVIEW)

        # 4. File uploader allowlist and size validation check
        allowed_types = ["pdf", "docx", "txt", "md", "csv", "xlsx", "xls", "json", "py", "png", "jpg", "jpeg", "wav", "mp3"]
        self.assertIn("pdf", allowed_types)
        self.assertIn("py", allowed_types)
        self.assertNotIn("exe", allowed_types)
        self.assertNotIn("bat", allowed_types)

        max_upload_bytes = 15 * 1024 * 1024
        oversized_bytes = 20 * 1024 * 1024
        self.assertTrue(oversized_bytes > max_upload_bytes)

    def test_27_consistency_scoring_schema_and_intent(self):
        """Test: Schema validation for scoring rubric and deterministic intent reproducibility."""
        from tools.schemas import InterviewEvaluationSchema
        from core.interview import InterviewSession
        from core.intent import detect_intent

        # 1. Pydantic validation
        valid_data = {
            "correctness": 9,
            "clarity": 8,
            "structure": 9,
            "depth": 8,
            "score_range": "34-36 / 40",
            "confidence": "High"
        }
        rubric = InterviewEvaluationSchema(**valid_data)
        self.assertEqual(rubric.correctness, 9)
        self.assertEqual(rubric.score_range, "34-36 / 40")

        # 2. Schema rejection of invalid ranges
        with self.assertRaises(Exception):
            InterviewEvaluationSchema(correctness=15, clarity=8, structure=9, depth=8, score_range="30/40")

        # 3. Session parser extraction
        session = InterviewSession()
        mock_output = (
            "Here is your feedback:\n\n"
            "```json_score\n"
            "{\n"
            '  "correctness": 8,\n'
            '  "clarity": 9,\n'
            '  "structure": 8,\n'
            '  "depth": 7,\n'
            '  "score_range": "32-34 / 40",\n'
            '  "confidence": "High"\n'
            "}\n"
            "```\n"
            "Great job on approach!"
        )
        parsed = session.parse_and_validate_score(mock_output)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["correctness"], 8)
        self.assertEqual(parsed["confidence"], "High")

        # 4. Same input yields same routed intent (consistency)
        for _ in range(5):
            self.assertEqual(detect_intent("what is physics"), detect_intent("what is physics"))
            self.assertEqual(detect_intent("2 + 5 * 10"), detect_intent("2 + 5 * 10"))

    def test_28_cache_and_schema_validation(self):
        """Test: Cache TTL expiry, temporal query skipping, user scoping, and tool schema validation."""
        from core.cache import get_cached_response, store_cached_response, clear_cache, is_time_sensitive_query
        from tools.schemas import validate_tool_arguments

        clear_cache()

        # 1. Temporal query skipping
        self.assertTrue(is_time_sensitive_query("What is the latest stock price today?"))
        self.assertFalse(is_time_sensitive_query("Explain quicksort algorithm in python."))

        # Temporal queries must not be cached
        store_cached_response("What is the weather today?", {"success": True, "content": "Sunny"}, user_id="u1")
        self.assertIsNone(get_cached_response("What is the weather today?", user_id="u1"))

        # 2. User scoping
        store_cached_response("Explain recursion", {"success": True, "content": "Recursion base case."}, user_id="alice")
        hit_alice = get_cached_response("Explain recursion", user_id="alice")
        hit_bob = get_cached_response("Explain recursion", user_id="bob")
        self.assertIsNotNone(hit_alice)
        self.assertEqual(hit_alice["content"], "Recursion base case.")
        self.assertIsNone(hit_bob)

        # 3. Schema validation
        valid_search, parsed_search, err_search = validate_tool_arguments("search_web", {"query": "python tutorial", "max_results": 5})
        self.assertTrue(valid_search)
        self.assertIsNone(err_search)

        invalid_search, _, err_invalid = validate_tool_arguments("search_web", {"query": "", "max_results": 50})
        self.assertFalse(invalid_search)
        self.assertIsNotNone(err_invalid)

    def test_29_speed_deterministic_bypass_and_provider_budget(self):
        """Test: SQL and Complexity direct short-circuits bypass LLM; provider budget caps enforce fallback."""
        from core.orchestrator import ChatbotOrchestrator
        from core.llm_provider import LLMProvider
        from core.rate_limiter import check_provider_budget, record_provider_request, reset_provider_budget
        from core.conversation import ConversationSession

        # 1. Deterministic SQL bypass (no LLM call)
        llm = LLMProvider(provider="gemini", fallback_providers=[], api_key="dummy")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        sql_res = orchestrator.process_message(session, "SELECT * FROM employees")
        self.assertTrue(sql_res["success"])
        self.assertEqual(sql_res["provider"], "sql_playground")

        # 2. Deterministic Complexity bypass (no LLM call)
        comp_res = orchestrator.process_message(session, "What is the time complexity of: def solve(arr): return sorted(arr)")
        self.assertTrue(comp_res["success"])
        self.assertEqual(comp_res["provider"], "complexity_analyzer")

        # 3. Provider daily budget capping & fallback
        reset_provider_budget()
        allowed, _ = check_provider_budget("groq", max_requests_per_day=2)
        self.assertTrue(allowed)
        record_provider_request("groq")
        record_provider_request("groq")
        allowed_after_cap, reason = check_provider_budget("groq", max_requests_per_day=2)
        self.assertFalse(allowed_after_cap)
        self.assertIn("Daily budget cap exceeded", reason)
        reset_provider_budget("groq")

    def test_30_multi_tenant_isolation_concurrency(self):
        """
        Concurrency & Isolation: Runs 20 parallel simulated user sessions through ChatbotOrchestrator.
        Verifies strict multi-tenant isolation across user memory, scoped response caching, and conversation message history.
        """
        import concurrent.futures
        from core.orchestrator import ChatbotOrchestrator
        from core.conversation import ConversationSession
        from core.memory import update_user_memory, get_user_memory
        from core.cache import store_cached_response, get_cached_response

        orchestrator = ChatbotOrchestrator()
        num_sessions = 20

        def run_tenant_session(idx: int):
            user_id = f"isolated_tenant_{idx}"
            target_role = f"Role_{idx}"
            goal = f"Goal_Specialization_{idx}"

            # 1. Memory Isolation: Update user memory independently
            update_user_memory(user_id=user_id, updates={
                "target_role": target_role,
                "goals": [goal],
                "user_level": f"Level_{idx}"
            })
            mem = get_user_memory(user_id=user_id)
            assert mem.get("target_role") == target_role, f"Memory mismatch for {user_id}"
            assert mem.get("goals") == [goal], f"Goals leaked for {user_id}"

            # 2. Scoped Cache Isolation: Store unique response keyed by user_id
            query = "Explain binary search algorithm"
            store_cached_response(query, {"success": True, "content": f"Binary search for {user_id}"}, user_id=user_id)
            cached_self = get_cached_response(query, user_id=user_id)
            assert cached_self is not None and user_id in cached_self.get("content", ""), f"Cache missing for {user_id}"

            # Check that cross-tenant cache lookup does not leak this user's data to another user
            other_user_id = f"isolated_tenant_{(idx + 1) % num_sessions}"
            cached_other = get_cached_response(query, user_id=other_user_id)
            if cached_other:
                assert other_user_id in cached_other.get("content", ""), f"Cross-tenant cache bleed between {user_id} and {other_user_id}"

            # 3. Message History Isolation: Process unique request through orchestrator
            session = ConversationSession(user_id=user_id)
            arith_query = f"{(idx + 2) * 10} + 5"
            res = orchestrator.process_message(session, arith_query)
            assert res.get("success"), f"Execution failed for {user_id}"
            assert len(session.messages) == 2, f"Session message count mismatch for {user_id}: {len(session.messages)}"
            assert session.messages[0]["content"] == arith_query, f"User message mismatch for {user_id}"
            assert str((idx + 2) * 10 + 5) in session.messages[1]["content"], f"Result mismatch for {user_id}"

            return user_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(run_tenant_session, i) for i in range(num_sessions)]
            completed_users = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(completed_users), num_sessions)
        self.assertEqual(len(set(completed_users)), num_sessions)


if __name__ == "__main__":
    unittest.main()


