"""
Configuration module.
Loads environment variables from .env and provides centralized configuration access.
Never exposes secret values.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load .env file from project root
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=False)
else:
    load_dotenv(override=False)

# Provider settings
DEFAULT_PROVIDER = os.environ.get("LLM_PROVIDER", "auto").lower()

# Fallback provider chain
raw_fallbacks = os.environ.get("LLM_FALLBACK_PROVIDERS", "gemini,groq,openai,ollama")
DEFAULT_FALLBACK_PROVIDERS: List[str] = [p.strip().lower() for p in raw_fallbacks.split(",") if p.strip()]

# Timeouts
PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30.0"))
