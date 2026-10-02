"""
Test Suite verifying the revised Intent-Driven Routing and Fallback Architecture.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.intent import detect_intent, IntentType
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator
from tools.deterministic_solver import can_deterministic_tool_answer, solve_deterministically

class TestArchitecture(unittest.TestCase):

    def test_01_intent_detection(self):
        # Simple knowledge
        self.assertEqual(detect_intent("what is physics"), IntentType.KNOWLEDGE)
        # Current info
        self.assertEqual(detect_intent("what is the latest Python version?"), IntentType.CURRENT_INFO)
        # Mathematical calculation
        self.assertEqual(detect_intent("calculate compound interest on ₹25,000 at 8% for 3 years"), IntentType.MATH_CALCULATION)
        self.assertEqual(detect_intent("solve x^2 - 5x + 6 = 0"), IntentType.MATH_CALCULATION)
        # Interview
        self.assertEqual(detect_intent("start mock interview for python developer"), IntentType.INTERVIEW)

    def test_02_what_is_physics_clean_response(self):
        # Test that 'what is physics' produces the clean definition with NO API-key warning
        provider = LLMProvider(provider="none", api_key="") # No LLM key
        orchestrator = ChatbotOrchestrator(provider=provider)
        session = ConversationSession()

        result = orchestrator.process_message(
            session=session,
            user_message="what is physics"
        )

        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        # Must contain physics definition
        self.assertIn("Physics is the branch of science", content)
        self.assertIn("matter, energy, motion, forces", content)
        # Must NOT contain any API key warning or banner
        self.assertNotIn("API-key", content)
        self.assertNotIn("API Key", content)
        self.assertNotIn("Cloud API Notice", content)
        self.assertNotIn("insufficient_quota", content)

    def test_03_math_deterministic_fallback(self):
        # Test financial calculation produces exact numbers
        provider = LLMProvider(provider="none", api_key="")
        orchestrator = ChatbotOrchestrator(provider=provider)
        session = ConversationSession()

        result = orchestrator.process_message(
            session=session,
            user_message="calculate compound interest for ₹25,000 at 8% for 3 years"
        )

        self.assertTrue(result.get("success"))
        content = result.get("content", "")
        self.assertIn("31,492.80", content)
        self.assertIn("Formula:", content)
        self.assertNotIn("API-key", content)

    def test_04_honest_error_when_cannot_answer_without_llm(self):
        # Query that cannot be answered deterministically and has no LLM
        provider = LLMProvider(provider="none", api_key="")
        orchestrator = ChatbotOrchestrator(provider=provider)
        session = ConversationSession()

        result = orchestrator.process_message(
            session=session,
            user_message="Write a 500-word creative essay on an imaginary astronaut who found a clock in Mars."
        )

        self.assertFalse(result.get("success"))
        content = result.get("content", "")
        # Must be the honest error
        self.assertEqual(content, "AI generation is temporarily unavailable. Please configure an available model provider.")

if __name__ == "__main__":
    unittest.main()
