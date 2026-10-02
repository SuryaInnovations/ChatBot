"""
Comprehensive Test Suite for LLMProvider, Modular Adapters, Fallback Chain, and Routing.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.conversation import ConversationSession
from core.llm_provider import (
    LLMProvider,
    AuthenticationError,
    QuotaExhaustedError,
    ProviderConnectionError,
    ProviderStatus
)
from core.orchestrator import ChatbotOrchestrator
from core.providers import GeminiProvider, GroqProvider, OpenAIProvider, OllamaProvider

class TestProviderFallbackAndIntent(unittest.TestCase):

    def test_00_what_is_llm(self):
        """Test: 'what is llm' produces a rich, accurate answer without failure."""
        llm = LLMProvider(provider="auto", api_key="")
        orchestrator = ChatbotOrchestrator(provider=llm)
        session = ConversationSession()

        result = orchestrator.process_message(session, "what is llm")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("Large Language Model", content)
        self.assertIn("artificial intelligence", content.lower())
        self.assertNotIn("Traceback", content)
        self.assertNotIn("TypeError", content)

    def test_01_llm_provider_constructor_compatibility(self):
        """Test: LLMProvider explicitly accepts fallback_providers without TypeError."""
        provider = LLMProvider(
            provider="gemini",
            fallback_providers=["groq", "openai", "ollama"],
            model="gemini-2.5-flash",
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
        self.assertIn("Physics is the branch of science", content)
        self.assertIn("matter, energy, motion, forces", content)
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
                "model": "gemini-2.5-flash"
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

if __name__ == "__main__":
    unittest.main()
