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
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv(override=True)

# Architecture & Backend settings
FASTAPI_BACKEND_URL = os.environ.get("FASTAPI_BACKEND_URL", "").rstrip("/")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./chatbot.db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Provider settings
DEFAULT_PROVIDER = os.environ.get("LLM_PROVIDER", "auto").lower()

# Fallback provider chain
raw_fallbacks = os.environ.get("LLM_FALLBACK_PROVIDERS", "gemini,groq,openai,ollama")
DEFAULT_FALLBACK_PROVIDERS: List[str] = [p.strip().lower() for p in raw_fallbacks.split(",") if p.strip()]

# Model defaults from environment variables with sensible defaults
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"

# Timeouts & Limits
PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30.0"))
SANDBOX_TIMEOUT_SECONDS = float(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "6.0"))
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
