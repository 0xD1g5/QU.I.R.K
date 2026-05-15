"""Tests for quirk.engine.cache.

Covers:
- BLOCK-05 / Phase 69 / D-10: load_cache TTL semantics.
- Phase 72 / D-18 / WR-15: _read_json malformed-JSON / unicode safety.
- Phase 72 / D-19 / WR-16: scope_hash includes connector enable flags.
- Phase 72 / D-06 / WR-21: profiles.py EOF marker integrity.
"""
from __future__ import annotations

import logging
import os
import py_compile
import types

import pytest

from quirk.config import ConnectorsCfg
from quirk.engine import cache as cache_mod
from quirk.engine.cache import _read_json, load_cache, save_cache, scope_hash


def _make_cfg(connectors: ConnectorsCfg) -> types.SimpleNamespace:
    """Minimal stand-in for AppConfig — scope_hash only reads cfg.targets,
    cfg.scan, cfg.connectors. Avoids dragging in the full AppConfig surface
    so these tests stay focused on the cache-scope contract."""
    targets = types.SimpleNamespace(
        fqdns=[], cidrs=[], include_ips=[], exclude_ips=[]
    )
    scan = types.SimpleNamespace(ports_tls=[443], include_sni=True)
    return types.SimpleNamespace(targets=targets, scan=scan, connectors=connectors)


def test_ttl_zero_returns_none_on_fresh_file(tmp_path):
    """ttl_hours=0 means cache disabled — never return cached object."""
    save_cache(str(tmp_path), "k", {"foo": "bar"})
    assert load_cache(str(tmp_path), "k", ttl_hours=0) is None


def test_ttl_negative_returns_none_on_fresh_file(tmp_path):
    """Negative ttl_hours is also treated as cache disabled."""
    save_cache(str(tmp_path), "k", {"foo": "bar"})
    assert load_cache(str(tmp_path), "k", ttl_hours=-1) is None


def test_ttl_positive_returns_obj_when_fresh(tmp_path):
    """ttl_hours>0 returns the cached object when age <= window."""
    save_cache(str(tmp_path), "k", {"foo": "bar"})
    obj = load_cache(str(tmp_path), "k", ttl_hours=1)
    assert obj is not None
    assert obj.get("foo") == "bar"
    assert "_cached_at" in obj


def test_ttl_positive_returns_none_when_stale(tmp_path, monkeypatch):
    """ttl_hours>0 returns None when cache age exceeds window."""
    save_cache(str(tmp_path), "k", {"foo": "bar"})
    # Advance "now" by 2 hours; ttl=1 hour → stale.
    real_now = cache_mod._now()
    monkeypatch.setattr(
        "quirk.engine.cache._now", lambda: real_now + 3600 * 2
    )
    assert load_cache(str(tmp_path), "k", ttl_hours=1) is None


# ---------------------------------------------------------------------------
# Phase 72 / D-18 / WR-15: _read_json malformed-JSON safety
# ---------------------------------------------------------------------------


