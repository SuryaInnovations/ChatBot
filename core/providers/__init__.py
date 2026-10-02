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
    InvalidRequestError
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
    "GeminiProvider",
    "GroqProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "PROVIDER_REGISTRY"
]
