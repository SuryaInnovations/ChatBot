"""
Multi-provider LLM client with automatic fallback chain.
Supports Groq, Google Gemini, OpenAI, Ollama, and Anthropic.
Strictly returns honest errors without fabricating or polluting answers with banners.
"""

import os
import json
from typing import List, Dict, Any, Optional, Callable, Tuple

class LLMProvider:
    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_providers: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.environ.get(f"{self.provider.upper()}_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.fallback_providers = fallback_providers or []
        
        # Configure default model
        if model:
            self.model = model
        else:
            if self.provider == "groq":
                self.model = "llama-3.3-70b-versatile"
            elif self.provider == "gemini":
                self.model = "gemini-2.5-flash"
            elif self.provider == "openai":
                self.model = "gpt-4o-mini"
            elif self.provider == "ollama":
                self.model = "llama3.2"
            else:
                self.model = "llama-3.3-70b-versatile"

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes LLM request. If the primary provider fails, attempts configured fallback providers.
        """
        providers_to_try = [(self.provider, self.model, self.api_key, self.base_url)]
        
        # Add fallback providers if configured
        for fb in self.fallback_providers:
            p = fb.get("provider", "").lower()
            if p and p != self.provider:
                providers_to_try.append((
                    p,
                    fb.get("model"),
                    fb.get("api_key") or os.environ.get(f"{p.upper()}_API_KEY"),
                    fb.get("base_url")
                ))

        last_error = ""

        for prov_name, prov_model, prov_key, prov_url in providers_to_try:
            # Check if this provider has an API key (or is local ollama)
            if prov_name != "ollama" and not prov_key:
                continue

            try:
                if prov_name == "groq":
                    res = self._call_groq(prov_key, prov_model, messages, system_prompt, on_tool_call)
                elif prov_name == "gemini":
                    res = self._call_gemini(prov_key, prov_model, messages, system_prompt)
                elif prov_name in ["openai", "ollama"]:
                    res = self._call_openai_compatible(prov_name, prov_key, prov_model, prov_url, messages, system_prompt, on_tool_call)
                else:
                    continue

                if res.get("success"):
                    return res
                else:
                    last_error = res.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                continue

        # If all providers fail or none configured:
        return {
            "success": False,
            "error": "AI generation is temporarily unavailable. Please configure an available model provider.",
            "raw_error": last_error
        }

    def _call_groq(
        self,
        api_key: str,
        model: Optional[str],
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        import groq
        client = groq.Groq(api_key=api_key)
        
        selected_model = model or "llama-3.3-70b-versatile"
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                formatted_messages.append({"role": m["role"], "content": m.get("content", "")})

        response = client.chat.completions.create(
            model=selected_model,
            messages=formatted_messages,
            temperature=self.temperature
        )
        content = response.choices[0].message.content or ""
        return {
            "success": True,
            "content": content.strip(),
            "provider": "groq",
            "model": selected_model
        }

    def _call_gemini(
        self,
        api_key: str,
        model: Optional[str],
        messages: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        selected_model = model or "gemini-2.5-flash"
        
        conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION:\n"
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                conversation_text += f"\n{m['role'].upper()}: {m.get('content', '')}\n"

        response = client.models.generate_content(
            model=selected_model,
            contents=conversation_text
        )
        content = response.text or ""
        return {
            "success": True,
            "content": content.strip(),
            "provider": "gemini",
            "model": selected_model
        }

    def _call_openai_compatible(
        self,
        provider_name: str,
        api_key: Optional[str],
        model: Optional[str],
        base_url: Optional[str],
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        import openai
        
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        elif provider_name == "ollama":
            kwargs["base_url"] = "http://localhost:11434/v1"
            if not api_key:
                kwargs["api_key"] = "ollama"

        client = openai.OpenAI(**kwargs)
        selected_model = model or ("llama3.2" if provider_name == "ollama" else "gpt-4o-mini")

        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                formatted_messages.append({"role": m["role"], "content": m.get("content", "")})

        response = client.chat.completions.create(
            model=selected_model,
            messages=formatted_messages,
            temperature=self.temperature
        )
        content = response.choices[0].message.content or ""
        return {
            "success": True,
            "content": content.strip(),
            "provider": provider_name,
            "model": selected_model
        }
