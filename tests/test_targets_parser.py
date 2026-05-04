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
"""
import os
import pytest

from quirk.util.targets import parse_target_tokens, load_targets_file


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


def test_mixed_csv_with_cidr_and_file_token(tmp_path):
    """Mixed CSV: host + CIDR + @file all routed correctly (MULTI-01/02/04)."""
    extras = tmp_path / "extras.txt"
    extras.write_text("x.com\n#comment\n\ny.com\n")

    fqdns, cidrs = parse_target_tokens(f"a.com,10.0.0.0/24,@{extras}")
    assert "a.com" in fqdns
    assert "x.com" in fqdns
    assert "y.com" in fqdns
    assert cidrs == ["10.0.0.0/24"]


def test_at_file_no_nested_at_prefix(tmp_path):
    """D-02: a line starting with '@' inside a targets file is treated as a bare host, not re-routed."""
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
    bad_path = "/no/such/targets.txt"
    with pytest.raises(FileNotFoundError) as exc_info:
        parse_target_tokens(f"@{bad_path}")
    assert bad_path in str(exc_info.value)


def test_whitespace_tokens_skipped():
    """Whitespace-only tokens between commas are silently ignored."""
    fqdns, cidrs = parse_target_tokens("a.com, ,b.com")
    assert fqdns == ["a.com", "b.com"]
    assert cidrs == []
