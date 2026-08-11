"""Shared logging setup and log redaction for SolArk modules.

The redaction helpers are ported verbatim from upstream
HammondAutomationHub/HomeAssistant_SolArk commit d336443 ("removed auth from
logs"), where they live in ``api.py``. This fork splits that module into
``solark_auth.py`` + ``solark_client.py``, and both need the helpers, so they
live here (a leaf module with no intra-package imports) to avoid a cycle.
``api.py`` re-exports ``_redact_secret_text`` so upstream's import path
(``from .api import _redact_secret_text``) keeps working.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict


def get_logger(name: str) -> logging.Logger:
    """Return a standard logger (respects Home Assistant logging config)."""
    return logging.getLogger(name)


_REDACTED = "***REDACTED***"
_SENSITIVE_KEYS = {
    "password",
    "username",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "client_secret",
}
_SECRET_STRING_PATTERNS = (
    re.compile(r'(?i)("password"\s*:\s*")([^"]*)(")'),
    re.compile(r'(?i)("username"\s*:\s*")([^"]*)(")'),
    re.compile(r'(?i)("access_token"\s*:\s*")([^"]*)(")'),
    re.compile(r'(?i)("refresh_token"\s*:\s*")([^"]*)(")'),
    re.compile(r'(?i)("token"\s*:\s*")([^"]*)(")'),
    re.compile(r"(?i)(Bearer\s+)\S+"),
)


def _redact_secrets(value: Any) -> Any:
    """Recursively redact credentials/tokens for safe logging."""
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                redacted[key] = _REDACTED
            else:
                redacted[key] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_text(value)
    return value


def _redact_secret_text(text: str) -> str:
    """Redact credential/token patterns from free-form log text."""
    if not text:
        return text
    sanitized = text
    for pattern in _SECRET_STRING_PATTERNS:
        if pattern.groups == 3:
            sanitized = pattern.sub(rf"\1{_REDACTED}\3", sanitized)
        else:
            sanitized = pattern.sub(rf"\1{_REDACTED}", sanitized)
    return sanitized
