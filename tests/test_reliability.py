"""
Reliability, Circuit Breaker, Key Pool, and Sandbox Automated Test Suite.
"""

import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.circuit_breaker import CircuitBreaker
from core.key_pool import ProviderKeyPool
from tools.sandbox import execute_in_sandbox
from tools.web_search import is_safe_public_url
from db.session import init_db, get_db_session
from db.repository import ChatRepository
from tools.extended_tools import (
    with_timeout_and_retry,
    convert_units,
    train_baseline_model,
    transcribe_audio,
    summarize_youtube,
    create_calendar_file,
)


class TestReliabilitySuite(unittest.TestCase):

    def setUp(self):
        from core.circuit_breaker import circuit_breaker
        from core.rate_limiter import reset_circuit_breaker
        for prov in ["gemini", "groq", "openai", "ollama"]:
            circuit_breaker.record_success(prov)
            reset_circuit_breaker(prov)

    def test_01_circuit_breaker_trip_and_recovery(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.5)
        # Initially closed
        avail, reason = cb.is_available("gemini")
        self.assertTrue(avail)

        # 3 failures trip the circuit
        cb.record_failure("gemini", "429 rate limit")
        cb.record_failure("gemini", "429 rate limit")
        cb.record_failure("gemini", "429 rate limit")

        avail, reason = cb.is_available("gemini")
        self.assertFalse(avail)
        self.assertIn("OPEN", reason)

        # After cooldown, probe is allowed
        import time
        time.sleep(0.6)
        avail, reason = cb.is_available("gemini")
        self.assertTrue(avail)
        self.assertIn("HALF_OPEN", reason)

        # Successful probe closes circuit
        cb.record_success("gemini")
        avail, reason = cb.is_available("gemini")
        self.assertTrue(avail)
        self.assertIn("CLOSED", reason)

    def test_02_key_pool_rotation_and_cooldown(self):
        pool = ProviderKeyPool()
        pool.add_keys("groq", ["key_A", "key_B"])

        # Rotates round-robin
        k1 = pool.get_key("groq")
        k2 = pool.get_key("groq")
        self.assertNotEqual(k1, k2)

        # Rate limiting key_A forces key_B
        pool.mark_key_rate_limited("groq", k1, cooldown_seconds=10.0)
        k3 = pool.get_key("groq")
        self.assertEqual(k3, k2)

    def test_03_sandbox_timeout_safety(self):
        # Infinite loop must time out safely without hanging
        res = execute_in_sandbox("while True: pass", timeout=1.5)
        self.assertFalse(res["success"])
        self.assertIn("timed out", res["stderr"])

    def test_04_ssrf_internal_ip_block(self):
        # Private and loopback IPs must be blocked
        safe_ext, _ = is_safe_public_url("https://www.google.com")
        self.assertTrue(safe_ext)

        safe_local, reason = is_safe_public_url("http://127.0.0.1:8501")
        self.assertFalse(safe_local)
        self.assertIn("SSRF", reason)

        safe_meta, reason_meta = is_safe_public_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe_meta)
        self.assertIn("SSRF", reason_meta)

        # Port blocking (only 80 and 443 permitted)
        safe_port, reason_port = is_safe_public_url("http://google.com:8080")
        self.assertFalse(safe_port)
        self.assertIn("port", reason_port.lower())

        # IPv6 loopback and 0.0.0.0
        safe_zero, _ = is_safe_public_url("http://0.0.0.0:80")
        self.assertFalse(safe_zero)

        safe_ipv6, _ = is_safe_public_url("http://[::1]:80")
        self.assertFalse(safe_ipv6)


    def test_05_db_idempotency_and_zero_loss(self):
        async def run_db():
            await init_db()
            async with get_db_session() as session:
                repo = ChatRepository(session)
                conv = await repo.create_conversation(title="Reliability Conv")
                
                # First submission
                m1 = await repo.save_message(
                    conversation_id=conv.id,
                    role="user",
                    content="Compute 2+2",
                    idempotency_key="unique-req-777"
                )
                
                # Duplicate network submission with same key
                m2 = await repo.save_message(
                    conversation_id=conv.id,
                    role="user",
                    content="Compute 2+2 DUPLICATE",
                    idempotency_key="unique-req-777"
                )
                
                self.assertEqual(m1.id, m2.id)
                self.assertEqual(m1.content, "Compute 2+2")

        asyncio.run(run_db())

    def test_06_circuit_breaker_exponential_ladder_and_misconfigured(self):
        """Verifies exponential cooldown ladder (60s -> 120s -> 300s) and non-transient MISCONFIGURED state."""
        import time
        cb = CircuitBreaker()

        # Non-transient HTTP 401 marks misconfigured immediately
        cb.record_failure("auth_fail_prov", "Unauthorized", http_code=401)
        avail, reason = cb.is_available("auth_fail_prov")
        self.assertFalse(avail)
        self.assertIn("MISCONFIGURED", reason)

        # Transient HTTP 429 advances cooldown ladder: 60s -> 120s -> 300s
        t_now = time.time()
        cb.record_failure("transient_prov", "429 Rate limit", http_code=429)
        entry1 = cb._get_local("transient_prov")
        self.assertEqual(entry1["state"], "OPEN")
        self.assertAlmostEqual(entry1["cooldown_until"] - t_now, 60.0, delta=2.0)

        cb.record_failure("transient_prov", "429 Rate limit", http_code=429)
        entry2 = cb._get_local("transient_prov")
        self.assertAlmostEqual(entry2["cooldown_until"] - t_now, 120.0, delta=2.0)

        cb.record_failure("transient_prov", "429 Rate limit", http_code=429)
        entry3 = cb._get_local("transient_prov")
        self.assertAlmostEqual(entry3["cooldown_until"] - t_now, 300.0, delta=2.0)

        # Success resets to CLOSED
        cb.record_success("transient_prov")
        avail, reason = cb.is_available("transient_prov")
        self.assertTrue(avail)
        self.assertIn("CLOSED", reason)

    def test_07_extended_tools_timeout_and_retry_bounded(self):
        """Verifies per-call hard timeout cutoff and bounded retry recovery for extended tools."""
        import time

        # 1. Test timeout cutoff on slow/hanging tool
        @with_timeout_and_retry(timeout_seconds=0.3, max_retries=0)
        def hanging_tool():
            time.sleep(1.0)
            return {"success": True}

        res_timeout = hanging_tool()
        self.assertFalse(res_timeout.get("success"))
        self.assertIn("timed out", res_timeout.get("error", "").lower())

        # 2. Test transient failure recovery with 1 retry
        call_count = [0]
        @with_timeout_and_retry(timeout_seconds=2.0, max_retries=1)
        def flaky_tool():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Transient network blip")
            return {"success": True, "call_count": call_count[0]}

        res_flaky = flaky_tool()
        self.assertTrue(res_flaky.get("success"))
        self.assertEqual(res_flaky.get("call_count"), 2)

        # 3. Test real decorated extended tool
        res_real = convert_units(100.0, "c", "f")
        self.assertTrue(res_real.get("success"))
        self.assertEqual(res_real.get("result"), 212.0)

    def test_08_timeout_returns_immediately_without_waiting_for_worker(self):
        """Verifies that a timed-out call returns on time without waiting for the background worker thread."""
        import time

        @with_timeout_and_retry(timeout_seconds=0.2, max_retries=0)
        def very_slow_worker():
            time.sleep(2.0)
            return {"success": True}

        t_start = time.time()
        res = very_slow_worker()
        elapsed = time.time() - t_start

        self.assertFalse(res.get("success"))
        self.assertIn("timed out", res.get("error", "").lower())
        # Returned on time (close to 0.2s), definitely not waiting for 2.0s sleep
        self.assertLess(elapsed, 0.8)

    def test_09_timeout_is_not_retried_while_running(self):
        """Verifies that a timed-out call is NOT retried while running even if max_retries > 0."""
        import time
        attempts = [0]

        @with_timeout_and_retry(timeout_seconds=0.2, max_retries=3)
        def slow_attempt():
            attempts[0] += 1
            time.sleep(1.0)
            return {"success": True}

        res = slow_attempt()
        self.assertFalse(res.get("success"))
        self.assertIn("timed out", res.get("error", "").lower())
        # Exactly 1 attempt because timeouts abort immediately without retrying
        self.assertEqual(attempts[0], 1)

    def test_10_heavy_tools_configured_with_zero_retries(self):
        """Verifies that non-idempotent or heavy tools use per-tool timeouts and max_retries=0."""
        for tool, min_timeout in [
            (train_baseline_model, 20.0),
            (transcribe_audio, 10.0),
            (summarize_youtube, 10.0),
            (create_calendar_file, 3.0),
        ]:
            self.assertEqual(getattr(tool, "_max_retries", None), 0, f"{tool.__name__} must have max_retries=0")
            self.assertGreaterEqual(
                getattr(tool, "_timeout_seconds", 0.0), min_timeout, f"{tool.__name__} timeout too low"
            )

    def test_11_provider_request_timeout_triggers_failover(self):
        """Verifies that a provider request exceeding the per-provider timeout fails over to the next provider."""
        import time
        from unittest.mock import patch
        from core.llm_provider import LLMProvider

        def slow_generate(*args, **kwargs):
            time.sleep(1.5)  # Exceeds 0.2s timeout
            return {"success": True, "content": "Slow result", "provider": "gemini"}

        def fast_generate(*args, **kwargs):
            return {"success": True, "content": "Fast fallback result", "provider": "groq"}

        with patch("core.providers.gemini.GeminiProvider.is_configured", return_value=True), \
             patch("core.providers.gemini.GeminiProvider.generate", side_effect=slow_generate), \
             patch("core.providers.groq.GroqProvider.is_configured", return_value=True), \
             patch("core.providers.groq.GroqProvider.generate", side_effect=fast_generate):
            provider_mgr = LLMProvider(
                provider="auto",
                fallback_providers=["gemini", "groq"],
                timeout=0.2
            )
            t_start = time.time()
            resp = provider_mgr.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="Test",
                timeout=0.2
            )
            elapsed = time.time() - t_start

            # Succeeded via the fast fallback provider (groq)
            self.assertTrue(resp.get("success"))
            self.assertEqual(resp.get("provider"), "groq")
            self.assertIn("Fast fallback result", resp.get("content"))
            # Must return on time without waiting for slow provider's 1.5s sleep
            self.assertLess(elapsed, 0.8)
            # Must record fallback notice indicating slow provider timed out
            self.assertIn("timed out", resp.get("fallback_notice", "").lower())

    def test_12_provider_generate_stream_yields_chunks_and_fails_over(self):
        """Verifies that generate_stream yields chunks and fails over if the initial provider errors."""
        from unittest.mock import patch
        from core.llm_provider import LLMProvider
        from core.providers.base import ProviderError

        def failing_stream(*args, **kwargs):
            raise ProviderError("Simulated stream error", status_code=500)
            yield ""

        def successful_stream(*args, **kwargs):
            yield "Hello "
            yield "world"
            yield "!"

        with patch("core.providers.gemini.GeminiProvider.is_configured", return_value=True), \
             patch("core.providers.gemini.GeminiProvider.generate_stream", side_effect=failing_stream), \
             patch("core.providers.groq.GroqProvider.is_configured", return_value=True), \
             patch("core.providers.groq.GroqProvider.generate_stream", side_effect=successful_stream):
            provider_mgr = LLMProvider(
                provider="auto",
                fallback_providers=["gemini", "groq"]
            )
            chunks = list(provider_mgr.generate_stream(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="Test"
            ))
            self.assertEqual("".join(chunks), "Hello world!")

    def test_13_default_and_configured_timeout_with_slow_provider(self):
        """Verifies default 8.0s timeout and failover with a mocked slow provider."""
        import time
        from unittest.mock import patch
        from core.config import PROVIDER_TIMEOUT_SECONDS
        from core.llm_provider import LLMProvider
        from core.provider_manager import ProviderManager

        # 1. Verify default timeout is 30.0s
        self.assertEqual(PROVIDER_TIMEOUT_SECONDS, 30.0)
        default_llm = LLMProvider()
        self.assertEqual(default_llm.timeout, 30.0)

        default_pm = ProviderManager()
        self.assertEqual(default_pm.timeout, 30.0)

        # 2. Mock slow provider exceeding a configured timeout (0.15s), verifying failover
        def slow_gemini(*args, **kwargs):
            time.sleep(1.0)
            return {"success": True, "content": "Too slow", "provider": "gemini"}

        def fast_groq(*args, **kwargs):
            return {"success": True, "content": "Fast failover ok", "provider": "groq"}

        with patch("core.providers.gemini.GeminiProvider.is_configured", return_value=True), \
             patch("core.providers.gemini.GeminiProvider.generate", side_effect=slow_gemini), \
             patch("core.providers.groq.GroqProvider.is_configured", return_value=True), \
             patch("core.providers.groq.GroqProvider.generate", side_effect=fast_groq):

            pm = ProviderManager(
                primary_provider="auto",
                fallback_providers=["gemini", "groq"],
                timeout=0.15
            )
            t0 = time.time()
            resp = pm.execute_with_fallback(
                messages=[{"role": "user", "content": "Timeout check"}],
                system_prompt="Test",
                timeout=0.15
            )
            elapsed = time.time() - t0

            self.assertTrue(resp.get("success"))
            self.assertEqual(resp.get("provider"), "groq")
            self.assertIn("Fast failover ok", resp.get("content"))
            self.assertLess(elapsed, 0.7)
            self.assertIn("timed out", resp.get("fallback_notice", "").lower())


if __name__ == "__main__":
    unittest.main()
