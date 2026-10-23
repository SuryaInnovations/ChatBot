"""
Structured Observability & Metrics Logging Module for SPARK-AI.
Tracks per-request latency, token estimates, provider health, failover transitions,
cache hit/miss ratio, and tool execution frequencies.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger("chatbot.observability")

# In-memory rolling metrics buffer (last 500 requests)
_REQUEST_LOGS: deque = deque(maxlen=500)

# Global aggregate counters
_METRICS: Dict[str, Any] = {
    "total_requests": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "tool_calls": 0,
    "provider_failovers": 0,
    "total_latency_ms": 0.0,
    "total_tokens": 0,
    "total_estimated_cost_usd": 0.0,
    "provider_requests": {},
    "tool_frequencies": {}
}

# Provider pricing estimates per 1,000,000 tokens (Blended input/output)
PROVIDER_PRICING_PER_1M = {
    "gemini": 0.15,      # Gemini Flash-Lite / 2.5 Flash blended
    "groq": 0.65,        # Llama-3.3-70b blended
    "openai": 0.35,      # GPT-4o-mini blended
    "ollama": 0.00       # Local self-hosted
}

def estimate_token_count(text: str) -> int:
    """Estimates token count from text length using standard ~4 chars/token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def estimate_cost_usd(provider: Optional[str], total_tokens: int) -> float:
    """Estimates monetary cost based on provider rate cards."""
    if not provider or total_tokens <= 0:
        return 0.0
    rate = PROVIDER_PRICING_PER_1M.get(provider.lower().strip(), 0.20)
    return round((total_tokens / 1_000_000.0) * rate, 6)

def calculate_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    """Calculates empirical p50, p95, and p99 from a list of latencies in ms."""
    if not latencies:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_l = sorted(latencies)
    n = len(sorted_l)
    def get_pct(p: float) -> float:
        idx = min(int(n * p), n - 1)
        return round(sorted_l[idx], 1)
    return {
        "p50": get_pct(0.50),
        "p95": get_pct(0.95),
        "p99": get_pct(0.99)
    }


def log_request_event(
    query: str,
    intent: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    latency_ms: float = 0.0,
    cache_hit: bool = False,
    tools_executed: Optional[List[str]] = None,
    failover_occurred: bool = False,
    success: bool = True,
    error_msg: Optional[str] = None,
    response_text: str = ""
) -> Dict[str, Any]:
    """Records a structured observability event for a user query."""
    tools = tools_executed or []
    prompt_tokens = estimate_token_count(query)
    completion_tokens = estimate_token_count(response_text)
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = estimate_cost_usd(provider, total_tokens)

    event = {
        "timestamp": time.time(),
        "query_prefix": query[:40] if query else "",
        "intent": intent,
        "provider": provider or "deterministic",
        "model": model or "none",
        "latency_ms": round(latency_ms, 1),
        "tokens": total_tokens,
        "estimated_cost_usd": cost_usd,
        "cache_hit": cache_hit,
        "tools_executed": tools,
        "failover_occurred": failover_occurred,
        "success": success,
        "error": error_msg
    }

    _REQUEST_LOGS.append(event)

    # Update aggregate metrics
    _METRICS["total_requests"] = int(_METRICS["total_requests"]) + 1
    _METRICS["total_tokens"] = int(_METRICS["total_tokens"]) + total_tokens
    _METRICS["total_estimated_cost_usd"] = float(_METRICS["total_estimated_cost_usd"]) + cost_usd

    if cache_hit:
        _METRICS["cache_hits"] = int(_METRICS["cache_hits"]) + 1
    else:
        _METRICS["cache_misses"] = int(_METRICS["cache_misses"]) + 1

    if failover_occurred:
        _METRICS["provider_failovers"] = int(_METRICS["provider_failovers"]) + 1

    _METRICS["total_latency_ms"] = float(_METRICS["total_latency_ms"]) + latency_ms

    if provider:
        p_dict: Dict[str, Any] = _METRICS["provider_requests"]
        p_stat = p_dict.setdefault(provider, {"count": 0, "success": 0, "error": 0, "tokens": 0, "cost_usd": 0.0})
        p_stat["count"] += 1
        p_stat["tokens"] += total_tokens
        p_stat["cost_usd"] = round(p_stat["cost_usd"] + cost_usd, 6)
        if success:
            p_stat["success"] += 1
        else:
            p_stat["error"] += 1

    tf_dict: Dict[str, int] = _METRICS["tool_frequencies"]
    for t in tools:
        _METRICS["tool_calls"] = int(_METRICS["tool_calls"]) + 1
        tf_dict[t] = tf_dict.get(t, 0) + 1

    logger.info(
        f"[METRICS] intent={intent} provider={provider} latency={latency_ms:.1f}ms "
        f"tokens={total_tokens} cost=${cost_usd:.5f} cache_hit={cache_hit} tools={len(tools)} success={success}"
    )
    return event


def record_request_metrics(
    endpoint: str = "/chat",
    latency_ms: float = 0.0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    success: bool = True
) -> Dict[str, Any]:
    """Helper to record request metrics with token counts directly."""
    return log_request_event(
        query="x" * (tokens_in * 4),
        intent=endpoint,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        success=success,
        response_text="y" * (tokens_out * 4)
    )


def get_observability_summary() -> Dict[str, Any]:
    """Computes real-time system performance summary, latency percentiles, and cost rates."""
    total = int(_METRICS["total_requests"])
    cache_hits = int(_METRICS["cache_hits"])
    total_lat = float(_METRICS["total_latency_ms"])
    cache_hit_rate = round((cache_hits / total) * 100, 1) if total > 0 else 0.0
    avg_lat = round(total_lat / total, 1) if total > 0 else 0.0

    recent_latencies = [e["latency_ms"] for e in _REQUEST_LOGS if "latency_ms" in e]
    percentiles = calculate_latency_percentiles(recent_latencies)

    return {
        "total_requests": total,
        "cache_hit_rate_pct": cache_hit_rate,
        "avg_latency_ms": avg_lat,
        "latency_percentiles": percentiles,
        "p50_latency_ms": percentiles["p50"],
        "p95_latency_ms": percentiles["p95"],
        "p99_latency_ms": percentiles["p99"],
        "total_tokens_processed": int(_METRICS["total_tokens"]),
        "total_estimated_cost_usd": round(float(_METRICS["total_estimated_cost_usd"]), 5),
        "total_tool_calls": int(_METRICS["tool_calls"]),
        "failover_count": int(_METRICS["provider_failovers"]),
        "provider_breakdown": dict(_METRICS["provider_requests"]),
        "tool_frequencies": dict(_METRICS["tool_frequencies"]),
        "recent_events_count": len(_REQUEST_LOGS)
    }


def reset_observability_metrics():
    """Flushes observability counters and rolling logs."""
    _REQUEST_LOGS.clear()
    _METRICS["total_requests"] = 0
    _METRICS["cache_hits"] = 0
    _METRICS["cache_misses"] = 0
    _METRICS["tool_calls"] = 0
    _METRICS["provider_failovers"] = 0
    _METRICS["total_latency_ms"] = 0.0
    _METRICS["provider_requests"].clear()
    _METRICS["tool_frequencies"].clear()
