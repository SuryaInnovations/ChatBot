"""
Unified LLM Provider module.
Manages provider routing, configurable fallback priority, loop safety,
hard validation layer, accurate runtime status tracking, and unified generation interface.
"""

import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable, Set, Tuple, cast

from core.config import DEFAULT_PROVIDER, PROVIDER_TIMEOUT_SECONDS
from core.providers import (
    ProviderError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError,
    InvalidProviderModelError,
    PROVIDER_REGISTRY
)
from core.models import (
    PROVIDER_CONFIG,
    get_supported_models,
    get_default_model,
    is_model_valid_for_provider,
    validate_provider_model,
    set_dynamic_models
)
from core.provider_status import (
    get_provider_status,
    record_provider_success,
    record_provider_error,
    is_provider_errored,
    get_provider_error_reason
)
from core.circuit_breaker import circuit_breaker
from core.key_pool import key_pool

logger = logging.getLogger("chatbot.llm_provider")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Canonical fallback order as requested: Gemini, Groq, OpenAI, Ollama
CANONICAL_FALLBACK_ORDER = ["gemini", "groq", "openai", "ollama"]

__all__ = [
    "LLMProvider",
    "ProviderError",
    "AuthenticationError",
    "QuotaExhaustedError",
    "RateLimitError",
    "ProviderConnectionError",
    "ModelUnavailableError",
    "InvalidRequestError",
    "InvalidProviderModelError",
    "CANONICAL_FALLBACK_ORDER",
    "classify_query_complexity",
    "select_model_for_complexity",
]

def classify_query_complexity(query: str, task_type: Optional[str] = None) -> int:
    """
    Classifies prompt complexity into 5 calibrated levels:
    - Level 1: Greetings, chit-chat, simple 1-sentence inquiries -> Fast/micro model.
    - Level 2: Definitions, brief conceptual overviews, single facts -> Lightweight Flash/Fast model.
    - Level 3: Coding, debugging, calculus/algebra, structured SQL -> Capable specialized models.
    - Level 4: Multi-step analytical reasoning, document synthesis, comparative studies -> Deep reasoning model.
    - Level 5: Open-ended research, autonomous agent runs, full-stack architecture design -> Strongest frontier model.
    """
    q = (query or "").strip().lower()
    t = (task_type or "").strip().lower()
    words = q.split()

    if len(words) <= 3 and any(w in q for w in ["hi", "hello", "hey", "ping", "who are you", "what can you do", "help", "thanks"]):
        return 1

    if t in ("agent", "research", "deep_think") or any(k in q for k in ["autonomous", "full-stack architecture", "comprehensive research", "exhaustive analysis", "system design"]):
        return 5

    if t in ("document", "vision", "long_context") or any(k in q for k in ["compare documents", "16-mark", "multi-step", "trade-off analysis", "case study"]):
        return 4

    if t in ("code", "coding", "debugging", "math", "hard_reasoning") or any(k in q for k in ["def ", "class ", "derivative", "integral", "calculate", "solve", "debug", "sql"]):
        return 3

    return 2


def select_model_for_complexity(complexity: int, provider: str = "gemini") -> str:
    """
    Selects the optimal model for a given complexity level (1 to 5) and provider.
    Ensures fast lightweight models for levels 1-2, capable models for level 3,
    and high-parameter reasoning models for levels 4-5.
    """
    p = (provider or "gemini").lower().strip()
    if p == "gemini":
        if complexity <= 2:
            return "gemini-3.5-flash-lite"
        return "gemini-3.8-flash"
    elif p == "groq":
        if complexity <= 2:
            return "llama-3.1-8b-instant"
        return "llama-3.3-70b-versatile"
    elif p == "openai":
        if complexity <= 2:
            return "gpt-4o-mini"
        return "gpt-4o"
    elif p == "ollama":
        if complexity <= 2:
            return "llama3.2"
        return "llama3.1:70b"
    return get_default_model(p)


