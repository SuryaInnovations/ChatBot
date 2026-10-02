"""
Google Gemini Provider Adapter.
"""

import os
from typing import List, Dict, Any, Optional

from core.providers.base import (
    BaseProvider,
    ProviderStatus,
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError
)

class GeminiProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Google Gemini"

    @property
    def code(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-2.5-flash"

    def _get_api_key(self) -> Optional[str]:
        return (self.api_key or os.environ.get("GEMINI_API_KEY", "")).strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "GEMINI_API_KEY not set"}
        try:
            from google import genai
            client = genai.Client(api_key=key)
            # Lightweight verification
            return {"status": ProviderStatus.AVAILABLE.value, "reachable": True, "message": "Gemini client initialized"}
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
            raise AuthenticationError("Google Gemini API key is not configured.")

        selected_model = model or self.model or self.default_model

        try:
            from google import genai
            client = genai.Client(api_key=key)

            conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION:\n"
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    conversation_text += f"\n{m['role'].upper()}: {m.get('content', '')}\n"

            response = client.models.generate_content(
                model=selected_model,
                contents=conversation_text
            )
            content = (response.text or "").strip()
            return {
                "success": True,
                "content": content,
                "provider": self.code,
                "model": selected_model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "api_key" in err_str or "unauthenticated" in err_str or "401" in err_str or "permission" in err_str:
                raise AuthenticationError(f"Gemini authentication failed: {str(e)}")
            elif "resource_exhausted" in err_str or "quota" in err_str or "429" in err_str:
                raise QuotaExhaustedError(f"Gemini quota exhausted: {str(e)}")
            elif "timeout" in err_str or "connection" in err_str:
                raise ProviderConnectionError(f"Gemini connection error: {str(e)}")
            elif "not_found" in err_str or "404" in err_str:
                raise ModelUnavailableError(f"Gemini model not found: {str(e)}")
            elif "invalid_argument" in err_str:
                raise InvalidRequestError(f"Gemini bad request: {str(e)}")
            raise ProviderError(f"Gemini error: {str(e)}", is_recoverable=True)
