"""
Rate Limiter, Error Diagnostics, and Request Pacing Module.
Provides:
- Per-provider minimum gap enforcement (pacing between requests)
- Extraction of HTTP status code, error status, and retry delay
- Redaction of API keys and sensitive tokens
"""

import os
import time
import re
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("chatbot.rate_limiter")

# In-memory timestamp cache: provider_code -> timestamp
_LAST_REQUEST_TIMESTAMPS: Dict[str, float] = {}

def redact_sensitive_text(text: str) -> str:
    """Redacts API keys, secrets, and auth tokens from strings."""
    if not text:
        return ""
    # Gemini API keys: AIza...
    text = re.sub(r'AIza[0-9A-Za-z\-_]{16,}', '[REDACTED_API_KEY]', text)
    # OpenAI API keys: sk-...
    text = re.sub(r'sk-[a-zA-Z0-9\-_]{20,}', '[REDACTED_API_KEY]', text)
    # Groq API keys: gsk_...
    text = re.sub(r'gsk_[a-zA-Z0-9\-_]{20,}', '[REDACTED_API_KEY]', text)
    # Bearer tokens
    text = re.sub(r'Bearer\s+[a-zA-Z0-9\-_.]+', 'Bearer [REDACTED]', text, flags=re.IGNORECASE)
    # URL query parameter keys
    text = re.sub(r'([?&]key=)[^&]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
    # JSON api_key values
    text = re.sub(r'("api_key":\s*")[^"]+(")', r'\1[REDACTED]\2', text, flags=re.IGNORECASE)
    return text

def extract_retry_delay(error: Any) -> Optional[float]:
    """
    Extracts the retry delay (in seconds) from provider exceptions.
    Inspects Google GenAI details, RetryInfo, response headers, and regex patterns.
    """
    if error is None:
        return None

    # 1. Google GenAI APIError details list or dictionary
    details = getattr(error, "details", None)
    det_list = []
    if isinstance(details, list):
        det_list = details
    elif isinstance(details, dict):
        if "details" in details and isinstance(details["details"], list):
            det_list = details["details"]
        elif "error" in details and isinstance(details["error"], dict):
            det_list = details["error"].get("details", [])
        else:
            det_list = [details]

    for d in det_list:
        if isinstance(d, dict):
            for key in ["retryDelay", "retry_delay"]:
                if key in d:
                    val = d[key]
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        m = re.search(r'([\d\.]+)', val)
                        if m:
                            try:
                                return float(m.group(1))
                            except ValueError:
                                pass

    # 2. HTTP response headers (Retry-After)
    resp = getattr(error, "response", None)
    if resp and hasattr(resp, "headers"):
        retry_after = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

    # 3. Regex on string representation
    err_str = str(error)
    m = re.search(r'retry(?:Delay|_delay| in| after)[:\s"]*([\d\.]+)\s*s?', err_str, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None

def parse_error_details(error: Any) -> Dict[str, Any]:
    """
    Extracts HTTP status code, error status (e.g. RESOURCE_EXHAUSTED),
    sanitized message, and retry delay.
    """
    http_code = getattr(error, "status_code", None) or getattr(error, "code", None)
    error_status = getattr(error, "status", None)
    raw_message = getattr(error, "message", None) or str(error)

    # Google GenAI error dict inspection
    details = getattr(error, "details", None)
    if isinstance(details, dict):
        err_dict = details.get("error", {})
        if isinstance(err_dict, dict):
            if not http_code and "code" in err_dict:
                http_code = err_dict["code"]
            if not error_status and "status" in err_dict:
                error_status = err_dict["status"]
            if "message" in err_dict and (not raw_message or raw_message == str(error)):
                raw_message = err_dict["message"]

    retry_delay = extract_retry_delay(error)
    str_repr = str(error)

    # Regex fallback for error status name
    if not error_status:
        m_st = re.search(r'\b(RESOURCE_EXHAUSTED|UNAVAILABLE|NOT_FOUND|INVALID_ARGUMENT|PERMISSION_DENIED|UNAUTHENTICATED|INTERNAL|DEADLINE_EXCEEDED|FAILED_PRECONDITION)\b', str_repr)
        if m_st:
            error_status = m_st.group(1)

    # Regex fallback for HTTP code
    if not http_code:
        m_cd = re.search(r'\b(400|401|403|404|429|500|502|503|504)\b', str_repr)
        if m_cd:
            try:
                http_code = int(m_cd.group(1))
            except ValueError:
                pass

    # Normalize error status if only code is known
    if not error_status:
        if http_code == 429:
            error_status = "RESOURCE_EXHAUSTED"
        elif http_code in (503, 502, 504):
            error_status = "UNAVAILABLE"
        elif http_code == 500:
            error_status = "INTERNAL"
        elif http_code == 404:
            error_status = "NOT_FOUND"
        elif http_code == 400:
            error_status = "INVALID_ARGUMENT"
        elif http_code in (401, 403):
            error_status = "PERMISSION_DENIED"

    # Redact sensitive information from message
    clean_msg = redact_sensitive_text(raw_message).strip()

    return {
        "http_code": http_code,
        "error_status": error_status,
        "message": clean_msg,
        "retry_delay": retry_delay
    }

def enforce_provider_gap(provider_code: str, min_gap_seconds: float = 0.2):
    """
    Enforces a per-provider minimum gap between consecutive requests
    to avoid hitting free-tier per-minute burst rate limits.
    """
    p = (provider_code or "default").lower().strip()
    now = time.time()
    last_time = _LAST_REQUEST_TIMESTAMPS.get(p, 0.0)
    elapsed = now - last_time
    if elapsed < min_gap_seconds:
        sleep_needed = min_gap_seconds - elapsed
        logger.info(f"[RateLimiter] Pacing request for '{p}': sleeping {sleep_needed:.2f}s to maintain {min_gap_seconds}s gap.")
        time.sleep(sleep_needed)
    _LAST_REQUEST_TIMESTAMPS[p] = time.time()


# Circuit Breaker state: provider_code -> cooldown_until_timestamp
_CIRCUIT_BREAKER_COOLDOWNS: Dict[str, float] = {}
_CIRCUIT_BREAKER_STREAKS: Dict[str, int] = {}
_MISCONFIGURED_PROVIDERS: Dict[str, str] = {}

BACKOFF_LADDER = [60.0, 120.0, 300.0]


def mark_provider_misconfigured(provider_code: str, reason: str = "Invalid credentials or malformed configuration"):
    """
    Permanently marks a provider as misconfigured (HTTP 400/401/403).
    Non-transient errors are not put on transient cooldowns; they are skipped
    until credentials/configuration are updated.
    """
    p = (provider_code or "default").lower().strip()
    _MISCONFIGURED_PROVIDERS[p] = reason
    logger.error(f"[CircuitBreaker] Provider '{p}' marked as MISCONFIGURED: {reason}")


def is_provider_misconfigured(provider_code: str) -> Tuple[bool, str]:
    """Returns (is_misconfigured, reason) for a provider."""
    p = (provider_code or "default").lower().strip()
    if p in _MISCONFIGURED_PROVIDERS:
        return True, _MISCONFIGURED_PROVIDERS[p]
    return False, ""


def trip_circuit_breaker(
    provider_code: str,
    cooldown_seconds: Optional[float] = None,
    http_code: Optional[int] = None,
    error_msg: str = ""
):
    """
    Trips circuit breaker for a provider upon 429, 5xx server error, or connection timeout.
    Applies exponential backoff: 60s -> 120s -> 300s on repeated failures.
    Non-transient errors (400, 401, 403) mark the provider misconfigured instead.
    """
    p = (provider_code or "default").lower().strip()

    # Do not treat 400, 401, 403 as transient cooldowns
    if http_code in (400, 401, 403):
        mark_provider_misconfigured(p, f"Non-transient auth/request failure (HTTP {http_code}). Check API credentials.")
        return

    streak = _CIRCUIT_BREAKER_STREAKS.get(p, 0) + 1
    _CIRCUIT_BREAKER_STREAKS[p] = streak

    is_quota = http_code == 429 and any(w in str(error_msg).lower() for w in ["quota", "credit", "resource_exhausted"])
    if cooldown_seconds is not None and cooldown_seconds > 0:
        actual_cooldown = cooldown_seconds
    elif is_quota:
        actual_cooldown = 300.0
    elif streak < 2 and http_code in (500, 502, 503, 504):
        # First transient timeout/network glitch: short recovery pause
        actual_cooldown = 3.0
    else:
        ladder_idx = min(streak - 1, len(BACKOFF_LADDER) - 1)
        actual_cooldown = BACKOFF_LADDER[ladder_idx]

    cooldown_until = time.time() + actual_cooldown
    _CIRCUIT_BREAKER_COOLDOWNS[p] = cooldown_until
    logger.warning(
        f"[CircuitBreaker] Provider '{p}' tripped (streak={streak})! "
        f"Cooldown applied: {actual_cooldown:.0f}s."
    )


def is_circuit_open(provider_code: str) -> bool:
    """
    Returns True if the circuit breaker is currently open (cooling down or misconfigured).
    Returns False if healthy.
    """
    p = (provider_code or "default").lower().strip()
    if p in _MISCONFIGURED_PROVIDERS:
        return True

    cooldown_until = _CIRCUIT_BREAKER_COOLDOWNS.get(p, 0.0)
    now = time.time()
    if now < cooldown_until:
        return True
    if p in _CIRCUIT_BREAKER_COOLDOWNS:
        del _CIRCUIT_BREAKER_COOLDOWNS[p]
    return False


def get_circuit_cooldown_remaining(provider_code: str) -> float:
    """Returns remaining seconds in cooldown, or 0.0 if healthy."""
    p = (provider_code or "default").lower().strip()
    if p in _MISCONFIGURED_PROVIDERS:
        return 9999.0
    cooldown_until = _CIRCUIT_BREAKER_COOLDOWNS.get(p, 0.0)
    now = time.time()
    return max(0.0, cooldown_until - now) if now < cooldown_until else 0.0


def reset_circuit_breaker(provider_code: Optional[str] = None):
    """Resets circuit breaker cooldown, streak, and misconfigured state."""
    global _CIRCUIT_BREAKER_COOLDOWNS, _CIRCUIT_BREAKER_STREAKS, _MISCONFIGURED_PROVIDERS
    if provider_code:
        p = (provider_code or "").lower().strip()
        _CIRCUIT_BREAKER_COOLDOWNS.pop(p, None)
        _CIRCUIT_BREAKER_STREAKS.pop(p, None)
        _MISCONFIGURED_PROVIDERS.pop(p, None)
    else:
        _CIRCUIT_BREAKER_COOLDOWNS.clear()
        _CIRCUIT_BREAKER_STREAKS.clear()
        _MISCONFIGURED_PROVIDERS.clear()


def reset_rate_limiter_pacing():
    """Resets timestamps, circuit breakers, and rate limiters (used primarily in tests)."""
    global _LAST_REQUEST_TIMESTAMPS, _CIRCUIT_BREAKER_COOLDOWNS, _MISCONFIGURED_PROVIDERS, _USER_REQUEST_HISTORY, _PROVIDER_DAILY_USAGE
    _LAST_REQUEST_TIMESTAMPS.clear()
    _CIRCUIT_BREAKER_COOLDOWNS.clear()
    _MISCONFIGURED_PROVIDERS.clear()
    _USER_REQUEST_HISTORY.clear()
    _PROVIDER_DAILY_USAGE.clear()


# Per-provider daily request budget capping (Scalability & Cost protection)
_PROVIDER_DAILY_USAGE: Dict[str, Dict[str, Any]] = {}
DEFAULT_PROVIDER_DAILY_BUDGET = int(os.getenv("PROVIDER_DAILY_REQUEST_BUDGET", "500"))


def check_provider_budget(provider_code: str, max_requests_per_day: int = DEFAULT_PROVIDER_DAILY_BUDGET) -> Tuple[bool, str]:
    """
    Tracks and checks per-provider daily request budget to protect against runaway cost or quota exhaustion.
    Returns (is_allowed, reason_if_exhausted).
    """
    p = (provider_code or "default").lower().strip()
    now = time.time()
    today_date = time.strftime("%Y-%m-%d", time.gmtime(now))

    usage_entry = _PROVIDER_DAILY_USAGE.setdefault(p, {"date": today_date, "count": 0})
    if usage_entry["date"] != today_date:
        usage_entry["date"] = today_date
        usage_entry["count"] = 0

    if usage_entry["count"] >= max_requests_per_day:
        return False, f"Daily budget cap exceeded for '{p}' ({usage_entry['count']}/{max_requests_per_day} requests today)."
    return True, ""


def record_provider_request(provider_code: str):
    """Increments the daily request count for a provider."""
    p = (provider_code or "default").lower().strip()
    now = time.time()
    today_date = time.strftime("%Y-%m-%d", time.gmtime(now))
    usage_entry = _PROVIDER_DAILY_USAGE.setdefault(p, {"date": today_date, "count": 0})
    if usage_entry["date"] != today_date:
        usage_entry["date"] = today_date
        usage_entry["count"] = 0
    usage_entry["count"] += 1


def reset_provider_budget(provider_code: Optional[str] = None):
    """Resets daily usage counters for testing or manual budget replenishment."""
    global _PROVIDER_DAILY_USAGE
    if provider_code:
        _PROVIDER_DAILY_USAGE.pop((provider_code or "").lower().strip(), None)
    else:
        _PROVIDER_DAILY_USAGE.clear()


# Per-user sliding window request rate limiting
_USER_REQUEST_HISTORY: Dict[str, List[float]] = {}
DEFAULT_USER_RATE_LIMIT = int(os.getenv("USER_RATE_LIMIT_PER_MINUTE", "30"))


def check_user_rate_limit(user_id: str, limit_per_minute: int = DEFAULT_USER_RATE_LIMIT) -> Tuple[bool, str]:
    """
    Sliding window per-user rate limiter.
    Limits user to `limit_per_minute` requests per 60-second window.
    Returns (is_allowed, reason_if_blocked).
    """
    uid = (user_id or "default_user").strip()
    now = time.time()
    window_start = now - 60.0

    history = _USER_REQUEST_HISTORY.get(uid, [])
    history = [t for t in history if t > window_start]

    if len(history) >= limit_per_minute:
        oldest_in_window = history[0]
        retry_after = max(1, int(60.0 - (now - oldest_in_window)))
        return False, f"Rate limit exceeded: maximum {limit_per_minute} requests per minute. Please retry in {retry_after}s."

    history.append(now)
    _USER_REQUEST_HISTORY[uid] = history
    return True, ""


