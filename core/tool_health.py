"""
core/tool_health.py — Tool Health, Circuit Breakers, and Degradation Manager.

Monitors error rates and latencies for each registered tool.
Implements circuit breaking with states (CLOSED, OPEN, HALF_OPEN)
so failing downstream APIs fail fast and don't stall user requests.
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger("chatbot.core.tool_health")


class CircuitState(str, Enum):
    CLOSED = "closed"        # Healthy, requests flow normally
    OPEN = "open"            # Failing, requests are short-circuited
    HALF_OPEN = "half_open"  # Trial mode after cooldown


class ToolHealthStats:
    def __init__(self, failure_threshold: int = 4, recovery_timeout_sec: float = 30.0):
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.failure_count: int = 0
        self.success_count: int = 0
        self.total_invocations: int = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()
        self.total_duration_ms: float = 0.0

    def record_success(self, duration_ms: float = 0.0):
        self.total_invocations += 1
        self.success_count += 1
        self.total_duration_ms += duration_ms
        if self.state == CircuitState.HALF_OPEN:
            logger.info("[CIRCUIT BREAKER] Probe succeeded. Resetting circuit to CLOSED.")
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def record_failure(self, error: str = ""):
        self.total_invocations += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("[CIRCUIT BREAKER] Half-open probe failed. Re-opening circuit.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.error(f"[CIRCUIT BREAKER] Failure threshold reached ({self.failure_count}). Tripping circuit to OPEN.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def can_execute(self) -> bool:
        """Determines if the tool can be safely called."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # Check if cooldown has elapsed
            if time.time() - self.last_state_change >= self.recovery_timeout_sec:
                logger.info("[CIRCUIT BREAKER] Recovery timeout elapsed. Switching to HALF_OPEN trial state.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        avg_ms = (self.total_duration_ms / self.total_invocations) if self.total_invocations > 0 else 0.0
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_invocations": self.total_invocations,
            "avg_duration_ms": round(avg_ms, 2),
            "last_failure_time": self.last_failure_time
        }


class ToolHealthManager:
    def __init__(self):
        self._tools: Dict[str, ToolHealthStats] = {}

    def get_tool_stats(self, tool_name: str) -> ToolHealthStats:
        if tool_name not in self._tools:
            self._tools[tool_name] = ToolHealthStats()
        return self._tools[tool_name]

    def can_call_tool(self, tool_name: str) -> bool:
        return self.get_tool_stats(tool_name).can_execute()

    def report_success(self, tool_name: str, duration_ms: float = 0.0):
        self.get_tool_stats(tool_name).record_success(duration_ms)

    def report_failure(self, tool_name: str, error: str = ""):
        self.get_tool_stats(tool_name).record_failure(error)

    def get_all_health(self) -> Dict[str, Any]:
        return {name: stats.to_dict() for name, stats in self._tools.items()}


default_tool_health = ToolHealthManager()
