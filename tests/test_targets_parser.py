"""Tests for quirk/util/targets.py — multi-target parser (Phase 47 / MULTI-01..05).

Covers:
  - CSV split (MULTI-01)
  - @file token loading with comment/blank stripping (MULTI-02)
  - CIDR routing (MULTI-04)
  - Malformed CIDR → ValueError with token in message (MULTI-05 / D-05)
  - Missing file → FileNotFoundError with path in message (MULTI-05 / D-05)
  - Mixed CSV combining all token types
  - Nested @file from inside a file treated as bare host (D-02)
  - Whitespace token silently skipped

Phase 58 / HARDEN-API-06 additions (CR-09):
  - TargetFileError reason codes (exact string values)
  - @file outside CWD raises TargetFileError(reason=path_traversal)
  - @file under /etc /proc /sys /dev raises TargetFileError(reason=path_not_allowed_prefix)
  - @file > 1 MB raises TargetFileError(reason=target_file_too_large)
  - @file > 10000 lines raises TargetFileError(reason=target_file_too_many_lines)
"""
import os
import pytest

from quirk.util.targets import (
    parse_target_tokens,
    load_targets_file,
    TargetFileError,
    RC_PATH_TRAVERSAL,
    RC_PATH_NOT_ALLOWED_PREFIX,
    RC_TARGET_FILE_TOO_LARGE,
    RC_TARGET_FILE_TOO_MANY_LINES,
)


# ---------------------------------------------------------------------------
# load_targets_file helpers
# ---------------------------------------------------------------------------

def test_at_file_strips_comments_and_blanks(tmp_path):
    """load_targets_file strips blank lines and '#'-prefixed lines."""
    f = tmp_path / "hosts.txt"
    f.write_text("#header\n  \nhost1\nhost2\n")
    result = load_targets_file(str(f))
    assert result == "host1,host2"


def test_missing_file_raises_with_path():
    """load_targets_file raises FileNotFoundError whose message contains the path (D-05/MULTI-05)."""
    missing_path = "/no/such/file.txt"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_targets_file(missing_path)
    assert missing_path in str(exc_info.value)


# ---------------------------------------------------------------------------
# parse_target_tokens
# ---------------------------------------------------------------------------

def test_csv_split():
    """CSV of bare hosts/IPs routes entirely to fqdns (MULTI-01)."""
    fqdns, cidrs = parse_target_tokens("a.com,b.com,1.2.3.4")
    assert fqdns == ["a.com", "b.com", "1.2.3.4"]
    assert cidrs == []


def test_cidr_routes_to_cidrs():
    """A CIDR token is validated and placed in cidrs list (MULTI-04)."""
    fqdns, cidrs = parse_target_tokens("10.0.0.0/24")
    assert fqdns == []
    assert cidrs == ["10.0.0.0/24"]


def test_mixed_csv_with_cidr_and_file_token(tmp_path, monkeypatch):
    """Mixed CSV: host + CIDR + @file all routed correctly (MULTI-01/02/04)."""
    monkeypatch.chdir(tmp_path)  # Phase 58: @file guard requires file within CWD
    extras = tmp_path / "extras.txt"
    extras.write_text("x.com\n#comment\n\ny.com\n")

    fqdns, cidrs = parse_target_tokens(f"a.com,10.0.0.0/24,@{extras}")
    assert "a.com" in fqdns
    assert "x.com" in fqdns
    assert "y.com" in fqdns
    assert cidrs == ["10.0.0.0/24"]


def test_at_file_no_nested_at_prefix(tmp_path, monkeypatch):
    """D-02: a line starting with '@' inside a targets file is treated as a bare host, not re-routed."""
    monkeypatch.chdir(tmp_path)  # Phase 58: @file guard requires file within CWD
    inner = tmp_path / "nested.txt"
    inner.write_text("real-host.com\n")

    targets_file = tmp_path / "hosts.txt"
    targets_file.write_text(f"@{inner}\nactual-host.com\n")

    # parse_target_tokens of the file's contents (via @-prefix at top level)
    fqdns, cidrs = parse_target_tokens(f"@{targets_file}")

    # "@<inner>" appearing inside the file is a bare host token (D-02: no nested @file)
    # actual-host.com should be a plain host
    assert "actual-host.com" in fqdns
    # The nested @file is NOT expanded — its contents must not appear in fqdns
    assert "real-host.com" not in fqdns


