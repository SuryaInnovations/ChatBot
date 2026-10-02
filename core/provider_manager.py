"""
Provider Manager module.
Manages LLM provider configuration, loop-safe fallback execution,
error classification, and developer logging.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Callable, Set

from core.llm_provider import (
    LLMProvider,
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError
)

logger = logging.getLogger("chatbot.provider_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def get_available_providers(custom_keys: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Returns list of supported providers and dynamically checks if each is actually configured.
    Never hard-codes configured=True. Never exposes key values.
    """
    keys = custom_keys or {}
    
    groq_key = keys.get("groq") or os.environ.get("GROQ_API_KEY")
    gemini_key = keys.get("gemini") or os.environ.get("GEMINI_API_KEY")
    openai_key = keys.get("openai") or os.environ.get("OPENAI_API_KEY")
    ollama_endpoint = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    # Check ollama configuration (optional, if endpoint is specified)
    ollama_configured = bool(os.environ.get("OLLAMA_BASE_URL"))

    return [
        {
            "name": "Groq",
            "code": "groq",
            "default_model": "llama-3.3-70b-versatile",
            "configured": bool(groq_key and groq_key.strip()),
        },
        {
            "name": "Google Gemini",
            "code": "gemini",
            "default_model": "gemini-2.5-flash",
            "configured": bool(gemini_key and gemini_key.strip()),
        },
        {
            "name": "OpenAI",
            "code": "openai",
            "default_model": "gpt-4o-mini",
            "configured": bool(openai_key and openai_key.strip()),
        },
        {
            "name": "Ollama (Local)",
            "code": "ollama",
            "default_model": "llama3.2",
            "configured": ollama_configured,
        }
    ]


class ProviderManager:
    """
    Orchestrates provider selection, failover chains, loop protection, and logging.
    """
    def __init__(
        self,
        primary_provider: str = "groq",
        primary_model: Optional[str] = None,
        primary_key: Optional[str] = None,
        custom_keys: Optional[Dict[str, str]] = None,
        temperature: float = 0.2
    ):
        self.primary_provider = primary_provider.lower().strip()
        self.primary_model = primary_model
        self.primary_key = primary_key
        self.custom_keys = custom_keys or {}
        if primary_key and primary_key.strip():
            self.custom_keys[self.primary_provider] = primary_key.strip()
        self.temperature = temperature

    def execute_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Attempts execution across configured providers in sequence.
        Guarantees protection against infinite fallback loops.
        """
        all_providers = get_available_providers(self.custom_keys)
        
        # Build prioritized chain starting with primary provider
        chain: List[Dict[str, Any]] = []
        
        # 1. Primary provider first
        primary_cfg = next((p for p in all_providers if p["code"] == self.primary_provider), None)
        if primary_cfg:
            chain.append({
                "code": primary_cfg["code"],
                "name": primary_cfg["name"],
                "model": self.primary_model or primary_cfg["default_model"],
                "key": self.custom_keys.get(self.primary_provider) or os.environ.get(f"{self.primary_provider.upper()}_API_KEY"),
                "configured": primary_cfg["configured"] or bool(self.primary_key)
            })
        else:
            # Custom or ad-hoc provider
            chain.append({
                "code": self.primary_provider,
                "name": self.primary_provider.capitalize(),
                "model": self.primary_model,
                "key": self.primary_key,
                "configured": bool(self.primary_key)
            })

        # 2. Add remaining configured fallback providers
        for p in all_providers:
            if p["code"] != self.primary_provider and p["configured"]:
                chain.append({
                    "code": p["code"],
                    "name": p["name"],
                    "model": p["default_model"],
                    "key": self.custom_keys.get(p["code"]) or os.environ.get(f"{p['code'].upper()}_API_KEY"),
                    "configured": True
                })

        # Protection against infinite loops: each provider attempted at most once
        attempted: Set[str] = set()
        last_error_detail = ""

        for prov_item in chain:
            prov_code = prov_item["code"]
            prov_name = prov_item["name"]
            
            # Loop protection
            if prov_code in attempted:
                continue
            attempted.add(prov_code)

            # Skip unconfigured providers
            if not prov_item["configured"] and prov_code != "ollama":
                logger.info(f"[LLM] Skipping {prov_name}: not configured.")
                continue

            logger.info(f"[LLM] Selected provider: {prov_name} (model: {prov_item['model']})")
            if on_status_update:
                on_status_update(f"Calling {prov_name}...")

            try:
                # Instantiate single LLMProvider with standard constructor
                provider_instance = LLMProvider(
                    provider=prov_code,
                    model=prov_item["model"],
                    api_key=prov_item["key"],
                    temperature=self.temperature
                )
                
                result = provider_instance.chat_completion(messages, system_prompt)
                
                if result.get("success"):
                    logger.info(f"[LLM] Success via {prov_name}")
                    return result

            except InvalidRequestError as ire:
                # Non-recoverable user/prompt error: do NOT switch providers
                logger.error(f"[LLM] Invalid user request on {prov_name}: {str(ire)}")
                return {
                    "success": False,
                    "error": f"Invalid request: {ire.message}",
                    "is_user_error": True
                }

            except (AuthenticationError, QuotaExhaustedError, RateLimitError, ProviderConnectionError, ModelUnavailableError) as rec_err:
                # Recoverable provider error: log developer detail, inform UI, and try next
                status_code = rec_err.status_code or 500
                logger.warning(f"[LLM] Request failed on {prov_name}: {status_code} - {rec_err.__class__.__name__}: {rec_err.message}")
                last_error_detail = f"{prov_name}: {rec_err.message}"

                if on_status_update:
                    on_status_update(f"The selected AI provider ({prov_name}) is temporarily unavailable. Trying next configured provider...")
                continue

            except Exception as e:
                # Unexpected application bug or library error
                logger.exception(f"[LLM] Application error while invoking {prov_name}: {str(e)}")
                last_error_detail = f"{prov_name}: {str(e)}"
                continue

        # If all providers fail or none were configured
        logger.error("[LLM] All configured providers failed or none available.")
        user_facing_error = (
            "AI generation is currently unavailable because no configured provider could complete the request.\n\n"
            "Please check your AI provider configuration or API quota."
        )
        return {
            "success": False,
            "error": user_facing_error,
            "developer_log": last_error_detail
        }
