"""
Test Suite verifying the 7 required test cases from the specification:
1. 'what is physics' -> Normal educational answer.
2. '2 + 5 * 10' -> 52 via deterministic calculator.
3. 'Explain Python list comprehensions simply.' -> Clear educational explanation.
4. 'Debug this Python code:\nfor i in range(5)\n    print(i)' -> Missing colon identified and corrected code provided.
5. Simulate invalid API key -> Provider fails -> Fallback provider attempted.
6. Simulate quota exhaustion (429) -> Provider fails -> Next configured provider attempted.
7. Make every provider unavailable -> Clean user-facing error, no traceback, no fake response.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.conversation import ConversationSession
from core.llm_provider import (
    LLMProvider,
    AuthenticationError,
    QuotaExhaustedError,
    ProviderConnectionError
)
from core.provider_manager import ProviderManager, get_available_providers
from core.orchestrator import ChatbotOrchestrator
from core.intent import detect_intent, IntentType

class TestProviderFallbackAndIntent(unittest.TestCase):

    def test_01_what_is_physics(self):
        """Test 1: 'what is physics' produces normal educational answer with no warning banners."""
        manager = ProviderManager(primary_provider="groq", primary_key="")
        orchestrator = ChatbotOrchestrator(provider=manager)
        session = ConversationSession()

        result = orchestrator.process_message(session, "what is physics")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("Physics is the branch of science", content)
        self.assertIn("matter, energy, motion, forces", content)
        # Verify no artificial API-key warning or notice is in the text
        self.assertNotIn("API-key", content)
        self.assertNotIn("Cloud API Notice", content)
        self.assertNotIn("Traceback", content)

    def test_02_pure_arithmetic_calculation(self):
        """Test 2: '2 + 5 * 10' produces 52 via deterministic calculator directly."""
        manager = ProviderManager(primary_provider="none", primary_key="")
        orchestrator = ChatbotOrchestrator(provider=manager)
        session = ConversationSession()

        result = orchestrator.process_message(session, "2 + 5 * 10")
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("52", content)
        self.assertEqual(result.get("provider"), "deterministic_calculator")

    def test_03_explain_list_comprehensions(self):
        """Test 3: 'Explain Python list comprehensions simply.' with an available provider."""
        # Mock a successful provider response
        manager = ProviderManager(primary_provider="groq", primary_key="valid-mock-key")
        session = ConversationSession()
        
        with patch.object(LLMProvider, "chat_completion") as mock_call:
            mock_call.return_value = {
                "success": True,
                "content": "List comprehensions in Python provide a concise way to create lists.\nSyntax: `[expression for item in iterable]`\nExample: `squares = [x**2 for x in range(5)]`",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }
            orchestrator = ChatbotOrchestrator(provider=manager)
            result = orchestrator.process_message(session, "Explain Python list comprehensions simply.")
            self.assertTrue(result.get("success"))
            self.assertIn("concise way to create lists", result.get("content", ""))

    def test_04_debug_python_code(self):
        """Test 4: Missing colon identified and corrected code provided."""
        manager = ProviderManager(primary_provider="none", primary_key="")
        orchestrator = ChatbotOrchestrator(provider=manager)
        session = ConversationSession()

        query = "Debug this Python code:\nfor i in range(5)\n    print(i)"
        result = orchestrator.process_message(session, query)
        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("colon", content.lower())
        self.assertIn("for i in range(5):", content)

    def test_05_simulate_invalid_api_key_fallback(self):
        """Test 5: Simulate invalid API key -> Current provider fails -> Fallback attempted."""
        # Configure primary as OpenAI (fails with 401), fallback as Gemini (succeeds)
        custom_keys = {
            "openai": "sk-invalid-test-key",
            "gemini": "AIza-valid-test-key"
        }
        manager = ProviderManager(
            primary_provider="openai",
            primary_key="sk-invalid-test-key",
            custom_keys=custom_keys
        )

        call_log = []

        def mock_chat_completion(self, messages, system_prompt):
            call_log.append(self.provider)
            if self.provider == "openai":
                raise AuthenticationError("Invalid API key for OpenAI.")
            elif self.provider == "gemini":
                return {
                    "success": True,
                    "content": "Answer generated successfully by Gemini.",
                    "provider": "gemini",
                    "model": "gemini-2.5-flash"
                }
            raise ProviderConnectionError("Other error")

        with patch.object(LLMProvider, "chat_completion", new=mock_chat_completion):
            session = ConversationSession()
            orchestrator = ChatbotOrchestrator(provider=manager)
            result = orchestrator.process_message(session, "What is photosynthesis?")
            
            # Verify primary provider was attempted first, then fallback
            self.assertEqual(call_log, ["openai", "gemini"])
            self.assertTrue(result.get("success"))
            self.assertEqual(result.get("provider"), "gemini")
            self.assertIn("Answer generated successfully by Gemini", result.get("content", ""))

    def test_06_simulate_quota_exhausted_fallback(self):
        """Test 6: Simulate quota exhaustion (429) -> Next configured provider is attempted."""
        custom_keys = {
            "groq": "gsk-quota-exhausted-key",
            "openai": "sk-valid-backup-key"
        }
        manager = ProviderManager(
            primary_provider="groq",
            primary_key="gsk-quota-exhausted-key",
            custom_keys=custom_keys
        )

        call_log = []

        def mock_chat_completion(self, messages, system_prompt):
            call_log.append(self.provider)
            if self.provider == "groq":
                raise QuotaExhaustedError("Groq 429: Insufficient credits or quota exceeded.")
            elif self.provider == "openai":
                return {
                    "success": True,
                    "content": "Answer generated successfully by OpenAI.",
                    "provider": "openai",
                    "model": "gpt-4o-mini"
                }
            raise ProviderConnectionError("Other error")

        with patch.object(LLMProvider, "chat_completion", new=mock_chat_completion):
            session = ConversationSession()
            orchestrator = ChatbotOrchestrator(provider=manager)
            result = orchestrator.process_message(session, "Explain the solar system.")
            
            # Verify groq failed with 429, fell back to openai
            self.assertEqual(call_log, ["groq", "openai"])
            self.assertTrue(result.get("success"))
            self.assertEqual(result.get("provider"), "openai")

    def test_07_all_providers_unavailable_honest_error(self):
        """Test 7: Make every provider unavailable -> Clean user-facing error, no traceback, no fake response."""
        manager = ProviderManager(primary_provider="none", primary_key="")
        orchestrator = ChatbotOrchestrator(provider=manager)
        session = ConversationSession()

        # Query that cannot be answered deterministically
        query = "Write a customized 20-page strategic business plan for a hyperloop venture."
        result = orchestrator.process_message(session, query)

        self.assertFalse(result.get("success"))
        content = result.get("content", "")
        # Clean user-facing message, no raw tracebacks, no fake claim of handling
        self.assertIn("AI generation is currently unavailable because no configured provider could complete the request.", content)
        self.assertIn("Please check your AI provider configuration or API quota.", content)
        self.assertNotIn("Traceback", content)
        self.assertNotIn("TypeError", content)

    def test_08_loop_protection(self):
        """Test 8: Step 12 loop protection ensures each provider is attempted at most once."""
        custom_keys = {
            "groq": "key1",
            "gemini": "key2"
        }
        manager = ProviderManager(primary_provider="groq", custom_keys=custom_keys)
        
        attempt_counts = {}

        def mock_failing_chat(self, messages, system_prompt):
            attempt_counts[self.provider] = attempt_counts.get(self.provider, 0) + 1
            raise QuotaExhaustedError(f"{self.provider} quota exhausted")

        with patch.object(LLMProvider, "chat_completion", new=mock_failing_chat):
            res = manager.execute_with_fallback([], "System prompt")
            self.assertFalse(res.get("success"))
            # Each provider must be attempted at most ONCE
            for prov, count in attempt_counts.items():
                self.assertEqual(count, 1, f"Provider {prov} was attempted {count} times (expected 1).")

if __name__ == "__main__":
    unittest.main()
