"""
LLM Provider module.
Defines individual LLM provider integrations (Groq, Gemini, OpenAI, Ollama)
and structured error classifications for robust fallback handling.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chatbot.llm_provider")

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


class LLMProvider:
    """
    Adapter for a single LLM provider instance.
    Accepts only standard constructor arguments and translates provider-specific errors.
    """
    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2
    ):
        self.provider = provider.lower().strip()
        self.api_key = api_key or os.environ.get(f"{self.provider.upper()}_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        
        # Determine model defaults
        if model and model.strip():
            self.model = model.strip()
        else:
            if self.provider == "groq":
                self.model = "llama-3.3-70b-versatile"
            elif self.provider == "gemini":
                self.model = "gemini-2.5-flash"
            elif self.provider == "openai":
                self.model = "gpt-4o-mini"
            elif self.provider == "ollama":
                self.model = "llama3.2"
            else:
                self.model = "llama-3.3-70b-versatile"

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        Executes chat completion against this provider.
        Raises classified ProviderError exceptions on failure.
        """
        if self.provider == "groq":
            return self._call_groq(messages, system_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(messages, system_prompt)
        elif self.provider in ["openai", "ollama"]:
            return self._call_openai_compatible(messages, system_prompt)
        else:
            raise ProviderError(f"Unsupported provider: '{self.provider}'", is_recoverable=True)

    def _call_groq(self, messages: List[Dict[str, Any]], system_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise AuthenticationError("Groq API key is not configured.")

        try:
            import groq
            client = groq.Groq(api_key=self.api_key)

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=self.model,
                messages=formatted,
                temperature=self.temperature
            )
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "content": content.strip(),
                "provider": "groq",
                "model": self.model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "invalid_api_key" in err_str or "unauthorized" in err_str or "authentication" in err_str:
                raise AuthenticationError(f"Groq authentication failed: {str(e)}")
            elif "rate_limit_exceeded" in err_str or "quota" in err_str or "429" in err_str:
                raise QuotaExhaustedError(f"Groq quota or rate limit exceeded: {str(e)}")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"Groq connection error: {str(e)}")
            elif "model_not_found" in err_str or "not_found" in err_str:
                raise ModelUnavailableError(f"Groq model unavailable: {str(e)}")
            elif "bad_request" in err_str:
                raise InvalidRequestError(f"Groq bad request: {str(e)}")
            raise ProviderError(f"Groq unexpected error: {str(e)}", is_recoverable=True)

    def _call_gemini(self, messages: List[Dict[str, Any]], system_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise AuthenticationError("Google Gemini API key is not configured.")

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION:\n"
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    conversation_text += f"\n{m['role'].upper()}: {m.get('content', '')}\n"

            response = client.models.generate_content(
                model=self.model,
                contents=conversation_text
            )
            content = response.text or ""
            return {
                "success": True,
                "content": content.strip(),
                "provider": "gemini",
                "model": self.model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "api_key" in err_str or "permission" in err_str or "unauthenticated" in err_str or "401" in err_str:
                raise AuthenticationError(f"Gemini authentication failed: {str(e)}")
            elif "resource_exhausted" in err_str or "quota" in err_str or "429" in err_str:
                raise QuotaExhaustedError(f"Gemini quota exhausted: {str(e)}")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"Gemini connection error: {str(e)}")
            elif "not_found" in err_str or "404" in err_str:
                raise ModelUnavailableError(f"Gemini model unavailable: {str(e)}")
            elif "invalid_argument" in err_str or "bad_request" in err_str:
                raise InvalidRequestError(f"Gemini bad request: {str(e)}")
            raise ProviderError(f"Gemini unexpected error: {str(e)}", is_recoverable=True)

    def _call_openai_compatible(self, messages: List[Dict[str, Any]], system_prompt: str) -> Dict[str, Any]:
        is_ollama = (self.provider == "ollama")
        if not is_ollama and not self.api_key:
            raise AuthenticationError(f"{self.provider.capitalize()} API key is not configured.")

        try:
            import openai
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            elif is_ollama:
                kwargs["base_url"] = "http://localhost:11434/v1"
                if not self.api_key:
                    kwargs["api_key"] = "ollama"

            client = openai.OpenAI(**kwargs)
            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=self.model,
                messages=formatted,
                temperature=self.temperature
            )
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "content": content.strip(),
                "provider": self.provider,
                "model": self.model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "insufficient_quota" in err_str or "credit_balance_exhausted" in err_str or "quota" in err_str:
                raise QuotaExhaustedError("OpenAI quota exceeded: No remaining credits.")
            elif "invalid_api_key" in err_str or "incorrect api key" in err_str or "401" in err_str:
                raise AuthenticationError(f"{self.provider.capitalize()} invalid API key.")
            elif "rate_limit" in err_str or "429" in err_str:
                raise RateLimitError(f"{self.provider.capitalize()} rate limit exceeded.")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"{self.provider.capitalize()} connection error: {str(e)}")
            elif "not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                raise ModelUnavailableError(f"{self.provider.capitalize()} model not found: {str(e)}")
            elif "bad_request" in err_str or "context_length" in err_str:
                raise InvalidRequestError(f"{self.provider.capitalize()} invalid request: {str(e)}")
            raise ProviderError(f"{self.provider.capitalize()} error: {str(e)}", is_recoverable=True)
