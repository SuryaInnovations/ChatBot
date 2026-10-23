"""
In-memory and file-backed LRU Response Cache with Temporal Query Detection and User Scoping.
Caches identical queries to conserve API quota and deliver instant sub-second responses.
Skips time-sensitive queries (news, prices, "today", "current", "weather").
"""

import re
import hashlib
import time
from typing import Dict, Any, Optional
from collections import OrderedDict

MAX_CACHE_ENTRIES = 1024
_RESPONSE_CACHE: OrderedDict = OrderedDict()
CACHE_TTL_SECONDS = 3600  # 1 hour TTL

TEMPORAL_KEYWORDS = {
    "today", "now", "current", "latest", "price", "prices", "stock", "stocks",
    "weather", "news", "time", "date", "breaking", "yesterday", "tomorrow", "live"
}


def is_time_sensitive_query(prompt: str) -> bool:
    """Returns True if the prompt involves real-time, volatile, or temporal information."""
    words = set(re.findall(r'\b[a-z]+\b', prompt.lower()))
    return bool(words & TEMPORAL_KEYWORDS)


def _generate_cache_key(
    prompt: str,
    mode: str = "auto",
    model: str = "",
    context_hash: str = "",
    tool_results_hash: str = "",
    file_hash: str = "",
    user_id: str = "default"
) -> str:
    """
    Computes a deterministic hash key from normalized prompt, mode, model,
    tool results, file hash, and user scope.
    """
    raw = (
        f"{prompt.strip().lower()}::"
        f"{mode.lower()}::"
        f"{model.lower()}::"
        f"{context_hash}::"
        f"{tool_results_hash}::"
        f"{file_hash}::"
        f"{user_id}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_response(
    prompt: str,
    mode: str = "auto",
    model: str = "",
    context_hash: str = "",
    tool_results_hash: str = "",
    file_hash: str = "",
    user_id: str = "default"
) -> Optional[Dict[str, Any]]:
    """Retrieves cached response if present, unexpired, and not time-sensitive."""
    if is_time_sensitive_query(prompt):
        return None

    key = _generate_cache_key(
        prompt=prompt,
        mode=mode,
        model=model,
        context_hash=context_hash,
        tool_results_hash=tool_results_hash,
        file_hash=file_hash,
        user_id=user_id
    )
    entry = _RESPONSE_CACHE.get(key)
    if entry:
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            _RESPONSE_CACHE.move_to_end(key)
            return dict(entry["response"])
        else:
            _RESPONSE_CACHE.pop(key, None)
    return None


def store_cached_response(
    prompt: str,
    response: Dict[str, Any],
    mode: str = "auto",
    model: str = "",
    context_hash: str = "",
    tool_results_hash: str = "",
    file_hash: str = "",
    user_id: str = "default"
):
    """Stores response in cache. Skips time-sensitive queries and unsuccessful responses."""
    if not response.get("success"):
        return
    if is_time_sensitive_query(prompt):
        return

    key = _generate_cache_key(
        prompt=prompt,
        mode=mode,
        model=model,
        context_hash=context_hash,
        tool_results_hash=tool_results_hash,
        file_hash=file_hash,
        user_id=user_id
    )
    if key in _RESPONSE_CACHE:
        _RESPONSE_CACHE.move_to_end(key)
    _RESPONSE_CACHE[key] = {
        "timestamp": time.time(),
        "response": dict(response),
        "user_id": user_id
    }
    # Enforce strict bounded LRU eviction
    if len(_RESPONSE_CACHE) > MAX_CACHE_ENTRIES:
        _RESPONSE_CACHE.popitem(last=False)


def clear_cache(user_id: Optional[str] = None):
    """Flushes cache completely or for a specific user."""
    global _RESPONSE_CACHE
    if user_id:
        keys_to_remove = [k for k, v in _RESPONSE_CACHE.items() if v.get("user_id") == user_id]
        for k in keys_to_remove:
            _RESPONSE_CACHE.pop(k, None)
    else:
        _RESPONSE_CACHE.clear()
