"""
Core package for All-in-One AI Assistant.
"""

from core.prompt import MASTER_SYSTEM_PROMPT, get_system_prompt
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator
from core.intent import detect_intent, IntentType

__all__ = [
    "MASTER_SYSTEM_PROMPT",
    "get_system_prompt",
    "ConversationSession",
    "LLMProvider",
    "ChatbotOrchestrator",
    "detect_intent",
    "IntentType"
]
