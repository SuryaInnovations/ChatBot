"""
Unified LLM Provider module.
Manages provider routing, configurable fallback priority, loop safety,
and unified generation interface.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Callable, Set

from core.config import DEFAULT_PROVIDER, DEFAULT_FALLBACK_PROVIDERS, PROVIDER_TIMEOUT_SECONDS
from core.providers import (
    BaseProvider,
    ProviderStatus,
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError,
    PROVIDER_REGISTRY
)

logger = logging.getLogger("chatbot.llm_provider")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class LLMProvider:
    """
    Unified LLM router and generation manager.
    Supports specific provider selection as well as 'auto' with customizable fallback chains.
    """
    def __init__(
        self,
        provider: str = "auto",
        fallback_providers: Optional[List[str]] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = PROVIDER_TIMEOUT_SECONDS
    ):
        self.requested_provider = (provider or DEFAULT_PROVIDER).lower().strip()
        self.fallback_providers = fallback_providers or list(DEFAULT_FALLBACK_PROVIDERS)
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout
        
        # For backwards compatibility with direct attribute reads
        self.provider = self.requested_provider

    def get_provider_diagnostics(self) -> List[Dict[str, Any]]:
        """
        Returns a developer-safe diagnostic report of all supported providers.
        Never exposes keys or secrets.
        """
        diagnostics = []
        for code, adapter_cls in PROVIDER_REGISTRY.items():
            key_override = self.api_key if self.requested_provider == code else None
            adapter = adapter_cls(api_key=key_override, base_url=self.base_url)
            check = adapter.health_check()
            diagnostics.append({
                "code": code,
                "name": adapter.name,
                "default_model": adapter.default_model,
                "configured": adapter.is_configured(),
                "status": check.get("status", ProviderStatus.UNKNOWN_ERROR.value),
                "message": check.get("message", "")
            })
        return diagnostics

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes generation using the requested provider or auto-fallback chain.
        Guarantees loop protection (each provider attempted at most once).
        """
        # Determine priority order of providers to try
        chain: List[str] = []
        if self.requested_provider != "auto":
            chain.append(self.requested_provider)

        for p in self.fallback_providers:
            p_code = p.lower().strip()
            if p_code not in chain and p_code in PROVIDER_REGISTRY:
                chain.append(p_code)

        attempted: Set[str] = set()
        diagnostics_log = []

        for prov_code in chain:
            if prov_code in attempted:
                continue
            attempted.add(prov_code)

            adapter_cls = PROVIDER_REGISTRY.get(prov_code)
            if not adapter_cls:
                continue

            # Check if this provider has an explicit key passed to constructor
            key_override = self.api_key if (self.requested_provider == prov_code and self.api_key) else None
            adapter = adapter_cls(api_key=key_override, model=self.model, base_url=self.base_url)

            if not adapter.is_configured():
                logger.info(f"[LLM] Skipping {adapter.name}: not configured.")
                diagnostics_log.append(f"• {adapter.name}: Not configured")
                continue

            logger.info(f"[LLM] Selected provider: {adapter.name} (model: {self.model or adapter.default_model})")
            if on_status_update:
                on_status_update(f"Calling {adapter.name}...")

            try:
                response = adapter.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=self.model,
                    temperature=self.temperature,
                    timeout=self.timeout
                )
                if response.get("success"):
                    logger.info(f"[LLM] Success via {adapter.name}")
                    return response

            except InvalidRequestError as ire:
                # User request or format error: do NOT cycle providers endlessly
                logger.error(f"[LLM] Invalid user request on {adapter.name}: {ire.message}")
                return {
                    "success": False,
                    "error": f"Invalid request: {ire.message}",
                    "is_user_error": True,
                    "provider": prov_code
                }

            except (AuthenticationError, QuotaExhaustedError, RateLimitError, ProviderConnectionError, ModelUnavailableError) as rec_err:
                status_code = rec_err.status_code or 500
                logger.warning(f"[LLM] Request failed on {adapter.name}: {status_code} - {rec_err.__class__.__name__}: {rec_err.message}")
                diagnostics_log.append(f"• {adapter.name}: {rec_err.__class__.__name__} ({rec_err.message})")

                if on_status_update:
                    on_status_update(f"Provider {adapter.name} temporarily unavailable. Trying next configured provider...")
                continue

            except Exception as e:
                logger.exception(f"[LLM] Unexpected error invoking {adapter.name}: {str(e)}")
                diagnostics_log.append(f"• {adapter.name}: Error ({str(e)})")
                continue

        # If all providers failed or none configured
        logger.error("[LLM] All configured providers failed or none available.")
        
        status_lines = "\n".join(diagnostics_log) if diagnostics_log else "No providers configured."
        user_facing_error = (
            "No AI provider is currently available.\n\n"
            f"**Provider Status:**\n{status_lines}\n\n"
            "Please configure at least one provider (Gemini, Groq, OpenAI, or Ollama) in your `.env` file or sidebar."
        )

        return {
            "success": False,
            "error": user_facing_error,
            "diagnostics": diagnostics_log
        }

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Backward-compatible alias for generate()."""
        return self.generate(messages, system_prompt, on_status_update=on_status_update)
