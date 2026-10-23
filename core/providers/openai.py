"""
OpenAI Provider Adapter.
"""

import os
import logging
from typing import List, Dict, Any, Optional, cast

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
from core.models import validate_provider_model

logger = logging.getLogger("chatbot.providers.openai")

class OpenAIProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def code(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    def _get_api_key(self) -> Optional[str]:
        if self.api_key and self.api_key.strip():
            return self.api_key.strip()
        try:
            import streamlit as st
            if hasattr(st, "runtime") and st.runtime.exists() and "openai_api_key" in st.session_state:
                val = st.session_state["openai_api_key"]
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
        except Exception:
            pass
        return (os.environ.get("OPENAI_API_KEY", "")).strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def list_available_models(self) -> List[str]:
        key = self._get_api_key()
        if not key:
            return []
        try:
            import openai
            client = openai.OpenAI(api_key=key, timeout=8.0)
            res = client.models.list()
            models = [m.id for m in res.data if any(p in m.id for p in ["gpt-", "o1", "o3", "chatgpt"])]
            return sorted(models)
        except Exception as e:
            logger.warning(f"Failed to list OpenAI models: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "OPENAI_API_KEY not set"}
        try:
            import openai
            _ = openai.OpenAI(api_key=key, timeout=5.0)
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

        # HARD VALIDATION LAYER: strictly rejects foreign models before any SDK request
        validate_provider_model(self.code, selected_model)

        try:
            import openai
            kwargs = {
                "api_key": key,
                "timeout": timeout
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            client = openai.OpenAI(**cast(Any, kwargs))

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=selected_model,
                messages=cast(Any, formatted),
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
                avail = self.list_available_models()
                raise ModelUnavailableError(f"OpenAI model '{selected_model}' not found or inaccessible.", available_models=avail)
            elif "bad_request" in err_str or "context_length" in err_str:
                raise InvalidRequestError(f"OpenAI bad request: {str(e)}")
            raise ProviderError(f"OpenAI error: {str(e)}", is_recoverable=True)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ):
        """
        Yields text chunks as they arrive from OpenAI streaming API.
        """
        key = self._get_api_key()
        if not key:
            raise AuthenticationError("OpenAI API key is not configured.")

        selected_model = model or self.model or self.default_model
        validate_provider_model(self.code, selected_model)

        try:
            import openai
            kwargs = {
                "api_key": key,
                "timeout": timeout
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            client = openai.OpenAI(**cast(Any, kwargs))

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=selected_model,
                messages=cast(Any, formatted),
                temperature=temperature,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            err_str = str(e).lower()
            if "invalid_api_key" in err_str or "incorrect api key" in err_str or "401" in err_str:
                raise AuthenticationError("OpenAI invalid API key.")
            raise ProviderError(f"OpenAI streaming error: {str(e)}", is_recoverable=True)
