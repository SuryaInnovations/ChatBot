"""
OpenAI Provider Adapter.
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

class OpenAIProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def code(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    def _get_api_key(self) -> Optional[str]:
        return (self.api_key or os.environ.get("OPENAI_API_KEY", "")).strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "OPENAI_API_KEY not set"}
        try:
            import openai
            client = openai.OpenAI(api_key=key, timeout=5.0)
            # Lightweight check
            return {"status": ProviderStatus.AVAILABLE.value, "reachable": True, "message": "OpenAI client initialized"}
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
            raise AuthenticationError("OpenAI API key is not configured.")

        selected_model = model or self.model or self.default_model

        try:
            import openai
            kwargs = {
                "api_key": key,
                "timeout": timeout
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            client = openai.OpenAI(**kwargs)

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
            if "insufficient_quota" in err_str or "credit_balance_exhausted" in err_str:
                raise QuotaExhaustedError("OpenAI quota exceeded: No remaining credits.")
            elif "invalid_api_key" in err_str or "incorrect api key" in err_str or "401" in err_str:
                raise AuthenticationError("OpenAI invalid API key.")
            elif "rate_limit" in err_str or "429" in err_str:
                raise RateLimitError("OpenAI rate limit exceeded.")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"OpenAI connection error: {str(e)}")
            elif "not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                raise ModelUnavailableError(f"OpenAI model not found: {str(e)}")
            elif "bad_request" in err_str or "context_length" in err_str:
                raise InvalidRequestError(f"OpenAI bad request: {str(e)}")
            raise ProviderError(f"OpenAI error: {str(e)}", is_recoverable=True)
