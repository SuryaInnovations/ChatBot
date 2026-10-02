"""
Groq Provider Adapter.
"""

import os
from typing import List, Dict, Any, Optional

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

class GroqProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Groq"

    @property
    def code(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    def _get_api_key(self) -> Optional[str]:
        return (self.api_key or os.environ.get("GROQ_API_KEY", "")).strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "GROQ_API_KEY not set"}
        try:
            import groq
            client = groq.Groq(api_key=key)
            return {"status": ProviderStatus.AVAILABLE.value, "reachable": True, "message": "Groq client initialized"}
        except Exception as e:
            return {"status": ProviderStatus.UNKNOWN_ERROR.value, "reachable": False, "message": str(e)}

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            raise AuthenticationError("Groq API key is not configured.")

        selected_model = model or self.model or self.default_model

        try:
            import groq
            client = groq.Groq(api_key=key, timeout=timeout)

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=selected_model,
                messages=formatted,
                temperature=temperature
            )
            content = (response.choices[0].message.content or "").strip()
            return {
                "success": True,
                "content": content,
                "provider": self.code,
                "model": selected_model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "invalid_api_key" in err_str or "unauthorized" in err_str or "authentication" in err_str or "401" in err_str:
                raise AuthenticationError(f"Groq authentication failed: {str(e)}")
            elif "insufficient_quota" in err_str or "quota" in err_str:
                raise QuotaExhaustedError(f"Groq quota exceeded: {str(e)}")
            elif "rate_limit_exceeded" in err_str or "429" in err_str:
                raise RateLimitError(f"Groq rate limit exceeded: {str(e)}")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"Groq connection error: {str(e)}")
            elif "model_not_found" in err_str or "not_found" in err_str:
                raise ModelUnavailableError(f"Groq model unavailable: {str(e)}")
            elif "bad_request" in err_str:
                raise InvalidRequestError(f"Groq bad request: {str(e)}")
            raise ProviderError(f"Groq error: {str(e)}", is_recoverable=True)