def test_malformed_cidr_raises_with_token():
    """parse_target_tokens raises ValueError whose message contains the offending token (D-05/MULTI-05)."""
    with pytest.raises(ValueError) as exc_info:
        parse_target_tokens("a.com,10.0.0.0/99")
    assert "10.0.0.0/99" in str(exc_info.value)


def test_missing_file_token_raises_with_path():
    """@-prefixed token pointing at missing file raises FileNotFoundError (D-05/MULTI-05)."""
    # Phase 58: external absolute paths now raise TargetFileError(path_traversal) before
    # file-existence check. Use a relative (within-CWD) path to exercise FileNotFoundError.
    bad_path = "./no_such_quirk_targets_test.txt"
    with pytest.raises(FileNotFoundError) as exc_info:
        parse_target_tokens(f"@{bad_path}")
    assert "no_such_quirk_targets_test" in str(exc_info.value)


def test_whitespace_tokens_skipped():
    """Whitespace-only tokens between commas are silently ignored."""
    fqdns, cidrs = parse_target_tokens("a.com, ,b.com")
    assert fqdns == ["a.com", "b.com"]
    assert cidrs == []


# ---------------------------------------------------------------------------
# Phase 58 / HARDEN-API-06: TargetFileError guard tests (CR-09)
# ---------------------------------------------------------------------------

def test_at_file_reason_codes_are_correct_strings():
    """RC_* constants must equal exact documented string values (D-13/D-14).

    Locks the reason-code strings so serialised error messages and API
    consumers don't silently drift.
    """
    assert RC_PATH_TRAVERSAL == "path_traversal"
    assert RC_PATH_NOT_ALLOWED_PREFIX == "path_not_allowed_prefix"
    assert RC_TARGET_FILE_TOO_LARGE == "target_file_too_large"
    assert RC_TARGET_FILE_TOO_MANY_LINES == "target_file_too_many_lines"


def test_at_file_outside_cwd_raises_path_traversal(tmp_path, monkeypatch):
    """@file that resolves outside CWD raises TargetFileError with reason path_traversal.

    Regression gate for CR-09 / HARDEN-API-06: guard must fire before any
    file open() so it cannot be bypassed by creating the file at the traversal path.
    """
    # Create a real file in a sibling directory (outside CWD subtree)
    sibling = tmp_path.parent / "sibling_quirk_test"
    sibling.mkdir(exist_ok=True)
    evil_file = sibling / "evil.txt"
    evil_file.write_text("10.0.0.1\n")

    # CWD is set to tmp_path; ../sibling_quirk_test/evil.txt escapes CWD
    monkeypatch.chdir(tmp_path)
    relative_escape = f"../sibling_quirk_test/evil.txt"

    with pytest.raises(TargetFileError) as exc_info:
        parse_target_tokens(f"@{relative_escape}")

    assert exc_info.value.reason == RC_PATH_TRAVERSAL
    assert "sibling_quirk_test" in exc_info.value.path or relative_escape in exc_info.value.path


def test_at_file_absolute_outside_cwd_raises_path_traversal(tmp_path, monkeypatch):
    """Absolute @file path that is outside CWD raises TargetFileError(path_traversal).

    Covers the direct absolute-path injection vector (e.g., @/tmp/attacker.txt).
    """
    monkeypatch.chdir(tmp_path)

    # /tmp or system temp directory is outside CWD (tmp_path is a unique subdir)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tf:
        tf.write("10.0.0.1\n")
        abs_path = tf.name

    try:
        with pytest.raises(TargetFileError) as exc_info:
            parse_target_tokens(f"@{abs_path}")
        assert exc_info.value.reason == RC_PATH_TRAVERSAL
    finally:
        os.unlink(abs_path)


