"""
monitoring/metrics.py — Performance Metrics, p50/p95 Latency, and Cost Tracking.

Measures:
- p50 and p95 latency across request types.
- Time to first token (TTFT).
- Tool failure rates and timeout frequency.
- Token consumption and estimated spend.
"""

import math
import time
from typing import Dict, Any, List, Optional


class PerformanceMetrics:
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._latencies: List[float] = []
        self._first_token_times: List[float] = []
        self._tool_calls: Dict[str, Dict[str, int]] = {}
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_cost_usd: float = 0.0

    def record_request_latency(self, latency_ms: float, first_token_ms: Optional[float] = None):
        self._latencies.append(latency_ms)
        if len(self._latencies) > self.max_samples:
            self._latencies.pop(0)

        if first_token_ms is not None:
            self._first_token_times.append(first_token_ms)
            if len(self._first_token_times) > self.max_samples:
                self._first_token_times.pop(0)

    def record_tool_call(self, tool_name: str, success: bool):
        if tool_name not in self._tool_calls:
            self._tool_calls[tool_name] = {"success": 0, "failure": 0}
        if success:
            self._tool_calls[tool_name]["success"] += 1
        else:
            self._tool_calls[tool_name]["failure"] += 1

    def record_token_usage(self, input_tokens: int, output_tokens: int, cost_usd: float = 0.0):
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost_usd += cost_usd

    def get_percentiles(self, values: List[float]) -> Dict[str, float]:
        if not values:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def percentile(p: float) -> float:
            idx = int(math.ceil(p * n)) - 1
            return round(sorted_vals[max(0, min(idx, n - 1))], 2)

        return {
            "p50": percentile(0.50),
            "p90": percentile(0.90),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "avg": round(sum(sorted_vals) / n, 2)
        }

    def get_summary(self) -> Dict[str, Any]:
        latency_stats = self.get_percentiles(self._latencies)
        ttft_stats = self.get_percentiles(self._first_token_times)

        tool_stats = {}
        for tname, counts in self._tool_calls.items():
            total = counts["success"] + counts["failure"]
            rate = (counts["failure"] / total) if total > 0 else 0.0
            tool_stats[tname] = {
                "total": total,
                "success": counts["success"],
                "failure": counts["failure"],
                "failure_rate": round(rate, 3)
            }

        return {
            "total_requests_recorded": len(self._latencies),
            "latency_ms": latency_stats,
            "time_to_first_token_ms": ttft_stats,
            "tool_call_metrics": tool_stats,
            "total_tokens": {
                "input": self._total_input_tokens,
                "output": self._total_output_tokens,
                "total": self._total_input_tokens + self._total_output_tokens
            },
            "estimated_cost_usd": round(self._total_cost_usd, 4),
            "meets_p95_target": latency_stats["p95"] <= 8000.0 if latency_stats["p95"] > 0 else True
        }


default_metrics = PerformanceMetrics()
