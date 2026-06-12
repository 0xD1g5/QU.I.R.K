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
    # CE-02: tighten so ARN path segments (e.g. role/MyLongRoleName) are not
    # over-redacted.  Two changes from the original r"\b[A-Za-z0-9+/]{40,}={0,2}\b":
    #   1. Require the run to START with [A-Za-z0-9] (not '/'), preventing matches
    #      that begin at the slash delimiter between ARN resource type and resource ID.
    #   2. Negative lookbehind (?<![:/]) excludes runs that immediately follow ':' or '/'
    #      — ARN colon-separated segments and slash-delimited paths are skipped.
    # Standalone tokens (API keys, AWS secret keys, base64 strings) remain redacted
    # because they start at a true word boundary not preceded by ':' or '/'.
    re.compile(r"(?<![:/])\b[A-Za-z0-9][A-Za-z0-9+/]{39,}={0,2}\b"),
    # API-key header name + value shapes (D-08)
    re.compile(r"X-Api-Key\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"X-Auth-Token\s*:\s*\S+", re.IGNORECASE),
    # Query-param API key shapes (D-08): ?api_key=<value> or &token=<value>
    re.compile(r"[?&](api_key|token|key|auth_token)=[^&\s]{8,}", re.IGNORECASE),
    # HTTP Basic credential payload
    re.compile(r"Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}={0,2}", re.IGNORECASE),
    # Phase 101 ISEC-02: Slack bot/user/app tokens
    re.compile(r"xox[bpoa]-[0-9A-Za-z\-]{10,}"),
    # Phase 101 ISEC-02: Slack incoming webhook URLs
    re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]+"),
    # Phase 101 ISEC-02: SMTP connection strings with embedded credentials
    re.compile(r"smtps?://[^:@\s]+:[^@\s]+@"),
    # Phase 104 ISEC-02: Jira/generic auth tuple repr — catches short PATs that
    # bypass the 40-char base64 pattern (e.g. basic_auth=('user', 'shortpat'),
    # token_auth='shortpat'). Requires a QUOTE as the first inner character so a
    # variable-reference repr (basic_auth=(user, token)) is NOT over-redacted —
    # only credential literals are scrubbed. Consumes through to the closing paren.
    re.compile(r"(basic_auth|token_auth)\s*=\s*\(?\s*['\"][^)\n]*", re.IGNORECASE),
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
