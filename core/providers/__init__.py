"""
Providers package.
Exports all adapters and registry.
"""

from core.providers.base import (
    BaseProvider,
    ProviderStatus,
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError,
    InvalidProviderModelError
)
from core.providers.gemini import GeminiProvider
from core.providers.groq import GroqProvider
from core.providers.openai import OpenAIProvider
from core.providers.ollama import OllamaProvider

PROVIDER_REGISTRY = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider
}


def register_provider(name: str, provider_cls: type):
    """
    Dynamically registers a pluggable AI provider adapter.
    Allows zero-code-change extensions for custom or mock LLM providers.
    """
    PROVIDER_REGISTRY[name.lower().strip()] = provider_cls


__all__ = [
    "BaseProvider",
    "ProviderStatus",
    "ProviderError",
    "AuthenticationError",
    "QuotaExhaustedError",
    "RateLimitError",
    "ProviderConnectionError",
    "ModelUnavailableError",
    "InvalidRequestError",
    "InvalidProviderModelError",
    "GeminiProvider",
    "GroqProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "PROVIDER_REGISTRY",
    "register_provider"
]
