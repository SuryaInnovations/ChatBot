"""
Google Gemini Provider Adapter.
Supports gemini-3.8-flash, gemini-3.7-flash, and dynamic model discovery.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Callable

from core.providers.base import (
    BaseProvider,
    ProviderStatus,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError
)
from core.models import validate_provider_model, sort_gemini_models
from core.rate_limiter import enforce_provider_gap, parse_error_details
from core.provider_status import record_provider_error, record_provider_success

logger = logging.getLogger("chatbot.providers.gemini")

class GeminiProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Google Gemini"

    @property
    def code(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"

    def _get_api_key(self) -> Optional[str]:
        # 1. Direct explicit key passed to adapter
        if self.api_key and self.api_key.strip():
            return self.api_key.strip()

        # 2. Key from Streamlit session state (immediate live sidebar update without restart)
        try:
            import streamlit as st
            if hasattr(st, "runtime") and st.runtime.exists() and "gemini_api_key" in st.session_state:
                val = st.session_state["gemini_api_key"]
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
        except Exception:
            pass

        # 3. Key from environment variables (.env fallback)
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        return key.strip() or None

    def is_configured(self) -> bool:
        return self._get_api_key() is not None

    def query_available_models(self) -> Dict[str, Any]:
        """
        Queries Google Gemini API for models available to this key.
        Keeps only models supporting generateContent, strips 'models/',
        and sorts Flash models first, newest versions first.
        """
        key = self._get_api_key()
        if not key:
            return {
                "success": False,
                "models": [],
                "count": 0,
                "error": "Google Gemini API key is not configured."
            }
        try:
            from google import genai
            client = genai.Client(api_key=key)
            models = []
            for m in client.models.list():
                # Check generateContent support
                actions = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None)
                if actions is None and hasattr(m, "to_json_dict"):
                    try:
                        d = m.to_json_dict()
                        actions = d.get("supported_actions") or d.get("supportedGenerationMethods") or d.get("supported_generation_methods")
                    except Exception:
                        pass

                if actions:
                    supports_generate = any("generatecontent" in str(a).lower() for a in actions)
                    if not supports_generate:
                        continue

                name = getattr(m, "name", "") or ""
                if name.startswith("models/"):
                    name = name[len("models/"):]
                name = name.strip()

                # Exclude retired models like gemini-2.5-flash
                if name and "gemini" in name.lower() and "gemini-2.5-flash" not in name.lower():
                    models.append(name)

            sorted_models = sort_gemini_models(models)
            return {
                "success": True,
                "models": sorted_models,
                "count": len(sorted_models),
                "error": None
            }
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Failed to query Gemini models: {err_msg}")
            return {
                "success": False,
                "models": [],
                "count": 0,
                "error": err_msg
            }

    def list_available_models(self) -> List[str]:
        """Queries Google Gemini API for models available to this key."""
        res = self.query_available_models()
        return res.get("models", [])

    def test_connection(self) -> Dict[str, Any]:
        """
        Sends a 1-word prompt to verify credentials and access.
        If a 404 occurs, automatically queries models and retries once with the best Flash model.
        """
        target_model = self.model or self.default_model
        try:
            res = self.generate(
                messages=[{"role": "user", "content": "ping"}],
                system_prompt="Respond with 'pong'.",
                model=target_model,
                timeout=12.0
            )
            return {
                "success": True,
                "message": f"Connection verified successfully using model '{res.get('model', target_model)}'.",
                "model": res.get("model", target_model)
            }
        except ModelUnavailableError as mue:
            logger.warning(f"[Gemini test_connection] Model '{target_model}' unavailable: {mue.message}. Attempting discovery...")
            query_res = self.query_available_models()
            models = query_res.get("models") or mue.available_models or []
            if models:
                best_model = next((m for m in models if "flash" in m.lower()), models[0])
                if best_model != target_model:
                    try:
                        _ = self.generate(
                            messages=[{"role": "user", "content": "ping"}],
                            system_prompt="Respond with 'pong'.",
                            model=best_model,
                            timeout=12.0
                        )
                        return {
                            "success": True,
                            "message": f"Model '{target_model}' not found. Auto-switched to '{best_model}' and verified successfully!",
                            "model": best_model,
                            "retried": True,
                            "available_models": models
                        }
                    except Exception as retry_err:
                        return {
                            "success": False,
                            "message": f"Model '{target_model}' not found. Retry with '{best_model}' failed: {str(retry_err)}",
                            "error_type": "ModelUnavailableError",
                            "available_models": models
                        }
            return {
                "success": False,
                "message": mue.message,
                "error_type": "ModelUnavailableError",
                "available_models": models
            }
        except ProviderError as pe:
            return {
                "success": False,
                "message": pe.message,
                "error_type": pe.__class__.__name__,
                "status_code": pe.status_code,
                "available_models": getattr(pe, "available_models", [])
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "error_type": "UnexpectedError",
                "available_models": []
            }

    def health_check(self) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "GEMINI_API_KEY not set"}
        try:
            from google import genai
            _ = genai.Client(api_key=key)
            return {"status": ProviderStatus.AVAILABLE.value, "reachable": True, "message": "Gemini client initialized"}
        except Exception as e:
            return {"status": ProviderStatus.UNKNOWN_ERROR.value, "reachable": False, "message": str(e)}

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0,
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        key = self._get_api_key()
        if not key:
            raise AuthenticationError("Google Gemini API key is not configured.")

        selected_model = model or self.model or self.default_model

        # HARD VALIDATION LAYER: strictly rejects foreign models before any SDK request
        validate_provider_model(self.code, selected_model)

        if not hasattr(self, "_cached_client") or getattr(self, "_cached_api_key", None) != key:
            from google import genai
            self._cached_client = genai.Client(api_key=key)
            self._cached_api_key = key
        client = self._cached_client

        conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION:\n"
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                conversation_text += f"\n{m['role'].upper()}: {m.get('content', '')}\n"

        rate_limit_retries = 0
        max_rate_limit_retries = 2

        server_error_retries = 0
        max_server_error_retries = 3

        while True:
            # Enforce minimum 0.2-second gap between requests to avoid free-tier burst limits
            enforce_provider_gap(self.code, min_gap_seconds=0.2)

            try:
                gen_kwargs: Dict[str, Any] = {"model": selected_model, "contents": conversation_text}
                # Gemini API enforces minimum allowed deadline of 10s for manual http_options.timeout
                if timeout >= 10.0:
                    try:
                        import inspect
                        sig = inspect.signature(client.models.generate_content)
                        if "config" in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
                            gen_kwargs["config"] = {"http_options": {"timeout": int(timeout * 1000)}}
                    except Exception:
                        pass

                response = client.models.generate_content(**gen_kwargs)
                content = (response.text or "").strip()
                return {
                    "success": True,
                    "content": content,
                    "provider": self.code,
                    "model": selected_model
                }
            except Exception as e:
                parsed = parse_error_details(e)
                http_code = parsed["http_code"]
                error_status = parsed["error_status"]
                retry_delay = parsed["retry_delay"]
                clean_msg = parsed["message"]
                err_str = str(e).lower()

                # TASK 2: Handle rate limits (HTTP 429 / RESOURCE_EXHAUSTED)
                is_rate_limited = (
                    http_code == 429 or 
                    error_status == "RESOURCE_EXHAUSTED" or 
                    "resource_exhausted" in err_str or 
                    "rate limit" in err_str or 
                    "too many requests" in err_str
                )
                if is_rate_limited:
                    # If this specific model hit a daily quota cap, attempt available alternate Flash models
                    if (retry_delay and retry_delay > 60) or "free_tier_requests" in err_str:
                        alt_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
                        for alt in alt_models:
                            if alt != selected_model:
                                try:
                                    logger.info(f"[Gemini] Quota limit on {selected_model}, auto-trying {alt}...")
                                    if on_status_update:
                                        on_status_update(f"Model {selected_model} quota reached, switching to {alt}...")
                                    alt_resp = client.models.generate_content(
                                        model=alt,
                                        contents=conversation_text
                                    )
                                    alt_content = alt_resp.text.strip() if hasattr(alt_resp, "text") and alt_resp.text else ""
                                    record_provider_success(self.code, model=alt)
                                    return {
                                        "success": True,
                                        "content": alt_content,
                                        "provider": self.code,
                                        "model": alt
                                    }
                                except Exception as alt_err:
                                    logger.debug(f"[Gemini] Alt model {alt} failed: {alt_err}")

                    if rate_limit_retries < max_rate_limit_retries:
                        rate_limit_retries += 1
                        # Cap delay at 30 seconds
                        wait_delay = min(retry_delay or (5.0 * rate_limit_retries), 30.0)
                        logger.warning(
                            f"[Gemini] Rate limited (429 RESOURCE_EXHAUSTED). Waiting {wait_delay:.1f}s "
                            f"(retry {rate_limit_retries}/{max_rate_limit_retries})..."
                        )
                        if on_status_update:
                            on_status_update(f"Rate limited, retrying in {int(wait_delay)} seconds...")
                        time.sleep(wait_delay)
                        continue
                    else:
                        logger.error(f"[Gemini] Rate limit retries exhausted after {max_rate_limit_retries} attempts.")
                        record_provider_error(self.code, e)
                        raise RateLimitError(
                            f"Gemini rate limit exceeded (429 RESOURCE_EXHAUSTED): {clean_msg}",
                            status_code=429,
                            error_status="RESOURCE_EXHAUSTED",
                            retry_delay=retry_delay
                        )

                # TASK 3: Handle temporary errors (HTTP 500/502/503/504 / UNAVAILABLE / INTERNAL)
                is_temp_error = (
                    http_code in (500, 502, 503, 504) or 
                    error_status in ("UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED") or 
                    "unavailable" in err_str or 
                    "temporarily unavailable" in err_str
                )
                if is_temp_error:
                    if server_error_retries < max_server_error_retries:
                        backoff = [1.0, 2.0, 4.0][server_error_retries]
                        server_error_retries += 1
                        logger.warning(
                            f"[Gemini] Temporary error ({http_code or error_status}). Backing off {backoff:.1f}s "
                            f"(retry {server_error_retries}/{max_server_error_retries})..."
                        )
                        if on_status_update:
                            on_status_update(f"Temporary server error ({error_status or http_code}), retrying in {int(backoff)}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"[Gemini] Temporary error retries exhausted after {max_server_error_retries} attempts.")
                        record_provider_error(self.code, e)
                        raise ProviderConnectionError(
                            f"Gemini server error ({http_code or error_status}): {clean_msg}",
                            status_code=http_code or 503,
                            error_status=error_status or "UNAVAILABLE"
                        )

                # Model Not Found (404 / NOT_FOUND)
                is_not_found = (
                    http_code == 404 or 
                    error_status == "NOT_FOUND" or 
                    "not_found" in err_str or 
                    "no longer available" in err_str or 
                    "not supported" in err_str
                )
                if is_not_found:
                    query_res = self.query_available_models()
                    avail = query_res.get("models", [])
                    short_msg = f"Gemini model '{selected_model}' not found (404 NOT_FOUND): {clean_msg}"
                    record_provider_error(self.code, e)
                    raise ModelUnavailableError(short_msg, status_code=404, error_status="NOT_FOUND", available_models=avail)

                # Authentication / Permission (401, 403 / PERMISSION_DENIED)
                is_auth_error = (
                    http_code in (401, 403) or 
                    error_status in ("PERMISSION_DENIED", "UNAUTHENTICATED") or 
                    "api_key" in err_str or 
                    "unauthenticated" in err_str or 
                    "permission" in err_str
                )
                if is_auth_error:
                    record_provider_error(self.code, e)
                    raise AuthenticationError(
                        f"Gemini authentication failed ({http_code or 401} {error_status or 'PERMISSION_DENIED'}): {clean_msg}",
                        status_code=http_code or 401,
                        error_status=error_status or "PERMISSION_DENIED"
                    )

                # Invalid Request (400 / INVALID_ARGUMENT)
                if http_code == 400 or error_status == "INVALID_ARGUMENT":
                    record_provider_error(self.code, e)
                    raise InvalidRequestError(
                        f"Gemini bad request (400 INVALID_ARGUMENT): {clean_msg}",
                        status_code=400,
                        error_status="INVALID_ARGUMENT"
                    )

                # Any other error: record real status code and details
                record_provider_error(self.code, e)
                raise ProviderError(
                    f"Gemini error ({http_code or ''} {error_status or ''}): {clean_msg}".strip(),
                    status_code=http_code,
                    error_status=error_status,
                    retry_delay=retry_delay,
                    is_recoverable=True
                )

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ):
        """
        Yields text chunks as they arrive from the Google Gemini streaming API.
        """
        key = self._get_api_key()
        if not key:
            raise AuthenticationError("Google Gemini API key is not configured.")

        selected_model = model or self.model or self.default_model
        validate_provider_model(self.code, selected_model)

        if not hasattr(self, "_cached_client") or getattr(self, "_cached_api_key", None) != key:
            from google import genai
            self._cached_client = genai.Client(api_key=key)
            self._cached_api_key = key
        client = self._cached_client

        conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION:\n"
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                conversation_text += f"\n{m['role'].upper()}: {m.get('content', '')}\n"

        enforce_provider_gap(self.code, min_gap_seconds=0.2)

        try:
            stream_kwargs: Dict[str, Any] = {"model": selected_model, "contents": conversation_text}
            # Gemini API enforces minimum allowed deadline of 10s for manual http_options.timeout
            if timeout >= 10.0:
                try:
                    import inspect
                    sig = inspect.signature(client.models.generate_content_stream)
                    if "config" in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
                        stream_kwargs["config"] = {"http_options": {"timeout": int(timeout * 1000)}}
                except Exception:
                    pass

            response_stream = client.models.generate_content_stream(**stream_kwargs)
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            record_provider_error(self.code, e)
            parsed = parse_error_details(e)
            http_code = parsed["http_code"]
            clean_msg = parsed["message"]
            if http_code in (401, 403):
                raise AuthenticationError(f"Gemini authentication failed: {clean_msg}")
            raise ProviderError(f"Gemini streaming error: {clean_msg}", is_recoverable=True)
