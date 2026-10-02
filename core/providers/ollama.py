"""
Ollama Local Provider Adapter.
"""

import os
from typing import List, Dict, Any, Optional
import httpx

from core.providers.base import (
    BaseProvider,
    ProviderStatus,
    ProviderError,
    ProviderConnectionError,
    ModelUnavailableError,
    InvalidRequestError
)

class OllamaProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Ollama (Local)"

    @property
    def code(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3.2"

    def _get_base_url(self) -> str:
        return self.base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    def _get_server_root(self) -> str:
        url = self._get_base_url()
        return url.replace("/v1", "").rstrip("/")

    def is_configured(self) -> bool:
        # Check if Ollama server is responding
        try:
            root = self._get_server_root()
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{root}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        root = self._get_server_root()
        try:
            with httpx.Client(timeout=1.5) as client:
                res = client.get(f"{root}/api/tags")
                if res.status_code == 200:
                    models_data = res.json().get("models", [])
                    names = [m.get("name") for m in models_data]
                    return {
                        "status": ProviderStatus.AVAILABLE.value,
                        "reachable": True,
                        "installed_models": names,
                        "message": f"Ollama online with {len(names)} model(s)"
                    }
                return {"status": ProviderStatus.NETWORK_ERROR.value, "reachable": False, "message": f"Ollama HTTP {res.status_code}"}
        except Exception as e:
            return {"status": ProviderStatus.NOT_CONFIGURED.value, "reachable": False, "message": "Ollama server is not running"}

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ProviderConnectionError("Ollama server is not reachable at " + self._get_server_root())

        selected_model = model or self.model or self.default_model

        try:
            import openai
            client = openai.OpenAI(
                base_url=self._get_base_url(),
                api_key="ollama",
                timeout=timeout
            )

            formatted = [{"role": "system", "content": system_prompt}]
            for m in messages:
                if m.get("role") in ["user", "assistant"]:
                    formatted.append({"role": m["role"], "content": m.get("content", "")})

            response = client.chat.completions.create(
                model=selected_model,
                messages=formatted,
                temperature=temperature
            )
            content = (response.choices[0].message.content or "").strip()
            return {
                "success": True,
                "content": content,
                "provider": self.code,
                "model": selected_model
            }
        except Exception as e:
            err_str = str(e).lower()
            if "model" in err_str and ("not found" in err_str or "does not exist" in err_str):
                raise ModelUnavailableError(f"Ollama model '{selected_model}' not installed: {str(e)}")
            elif "connection" in err_str or "timeout" in err_str:
                raise ProviderConnectionError(f"Ollama connection error: {str(e)}")
            raise ProviderError(f"Ollama error: {str(e)}", is_recoverable=True)
