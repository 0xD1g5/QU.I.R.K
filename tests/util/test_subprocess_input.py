"""Tests for quirk/util/subprocess_input.py — subprocess input validators (Phase 57 / CR-02, CR-03).

Covers:
  validate_repo_path:
    - Existing directory → ok=True
    - Shell metacharacters → shell_metachar
    - Path traversal ('..') → path_traversal
    - Non-existent path → nonexistent_path
    - Leading dash → leading_dash
    - Empty string → path_traversal (first check: '..' in "" is False, "" == "" is True)

  validate_image_ref:
    - Legitimate OCI refs → ok=True
    - dir:/ prefix → invalid_image_ref
    - file:// prefix → invalid_image_ref
    - Leading dash → leading_dash
    - Shell metacharacters → shell_metachar
    - Empty string → invalid_image_ref

  Both helpers:
    - Return ValidationResult instance
    - redacted_preview <= 32 chars, no control chars
"""
import pytest

from quirk.util.subprocess_input import (
    validate_repo_path,
    validate_image_ref,
    ValidationResult,
    RC_SHELL_METACHAR,
    RC_PATH_TRAVERSAL,
    RC_NONEXISTENT_PATH,
    RC_INVALID_IMAGE_REF,
    RC_LEADING_DASH,
    RC_PATH_SHAPED_REF,  # Phase 123 SSRF-03 — does not exist yet; import fails until Plan 02
)


# ---------------------------------------------------------------------------
# validate_repo_path — parametrized behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,expected_ok,expected_reason", [
    # Shell metacharacters
    ("/path/with spaces and; rm -rf", False, RC_SHELL_METACHAR),
    ("/tmp/pipe|attack", False, RC_SHELL_METACHAR),
    ("/tmp/amp&attack", False, RC_SHELL_METACHAR),
    ("/tmp/dollar$HOME", False, RC_SHELL_METACHAR),
    ("/tmp/backtick`whoami`", False, RC_SHELL_METACHAR),
    # Path traversal
    ("../../etc/passwd", False, RC_PATH_TRAVERSAL),
    ("../something", False, RC_PATH_TRAVERSAL),
    # Empty string — path_traversal (p == "" check)
    ("", False, RC_PATH_TRAVERSAL),
    # Non-existent path (no metachar, no traversal, not leading dash, just missing)
    ("/nonexistent/xyz123abc987", False, RC_NONEXISTENT_PATH),
    # Leading dash
    ("-config=evil", False, RC_LEADING_DASH),
], ids=[
    "metachar_semicolon_space",
    "metachar_pipe",
    "metachar_amp",
    "metachar_dollar",
    "metachar_backtick",
    "traversal_dotdot_relative",
    "traversal_single_dotdot",
    "empty_string",
    "nonexistent_path",
    "leading_dash",
])
def test_validate_repo_path_rejected(path, expected_ok, expected_reason):
    result = validate_repo_path(path)
    assert result.ok == expected_ok
    assert result.reason == expected_reason
    assert len(result.redacted_preview) <= 32
    for ch in result.redacted_preview:
        assert ord(ch) >= 0x20, f"Control char 0x{ord(ch):02x} in preview"


def test_validate_repo_path_existing_dir(tmp_path):
    """An existing directory with no metacharacters should be accepted."""
    result = validate_repo_path(str(tmp_path))
    assert result.ok is True
    assert result.reason == ""
    assert result.redacted_preview == ""


# ---------------------------------------------------------------------------
# validate_image_ref — parametrized behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ref,expected_ok,expected_reason", [
    # Valid OCI-style refs
    ("registry.example.com/myimage:1.2.3", True, ""),
    ("alpine:latest", True, ""),
    ("ghcr.io/org/repo:sha-abc123", True, ""),
    ("docker.io/library/nginx@sha256:abc123", True, ""),
    # dir:/ prefix
    ("dir:/", False, RC_INVALID_IMAGE_REF),
    # file:// prefix
    ("file:///etc/passwd", False, RC_INVALID_IMAGE_REF),
    # Leading dash
    ("-q --output=evil", False, RC_LEADING_DASH),
    # Shell metacharacters
    ("alpine; rm -rf /", False, RC_SHELL_METACHAR),
    ("alpine`whoami`", False, RC_SHELL_METACHAR),
    # Empty string
    ("", False, RC_INVALID_IMAGE_REF),
    # Phase 123 SSRF-03: path-shaped refs must be rejected (RED until Plan 02)
    ("etc/passwd", False, RC_PATH_SHAPED_REF),
    ("home/user/.ssh/id_rsa", False, RC_PATH_SHAPED_REF),
    ("tmp/evil", False, RC_PATH_SHAPED_REF),
    # Phase 123: valid refs with registry authority still pass
    ("registry.io/img:latest", True, ""),
    ("localhost/img:tag", True, ""),
    ("localhost:5000/img", True, ""),
    ("docker.io/library/nginx", True, ""),
], ids=[
    "valid_registry_tag",
    "valid_alpine",
    "valid_ghcr_sha",
    "valid_digest",
    "dir_prefix",
    "file_prefix",
    "leading_dash",
    "metachar_semicolon",
    "metachar_backtick",
    "empty_string",
    "path_shaped_etc_passwd",
    "path_shaped_home",
    "path_shaped_tmp",
    "valid_registry_io",
    "valid_localhost_img",
    "valid_localhost_port",
    "valid_dockerio_library",
])
def test_validate_image_ref(ref, expected_ok, expected_reason):
    result = validate_image_ref(ref)
    assert result.ok == expected_ok
    assert result.reason == expected_reason
    if not expected_ok:
        assert len(result.redacted_preview) <= 32
        for ch in result.redacted_preview:
            assert ord(ch) >= 0x20, f"Control char 0x{ord(ch):02x} in preview"


# ---------------------------------------------------------------------------
# redacted_preview quality
# ---------------------------------------------------------------------------

def test_redacted_preview_max_length_repo_path():
    """redacted_preview must not exceed 32 chars even for 200-char attack inputs."""
    long_input = "/tmp/../" + "a" * 200
    result = validate_repo_path(long_input)
    assert not result.ok
    assert len(result.redacted_preview) <= 32


def test_redacted_preview_control_char_stripping():
    """Control characters in input are stripped from redacted_preview."""
    ref_with_ctrl = "dir:/\x00\x01\x07evil"
    result = validate_image_ref(ref_with_ctrl)
    assert not result.ok
    for ch in result.redacted_preview:
        assert ord(ch) >= 0x20, f"Control char 0x{ord(ch):02x} in preview"


# ---------------------------------------------------------------------------
# Type assertions
# ---------------------------------------------------------------------------

def test_validate_repo_path_returns_validation_result(tmp_path):
    """validate_repo_path must return a ValidationResult instance."""
    result = validate_repo_path(str(tmp_path))
    assert isinstance(result, ValidationResult)


def test_validate_image_ref_returns_validation_result():
    """validate_image_ref must return a ValidationResult instance."""
    result = validate_image_ref("alpine:latest")
    assert isinstance(result, ValidationResult)
