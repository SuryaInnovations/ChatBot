"""
Groq Provider Adapter.
"""

import os
import logging
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
from core.models import validate_provider_model

logger = logging.getLogger("chatbot.providers.groq")

class GroqProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Groq"

    @property
    def code(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"

    def _get_api_key(self) -> Optional[str]:
        if self.api_key and self.api_key.strip():
            return self.api_key.strip()
        try:
            import streamlit as st
            if hasattr(st, "runtime") and st.runtime.exists() and "groq_api_key" in st.session_state:
                val = st.session_state["groq_api_key"]
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
        except Exception:
            pass
        return (os.environ.get("GROQ_API_KEY", "")).strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def list_available_models(self) -> List[str]:
        key = self._get_api_key()
        if not key:
            return []
        try:
            import groq
            client = groq.Groq(api_key=key, timeout=8.0)
            res = client.models.list()
            models = [m.id for m in res.data]
            return sorted(models)
        except Exception as e:
            logger.warning(f"Failed to list Groq models: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "GROQ_API_KEY not set"}
        try:
            import groq
            _ = groq.Groq(api_key=key)
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

        # HARD VALIDATION LAYER: strictly rejects foreign models before any SDK request
        validate_provider_model(self.code, selected_model)

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
                raise AuthenticationError("Groq authentication failed: Invalid API key.")
            elif "insufficient_quota" in err_str or "quota" in err_str:
                raise QuotaExhaustedError("Groq quota exceeded: Insufficient credits or quota.")
            elif "rate_limit_exceeded" in err_str or "429" in err_str:
                raise RateLimitError("Groq rate limit exceeded.")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"Groq connection error: {str(e)}")
            elif "model_not_found" in err_str or "not_found" in err_str or "404" in err_str:
                avail = self.list_available_models()
                raise ModelUnavailableError(f"Groq model '{selected_model}' not found or unavailable.", available_models=avail)
            elif "bad_request" in err_str:
                raise InvalidRequestError(f"Groq bad request: {str(e)}")
            raise ProviderError(f"Groq error: {str(e)}", is_recoverable=True)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ):
        """
        Yields text chunks as they arrive from Groq streaming API.
        """
        key = self._get_api_key()
        if not key:
            raise AuthenticationError("Groq API key is not configured.")

        selected_model = model or self.model or self.default_model
        validate_provider_model(self.code, selected_model)

        try:
            import groq
            client = groq.Groq(api_key=key, timeout=timeout)

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            stream = client.chat.completions.create(
                model=selected_model,
                messages=formatted,
                temperature=temperature,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            err_str = str(e).lower()
            if "invalid_api_key" in err_str or "unauthorized" in err_str or "401" in err_str:
                raise AuthenticationError("Groq authentication failed: Invalid API key.")
            raise ProviderError(f"Groq streaming error: {str(e)}", is_recoverable=True)