def test_read_json_returns_none_on_malformed_json(tmp_path, caplog):
    """Corrupt JSON returns None (no exception); WARNING logged.

    File MUST remain on disk for forensics (D-18).
    """
    path = tmp_path / "corrupt.json"
    path.write_text("{not valid json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="quirk.engine.cache"):
        result = _read_json(str(path))
    assert result is None
    assert "corrupt" in caplog.text.lower()
    # Forensics: file must still exist on disk.
    assert path.exists()


def test_read_json_returns_none_on_unicode_error(tmp_path, caplog):
    """Invalid UTF-8 returns None (no exception); WARNING logged."""
    path = tmp_path / "bad-utf8.json"
    path.write_bytes(b"\xff\xfe invalid utf-8 bytes")
    with caplog.at_level(logging.WARNING, logger="quirk.engine.cache"):
        result = _read_json(str(path))
    assert result is None
    assert path.exists()


def test_load_cache_skips_corrupt_file(tmp_path):
    """load_cache on a corrupt cache file returns None (cache miss), not raise."""
    cdir = cache_mod.cache_dir(str(tmp_path))
    os.makedirs(cdir, exist_ok=True)
    corrupt_path = os.path.join(cdir, "bad.json")
    with open(corrupt_path, "w", encoding="utf-8") as f:
        f.write("{not valid")
    # ttl > 0 so the TTL gate doesn't short-circuit; we want to exercise the
    # corrupt-file path specifically.
    assert load_cache(str(tmp_path), "bad", ttl_hours=1) is None


# ---------------------------------------------------------------------------
# Phase 72 / D-19 / WR-16: scope_hash includes connector enable flags
# ---------------------------------------------------------------------------


def test_scope_hash_changes_when_enable_email_flips():
    """Toggling cfg.connectors.enable_email MUST invalidate the cache."""
    cfg_a = _make_cfg(ConnectorsCfg(enable_email=False))
    cfg_b = _make_cfg(ConnectorsCfg(enable_email=True))
    assert scope_hash(cfg_a, "fast") != scope_hash(cfg_b, "fast")


def test_scope_hash_changes_when_enable_broker_flips():
    """Toggling cfg.connectors.enable_broker MUST invalidate the cache."""
    cfg_a = _make_cfg(ConnectorsCfg(enable_broker=False))
    cfg_b = _make_cfg(ConnectorsCfg(enable_broker=True))
    assert scope_hash(cfg_a, "fast") != scope_hash(cfg_b, "fast")


def test_scope_hash_stable_for_identical_cfg():
    """Sanity: identical cfgs produce identical hashes (deterministic)."""
    cfg_a = _make_cfg(ConnectorsCfg(enable_email=True, enable_aws=True))
    cfg_b = _make_cfg(ConnectorsCfg(enable_email=True, enable_aws=True))
    assert scope_hash(cfg_a, "fast") == scope_hash(cfg_b, "fast")


def test_scope_hash_handles_user_set_fields_sidecar():
    """D-19: scope_hash MUST not raise TypeError when the D-02 sidecar
    (`_user_set_fields: frozenset`) is present on cfg.connectors.

    Simulates PLAN-05 D-02 having landed by injecting the sidecar attribute
    directly. The defensive pop in scope_hash removes it before json.dumps.
    """
    connectors = ConnectorsCfg(enable_email=True)
    # Inject the sidecar — PLAN 05 will declare this as a dataclass field
    # in quirk.config.ConnectorsCfg (default_factory=frozenset, repr=False,
    # compare=False); we set it directly here for the sidecar-pop contract.
    connectors._user_set_fields = frozenset({"enable_email"})
    cfg = _make_cfg(connectors)
    # MUST NOT raise "Object of type frozenset is not JSON serializable".
    h = scope_hash(cfg, "fast")
    assert isinstance(h, str) and len(h) == 16


def test_scope_hash_sidecar_does_not_affect_hash():
    """The sidecar is popped before hashing, so its presence/contents MUST
    NOT change the resulting hash (D-19 implementation detail)."""
    connectors_plain = ConnectorsCfg(enable_email=True)
    connectors_with_sidecar = ConnectorsCfg(enable_email=True)
    connectors_with_sidecar._user_set_fields = frozenset({"enable_email"})
    h_plain = scope_hash(_make_cfg(connectors_plain), "fast")
    h_sidecar = scope_hash(_make_cfg(connectors_with_sidecar), "fast")
    assert h_plain == h_sidecar


# ---------------------------------------------------------------------------
# Phase 72 / D-06 / WR-21: profiles.py EOF marker integrity
# ---------------------------------------------------------------------------


def test_profiles_py_has_eof_marker():
    """The final non-empty line of profiles.py MUST be the literal `# eof`."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "quirk", "engine", "profiles.py",
    )
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    # Strip trailing empty lines, then assert the last non-empty line.
    while lines and not lines[-1].strip():
        lines.pop()
    assert lines, "profiles.py is empty"
    assert lines[-1] == "# eof", (
        f"profiles.py final non-empty line must be '# eof', got: {lines[-1]!r}"
    )


def test_profiles_py_compiles():
    """profiles.py MUST py_compile cleanly (D-06 step 1)."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "quirk", "engine", "profiles.py",
    )
    # Raises PyCompileError on failure.
    py_compile.compile(path, doraise=True)
