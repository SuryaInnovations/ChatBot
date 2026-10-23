"""
Provider Status Tracker.
Maintains live runtime status of all AI providers:
- NOT_CONFIGURED (no key)
- READY (key present and last request/test succeeded)
- ERROR (with short reason: quota exhausted, model not found, invalid key, network error)
"""

import time
from typing import Dict, Any, Optional

STATUS_ERROR_TTL_SECONDS = 60.0

# Module-level in-memory cache of provider runtime state: code -> {"status": str, "reason": str, "message": str}
_PROVIDER_STATUS_CACHE: Dict[str, Dict[str, Any]] = {}

def get_provider_status(code: str, is_configured: bool) -> Dict[str, Any]:
    """
    Returns accurate status for a provider code:
    - NOT_CONFIGURED (no key)
    - READY (key present and last request succeeded)
    - ERROR (with short reason: quota exhausted, model not found, invalid key, etc.)
    """
    p_code = code.lower().strip()
    if not is_configured:
        if p_code == "ollama":
            return {
                "status": "NOT_CONFIGURED",
                "reason": "server unreachable (http://localhost:11434)",
                "display": "⚪ NOT_CONFIGURED (server unreachable)"
            }
        return {
            "status": "NOT_CONFIGURED",
            "reason": "no key",
            "display": "⚪ NOT_CONFIGURED (no key)"
        }

    recorded = _PROVIDER_STATUS_CACHE.get(p_code)
    if recorded:
        status = recorded.get("status", "NOT_CONFIGURED")
        reason = recorded.get("reason", "")
        rec_at = recorded.get("recorded_at", 0.0)
        
        # Check if error has expired
        if status == "ERROR" and rec_at and (time.time() - rec_at > STATUS_ERROR_TTL_SECONDS):
            _PROVIDER_STATUS_CACHE.pop(p_code, None)
            return {
                "status": "CONFIGURED",
                "reason": "cooldown expired",
                "display": "🟡 CONFIGURED (recovering)"
            }
        
        if status == "READY":
            return {
                "status": "READY",
                "reason": "",
                "display": "🟢 READY"
            }
        elif status == "ERROR":
            disp = recorded.get("display") or (f"🔴 ERROR ({reason})" if reason else "🔴 ERROR")
            return {
                "status": "ERROR",
                "http_code": recorded.get("http_code"),
                "error_status": recorded.get("error_status"),
                "retry_delay": recorded.get("retry_delay"),
                "reason": reason,
                "message": recorded.get("message", ""),
                "display": disp
            }

    # Configured with credentials but untested
    return {
        "status": "CONFIGURED",
        "reason": "untested",
        "display": "🟡 CONFIGURED (untested)"
    }

# Provider performance metrics: code -> {"success_count": int, "error_count": int, "last_latency_ms": float, "total_latency_ms": float}
_PROVIDER_METRICS: Dict[str, Dict[str, Any]] = {}


def record_provider_success(code: str, model: Optional[str] = None, latency_seconds: Optional[float] = None):
    """Marks a provider as READY and logs latency/success metrics."""
    p_code = code.lower().strip()
    _PROVIDER_STATUS_CACHE[p_code] = {
        "status": "READY",
        "reason": "",
        "message": "Ready",
        "model": model or ""
    }
    try:
        from core.rate_limiter import reset_circuit_breaker
        reset_circuit_breaker(p_code)
    except Exception:
        pass
    metrics = _PROVIDER_METRICS.setdefault(p_code, {"success_count": 0, "error_count": 0, "last_latency_ms": 0.0, "total_latency_ms": 0.0})
    metrics["success_count"] += 1
    if latency_seconds is not None:
        lat_ms = round(latency_seconds * 1000, 1)
        metrics["last_latency_ms"] = lat_ms
        metrics["total_latency_ms"] += lat_ms


def get_provider_metrics(code: str) -> Dict[str, Any]:
    """Returns runtime metrics for a provider."""
    p_code = code.lower().strip()
    m = _PROVIDER_METRICS.get(p_code, {"success_count": 0, "error_count": 0, "last_latency_ms": 0.0, "total_latency_ms": 0.0})
    avg_lat = round(m["total_latency_ms"] / m["success_count"], 1) if m["success_count"] > 0 else 0.0
    return {
        "success_count": m["success_count"],
        "error_count": m["error_count"],
        "last_latency_ms": m["last_latency_ms"],
        "avg_latency_ms": avg_lat
    }

