"""Phase 81 CMVP-03 — refresh CLI tests.

Mocks ``quirk.compliance.cmvp.httpx`` with frozen NIST CSRC HTML fixtures and
verifies:
- Happy-path mocked HTML → cache file written with today's date and N modules
- ``httpx.ConnectError`` → ``CMVPRefreshNetworkError``; CLI exits 1 with
  ``CMVP-REFRESH-NETWORK`` in stderr
- HTML missing ``#searchResultsTable`` → ``CMVPRefreshParseError``; CLI exits 1
  with ``CMVP-REFRESH-PARSE`` in stderr
- ``dry_run=True`` writes no file and returns a diff dict
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Skip the entire suite gracefully when bs4 isn't installed — refresh CLI
# tests are only meaningful in the full dev environment.
pytest.importorskip("bs4")
pytest.importorskip("httpx")


# ---------------------------------------------------------------------------
# Frozen NIST HTML fixtures (anchored on the selectors verified in RESEARCH
# §NIST CMVP Page Structure: table#searchResultsTable, #cert-number-link-N,
# table#fips-algo-table).
# ---------------------------------------------------------------------------

SEARCH_PAGE_HTML = """
<html><body>
<table id="searchResultsTable">
  <tbody>
    <tr>
      <td><a id="cert-number-link-1" href="/certificate/4985">4985</a></td>
      <td>The OpenSSL Project</td>
      <td>OpenSSL FIPS Provider</td>
      <td>Software</td>
    </tr>
  </tbody>
</table>
</body></html>
"""

CERT_DETAIL_HTML = """
<html><body>
<div class="row padrow">
  <div class="col-md-3">Module Name</div>
  <div class="col-md-9" id="module-name">OpenSSL FIPS Provider</div>
</div>
<div class="row padrow">
  <div class="col-md-3">Standard</div>
  <div class="col-md-9" id="module-standard">FIPS 140-3</div>
</div>
<div class="row padrow">
  <div class="col-md-3">Version</div>
  <div class="col-md-9">3.1.2</div>
</div>
<div class="row padrow">
  <div class="col-md-3">Overall Level</div>
  <div class="col-md-9">1</div>
</div>
<table id="fips-algo-table">
  <tr><td class="text-nowrap">AES</td><td>certs</td></tr>
  <tr><td class="text-nowrap">SHS</td><td>certs</td></tr>
  <tr><td class="text-nowrap">HMAC</td><td>certs</td></tr>
</table>
</body></html>
"""

PARSE_FAILURE_HTML = "<html><body><h1>NIST search unavailable</h1></body></html>"


def _make_response(text: str, status: int = 200):
    """Return a MagicMock that mimics httpx.Response shape used by cmvp.py."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def _stub_client(responses):
    """Build a MagicMock httpx.Client whose .get() returns the next response.

    ``responses`` is a list of (text, status) tuples consumed in order.
    """
    client = MagicMock()
    client.__enter__ = lambda self: self
    client.__exit__ = lambda self, *a: None

    iterator = iter(responses)

    def _get(*args, **kwargs):
        text, status = next(iterator)
        return _make_response(text, status)

    client.get = MagicMock(side_effect=_get)
    return client


# ---------------------------------------------------------------------------
# Happy path: refresh writes the cache atomically with today's date.
# ---------------------------------------------------------------------------

