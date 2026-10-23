"""
Provider Manager module.
Manages provider configuration checks and provides backwards compatibility.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Callable

from core.llm_provider import LLMProvider
from core.models import get_default_model
from core.config import PROVIDER_TIMEOUT_SECONDS

logger = logging.getLogger("chatbot.provider_manager")

def get_available_providers(custom_keys: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Returns list of supported providers and dynamically checks if each is actually configured.
    Never hard-codes configured=True. Never exposes key values.
    """
    keys = custom_keys or {}
    
    groq_key = keys.get("groq") or os.environ.get("GROQ_API_KEY")
    gemini_key = keys.get("gemini") or os.environ.get("GEMINI_API_KEY")
    openai_key = keys.get("openai") or os.environ.get("OPENAI_API_KEY")
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "")
    ollama_configured = bool(ollama_url.strip())
    if not ollama_configured:
        try:
            from core.providers.ollama import OllamaProvider
            ollama_configured = OllamaProvider().is_configured()
        except Exception:
            ollama_configured = False

    providers_info = [
        {
            "name": "Auto (Best Available)",
            "code": "auto",
            "default_model": "auto",
            "configured": bool((groq_key and groq_key.strip()) or (gemini_key and gemini_key.strip()) or (openai_key and openai_key.strip()) or ollama_configured),
        },
        {
            "name": "Google Gemini",
            "code": "gemini",
            "default_model": get_default_model("gemini"),
            "configured": bool(gemini_key and gemini_key.strip()),
        },
        {
            "name": "Groq",
            "code": "groq",
            "default_model": get_default_model("groq"),
            "configured": bool(groq_key and groq_key.strip()),
        },
        {
            "name": "OpenAI",
            "code": "openai",
            "default_model": get_default_model("openai"),
            "configured": bool(openai_key and openai_key.strip()),
        },
        {
            "name": "Ollama (Local)",
            "code": "ollama",
            "default_model": get_default_model("ollama"),
            "configured": ollama_configured,
        }
    ]

    return providers_info


class ProviderManager:
    """
    Wrapper providing backwards compatibility for ProviderManager calls.
    Delegates to the unified LLMProvider.
    """
    def __init__(
        self,
        primary_provider: str = "auto",
        primary_model: Optional[str] = None,
        primary_key: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        custom_keys: Optional[Dict[str, str]] = None,
        temperature: float = 0.2,
        timeout: float = PROVIDER_TIMEOUT_SECONDS
    ):
        self.primary_provider = primary_provider.lower().strip()
        self.primary_model = primary_model
        self.primary_key = primary_key
        self.fallback_providers = fallback_providers
        self.custom_keys = custom_keys or {}
        if primary_key and primary_key.strip():
            self.custom_keys[self.primary_provider] = primary_key.strip()
        self.temperature = temperature
        self.timeout = timeout

        self.llm = LLMProvider(
            provider=self.primary_provider,
            fallback_providers=fallback_providers,
            model=primary_model,
            api_key=primary_key,
            temperature=temperature,
            timeout=timeout
        )

    def execute_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_status_update: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        return self.llm.generate(
            messages,
            system_prompt,
            on_status_update=on_status_update,
            timeout=timeout or self.timeout
        )

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        task_type: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """Yields chunks using provider streaming where supported."""
        return self.llm.generate_stream(
            messages=messages,
            system_prompt=system_prompt,
            task_type=task_type,
            timeout=timeout or self.timeout
        )
