"""
Distributed Circuit Breaker with Exponential Backoff and Jitter.
Stops cascading failure by temporarily isolating failing AI providers.
Enforces State: CLOSED (healthy), OPEN (cooldown/bypassed), HALF_OPEN (probe).
"""

import time
import random
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("chatbot.circuit_breaker")


BACKOFF_LADDER = [60.0, 120.0, 300.0]


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 1,
        cooldown_seconds: float = 60.0,
        half_open_success_threshold: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_success_threshold = half_open_success_threshold
        if cooldown_seconds != 60.0:
            self.backoff_ladder = [cooldown_seconds, cooldown_seconds * 2.0, cooldown_seconds * 5.0]
        else:
            self.backoff_ladder = BACKOFF_LADDER
        
        # Local state fallback: provider -> {"state": str, "failures": int, "cooldown_until": float}
        self._local_state: Dict[str, Dict[str, Any]] = {}

    def _get_local(self, provider: str) -> Dict[str, Any]:
        p = provider.lower().strip()
        if p not in self._local_state:
            self._local_state[p] = {
                "state": "CLOSED",
                "failures": 0,
                "cooldown_until": 0.0,
                "half_open_probes": 0,
                "misconfigured_reason": ""
            }
        return self._local_state[p]

    def is_available(self, provider: str) -> Tuple[bool, str]:
        """
        Determines if a provider is eligible to receive traffic.
        Returns (is_available, state_reason).
        """
        entry = self._get_local(provider)
        now = time.time()
        state = entry["state"]

        if state == "MISCONFIGURED":
            return False, f"MISCONFIGURED ({entry.get('misconfigured_reason', 'Bad configuration')})"

        if state == "CLOSED":
            return True, "CLOSED (Healthy)"

        if state == "OPEN":
            if now >= entry["cooldown_until"]:
                # Cooldown expired -> move to HALF_OPEN
                entry["state"] = "HALF_OPEN"
                entry["half_open_probes"] = 0
                logger.info(f"[CIRCUIT BREAKER] {provider} transitioning to HALF_OPEN (probe allowed).")
                return True, "HALF_OPEN (Probing recovery)"
            remaining = int(entry["cooldown_until"] - now)
            return False, f"OPEN (Cooling down, {remaining}s remaining)"

        if state == "HALF_OPEN":
            # Allow limited probe requests
            if entry["half_open_probes"] < 2:
                entry["half_open_probes"] += 1
                return True, "HALF_OPEN (Probe in flight)"
            return False, "HALF_OPEN (Max probes active)"

        return True, "CLOSED"

    def mark_misconfigured(self, provider: str, reason: str = "Invalid credentials or request structure"):
        """Marks provider as permanently misconfigured until updated; bypasses transient cooldowns."""
        entry = self._get_local(provider)
        entry["state"] = "MISCONFIGURED"
        entry["misconfigured_reason"] = reason
        logger.error(f"[CIRCUIT BREAKER] Provider '{provider}' marked as MISCONFIGURED: {reason}")

    def reset(self, provider: Optional[str] = None):
        """Resets the circuit breaker state for a specific provider or all providers."""
        if provider:
            p = provider.lower().strip()
            if p in self._local_state:
                self._local_state[p] = {
                    "state": "CLOSED",
                    "failures": 0,
                    "cooldown_until": 0.0,
                    "half_open_probes": 0,
                    "misconfigured_reason": ""
                }
        else:
            self._local_state.clear()

    def record_success(self, provider: str):
        """Records a successful request, resetting failures and closing circuit."""
        entry = self._get_local(provider)
        if entry["state"] != "CLOSED":
            logger.info(f"[CIRCUIT BREAKER] {provider} recovered successfully! Circuit reset to CLOSED.")
        entry["state"] = "CLOSED"
        entry["failures"] = 0
        entry["cooldown_until"] = 0.0
        entry["half_open_probes"] = 0

    def record_failure(self, provider: str, error_msg: str = "", http_code: Optional[int] = None):
        """
        Records a failure. Transient errors (429/5xx/timeouts) climb the ladder (60s -> 120s -> 300s).
        Non-transient errors (400, 401, 403) transition to MISCONFIGURED without retries.
        """
        if http_code in (400, 401, 403):
            self.mark_misconfigured(provider, f"HTTP {http_code}: {error_msg}")
            return

        entry = self._get_local(provider)
        entry["failures"] += 1
        now = time.time()

        streak = entry["failures"]
        trips = max(0, streak - self.failure_threshold)
        ladder_idx = min(trips, len(self.backoff_ladder) - 1)
        cooldown = self.backoff_ladder[ladder_idx]

        if entry["state"] == "HALF_OPEN":
            # Probe failed: return to OPEN with exponential cooldown
            entry["state"] = "OPEN"
            entry["cooldown_until"] = now + cooldown
            logger.warning(f"[CIRCUIT BREAKER] Probe for {provider} failed. Returned to OPEN for {cooldown}s.")
            return

        # Explicit quota exhaustion trips immediately for 300s to avoid repeated failures
        is_quota = http_code == 429 and any(w in str(error_msg).lower() for w in ["quota", "credit", "resource_exhausted"])
        if is_quota or entry["failures"] >= self.failure_threshold:
            entry["state"] = "OPEN"
            entry["cooldown_until"] = now + (300.0 if is_quota else cooldown)
            logger.error(
                f"[CIRCUIT BREAKER] Provider '{provider}' tripped (streak={streak}, quota={is_quota}). "
                f"Cooldown applied: {cooldown}s. ({error_msg})"
            )

    @staticmethod
    def calculate_backoff(attempt: int, base_delay: float = 0.5, max_delay: float = 15.0) -> float:
        """
        Calculates exponential backoff with full jitter to avoid thundering herd.
        formula: sleep = min(max_delay, Uniform(0, base_delay * (2 ** attempt)))
        """
        ceiling = min(max_delay, base_delay * (2 ** attempt))
        return random.uniform(0.1, ceiling)


circuit_breaker = CircuitBreaker()