def test_refresh_happy_path(tmp_path, monkeypatch) -> None:
    """Mocked NIST responses → refresh_cache(dry_run=False) writes a cache
    file with today's date and at least one module."""
    import quirk.compliance.cmvp as cmvp_mod

    cache_path = tmp_path / "cmvp_cache.json"
    monkeypatch.setattr(cmvp_mod, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(cmvp_mod, "_CACHE", None)

    # Curated CSV → single anchor cert (4985 — RESEARCH OpenSSL FIPS Provider 3.1.2).
    monkeypatch.setattr(
        cmvp_mod,
        "_read_curated_cert_numbers",
        lambda: ["4985"],
    )

    fake_httpx = MagicMock()
    fake_httpx.Timeout = lambda *a, **kw: None
    fake_httpx.HTTPError = Exception  # any non-CMVP exception will be wrapped
    fake_httpx.Client = MagicMock(
        return_value=_stub_client([
            (SEARCH_PAGE_HTML, 200),  # index page
            (CERT_DETAIL_HTML, 200),  # cert 4985 detail
        ])
    )
    monkeypatch.setattr(cmvp_mod, "time", SimpleNamespace(sleep=lambda *_: None))

    with patch.dict("sys.modules", {"httpx": fake_httpx}):
        result = cmvp_mod.refresh_cache(dry_run=False)

    assert cache_path.exists(), "refresh did not write cmvp_cache.json"
    written = json.loads(cache_path.read_text())
    assert written["modules"], "refresh wrote a cache with no modules"
    import datetime as _dt

    today = _dt.date.today().isoformat()
    assert written["last_verified"] == today
    assert result["last_verified"] == today
    assert any(
        "AES" in m.get("algorithms", []) for m in written["modules"]
    ), "AES algorithm not preserved through refresh"


# ---------------------------------------------------------------------------
# Network failure: ConnectError → CMVPRefreshNetworkError; CLI exits 1.
# ---------------------------------------------------------------------------

def test_refresh_network_failure_raises(monkeypatch, tmp_path) -> None:
    """Mocked Client raising HTTPError → CMVPRefreshNetworkError."""
    import quirk.compliance.cmvp as cmvp_mod
    from quirk.compliance.cmvp import CMVPRefreshNetworkError

    monkeypatch.setattr(cmvp_mod, "_CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(cmvp_mod, "_CACHE", None)
    monkeypatch.setattr(cmvp_mod, "_read_curated_cert_numbers", lambda: ["4985"])

    class _BoomHTTPError(Exception):
        pass

    fake_httpx = MagicMock()
    fake_httpx.Timeout = lambda *a, **kw: None
    fake_httpx.HTTPError = _BoomHTTPError

    failing_client = MagicMock()
    failing_client.__enter__ = lambda self: self
    failing_client.__exit__ = lambda self, *a: None
    failing_client.get = MagicMock(
        side_effect=_BoomHTTPError("connection refused")
    )
    fake_httpx.Client = MagicMock(return_value=failing_client)

    with patch.dict("sys.modules", {"httpx": fake_httpx}):
        with pytest.raises(CMVPRefreshNetworkError):
            cmvp_mod.refresh_cache(dry_run=False)


def test_cli_refresh_emits_network_error_code(monkeypatch, capsys) -> None:
    """``run_cmvp(refresh)`` with a CMVPRefreshNetworkError exits 1 and emits
    ``CMVP-REFRESH-NETWORK`` in stderr."""
    from quirk.compliance.cmvp import CMVPRefreshNetworkError
    from quirk.cli import cmvp_cmd

    def _boom(**_kw):
        raise CMVPRefreshNetworkError("unreachable")

    monkeypatch.setattr(
        "quirk.compliance.cmvp.refresh_cache", _boom
    )

    args = SimpleNamespace(cmvp_action="refresh", dry_run=False)
    with pytest.raises(SystemExit) as exc:
        cmvp_cmd.run_cmvp(args)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "CMVP-REFRESH-NETWORK" in captured.err


# ---------------------------------------------------------------------------
# Parse failure: searchResultsTable absent → CMVPRefreshParseError; CLI exits 1.
# ---------------------------------------------------------------------------

def test_refresh_parse_failure_raises(monkeypatch, tmp_path) -> None:
    """Mocked Client returning HTML with NO searchResultsTable →
    CMVPRefreshParseError."""
    import quirk.compliance.cmvp as cmvp_mod
    from quirk.compliance.cmvp import CMVPRefreshParseError

    monkeypatch.setattr(cmvp_mod, "_CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(cmvp_mod, "_CACHE", None)
    monkeypatch.setattr(cmvp_mod, "_read_curated_cert_numbers", lambda: ["4985"])

    fake_httpx = MagicMock()
    fake_httpx.Timeout = lambda *a, **kw: None
    fake_httpx.HTTPError = Exception
    fake_httpx.Client = MagicMock(
        return_value=_stub_client([(PARSE_FAILURE_HTML, 200)])
    )

    with patch.dict("sys.modules", {"httpx": fake_httpx}):
        with pytest.raises(CMVPRefreshParseError):
            cmvp_mod.refresh_cache(dry_run=False)


def test_cli_refresh_emits_parse_error_code(monkeypatch, capsys) -> None:
    """``run_cmvp(refresh)`` with CMVPRefreshParseError exits 1 and emits
    ``CMVP-REFRESH-PARSE`` in stderr."""
    from quirk.compliance.cmvp import CMVPRefreshParseError
    from quirk.cli import cmvp_cmd

    def _boom(**_kw):
        raise CMVPRefreshParseError("table missing")

    monkeypatch.setattr(
        "quirk.compliance.cmvp.refresh_cache", _boom
    )

    args = SimpleNamespace(cmvp_action="refresh", dry_run=False)
    with pytest.raises(SystemExit) as exc:
        cmvp_cmd.run_cmvp(args)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "CMVP-REFRESH-PARSE" in captured.err


# ---------------------------------------------------------------------------
# Dry-run: writes nothing, returns a diff dict.
# ---------------------------------------------------------------------------

def test_refresh_dry_run_writes_nothing(tmp_path, monkeypatch) -> None:
    """``refresh_cache(dry_run=True)`` returns a diff and does not touch the
    cache file. Diff dict has expected keys: added / removed / changed."""
    import quirk.compliance.cmvp as cmvp_mod

    cache_path = tmp_path / "cmvp_cache.json"
    # Seed an existing cache with a known module so the diff has something to
    # compare against.
    initial = {
        "schema_version": "1.0",
        "last_verified": "2026-01-01",
        "source_url": cmvp_mod.CMVP_SEARCH_URL,
        "modules": [
            {
                "certificate_number": "9999",
                "vendor": "Old Vendor",
                "name": "Old Module",
                "module_version": "",
                "fips_level": "140-3",
                "overall_level": "1",
                "algorithms": ["AES"],
            }
        ],
    }
    cache_path.write_text(json.dumps(initial))
    initial_bytes = cache_path.read_bytes()

    monkeypatch.setattr(cmvp_mod, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(cmvp_mod, "_CACHE", None)
    monkeypatch.setattr(cmvp_mod, "_read_curated_cert_numbers", lambda: ["4985"])
    monkeypatch.setattr(cmvp_mod, "time", SimpleNamespace(sleep=lambda *_: None))

    fake_httpx = MagicMock()
    fake_httpx.Timeout = lambda *a, **kw: None
    fake_httpx.HTTPError = Exception
    fake_httpx.Client = MagicMock(
        return_value=_stub_client([
            (SEARCH_PAGE_HTML, 200),
            (CERT_DETAIL_HTML, 200),
        ])
    )

    with patch.dict("sys.modules", {"httpx": fake_httpx}):
        result = cmvp_mod.refresh_cache(dry_run=True)

    # File unchanged
    assert cache_path.read_bytes() == initial_bytes
    # Result is a diff dict
    assert isinstance(result, dict)
    for key in ("added", "removed", "changed"):
        assert key in result, f"diff missing key {key!r}: {result}"
    # 4985 is new; 9999 is removed.
    assert "4985" in result["added"]
    assert "9999" in result["removed"]
