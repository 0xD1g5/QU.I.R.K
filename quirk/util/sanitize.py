"""Scanner-controlled string sanitization chokepoint — Phase 78 / HARDEN-02..HARDEN-03.

Single source of truth for scanner-controlled string sanitization. Strict
text-only allowlist. URLs stripped. Used by every Jinja `| sanitize` filter
call and every report-side scanner-string write. Never bypass.

Decision enforcement:
  - HARDEN-02: Allowlist policy defined exactly once, in this module. Callers
    never pass tag/attribute overrides; nh3 invocation is sealed inside
    sanitize_scanner_text.
  - HARDEN-03: Scanner-emitted free-text (CN/SAN, host, error msg, finding
    desc, banners) flows through this function before reaching HTML/PDF/MD
    renderers.
  - HARDEN-06: nh3 is a hard (non-optional) project dep — imported at module
    top, not lazily.
  - Module independence: no cross-imports from other quirk.util modules so
    this helper remains importable in isolation (mirrors safe_exc.py
    D-02 / D-03 rule).

Public surface:
  sanitize_scanner_text(value) -> str
"""
from __future__ import annotations

import re
from typing import Final

import nh3

# Hostile schemes + plain URL text — stripped before nh3 sees the text. nh3
# has no plain-text URL stripper; its `url_schemes` option only constrains
# attribute schemes on tags like <a href> / <img src>, and we strip every
# tag anyway. So bare-text URL stripping must happen here.
_URL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:https?|javascript|data|vbscript|file|ftp):\S+",
    re.IGNORECASE,
)

# Strict text-only allowlist — empty tag set, empty attribute map. nh3
# returns the textual content with every tag (and its attributes) stripped.
_NH3_TAGS: Final[set[str]] = set()
_NH3_ATTRS: Final[dict[str, set[str]]] = {}
# Override nh3's default `clean_content_tags` (which includes <script>,
# <style>, etc. and removes their *content* entirely). For scanner-text
# sanitization we want every tag stripped but its textual content kept
# (per Phase 78 must_have: "<script>x</script>" -> "x"). Passing an empty
# set preserves text under all tags.
_NH3_CLEAN_CONTENT_TAGS: Final[set[str]] = set()


def sanitize_scanner_text(value) -> str:
    """Return a sanitized plain-text rendering of scanner-controlled input.

    Pipeline:
      1. ``None`` → ``""``.
      2. Coerce to ``str`` (errors collapse to ``""``).
      3. Strip URL-like substrings for every hostile scheme
         (``http``, ``https``, ``javascript``, ``data``, ``vbscript``,
         ``file``, ``ftp``).
      4. ``nh3.clean()`` with empty tag + attribute allowlists — every tag
         is stripped, text content is preserved.

    The output is safe for direct interpolation into HTML (via Jinja
    autoescape and the ``| sanitize`` filter) or markdown (paired with
    ``md_cell`` for table-cell contexts). Idempotent: feeding the output
    back through this function yields the same string.
    """
    if value is None:
        return ""
    try:
        text = str(value)
    except Exception:
        return ""
    text = _URL_RE.sub("", text)
    return nh3.clean(
        text,
        tags=_NH3_TAGS,
        attributes=_NH3_ATTRS,
        clean_content_tags=_NH3_CLEAN_CONTENT_TAGS,
    )
