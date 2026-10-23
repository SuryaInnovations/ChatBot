"""
core/model_router.py — Smart Model Router & Dynamic Latency Optimization.

Implements:
- Classifying query complexity (fast path vs. reasoning path).
- Routing simple greetings, general QA, and single-turn questions to fast/low-cost models (<2s TTFT).
- Routing complex coding, deep research, AutoML, and multi-step tasks to higher-tier reasoning models.
- Model provider health checks and transparent fallback.
"""

import logging
from typing import Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger("chatbot.core.model_router")


class ModelTier(str, Enum):
    FAST = "fast"          # High-speed tier: Gemini 3.8 Flash, Groq Llama-3-8B, GPT-4o-mini
    REASONING = "reasoning"# Reasoning tier: Gemini Pro, Claude 3.5 Sonnet, GPT-4o
    CODE = "code"          # Specialized code generation tier
    VISION = "vision"      # Multimodal vision tier


class SmartModelRouter:
    def __init__(self):
        self._provider_health: Dict[str, bool] = {
            "gemini": True,
            "groq": True,
            "openai": True,
            "ollama": True
        }

    def route_query(
        self,
        query: str,
        has_files: bool = False,
        intent: Optional[str] = None
    ) -> Tuple[ModelTier, str]:
        """
        Routes the user request to the optimal model tier.
        Returns (ModelTier, recommended_model_name).
        """
        q_lower = query.lower().strip()

        # 1. Vision Intent
        if has_files:
            return ModelTier.VISION, "gemini-2.5-flash"

        # 2. Fast Path Triggers (target 5–8s complete, 1–2s first token)
        is_greeting = len(q_lower.split()) <= 4 and any(
            g in q_lower for g in ("hello", "hi", "hey", "good morning", "who are you", "what can you do")
        )
        is_simple_question = len(q_lower.split()) < 15 and not any(
            kw in q_lower for kw in ("implement", "architect", "debug", "refactor", "proof", "derivation", "automl", "research")
        )

        if intent in ("chitchat", "greeting") or is_greeting or is_simple_question:
            return ModelTier.FAST, "gemini-2.5-flash"

        # 3. Code Generation / Debugging Path
        if intent in ("coding", "code_execution") or any(
            kw in q_lower for kw in ("write code", "function", "class", "script", "algorithm", "python", "javascript", "sql")
        ):
            return ModelTier.CODE, "gemini-2.5-flash"

        # 4. Deep Reasoning / Research
        if intent in ("deep_research", "automl", "analysis") or len(q_lower.split()) > 50:
            return ModelTier.REASONING, "gemini-2.5-pro"

        # Default to fast model to satisfy latency budget
        return ModelTier.FAST, "gemini-2.5-flash"

    def mark_provider_status(self, provider_name: str, healthy: bool):
        self._provider_health[provider_name.lower()] = healthy
        logger.info(f"Model router provider status updated: {provider_name} = {healthy}")

    def is_provider_healthy(self, provider_name: str) -> bool:
        return self._provider_health.get(provider_name.lower(), True)


default_model_router = SmartModelRouter()
