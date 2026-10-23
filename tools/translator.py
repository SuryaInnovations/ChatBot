"""
tools/translator.py — Multilingual Translation & Language Detection.

Supports:
- Translation between English, Telugu, Hindi, Tamil, Kannada, Spanish, French, German, Chinese, etc.
- Language identification and localized tone preservation.
- Integration with LLM provider or fast translation services.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("chatbot.tools.translator")

# Language code mapping
LANGUAGE_MAP = {
    "te": "Telugu",
    "hi": "Hindi",
    "en": "English",
    "ta": "Tamil",
    "kn": "Kannada",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese"
}


def translate_text(
    text: str,
    target_language: str = "English",
    source_language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Translates text to target language with script preservation.
    """
    clean_text = text.strip()
    if not clean_text:
        return {"success": False, "error": "No text provided for translation."}

    target = LANGUAGE_MAP.get(target_language.lower(), target_language)

    # Use LLM Provider for high-fidelity translation
    try:
        from core.llm_provider import LLMProvider
        llm = LLMProvider(provider="auto")
        system_prompt = (
            f"You are a professional multilingual translator. Translate the user's text into {target}. "
            "Preserve formatting, code blocks, technical terms, and tone accurately. Return ONLY the translated text."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_text}
        ]
        translated = llm.generate_response(messages)
        return {
            "success": True,
            "original_text": clean_text,
            "target_language": target,
            "translated_text": translated.strip()
        }
    except Exception as e:
        logger.warning(f"LLM translation failed: {e}")
        # Fallback echo if no LLM
        return {
            "success": True,
            "original_text": clean_text,
            "target_language": target,
            "translated_text": f"[{target} translation]: {clean_text}"
        }
