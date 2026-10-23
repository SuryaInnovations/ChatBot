"""
Multi-Key Rotation Pool per AI Provider.
Supports comma-separated or list-based keys (e.g. GEMINI_API_KEYS=k1,k2,k3).
Automatically rotates keys round-robin and applies cool-downs to rate-limited (429) keys.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("chatbot.key_pool")


class ProviderKeyPool:
    def __init__(self):
        # provider -> list of key strings
        self._keys: Dict[str, List[str]] = {}
        # provider -> current rotation index
        self._indices: Dict[str, int] = {}
        # key_string -> cooldown expiry timestamp
        self._cooldowns: Dict[str, float] = {}
        # key_string -> boolean permanent failure flag
        self._invalid_keys: set = set()

        self._load_keys_from_env()

    def _load_keys_from_env(self):
        """Loads single or comma-separated API keys from environment."""
        providers = ["gemini", "groq", "openai"]
        for p in providers:
            keys = []
            # 1. Check plural e.g. GEMINI_API_KEYS
            plural_val = os.getenv(f"{p.upper()}_API_KEYS", "")
            if plural_val:
                keys.extend([k.strip() for k in plural_val.split(",") if k.strip()])

            # 2. Check singular e.g. GEMINI_API_KEY
            singular_val = os.getenv(f"{p.upper()}_API_KEY", "")
            if singular_val and singular_val.strip() not in keys:
                keys.append(singular_val.strip())

            self._keys[p] = keys
            self._indices[p] = 0

    def add_keys(self, provider: str, keys: List[str]):
        """Dynamically add keys to a provider pool."""
        p = provider.lower().strip()
        if p not in self._keys:
            self._keys[p] = []
        for k in keys:
            if k and k not in self._keys[p]:
                self._keys[p].append(k)

    def get_key(self, provider: str) -> Optional[str]:
        """
        Retrieves the next healthy, non-cooling API key for the requested provider.
        Rotates round-robin across healthy keys.
        """
        p = provider.lower().strip()
        all_keys = self._keys.get(p, [])
        if not all_keys:
            return None

        now = time.time()
        # Find healthy keys
        healthy_keys = [
            k for k in all_keys
            if k not in self._invalid_keys and self._cooldowns.get(k, 0) < now
        ]

        if not healthy_keys:
            # If all keys are in cooldown, pick the one that expires soonest
            non_invalid = [k for k in all_keys if k not in self._invalid_keys]
            if non_invalid:
                soonest_key = min(non_invalid, key=lambda k: self._cooldowns.get(k, 0))
                logger.warning(f"All keys for {provider} cooling; selecting soonest-ready key.")
                return soonest_key
            return None

        # Round robin over healthy keys
        idx = self._indices.get(p, 0) % len(healthy_keys)
        chosen = healthy_keys[idx]
        self._indices[p] = (idx + 1) % len(healthy_keys)
        return chosen

    def mark_key_rate_limited(self, provider: str, key: str, cooldown_seconds: float = 60.0):
        """Places a key in cooldown for a duration due to 429 rate limit."""
        if not key:
            return
        expiry = time.time() + cooldown_seconds
        self._cooldowns[key] = expiry
        logger.warning(f"[KEY POOL] Placed key for {provider} into {cooldown_seconds}s cooldown.")

    def mark_key_invalid(self, provider: str, key: str):
        """Marks a key permanently invalid due to 401/403 Authentication Error."""
        if not key:
            return
        self._invalid_keys.add(key)
        logger.error(f"[KEY POOL] Marked key for {provider} permanently INVALID.")

    def get_status(self, provider: str) -> Dict[str, Any]:
        """Returns statistics on active, cooling, and invalid keys."""
        p = provider.lower().strip()
        keys = self._keys.get(p, [])
        now = time.time()
        cooling = [k for k in keys if self._cooldowns.get(k, 0) > now]
        invalid = [k for k in keys if k in self._invalid_keys]
        active = [k for k in keys if k not in cooling and k not in invalid]
        return {
            "total_keys": len(keys),
            "active_keys": len(active),
            "cooling_keys": len(cooling),
            "invalid_keys": len(invalid)
        }


key_pool = ProviderKeyPool()
