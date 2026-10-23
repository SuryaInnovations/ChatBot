"""
memory/preferences.py — Personalized User Preference Controls & Management.

Allows users to:
- Inspect all saved memories and preferences.
- Correct or edit wrong facts.
- Disable/pause memory collection.
- Export all personal memory data in JSON/Markdown.
- Permanently purge/delete specific or all preferences (GDPR compliance).
"""

import json
import logging
from typing import Dict, Any, List
from memory.long_term import default_long_term_memory

logger = logging.getLogger("chatbot.memory.preferences")


class UserPreferenceManager:
    def __init__(self, memory_manager=None):
        self.memory = memory_manager or default_long_term_memory
        self._disabled_users: set[str] = set()

    def set_memory_enabled(self, user_id: str, enabled: bool):
        if enabled:
            self._disabled_users.discard(user_id)
        else:
            self._disabled_users.add(user_id)

    def is_memory_enabled(self, user_id: str) -> bool:
        return user_id not in self._disabled_users

    def inspect_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all recorded preferences and facts for the user."""
        return self.memory.get_user_facts(user_id)

    def update_preference(self, user_id: str, key: str, value: str, category: str = "preference") -> Dict[str, Any]:
        """User corrects or overrides an existing saved preference."""
        fact = self.memory.set_fact(user_id, key, value, category=category, confidence=1.0)
        return fact.to_dict()

    def delete_preference(self, user_id: str, key: str) -> bool:
        """Deletes a single preference key."""
        return self.memory.delete_fact(user_id, key)

    def purge_all(self, user_id: str):
        """Purges all stored data for user."""
        self.memory.clear_user_memory(user_id)

    def export_preferences_json(self, user_id: str) -> str:
        """Exports user preferences as a formatted JSON document."""
        facts = self.inspect_preferences(user_id)
        payload = {
            "user_id": user_id,
            "memory_collection_enabled": self.is_memory_enabled(user_id),
            "total_facts": len(facts),
            "facts": facts
        }
        return json.dumps(payload, indent=2)


default_preference_manager = UserPreferenceManager()
