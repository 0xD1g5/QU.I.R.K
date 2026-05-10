"""Credential-safe exception stringification — Phase 59 / LEAK-01.

Decision enforcement:
  - LEAK-01: Default return is f'{type(exc).__name__}'; class+message is
    returned only when str(exc) does not match any _SENSITIVE_PATTERNS
    regex. Errors during str(exc) collapse to class-name-only.
  - Module independence: no cross-imports from other quirk.util modules
    so this helper remains importable in isolation (mirrors Phase 57
    subprocess_input.py D-02 / D-03).

Public surface:
  safe_str(exc: BaseException) -> str
"""
from __future__ import annotations

import re
from typing import Final

# Patterns indicating credential-bearing content. Order is irrelevant —
# any match triggers class-name-only return.
_SENSITIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Vault hvac token (s. prefix + 20+ url-safe chars)
    re.compile(r"\b(s\.|hvs\.)[A-Za-z0-9_\-]{20,}"),
    # Connection string with embedded password: scheme://user:pass@host
    re.compile(r"://[^:@\s]+:[^@\s]+@"),
    # GCP ADC config path
    re.compile(r"[\\/]\.?config[\\/]gcloud[\\/]"),
    re.compile(r"gcloud[\\/]application_default_credentials"),
    # Authorization header leaked into exception text
    re.compile(r"Authorization:\s*(Bearer|Basic)\s+\S+", re.IGNORECASE),
    # Long base64-shaped token (40+ chars, optional = padding)
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)


def safe_str(exc: BaseException) -> str:
    """Return a credential-safe string representation of *exc*.

    Returns f'{type(exc).__name__}' when:
      - str(exc) raises, OR
      - the message matches any pattern in _SENSITIVE_PATTERNS.

    Otherwise returns f'{type(exc).__name__}: {msg}'.
    """
    class_name = type(exc).__name__
    try:
        msg = str(exc)
    except Exception:
        return class_name
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(msg):
            return class_name
    return f"{class_name}: {msg}"