class LLMProvider:
    """
    Unified LLM router and generation manager.
    Supports specific provider selection as well as 'auto' with customizable fallback chains.
    Enforces strict provider-to-model pairing and hard validation.
    """
    def __init__(
        self,
        provider: str = "auto",
        fallback_providers: Optional[List[str]] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = PROVIDER_TIMEOUT_SECONDS
    ):
        self.requested_provider = (provider or DEFAULT_PROVIDER).lower().strip()
        self.requested_model = (model or "").strip() or None
        self.model = self.requested_model # Backwards compatibility attribute
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout
        
        # Configure fallback providers list (defaulting to Gemini -> Groq -> OpenAI -> Ollama)
        if fallback_providers is not None:
            self.fallback_providers = [p.lower().strip() for p in fallback_providers]
        else:
            self.fallback_providers = list(CANONICAL_FALLBACK_ORDER)

        # For backwards compatibility with direct attribute reads
        self.provider = self.requested_provider

    def _build_execution_chain(self, task_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Builds an ordered sequence of (provider, model) pairs.
        Supports per-task routing:
        - 'fast_chat': Groq preferred first for speed.
        - 'document' / 'vision': Gemini preferred first for 1M context / vision.
        - 'hard_reasoning' / 'code' / 'math': OpenAI / Gemini preferred.
        """
        chain: List[Tuple[str, str]] = []

        # Determine task-optimized ordering
        if task_type in ("fast_chat", "chat"):
            task_priority = ["groq", "gemini", "openai", "ollama"]
        elif task_type in ("document", "vision", "long_context"):
            task_priority = ["gemini", "openai", "groq", "ollama"]
        elif task_type in ("hard_reasoning", "reasoning", "code", "coding", "math"):
            task_priority = ["openai", "gemini", "groq", "ollama"]
        else:
            task_priority = CANONICAL_FALLBACK_ORDER

        # Re-order fallback list respecting user's explicit preference if provided
        if self.fallback_providers is not None and self.requested_provider != "auto":
            fallbacks = list(self.fallback_providers)
        else:
            # Keep configured fallbacks sorted by task priority
            base_set = self.fallback_providers if self.fallback_providers is not None else CANONICAL_FALLBACK_ORDER
            fallbacks = [p for p in task_priority if p in base_set] + [p for p in base_set if p not in task_priority]

        if self.requested_provider == "auto":
            # Auto mode: try task-optimized fallback order
            for prov in fallbacks:
                if prov in PROVIDER_CONFIG:
                    chain.append((prov, get_default_model(prov)))
        else:
            primary_prov = self.requested_provider
            if primary_prov in PROVIDER_CONFIG:
                if self.requested_model:
                    primary_model = self.requested_model
                else:
                    primary_model = get_default_model(primary_prov)
                chain.append((primary_prov, primary_model))

            # Next configured providers in fallback order
            for prov in fallbacks:
                if prov != primary_prov and prov in PROVIDER_CONFIG:
                    chain.append((prov, get_default_model(prov)))

        return chain

    def get_provider_diagnostics(self) -> List[Dict[str, Any]]:
        """
        Returns a developer-safe diagnostic report of all supported providers.
        Reflects accurate states: NOT_CONFIGURED (no key), READY (last request succeeded),
        or ERROR with a short reason (quota exhausted, model not found, invalid key).
        """
        diagnostics = []
        for code, adapter_cls in PROVIDER_REGISTRY.items():
            key_override = self.api_key if self.requested_provider == code else None
            adapter = cast(Any, adapter_cls)(api_key=key_override, base_url=self.base_url)
            is_cfg = adapter.is_configured()
            
            status_info = get_provider_status(code, is_cfg)
            status_val = status_info["status"]
            reason = status_info.get("reason", "")
            display_text = status_info.get("display", status_val)

            diagnostics.append({
                "code": code,
                "name": adapter.name,
                "default_model": adapter.default_model,
                "supported_models": get_supported_models(code),
                "configured": is_cfg,
                "status": status_val,
                "http_code": status_info.get("http_code"),
                "error_status": status_info.get("error_status"),
                "retry_delay": status_info.get("retry_delay"),
                "reason": reason,
                "display": display_text,
                "message": status_info.get("message", reason or "Ready")
            })
        return diagnostics

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        task_type: Optional[str] = None,
        on_status_update: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes generation using the requested provider or auto-fallback chain.
        Guarantees:
        1. Explicit (provider, model) pairing.
        2. Hard validation layer before SDK calls.
        3. Automatic fallback on ModelUnavailableError, QuotaExhaustedError, RateLimitError, or network error.
        4. Skip providers whose key is missing or circuit breaker is open.
        5. Accurate status updates (READY or ERROR with reason).
        6. Short clear error messages without exposing API keys.
        """
        import time
        from core.rate_limiter import (
            enforce_provider_gap,
            is_circuit_open,
            trip_circuit_breaker,
            mark_provider_misconfigured,
            is_provider_misconfigured,
            check_provider_budget,
            record_provider_request
        )
        chain = self._build_execution_chain(task_type=task_type)

        attempted: Set[str] = set()
        diagnostics_log: List[str] = []
        failed_attempts: List[str] = []
        attempt_num = 0

        for prov_code, prov_model in chain:
            if prov_code in attempted:
                continue
            attempted.add(prov_code)
            attempt_num += 1

            adapter_cls = PROVIDER_REGISTRY.get(prov_code)
            if not adapter_cls:
                continue

            # Check Misconfigured state & Circuit Breaker cooldown
            is_misconf, misconf_reason = is_provider_misconfigured(prov_code)
            if is_misconf:
                logger.info(f"[LLM] Provider {prov_code} is misconfigured ({misconf_reason}). Skipping without cooldown.")
                diagnostics_log.append(f"• **{prov_code.title()}**: Misconfigured ({misconf_reason})")
                continue

            is_avail, cb_reason = circuit_breaker.is_available(prov_code)
            if is_circuit_open(prov_code):
                is_avail = False
                cb_reason = "cooldown active after 429 rate limit or transient failure"

            if not is_avail:
                logger.info(f"[LLM] Circuit breaker open for {prov_code}: {cb_reason}. Skipping.")
                diagnostics_log.append(f"• **{prov_code.title()}**: Circuit breaker open ({cb_reason})")
                continue

            # Check Daily Budget Cap
            budget_ok, budget_reason = check_provider_budget(prov_code)
            if not budget_ok:
                logger.warning(f"[LLM] Provider {prov_code} budget cap reached: {budget_reason}. Falling back.")
                failed_attempts.append(f"{prov_code} budget cap exceeded")
                diagnostics_log.append(f"• **{prov_code.title()}**: Budget cap exceeded ({budget_reason})")
                continue


            # Instantiate provider adapter with rotated key
            key_override = self.api_key if (self.requested_provider == prov_code and self.api_key) else key_pool.get_key(prov_code)
            adapter = cast(Any, adapter_cls)(api_key=key_override, model=prov_model, base_url=self.base_url)

            # TASK 3 & 6: Skip providers whose key is missing
            if not adapter.is_configured():
                logger.info(f"[LLM] Skipping {adapter.name}: key missing / not configured.")
                if prov_code == "ollama":
                    diagnostics_log.append(f"• **{adapter.name}**: Server not running / unreachable on http://localhost:11434")
                else:
                    diagnostics_log.append(f"• **{adapter.name}**: Not configured (missing API key)")
                continue

            # TASK 6: Skip fallback providers with an active ERROR status
            if attempt_num > 1 and is_provider_errored(prov_code):
                err_reason = get_provider_error_reason(prov_code) or "error"
                logger.info(f"[LLM] Skipping fallback {adapter.name}: provider currently has ERROR status ({err_reason}).")
                diagnostics_log.append(f"• **{adapter.name}**: Skipped (status is ERROR: {err_reason})")
                continue

            # Enforce per-provider minimum gap of 0.2 seconds (prevents bursts without human-visible lag)
            enforce_provider_gap(prov_code, min_gap_seconds=0.2)

            # STEP 13: Diagnostic debug logging (safe, no keys)
            logger.info(
                f"[LLM DEBUG] attempt={attempt_num} provider={prov_code} model={prov_model} "
                f"adapter={adapter_cls.__name__}"
            )

            # STEP 4: Hard validation layer
            try:
                validate_provider_model(prov_code, prov_model)
            except InvalidProviderModelError as ipme:
                logger.error(f"[LLM VALIDATION ERROR] {ipme.message}")
                record_provider_error(prov_code, ipme)
                failed_attempts.append(f"{adapter.name} failed (invalid model)")
                diagnostics_log.append(f"• **{adapter.name}**: Invalid model ({prov_model})")
                continue

            logger.info(f"[LLM] Selected provider: {adapter.name} (model: {prov_model})")
            if on_status_update:
                on_status_update(f"Calling {adapter.name} ({prov_model})...")

            prov_timeout = float(timeout if timeout is not None else (self.timeout or PROVIDER_TIMEOUT_SECONDS))
            max_network_retries = 1
            for net_attempt in range(max_network_retries + 1):
                start_t = time.perf_counter()
                try:
                    generate_kwargs = {
                        "messages": messages,
                        "system_prompt": system_prompt,
                        "model": prov_model,
                        "temperature": self.temperature,
                        "timeout": prov_timeout
                    }
                    import inspect
                    if "on_status_update" in inspect.signature(adapter.generate).parameters:
                        generate_kwargs["on_status_update"] = on_status_update

                    # Enforce per-provider request timeout and detach cleanly on timeout
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    try:
                        future = executor.submit(adapter.generate, **cast(Any, generate_kwargs))
                        try:
                            response = future.result(timeout=prov_timeout)
                            executor.shutdown(wait=False, cancel_futures=True)
                        except concurrent.futures.TimeoutError:
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise ProviderConnectionError(
                                f"Request to {adapter.name} timed out after {prov_timeout}s.",
                                status_code=504
                            )
                    except ProviderConnectionError:
                        raise
                    except Exception:
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise

                    lat_sec = time.perf_counter() - start_t
                    if response and response.get("success"):
                        logger.info(f"[LLM] Success via {adapter.name} using {prov_model} in {lat_sec:.2f}s")
                        # Update circuit breaker and status to READY (last request succeeded)
                        circuit_breaker.record_success(prov_code)
                        from core.rate_limiter import reset_circuit_breaker
                        reset_circuit_breaker(prov_code)
                        record_provider_request(prov_code)
                        record_provider_success(prov_code, prov_model, latency_seconds=lat_sec)
                        response["latency_ms"] = round(lat_sec * 1000, 1)
                        # Add clean fallback notice if a previous provider failed
                        if failed_attempts:
                            response["fallback_notice"] = f"The selected AI provider is temporarily unavailable: {failed_attempts[0]}, answered by {adapter.name}."
                            # Check if Gemini was rate limited
                            if any("rate limited" in f.lower() for f in failed_attempts):
                                response["rate_limit_suggestion"] = True
                        return response
                    break

                except ProviderConnectionError as pce:
                    if net_attempt < max_network_retries:
                        backoff_delay = circuit_breaker.calculate_backoff(net_attempt, base_delay=0.4, max_delay=1.5)
                        logger.warning(
                            f"[LLM] Transient network error on {adapter.name} ({pce.message}). "
                            f"Retrying once in {backoff_delay:.2f}s..."
                        )
                        if on_status_update:
                            on_status_update(f"Network glitch on {adapter.name}. Retrying once...")
                        time.sleep(backoff_delay)
                        continue
                    else:
                        logger.warning(f"[LLM] ConnectionError/Timeout on {adapter.name} after retries: {pce.message}")
                        circuit_breaker.record_failure(prov_code, f"Timeout ({prov_timeout}s)", http_code=504)
                        trip_circuit_breaker(prov_code, http_code=504, error_msg=f"Timeout ({prov_timeout}s)")
                        record_provider_error(prov_code, pce)
                        failed_attempts.append(f"{adapter.name} failed ({pce.message})")
                        diagnostics_log.append(f"• **{adapter.name}**: Request timed out ({prov_timeout}s) - failed over")
                        if on_status_update:
                            on_status_update(f"Timeout on {adapter.name} ({prov_timeout}s). Trying next configured provider...")
                        break

                except ModelUnavailableError as mue:
                    logger.warning(f"[LLM] ModelUnavailable on {adapter.name}: {mue.message}")
                    
                    # TASK 5: Automatically run model discovery once, retry with best available model
                    query_res = adapter.query_available_models() if hasattr(adapter, "query_available_models") else {"models": adapter.list_available_models(), "success": True}
                    disc_models = query_res.get("models") or mue.available_models or []
                    if disc_models:
                        set_dynamic_models(prov_code, disc_models)
                        try:
                            import streamlit as st
                            if hasattr(st, "runtime") and st.runtime.exists():
                                st.session_state[f"dynamic_models_{prov_code}"] = disc_models
                        except Exception:
                            pass
                        
                        best_model = next((m for m in disc_models if "flash" in m.lower()), disc_models[0])
                        if best_model != prov_model:
                            logger.info(f"[LLM] Retrying {adapter.name} with discovered model: {best_model}")
                            if on_status_update:
                                on_status_update(f"{adapter.name}: Model '{prov_model}' not found. Retrying with '{best_model}'...")
                            try:
                                retry_resp = adapter.generate(
                                    messages=messages,
                                    system_prompt=system_prompt,
                                    model=best_model,
                                    temperature=self.temperature,
                                    timeout=self.timeout
                                )
                                if retry_resp.get("success"):
                                    logger.info(f"[LLM] Retry success via {adapter.name} using {best_model}")
                                    circuit_breaker.record_success(prov_code)
                                    reset_circuit_breaker(prov_code)
                                    record_provider_request(prov_code)
                                    record_provider_success(prov_code, best_model)
                                    if failed_attempts:
                                        retry_resp["fallback_notice"] = f"The selected AI provider is temporarily unavailable: {failed_attempts[0]}, answered by {adapter.name} using {best_model}."
                                    else:
                                        retry_resp["model_recovery_notice"] = f"Model '{prov_model}' was retired. Automatically switched to '{best_model}'."
                                    return retry_resp
                            except Exception as retry_err:
                                exact_retry_err = str(retry_err)
                                logger.warning(f"[LLM] Retry on {adapter.name} with '{best_model}' also failed: {exact_retry_err}")
                                record_provider_error(prov_code, exact_retry_err)
                                failed_attempts.append(f"{adapter.name} failed ({exact_retry_err})")
                                diagnostics_log.append(f"• **{adapter.name}**: {exact_retry_err}")
                                break

                    record_provider_error(prov_code, mue)
                    failed_attempts.append(f"{adapter.name} failed (model not found)")
                    diagnostics_log.append(f"• **{adapter.name}**: Model not found ({prov_model})")

                    if on_status_update:
                        on_status_update(f"Model unavailable on {adapter.name}. Trying next configured provider...")
                    break

                except RateLimitError as rle:
                    logger.warning(f"[LLM] RateLimit on {adapter.name}: {rle.message}")
                    circuit_breaker.record_failure(prov_code, "Rate limited", http_code=429)
                    trip_circuit_breaker(prov_code, http_code=429, error_msg="Rate limited")
                    if key_override:
                        key_pool.mark_key_rate_limited(prov_code, key_override, cooldown_seconds=60)
                    record_provider_error(prov_code, rle)
                    failed_attempts.append(f"{adapter.name} failed (rate limited)")
                    diagnostics_log.append(f"• **{adapter.name}**: Rate limited (429) - progressive cooldown applied")

                    if on_status_update:
                        on_status_update(f"Rate limited on {adapter.name}. Trying next configured provider...")
                    break

                except QuotaExhaustedError as qe:
                    logger.warning(f"[LLM] QuotaExhausted on {adapter.name}: {qe.message}")
                    circuit_breaker.record_failure(prov_code, "Quota exhausted", http_code=429)
                    trip_circuit_breaker(prov_code, http_code=429, error_msg="Quota exhausted")
                    if key_override:
                        key_pool.mark_key_rate_limited(prov_code, key_override, cooldown_seconds=300)
                    record_provider_error(prov_code, qe)
                    failed_attempts.append(f"{adapter.name} failed (quota exhausted)")
                    diagnostics_log.append(f"• **{adapter.name}**: Quota exhausted (no credits)")

                    if on_status_update:
                        on_status_update(f"Quota exhausted on {adapter.name}. Trying next configured provider...")
                    break

                except AuthenticationError as ae:
                    logger.warning(f"[LLM] AuthenticationError on {adapter.name}: {ae.message}")
                    mark_provider_misconfigured(prov_code, "Invalid API key (HTTP 401/403)")
                    circuit_breaker.record_failure(prov_code, "Invalid API key", http_code=401)
                    if key_override:
                        key_pool.mark_key_invalid(prov_code, key_override)
                    record_provider_error(prov_code, ae)
                    failed_attempts.append(f"{adapter.name} failed (invalid key)")
                    diagnostics_log.append(f"• **{adapter.name}**: Misconfigured (Invalid API key - skipped without retry)")

                    if on_status_update:
                        on_status_update(f"Authentication failed on {adapter.name}. Trying next configured provider...")
                    break

                except InvalidRequestError as ire:
                    logger.error(f"[LLM] Invalid user request on {adapter.name}: {ire.message}")
                    return {
                        "success": False,
                        "error": f"Invalid request: {ire.message}",
                        "is_user_error": True,
                        "provider": prov_code
                    }

                except Exception as e:
                    logger.exception(f"[LLM] Unexpected error invoking {adapter.name}: {str(e)}")
                    record_provider_error(prov_code, e)
                    failed_attempts.append(f"{adapter.name} failed ({str(e)})")
                    diagnostics_log.append(f"• **{adapter.name}**: Error ({str(e)})")
                    break

        # If all providers failed or none configured
        logger.error("[LLM] All configured providers failed or none available.")
        
        any_configured = False
        for code in CANONICAL_FALLBACK_ORDER:
            cls = PROVIDER_REGISTRY.get(code)
            if cls:
                key_override = self.api_key if self.requested_provider == code else None
                inst = cast(Any, cls)(api_key=key_override, base_url=self.base_url)
                if inst.is_configured():
                    any_configured = True
                    break

        if not any_configured:
            user_facing_error = (
                "⚠️ **No AI provider is currently available to complete the request.**\n\n"
                "No AI provider is configured yet. Add a valid API key in Settings or start a local Ollama model to begin."
            )
        else:
            user_facing_error = (
                "⚠️ **No AI provider is currently available to complete the request.**\n\n"
                "SPARK-AI couldn't connect to any available AI provider. Check the provider status in Settings and try again."
            )

        return {
            "success": False,
            "error": user_facing_error,
            "diagnostics": diagnostics_log,
            "provider_diagnostics": self.get_provider_diagnostics()
        }

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        task_type: Optional[str] = None,
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Backward-compatible alias for generate()."""
        return self.generate(messages, system_prompt, task_type=task_type, on_status_update=on_status_update)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        task_type: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        Yields text chunks directly from the active provider using provider-level streaming.
        Fails over to subsequent providers if an error occurs before chunks are emitted.
        """
        from core.rate_limiter import enforce_provider_gap, record_provider_request
        from core.provider_status import record_provider_success, record_provider_error

        chain = self._build_execution_chain(task_type)
        prov_timeout = float(timeout if timeout is not None else (self.timeout or PROVIDER_TIMEOUT_SECONDS))

        for prov_code, prov_model in chain:
            adapter_cls = PROVIDER_REGISTRY.get(prov_code)
            if not adapter_cls:
                continue

            key_override = self.api_key if (self.requested_provider == prov_code and self.api_key) else key_pool.get_key(prov_code)
            adapter = cast(Any, adapter_cls)(api_key=key_override, model=prov_model, base_url=self.base_url)

            if not adapter.is_configured():
                continue

            if is_provider_errored(prov_code):
                continue

            enforce_provider_gap(prov_code, min_gap_seconds=0.2)

            try:
                validate_provider_model(prov_code, prov_model)
            except InvalidProviderModelError:
                continue

            try:
                stream_iter = adapter.generate_stream(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=prov_model,
                    temperature=self.temperature,
                    timeout=prov_timeout
                )
                yielded_any = False
                for chunk in stream_iter:
                    yielded_any = True
                    yield chunk
                if yielded_any:
                    circuit_breaker.record_success(prov_code)
                    record_provider_request(prov_code)
                    record_provider_success(prov_code, prov_model)
                    return
            except Exception as e:
                logger.warning(f"[LLM STREAM] Provider {prov_code} failed during streaming: {e}")
                record_provider_error(prov_code, e)
                continue

    @classmethod
    def select_model_for_complexity(cls, provider: str, complexity_level: int) -> str:
        """Selects provider-compatible model based on the 5-level complexity classification."""
        p = provider.lower().strip()
        if p == "gemini":
            if complexity_level <= 2:
                return "gemini-3.5-flash-lite"
            elif complexity_level in (3, 4):
                return "gemini-3.8-flash"
            else:
                return "gemini-3.8-flash"
        elif p == "groq":
            return "llama-3.3-70b-versatile"
        elif p == "openai":
            if complexity_level <= 3:
                return "gpt-4o-mini"
            return "gpt-4o"
        elif p == "ollama":
            if complexity_level >= 4:
                return "deepseek-r1" if is_model_valid_for_provider("ollama", "deepseek-r1") else "llama3.2"
            return "llama3.2"
        return get_default_model(provider)

    @classmethod
    def select_task_optimal_model(cls, provider: str, task_category: str) -> str:
        """
        Task-aware model selection: chooses appropriate models based on reasoning vs speed requirements.
        """
        task_lower = (task_category or "").lower()
        is_deep_reasoning = any(k in task_lower for k in ("code", "math", "symbolic", "automl", "verification"))

        if provider == "gemini":
            return "gemini-3.8-flash" if is_deep_reasoning else "gemini-3.5-flash-lite"
        elif provider == "openai":
            return "gpt-4o" if is_deep_reasoning else "gpt-4o-mini"
        elif provider == "groq":
            return "llama-3.3-70b-versatile"
        elif provider == "ollama":
            return "deepseek-r1" if is_deep_reasoning else "llama3"
        return get_default_model(provider)

    def compare_model_outputs(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        competitor_provider: str = "openai",
        competitor_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs dual-model inference to compare primary provider output against competitor.
        Computes consensus score and highlights disagreements.
        """
        import difflib

        # 1. Primary generation
        primary_res = self.generate(messages, system_prompt)

        # 2. Competitor generation
        c_model = competitor_model or get_default_model(competitor_provider)
        comp_provider = LLMProvider(provider=competitor_provider, model=c_model)
        comp_res = comp_provider.generate(messages, system_prompt)

        text_a = primary_res.get("content", "").strip()
        text_b = comp_res.get("content", "").strip()

        # Compute similarity ratio
        matcher = difflib.SequenceMatcher(None, text_a.split(), text_b.split())
        similarity = round(matcher.ratio(), 3)

        consensus = "High Consensus" if similarity >= 0.75 else "Moderate Agreement" if similarity >= 0.45 else "Divergent / Disagreement"

        return {
            "primary": {
                "provider": primary_res.get("provider", self.provider),
                "model": primary_res.get("model", self.model),
                "content": text_a
            },
            "competitor": {
                "provider": competitor_provider,
                "model": c_model,
                "content": text_b
            },
            "similarity_score": similarity,
            "consensus_level": consensus,
            "has_disagreement": bool(similarity < 0.45)
        }

