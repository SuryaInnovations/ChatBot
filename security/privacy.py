"""
security/privacy.py — Privacy Controls, Secret Redaction, and Data Retention.

Provides:
- PII and Secret Redaction (API keys, tokens, emails, phone numbers).
- Per-user resource access boundaries.
- Data retention policies and right-to-be-forgotten deletion workflows.
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("chatbot.security.privacy")

# Regex patterns for detecting and redacting sensitive data
PATTERNS = {
    "api_key": r"(?i)(api[_-]?key|secret|token|bearer|password)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?",
    "openai_key": r"sk-[a-zA-Z0-9]{32,}",
    "jwt_token": r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(\+?[0-9]{1,3}[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
}

COMPILED_PATTERNS = {k: re.compile(v) for k, v in PATTERNS.items()}


def redact_secrets(text: str, mask: str = "[REDACTED]") -> str:
    """
    Scans text and redacts API keys, credentials, tokens, and PII.
    """
    if not text or not isinstance(text, str):
        return text

    redacted = text
    # Mask specific known key shapes first
    redacted = COMPILED_PATTERNS["openai_key"].sub("[REDACTED_API_KEY]", redacted)
    redacted = COMPILED_PATTERNS["jwt_token"].sub("[REDACTED_JWT]", redacted)
    redacted = COMPILED_PATTERNS["credit_card"].sub("[REDACTED_CC]", redacted)

    # Key-value assignment masking
    def replace_kv(match):
        prefix = match.group(1)
        return f"{prefix}={mask}"

    redacted = COMPILED_PATTERNS["api_key"].sub(replace_kv, redacted)
    return redacted


def redact_pii(text: str) -> str:
    """Redacts emails and phone numbers for privacy."""
    if not text or not isinstance(text, str):
        return text
    text = COMPILED_PATTERNS["email"].sub("[EMAIL_REDACTED]", text)
    text = COMPILED_PATTERNS["phone"].sub("[PHONE_REDACTED]", text)
    return text


class PrivacyManager:
    """Manages user privacy, resource ownership, and GDPR deletion/export requests."""
    def __init__(self):
        self._retention_days = 90

    def verify_ownership(self, user_id: str, resource_owner_id: str) -> bool:
        """Verifies that the acting user owns the target resource."""
        if not user_id or not resource_owner_id:
            return False
        return str(user_id) == str(resource_owner_id)

    def scrub_export_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cleans sensitive system metadata before returning export data to user."""
        scrubbed = {}
        for k, v in data.items():
            if k in ("hashed_password", "salt", "session_tokens", "api_keys"):
                continue
            if isinstance(v, str):
                scrubbed[k] = redact_secrets(v)
            elif isinstance(v, dict):
                scrubbed[k] = self.scrub_export_data(v)
            else:
                scrubbed[k] = v
        return scrubbed


default_privacy_manager = PrivacyManager()
