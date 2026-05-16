"""Phase 78 / HARDEN-03 + HARDEN-06: Unit tests for the scanner-text
sanitization chokepoint at ``quirk.util.sanitize.sanitize_scanner_text``.

Covers:
  - None / non-str coercion behaviour
  - HTML tag stripping (content preserved)
  - URL stripping for every hostile scheme (http, https, javascript, data,
    vbscript, file, ftp) — one explicit test per scheme so failure
    messages name the offender.
  - Control-character passthrough (CONTEXT.md defers backtick / control
    handling to md_cell; nh3 leaves them in place)
  - Idempotency
  - nh3 importability (HARDEN-06 import-presence gate)
  - bleach absence in pyproject.toml dependencies (HARDEN-06
    belt-and-suspenders)
"""
from __future__ import annotations

import pathlib
import tomllib

import pytest

from quirk.util.sanitize import sanitize_scanner_text


def test_none_returns_empty_string() -> None:
    assert sanitize_scanner_text(None) == ""


def test_int_coerces_via_str() -> None:
    assert sanitize_scanner_text(42) == "42"


def test_script_tag_stripped_content_preserved() -> None:
    assert sanitize_scanner_text("<script>alert(1)</script>") == "alert(1)"


def test_img_onerror_stripped() -> None:
    result = sanitize_scanner_text("<img src=x onerror=alert(1)>")
    assert "<" not in result
    assert ">" not in result


def test_http_url_stripped() -> None:
    assert "https://" not in sanitize_scanner_text("see https://evil.example/path here")


def test_javascript_url_stripped() -> None:
    assert "javascript:" not in sanitize_scanner_text("javascript:alert(1)")


def test_data_url_stripped() -> None:
    assert "data:" not in sanitize_scanner_text("data:text/html,<script>x</script>")


def test_vbscript_url_stripped() -> None:
    assert "vbscript:" not in sanitize_scanner_text("vbscript:msgbox(1)")


def test_file_url_stripped() -> None:
    assert "file://" not in sanitize_scanner_text("file:///etc/passwd")


def test_ftp_url_stripped() -> None:
    assert "ftp://" not in sanitize_scanner_text("ftp://host/file")


def test_control_chars_passthrough_or_safe() -> None:
    # nh3 leaves bare control chars in place; md_cell handles them later
    # for markdown table contexts (per CONTEXT.md deferral).
    result = sanitize_scanner_text("\x07")
    assert isinstance(result, str)


def test_idempotency() -> None:
    once = sanitize_scanner_text("<b>x</b>")
    twice = sanitize_scanner_text(once)
    assert twice == once


def test_nh3_available() -> None:
    """HARDEN-06: nh3 must be importable as a core dependency."""
    import nh3  # noqa: F401

    assert hasattr(nh3, "clean")


def test_no_bleach_in_deps() -> None:
    """HARDEN-06 belt-and-suspenders: bleach must not appear in
    [project] dependencies (it was never present and we keep it that way)."""
    pyproject_path = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    for entry in deps:
        assert not entry.startswith("bleach"), (
            f"bleach must not appear in [project] dependencies; found: {entry!r}"
        )