@pytest.mark.parametrize("blocked_prefix", ["/etc", "/proc", "/sys", "/dev"])
def test_at_file_blocked_prefix_raises_path_not_allowed(blocked_prefix, tmp_path, monkeypatch):
    """@file path that resolves under a blocked system prefix raises path_not_allowed_prefix.

    The four blocked prefixes (/etc /proc /sys /dev) are enumerated to ensure
    all are covered by the _BLOCKED_PREFIXES tuple in targets.py.

    The guard checks CWD-anchor first, then blocked prefix.  To isolate the
    blocked-prefix check, we mock os.path.realpath so that the file's resolved
    path sits inside a faked CWD subtree that happens to start with the blocked
    prefix (simulating a scenario where CWD is itself under the blocked prefix,
    e.g. a misconfigured container that chroots into /etc).  This is
    intentionally a whitebox test — it exercises Check 2 of the guard directly.
    """
    target_path = "guarded_test_target.txt"
    fake_cwd = f"{blocked_prefix}/quirk_test_cwd"
    fake_resolved = f"{blocked_prefix}/quirk_test_cwd/subdir/attacker.txt"

    original_realpath = os.path.realpath

    def patched_realpath(p, **kwargs):
        # os.getcwd() path (absolute) → fake CWD
        cwd = os.getcwd()
        if os.path.abspath(p) == cwd or p == cwd:
            return fake_cwd
        # The target file path → fake resolved inside the fake CWD (passes CWD check)
        if target_path in str(p):
            return fake_resolved
        return original_realpath(p, **kwargs)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os.path, "realpath", patched_realpath)

    with pytest.raises(TargetFileError) as exc_info:
        parse_target_tokens(f"@{target_path}")

    assert exc_info.value.reason == RC_PATH_NOT_ALLOWED_PREFIX
    assert exc_info.value.path == target_path


def test_at_file_too_large_raises(tmp_path, monkeypatch):
    """@file exceeding 1 MB raises TargetFileError with reason target_file_too_large (D-13).

    Creates a 1 MB + 1 byte file in tmp_path so the size-cap guard fires before
    the file contents are ever loaded into memory.
    """
    monkeypatch.chdir(tmp_path)

    large_file = tmp_path / "large.txt"
    # Write slightly over the 1 MB cap (1_048_577 bytes)
    large_file.write_bytes(b"x" * 1_048_577)

    with pytest.raises(TargetFileError) as exc_info:
        parse_target_tokens("@large.txt")

    assert exc_info.value.reason == RC_TARGET_FILE_TOO_LARGE
    assert "large.txt" in exc_info.value.path


def test_at_file_too_many_lines_raises(tmp_path, monkeypatch):
    """@file with more than 10000 lines raises TargetFileError(target_file_too_many_lines) (D-13).

    The guard stream-counts lines to avoid loading the full content into memory.
    A 10001-line file must trigger the cap.
    """
    monkeypatch.chdir(tmp_path)

    many_lines_file = tmp_path / "many_lines.txt"
    # Write 10001 lines; each is a small host token
    many_lines_file.write_text("\n".join([f"host{i}.com" for i in range(10_001)]) + "\n")

    with pytest.raises(TargetFileError) as exc_info:
        parse_target_tokens("@many_lines.txt")

    assert exc_info.value.reason == RC_TARGET_FILE_TOO_MANY_LINES
    assert "many_lines.txt" in exc_info.value.path


def test_target_file_error_is_value_error():
    """TargetFileError must extend ValueError for backward compatibility (D-14)."""
    err = TargetFileError("/some/path", RC_PATH_TRAVERSAL)
    assert isinstance(err, ValueError)
    assert err.path == "/some/path"
    assert err.reason == RC_PATH_TRAVERSAL
    assert "path_traversal" in str(err)


def test_at_file_within_cwd_and_valid_succeeds(tmp_path, monkeypatch):
    """A well-formed @file within CWD and under size/line caps must load normally.

    Sanity check: guard must NOT block legitimate @file usage.
    """
    monkeypatch.chdir(tmp_path)

    good_file = tmp_path / "good.txt"
    good_file.write_text("10.0.0.1\n192.168.1.1\n")

    fqdns, cidrs = parse_target_tokens("@good.txt")

    assert "10.0.0.1" in fqdns
    assert "192.168.1.1" in fqdns
