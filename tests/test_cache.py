"""Tests for quirk.engine.cache.load_cache TTL semantics (BLOCK-05 / Phase 69).

Contract (per D-10):
- ttl_hours <= 0 means "cache disabled" — load_cache MUST return None,
  even when a fresh cache file exists on disk.
- ttl_hours > 0 means "honor cache within window" — load_cache returns the
  cached object when age <= ttl_hours*3600, else None.
"""
from __future__ import annotations

from quirk.engine import cache as cache_mod
from quirk.engine.cache import load_cache, save_cache


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
