"""Subprocess input validators for QUIRK — Phase 57 / CR-02, CR-03.

Decision enforcement:
  D-02: sibling validators in one module — validate_repo_path (CR-02) +
        validate_image_ref (CR-03).
  D-03: ValidationResult shape (ok, reason, redacted_preview) — duplicated here
        from url_allowlist for module independence.
  D-08: redacted_preview strips control chars, truncates to 32 chars.

Public surface:
  validate_repo_path(p) -> ValidationResult
  validate_image_ref(r) -> ValidationResult
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Final


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    """Frozen result returned by validation functions.

    Intentionally re-defined here (not imported from url_allowlist) to keep
    this module independently testable and importable (D-02 / D-03).

    Attributes:
        ok: True when the input passed all checks.
        reason: Empty string when ok=True; a reason-code constant otherwise.
        redacted_preview: Empty string when ok=True; a <= 32-char, control-char-
            stripped preview of the rejected input otherwise.
    """

    ok: bool
    reason: str            # "" when ok=True; reason-code constant otherwise
    redacted_preview: str  # "" when ok=True; <=32-char preview otherwise


# ---------------------------------------------------------------------------
# Reason-code constants (D-03 — fixed enum, NOT free-form strings)
# ---------------------------------------------------------------------------

RC_SHELL_METACHAR: Final[str] = "shell_metachar"
RC_PATH_TRAVERSAL: Final[str] = "path_traversal"
RC_NONEXISTENT_PATH: Final[str] = "nonexistent_path"
RC_INVALID_IMAGE_REF: Final[str] = "invalid_image_ref"
RC_LEADING_DASH: Final[str] = "leading_dash"


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Shell metacharacter set.  Matches semicolon, pipe, ampersand, dollar,
# backtick, angle brackets, glob chars, parens, backslash, and whitespace
# (including newline / carriage return) so that user-supplied paths and image
# refs cannot be used for command injection in subprocess.run invocations.
_SHELL_METACHARS: re.Pattern[str] = re.compile(r"[;|&$`<>*?()\\\s]")

# OCI distribution-spec subset: [registry/]repo[:tag][@digest]
# Allowed chars: alnum, '.', '-', '_', '/', ':', '@'
# Starts with an alphanumeric character; max 255 chars total.
_IMAGE_REF_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-/:@]{0,254}$")

# Local-filesystem / daemon-socket scheme prefixes that must be blocked.
# These cause Syft/Trivy to read from the local filesystem or Docker daemon
# rather than pull from a registry (analogous to the blocked dir:/file: vectors).
_LOCAL_REF_PREFIXES = ("dir:", "file:", "oci:", "docker-daemon:", "podman:", "docker-archive:")

# Pattern for stripping ASCII control characters (D-08).
_CTRL_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redact_preview(raw: str, max_len: int = 32) -> str:
    """Strip ASCII control characters from *raw* and truncate to *max_len* chars.

    Args:
        raw: The raw input string (path, image ref, …).
        max_len: Maximum length of the returned string (default 32 per D-08).

    Returns:
        A sanitised, truncated substring of *raw*.
    """
    cleaned = _CTRL_RE.sub("", raw)
    return cleaned[:max_len]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_repo_path(p: str) -> ValidationResult:
    """Validate *p* is safe to pass to semgrep as a target path (CR-02).

    Rejects:
    - Paths starting with ``-`` → RC_LEADING_DASH (argv injection guard).
    - Paths containing ``..`` or empty string → RC_PATH_TRAVERSAL.
    - Paths containing shell metacharacters → RC_SHELL_METACHAR.
    - Paths that do not point to an existing directory → RC_NONEXISTENT_PATH.

    Check order: leading-dash → path-traversal → shell-metachar → existence.
    An empty string is caught by the ``p == ""`` branch of the path-traversal
    check (documented choice: prefer RC_PATH_TRAVERSAL over RC_SHELL_METACHAR
    since an empty path is semantically a traversal / missing target rather than
    a metacharacter injection attempt).

    Args:
        p: Repository path string to validate.

    Returns:
        ``ValidationResult(ok=True, ...)`` when the path is safe and exists.
        ``ValidationResult(ok=False, reason=<code>, redacted_preview=<snippet>)``
        otherwise.
    """
    if p.startswith("-"):
        return ValidationResult(False, RC_LEADING_DASH, _redact_preview(p))

    if ".." in p or p == "":
        return ValidationResult(False, RC_PATH_TRAVERSAL, _redact_preview(p))

    if _SHELL_METACHARS.search(p):
        return ValidationResult(False, RC_SHELL_METACHAR, _redact_preview(p))

    real = os.path.realpath(p)
    if ".." in real:
        return ValidationResult(False, RC_PATH_TRAVERSAL, _redact_preview(p))
    if not os.path.isdir(real):
        return ValidationResult(False, RC_NONEXISTENT_PATH, _redact_preview(p))

    return ValidationResult(True, "", "")


def validate_image_ref(r: str) -> ValidationResult:
    """Validate *r* is a safe OCI image reference (CR-03).

    Rejects:
    - Refs starting with ``-`` → RC_LEADING_DASH (argv injection guard).
    - Refs starting with any local-access prefix (``dir:``, ``file:``, ``oci:``,
      ``docker-daemon:``, ``podman:``, ``docker-archive:``) → RC_INVALID_IMAGE_REF
      (Syft/Trivy local-filesystem / daemon-socket escape vectors).
    - Refs containing shell metacharacters → RC_SHELL_METACHAR.
    - Empty string or refs not matching the OCI distribution-spec regex →
      RC_INVALID_IMAGE_REF.

    Args:
        r: Image reference string to validate.

    Returns:
        ``ValidationResult(ok=True, ...)`` for valid OCI refs.
        ``ValidationResult(ok=False, reason=<code>, redacted_preview=<snippet>)``
        otherwise.
    """
    if r.startswith("-"):
        return ValidationResult(False, RC_LEADING_DASH, _redact_preview(r))

    if any(r.startswith(p) for p in _LOCAL_REF_PREFIXES):
        return ValidationResult(False, RC_INVALID_IMAGE_REF, _redact_preview(r))

    if _SHELL_METACHARS.search(r):
        return ValidationResult(False, RC_SHELL_METACHAR, _redact_preview(r))

    if not _IMAGE_REF_RE.match(r):
        return ValidationResult(False, RC_INVALID_IMAGE_REF, _redact_preview(r))

    return ValidationResult(True, "", "")
