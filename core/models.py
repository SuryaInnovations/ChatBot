"""
Centralized model definitions, provider-specific model mappings, and isolation rules.
Strictly prevents sharing model names across different providers.
Supports dynamic environment variable defaults and runtime model updates.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from core.providers.base import InvalidProviderModelError

logger = logging.getLogger("chatbot.models")

# Dynamic model storage populated at runtime if provider list-models is queried (e.g. on 404)
_DYNAMIC_MODELS: Dict[str, List[str]] = {}

def get_default_model(provider: str) -> str:
    """Returns the default model for a specific provider, reading from env with code default."""
    p = provider.lower().strip()
    if p == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    elif p == "groq":
        return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
    elif p == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    elif p == "ollama":
        return os.environ.get("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"
    return "gemini-3.5-flash-lite"

def sort_gemini_models(models: List[str]) -> List[str]:
    """Sorts Gemini models so Flash models come first and newest versions come first."""
    import re
    def sort_key(name: str):
        is_flash = 0 if "flash" in name.lower() else 1
        nums = [int(n) for n in re.findall(r"\d+", name)]
        major = nums[0] if len(nums) > 0 else 0
        minor = nums[1] if len(nums) > 1 else 0
        return (is_flash, -major, -minor, name)

    seen = set()
    deduped = []
    for m in models:
        clean = m.strip()
        if clean and clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return sorted(deduped, key=sort_key)

def get_base_models(provider: str) -> List[str]:
    """Returns static base models supported for each provider."""
    p = provider.lower().strip()
    if p == "gemini":
        default_m = get_default_model("gemini")
        models = [default_m, "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-pro-latest", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        return sort_gemini_models(models)
    elif p == "groq":
        default_m = get_default_model("groq")
        models = [default_m, "llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant", "gemma2-9b-it"]
        seen = set()
        out = []
        for m in models:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out
    elif p == "openai":
        default_m = get_default_model("openai")
        models = [default_m, "gpt-4o-mini", "gpt-4o", "o3-mini", "gpt-4-turbo"]
        seen = set()
        out = []
        for m in models:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out
    elif p == "ollama":
        default_m = get_default_model("ollama")
        models = [default_m, "llama3.2", "mistral", "llama3", "phi3", "qwen2.5"]
        seen = set()
        out = []
        for m in models:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out
    return []

def get_supported_models(provider: str) -> List[str]:
    """Returns list of valid models for a specific provider, including runtime discovered models."""
    p = provider.lower().strip()
    dynamic = _DYNAMIC_MODELS.get(p)
    if dynamic:
        return list(dynamic)
    return get_base_models(p)

def set_dynamic_models(provider: str, models: List[str]):
    """Sets dynamically discovered models from a provider list-models API call."""
    p = provider.lower().strip()
    if models:
        cleaned = [m.strip() for m in models if m and m.strip()]
        if p == "gemini":
            cleaned = [m for m in cleaned if "gemini-2.5-flash" not in m.lower()]
            cleaned = sort_gemini_models(cleaned)
        _DYNAMIC_MODELS[p] = cleaned
        logger.info(f"[Models] Updated available models for {p}: {cleaned[:5]} (total {len(cleaned)})")

# Registry representation
PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "name": "Google Gemini",
        "env_var": "GEMINI_MODEL",
        "get_default": lambda: get_default_model("gemini"),
        "get_models": lambda: get_supported_models("gemini")
    },
    "groq": {
        "name": "Groq",
        "env_var": "GROQ_MODEL",
        "get_default": lambda: get_default_model("groq"),
        "get_models": lambda: get_supported_models("groq")
    },
    "openai": {
        "name": "OpenAI",
        "env_var": "OPENAI_MODEL",
        "get_default": lambda: get_default_model("openai"),
        "get_models": lambda: get_supported_models("openai")
    },
    "ollama": {
        "name": "Ollama (Local)",
        "env_var": "OLLAMA_MODEL",
        "get_default": lambda: get_default_model("ollama"),
        "get_models": lambda: get_supported_models("ollama")
    }
}

def is_model_valid_for_provider(provider: str, model: Optional[str]) -> bool:
    """
    Checks if a model identifier belongs to a specific provider.
    Rejects foreign model names (e.g. gemini-3.8-flash for openai).
    """
    if not model or not model.strip():
        return False

    p = provider.lower().strip()
    m = model.lower().strip()

    valid_list = [x.lower() for x in get_supported_models(p)]

    # Exact match in known or discovered list
    if m in valid_list:
        return True

    # Provider prefix heuristics to prevent cross-provider contamination
    if p == "openai":
        if any(foreign in m for foreign in ["gemini", "llama", "mixtral", "claude", "mistral"]):
            return False
        return m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3") or m.startswith("text-") or m.startswith("chatgpt-")

    elif p == "gemini":
        if "gemini-2.5-flash" in m:
            return False
        if any(foreign in m for foreign in ["gpt-", "llama", "mixtral", "claude"]):
            return False
        return m.startswith("gemini-")

    elif p == "groq":
        if any(foreign in m for foreign in ["gpt-", "gemini", "claude"]):
            return False
        return any(family in m for family in ["llama", "mixtral", "gemma", "whisper", "deepseek"])

    elif p == "ollama":
        if any(foreign in m for foreign in ["gpt-", "gemini"]):
            return False
        return True

    return False

def validate_provider_model(provider: str, model: Optional[str]) -> bool:
    """
    Hard validation layer ensuring provider and model are compatible.
    Raises InvalidProviderModelError if incompatible.
    """
    p = (provider or "").lower().strip()
    m = (model or "").strip()

    if not is_model_valid_for_provider(p, m):
        logger.error(f"[VALIDATION FAILED] Provider '{p}' cannot be used with model '{m}'")
        raise InvalidProviderModelError(provider=p, model=m)
    return True

def resolve_model_for_provider(provider: str, requested_model: Optional[str] = None) -> str:
    """
    Resolves the exact model to use for a provider.
    If the requested model is valid for this provider, uses it.
    If the requested model is None, empty, or belongs to a DIFFERENT provider,
    safely and automatically resets to this provider's default model.
    """
    p = provider.lower().strip()
    default_m = get_default_model(p)

    if not requested_model or not requested_model.strip():
        return default_m

    if is_model_valid_for_provider(p, requested_model):
        return requested_model.strip()

    logger.warning(
        f"[Models] Model '{requested_model}' is not valid for provider '{p}'. "
        f"Resetting to default '{default_m}'."
    )
    return default_m
