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
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_status: Optional[str] = None,
        retry_delay: Optional[float] = None,
        is_recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_status = error_status
        self.retry_delay = retry_delay
        self.is_recoverable = is_recoverable

class AuthenticationError(ProviderError):
    def __init__(self, message: str = "Invalid API key or authentication failed", status_code: int = 401, error_status: str = "PERMISSION_DENIED"):
        super().__init__(message, status_code=status_code, error_status=error_status, is_recoverable=True)

class QuotaExhaustedError(ProviderError):
    def __init__(self, message: str = "Quota exhausted / insufficient credits", status_code: int = 429, error_status: str = "RESOURCE_EXHAUSTED", retry_delay: Optional[float] = None):
        super().__init__(message, status_code=status_code, error_status=error_status, retry_delay=retry_delay, is_recoverable=True)

class RateLimitError(ProviderError):
    def __init__(self, message: str = "Rate limit exceeded", status_code: int = 429, error_status: str = "RESOURCE_EXHAUSTED", retry_delay: Optional[float] = None):
        super().__init__(message, status_code=status_code, error_status=error_status, retry_delay=retry_delay, is_recoverable=True)

class ProviderConnectionError(ProviderError):
    def __init__(self, message: str = "Connection failed or timed out", status_code: int = 503, error_status: str = "UNAVAILABLE"):
        super().__init__(message, status_code=status_code, error_status=error_status, is_recoverable=True)

class ModelUnavailableError(ProviderError):
    def __init__(self, message: str = "Requested model is unavailable", status_code: int = 404, error_status: str = "NOT_FOUND", available_models: Optional[List[str]] = None):
        super().__init__(message, status_code=status_code, error_status=error_status, is_recoverable=True)
        self.available_models = available_models or []

class InvalidRequestError(ProviderError):
    def __init__(self, message: str = "Invalid request or prompt format", status_code: int = 400, error_status: str = "INVALID_ARGUMENT"):
        super().__init__(message, status_code=status_code, error_status=error_status, is_recoverable=False)

class InvalidProviderModelError(ProviderError):
    """Raised when an incompatible model is passed to a provider."""
    def __init__(self, provider: str, model: str):
        message = f"Invalid provider/model combination: provider={provider}, model={model}"
        super().__init__(message, status_code=400, is_recoverable=False)
        self.provider = provider
        self.model = model


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

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ):
        """
        Yields text chunks as they arrive from the provider when native streaming is supported.
        Default implementation yields generated content.
        """
        res = self.generate(messages, system_prompt, model=model, temperature=temperature, timeout=timeout)
        yield res.get("content", "")

    def list_available_models(self) -> List[str]:
        """Lists available models from the provider API if supported."""
        return []

    def test_connection(self) -> Dict[str, Any]:
        """
        Sends a minimal one-word prompt to verify credentials, model accessibility, and quota.
        Returns: {"success": bool, "message": str, "model": str}
        """
        try:
            res = self.generate(
                messages=[{"role": "user", "content": "ping"}],
                system_prompt="Respond with 'pong'.",
                timeout=12.0
            )
            return {
                "success": True,
                "message": f"Connection verified successfully using model '{res.get('model', self.default_model)}'.",
                "model": res.get("model", self.default_model)
            }
        except ProviderError as pe:
            return {
                "success": False,
                "message": pe.message,
                "error_type": pe.__class__.__name__,
                "status_code": pe.status_code,
                "available_models": getattr(pe, "available_models", [])
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "error_type": "UnexpectedError",
                "available_models": []
            }

