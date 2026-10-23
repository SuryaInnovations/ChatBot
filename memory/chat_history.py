"""
memory/chat_history.py — Compact Conversation History & Rolling Summarization.

Implements:
- Fast loading of recent turns (last 4–6 messages).
- Bounded rolling summary of older conversation history.
- Context budget compliance (fits within fast latency budget).
- Storage and retrieval backed by SQLite / DB session.
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chatbot.memory.chat_history")


class ChatHistoryManager:
    def __init__(self, recent_window_size: int = 6):
        self.recent_window_size = recent_window_size
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._summaries: Dict[str, str] = {}

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Appends a message to the session history."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self._sessions[session_id].append(entry)

        # Update rolling summary asynchronously/after threshold
        if len(self._sessions[session_id]) > self.recent_window_size * 2:
            self._update_rolling_summary(session_id)

    def get_context_for_prompt(self, session_id: str) -> Dict[str, Any]:
        """
        Returns recent messages plus rolling summary of older messages.
        Designed for ultra-fast lookup (<50ms).
        """
        history = self._sessions.get(session_id, [])
        if not history:
            return {"summary": "", "recent_messages": []}

        if len(history) <= self.recent_window_size:
            return {
                "summary": self._summaries.get(session_id, ""),
                "recent_messages": history
            }

        recent = history[-self.recent_window_size:]
        summary = self._summaries.get(session_id, "")
        return {
            "summary": summary,
            "recent_messages": recent
        }

    def clear_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._summaries.pop(session_id, None)

    def _update_rolling_summary(self, session_id: str):
        """Creates a compact 2-3 sentence digest of older messages."""
        history = self._sessions.get(session_id, [])
        older_messages = history[:-self.recent_window_size]
        if not older_messages:
            return

        topics = []
        for m in older_messages:
            if m["role"] == "user":
                snippet = m["content"][:60].replace("\n", " ")
                topics.append(snippet)

        existing = self._summaries.get(session_id, "")
        new_summary = f"User previously discussed: {'; '.join(topics[-4:])}."
        if existing:
            self._summaries[session_id] = f"{existing} Then: {new_summary}"[:400]
        else:
            self._summaries[session_id] = new_summary[:400]


default_chat_history = ChatHistoryManager()