def record_provider_error(code: str, error: Any):
    """Marks a provider as ERROR with real HTTP code, provider status, message, and retry delay."""
    p_code = code.lower().strip()
    
    from core.rate_limiter import parse_error_details
    parsed = parse_error_details(error)

    http_code = parsed.get("http_code")
    error_status = parsed.get("error_status")
    retry_delay = parsed.get("retry_delay")
    clean_msg = parsed.get("message") or str(error)

    err_str = str(error).lower()
    from core.providers.base import (
        QuotaExhaustedError,
        RateLimitError,
        ModelUnavailableError,
        AuthenticationError,
        ProviderConnectionError,
        InvalidProviderModelError
    )

    if isinstance(error, RateLimitError) or "rate limit" in err_str or "too many requests" in err_str or (http_code == 429 and retry_delay):
        reason = "rate limited"
    elif isinstance(error, QuotaExhaustedError) or "quota" in err_str or "credit" in err_str or (http_code == 429):
        reason = "quota exhausted"
    elif isinstance(error, ModelUnavailableError) or (http_code == 404) or ("model" in err_str and "not found" in err_str):
        reason = "model not found"
    elif isinstance(error, AuthenticationError) or http_code in (401, 403) or ("key" in err_str and ("invalid" in err_str or "unauthorized" in err_str)):
        reason = "invalid key"
    elif isinstance(error, ProviderConnectionError) or http_code in (500, 502, 503, 504) or "timeout" in err_str or "connection" in err_str:
        reason = "network error"
    elif isinstance(error, InvalidProviderModelError):
        reason = "invalid model"
    elif error_status:
        reason = error_status.lower().replace("_", " ")
    else:
        reason = f"HTTP {http_code}" if http_code else "error"

    if http_code and error_status:
        if retry_delay:
            display = f"🔴 ERROR ({http_code} {error_status}: {reason} [retry in {int(retry_delay)}s])"
        else:
            display = f"🔴 ERROR ({http_code} {error_status}: {reason})"
    elif http_code:
        display = f"🔴 ERROR ({http_code}: {reason})"
    elif error_status:
        display = f"🔴 ERROR ({error_status}: {reason})"
    else:
        display = f"🔴 ERROR ({reason})"

    _PROVIDER_STATUS_CACHE[p_code] = {
        "status": "ERROR",
        "http_code": http_code,
        "error_status": error_status,
        "retry_delay": retry_delay,
        "reason": reason,
        "message": clean_msg,
        "display": display,
        "recorded_at": time.time()
    }
    m = _PROVIDER_METRICS.setdefault(p_code, {"success_count": 0, "error_count": 0, "last_latency_ms": 0.0, "total_latency_ms": 0.0})
    m["error_count"] += 1

def reset_provider_status(code: str):
    """Resets the cached status for a provider (e.g., when key changes)."""
    p_code = code.lower().strip()
    _PROVIDER_STATUS_CACHE.pop(p_code, None)
    from core.rate_limiter import reset_circuit_breaker
    reset_circuit_breaker(p_code)

def reset_all_provider_statuses():
    """Resets all cached provider statuses and circuit breakers."""
    _PROVIDER_STATUS_CACHE.clear()
    from core.circuit_breaker import circuit_breaker
    from core.rate_limiter import reset_circuit_breaker
    circuit_breaker.reset()
    reset_circuit_breaker()

def is_provider_errored(code: str) -> bool:
    """
    Returns True if the provider has an active, unexpired ERROR state.
    Expired errors are automatically cleared.
    """
    p_code = code.lower().strip()
    rec = _PROVIDER_STATUS_CACHE.get(p_code)
    if not rec or rec.get("status") != "ERROR":
        return False
    rec_at = rec.get("recorded_at")
    if rec_at and (time.time() - rec_at > STATUS_ERROR_TTL_SECONDS):
        _PROVIDER_STATUS_CACHE.pop(p_code, None)
        return False
    return True

def get_provider_error_reason(code: str) -> Optional[str]:
    """Returns the recorded error reason if any."""
    p_code = code.lower().strip()
    rec = _PROVIDER_STATUS_CACHE.get(p_code)
    return rec.get("reason") if rec and rec.get("status") == "ERROR" else None

def get_all_statuses() -> Dict[str, Dict[str, Any]]:
    return dict(_PROVIDER_STATUS_CACHE)
