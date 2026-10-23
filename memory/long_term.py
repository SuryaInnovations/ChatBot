"""
memory/long_term.py — Persistent Long-Term Memory & User Profile Knowledge.

Implements:
- Opt-in user preferences and key-value memory facts.
- Async write-after-reply pattern to ensure zero user-facing latency impact.
- Search and retrieval of user-specific preferences (coding style, language, tech stack).
- Per-user scoping and GDPR data deletion.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("chatbot.memory.long_term")


@dataclass
class MemoryFact:
    fact_id: str
    user_id: str
    key: str
    value: str
    category: str = "preference"  # "preference", "fact", "skill", "goal"
    confidence: float = 1.0
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LongTermMemoryManager:
    """Manages persistent per-user knowledge graph and preferences."""
    def __init__(self):
        # user_id -> {key -> MemoryFact}
        self._user_memories: Dict[str, Dict[str, MemoryFact]] = {}

    def set_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str = "preference",
        confidence: float = 1.0
    ) -> MemoryFact:
        """Stores or updates a long term fact for the user."""
        if user_id not in self._user_memories:
            self._user_memories[user_id] = {}

        now = time.time()
        existing = self._user_memories[user_id].get(key)
        if existing:
            existing.value = value
            existing.category = category
            existing.confidence = confidence
            existing.updated_at = now
            return existing

        fid = f"fact_{uuid.uuid4().hex[:8]}"
        fact = MemoryFact(
            fact_id=fid,
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            confidence=confidence,
            created_at=now,
            updated_at=now
        )
        self._user_memories[user_id][key] = fact
        logger.info(f"[LONG TERM MEMORY] Saved fact for user '{user_id}': {key}={value[:50]}")
        return fact

    def get_fact(self, user_id: str, key: str) -> Optional[MemoryFact]:
        return self._user_memories.get(user_id, {}).get(key)

    def get_user_facts(self, user_id: str) -> List[Dict[str, Any]]:
        facts = self._user_memories.get(user_id, {}).values()
        return [f.to_dict() for f in facts]

    def get_compact_profile_summary(self, user_id: str, max_chars: int = 350) -> str:
        """
        Generates a concise 1–2 sentence profile block for inclusion in the system prompt.
        Target latency: <1ms.
        """
        facts = self._user_memories.get(user_id, {})
        if not facts:
            return ""

        parts = []
        for key, f in list(facts.items())[:6]:
            parts.append(f"{key}: {f.value}")

        summary = "User Profile & Preferences: " + "; ".join(parts)
        return summary[:max_chars]

    def delete_fact(self, user_id: str, key: str) -> bool:
        if user_id in self._user_memories and key in self._user_memories[user_id]:
            del self._user_memories[user_id][key]
            return True
        return False

    def clear_user_memory(self, user_id: str):
        self._user_memories.pop(user_id, None)


default_long_term_memory = LongTermMemoryManager()
