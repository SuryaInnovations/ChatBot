"""
Core package for All-in-One AI Assistant.
"""

from core.prompt import MASTER_SYSTEM_PROMPT, get_system_prompt, detect_length_mode, detect_adaptive_level
from core.conversation import ConversationSession
from core.llm_provider import (
    LLMProvider,
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError
)
from core.provider_manager import ProviderManager, get_available_providers
from core.orchestrator import ChatbotOrchestrator
from core.intent import detect_intent, IntentType

from core.tool_registry import default_tool_registry, CentralToolRegistry
from core.tool_contracts import ToolMetadata, ToolInvocation, ToolResult, PermissionLevel, ToolCategory
from core.model_router import default_model_router, SmartModelRouter, ModelTier
from core.event_stream import EventStream, CancellationToken, StreamEvent
from core.context_manager import default_context_manager, ContextBudgetManager
from core.response_validator import default_response_validator, ResponseValidator
from core.tool_health import default_tool_health, ToolHealthManager

__all__ = [
    "MASTER_SYSTEM_PROMPT",
    "get_system_prompt",
    "detect_length_mode",
    "ConversationSession",
    "LLMProvider",
    "ProviderManager",
    "get_available_providers",
    "ChatbotOrchestrator",
    "detect_intent",
    "IntentType",
    "ProviderError",
    "AuthenticationError",
    "QuotaExhaustedError",
    "RateLimitError",
    "ProviderConnectionError",
    "ModelUnavailableError",
    "InvalidRequestError",
    "default_tool_registry",
    "CentralToolRegistry",
    "ToolMetadata",
    "ToolInvocation",
    "ToolResult",
    "PermissionLevel",
    "ToolCategory",
    "default_model_router",
    "SmartModelRouter",
    "ModelTier",
    "EventStream",
    "CancellationToken",
    "StreamEvent",
    "default_context_manager",
    "ContextBudgetManager",
    "default_response_validator",
    "ResponseValidator",
    "default_tool_health",
    "ToolHealthManager"
]
