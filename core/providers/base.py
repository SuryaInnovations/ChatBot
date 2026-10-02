"""
Base Provider Adapter.
Defines common interface, status classifications, and structured exceptions for all LLM providers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional

class ProviderStatus(Enum):
    AVAILABLE = "AVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    AUTH_ERROR = "AUTH_ERROR"
    QUOTA_ERROR = "QUOTA_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ProviderError(Exception):
    """Base exception for provider calls."""
    def __init__(self, message: str, status_code: Optional[int] = None, is_recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_recoverable = is_recoverable

class AuthenticationError(ProviderError):
    def __init__(self, message: str = "Invalid API key or authentication failed"):
        super().__init__(message, status_code=401, is_recoverable=True)

class QuotaExhaustedError(ProviderError):
    def __init__(self, message: str = "Quota exhausted / insufficient credits"):
        super().__init__(message, status_code=429, is_recoverable=True)

class RateLimitError(ProviderError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, is_recoverable=True)

class ProviderConnectionError(ProviderError):
    def __init__(self, message: str = "Connection failed or timed out"):
        super().__init__(message, status_code=503, is_recoverable=True)

class ModelUnavailableError(ProviderError):
    def __init__(self, message: str = "Requested model is unavailable"):
        super().__init__(message, status_code=404, is_recoverable=True)

class InvalidRequestError(ProviderError):
    def __init__(self, message: str = "Invalid request or prompt format"):
        super().__init__(message, status_code=400, is_recoverable=False)


class BaseProvider(ABC):
    """Abstract base class for all LLM provider adapters."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'Google Gemini'."""
        pass

    @property
    @abstractmethod
    def code(self) -> str:
        """Machine code, e.g. 'gemini'."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has the necessary credentials/configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Performs a safe check of provider configuration and reachability."""
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Executes text generation. Raises classified ProviderError on failure.
        Returns: {'success': True, 'content': str, 'provider': str, 'model': str}
        """
        pass
