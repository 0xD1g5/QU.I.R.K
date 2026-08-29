"""Phase 172 / Plan 03 — unit coverage for quirk/util/subprocess_input.py (SAFE-03).

This is the first dedicated test file for this module's validators
(``tests/test_subprocess_logging.py`` covers unrelated container/source/ssh
scanner logging, not these validators — confirmed in RESEARCH.md).

Covers:
  1. The renamed truncation helper (``_truncate_preview``) is importable and
     the pre-rename name (``_redact_preview``) is not.
  2. ``validate_repo_path`` previews for its rejection branches are truncated,
     not URL-parsed.
  3. A path or image ref containing ``@`` or ``?`` survives with those
     characters intact (Pitfall 3 regression lock — these are legal path /
     image-ref characters, not URL syntax, and must never be mis-parsed as
     userinfo/query by a helper that only truncates).
  4. The truncation boundary is still 32 characters.

Falsifiability: applying URL-component-parsing logic (stripping anything that
looks like userinfo or a query string) to this module's helper would make the
``@``/``?``-preservation tests below fail. Reverting the rename (restoring the
name ``_redact_preview``) would make the importability test fail.
"""
from __future__ import annotations

import pytest

from quirk.util.subprocess_input import (
    RC_INVALID_IMAGE_REF,
    RC_LEADING_DASH,
    RC_NONEXISTENT_PATH,
    RC_PATH_TRAVERSAL,
    RC_SHELL_METACHAR,
    ValidationResult,
    _truncate_preview,
    validate_image_ref,
    validate_repo_path,
)


def test_truncate_preview_importable_old_name_gone():
    """The renamed helper is importable; the pre-rename name no longer exists."""
    import quirk.util.subprocess_input as mod

    assert hasattr(mod, "_truncate_preview")
    assert not hasattr(mod, "_redact_preview")


def test_validate_repo_path_leading_dash_preview_truncated():
    r = validate_repo_path("-rf")
    assert r.ok is False
    assert r.reason == RC_LEADING_DASH
    assert r.redacted_preview == "-rf"


def test_validate_repo_path_traversal_preview_truncated():
    r = validate_repo_path("../../etc/passwd")
    assert r.ok is False
    assert r.reason == RC_PATH_TRAVERSAL
    assert r.redacted_preview == "../../etc/passwd"


def test_validate_repo_path_shell_metachar_preview_truncated():
    r = validate_repo_path("foo; rm -rf /")
    assert r.ok is False
    assert r.reason == RC_SHELL_METACHAR
    assert r.redacted_preview == "foo; rm -rf /"


def test_validate_repo_path_nonexistent_preview_truncated():
    path = "/definitely/not/a/real/path/xyz/deeper/nesting/here"
    r = validate_repo_path(path)
    assert r.ok is False
    assert r.reason == RC_NONEXISTENT_PATH
    assert r.redacted_preview == path[:32]
    assert len(r.redacted_preview) == 32


def test_image_ref_with_at_and_digest_survives_intact():
    """A legitimate '@sha256:...' digest ref is truncation-only, never URL-parsed.

    Pitfall 3 regression lock: if urlparse-based stripping were mistakenly
    applied here, the '@' would be treated as a userinfo separator and the
    digest would be silently dropped from the preview.
    """
    ref = "repo@sha256:" + ("a" * 64)
    r = validate_image_ref(ref + "$(evil)")  # force a shell-metachar rejection
    assert r.ok is False
    assert r.reason == RC_SHELL_METACHAR
    assert "@" in r.redacted_preview
    assert "sha256:" in r.redacted_preview


def test_repo_path_with_question_mark_survives_intact():
    """A path containing a literal '?' (legal on most filesystems) is preserved, not parsed as a query string."""
    r = validate_repo_path("weird?path;rm")
    assert r.ok is False
    assert "?" in r.redacted_preview


def test_truncate_preview_boundary_is_32_chars():
    long_input = "a" * 100
    assert len(_truncate_preview(long_input)) == 32
    assert _truncate_preview(long_input) == "a" * 32


def test_truncate_preview_does_not_apply_url_parsing():
    """A value containing '://', '@', and '?' together (URL-shaped) is still
    just truncated — no scheme/host/query extraction happens here.
    """
    raw = "https://user:pass@host.example/path?token=secret"
    preview = _truncate_preview(raw, max_len=200)
    # Truncation-only: the full string (all components) survives verbatim.
    assert preview == raw
    assert "user:pass" in preview
    assert "token=secret" in preview
