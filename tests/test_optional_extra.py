"""Phase 45 / Plan 02: unit tests for the centralized optional-extra registry + probe.

Tests lock in the registry shape (which extras are covered, motion+redis omitted),
the install-hint contract (every advisory contains the literal `pip install
quirk[<extra>]` invocation), and probe semantics (config-disabled = silent;
extra-available = silent; one advisory per skipped scanner).
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Test 1 — registry covers identity/db/cloud/dashboard; motion + redis omitted
# ---------------------------------------------------------------------------
def test_registry_omits_motion_and_redis():
    from quirk.util.optional_extra import REGISTRY

    extras = {entry.extra for entry in REGISTRY}
    assert "identity" in extras
    assert "db" in extras
    assert "cloud" in extras
    assert "dashboard" in extras
    # Q1: motion intentionally omitted (Phase 41 inline calls remain authoritative).
    assert "motion" not in extras
    # Q3: redis covered transitively; no standalone entry.
    assert "redis" not in extras


# ---------------------------------------------------------------------------
# Test 2 — every install_hint contains the literal `pip install quirk[<extra>]`
# ---------------------------------------------------------------------------
def test_all_hints_contain_pip_install_literal():
    from quirk.util.optional_extra import REGISTRY

    for entry in REGISTRY:
        literal = f"pip install quirk[{entry.extra}]"
        assert literal in entry.install_hint, (
            f"entry {entry.extra!r} hint missing literal {literal!r}: "
            f"{entry.install_hint!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — is_extra_available uses find_spec (no actual import)
# ---------------------------------------------------------------------------
def test_is_extra_available_uses_find_spec():
    from quirk.util import optional_extra

    # All None → identity unavailable.
    with patch.object(optional_extra, "find_spec", return_value=None):
        assert optional_extra.is_extra_available("identity") is False

    # Non-None spec for every probed module → db available.
    fake_spec = object()
    with patch.object(optional_extra, "find_spec", return_value=fake_spec):
        assert optional_extra.is_extra_available("db") is True


# ---------------------------------------------------------------------------
# Test 4 — probe emits exactly one advisory per missing extra whose flag is on
# ---------------------------------------------------------------------------
def _make_cfg(**enable_flags):
    """Build a duck-typed cfg with cfg.connectors.enable_<flag> attributes."""
    connectors = SimpleNamespace(**enable_flags)
    return SimpleNamespace(connectors=connectors)


def test_probe_emits_one_advisory_per_missing_extra():
    from quirk.util import optional_extra

    cfg = _make_cfg(
        enable_kerberos=True,
        enable_db=True,
        enable_gcp=False,
        enable_k8s=False,
        enable_vault=False,
    )
    error_endpoints = []

    # Every module unavailable.
    with patch.object(optional_extra, "find_spec", return_value=None):
        optional_extra.probe_missing_extras(cfg, error_endpoints)

    # identity + db enabled-and-missing ⇒ 2 advisories.
    # dashboard has enabled_attrs=() (always probe) ⇒ +1 advisory = 3 total.
    advisories_by_label = {ep.host: ep for ep in error_endpoints}
    assert "kerberos_scanner" in advisories_by_label
    assert "db_connector" in advisories_by_label
    # cloud must NOT advise (all gating flags False).
    assert "cloud_connectors" not in advisories_by_label

    for ep in error_endpoints:
        assert ep.protocol == "ADVISORY"
        assert ep.scan_error_category == "missing_extra"

    # Hint literals.
    assert "pip install quirk[identity]" in advisories_by_label["kerberos_scanner"].scan_error
    assert "pip install quirk[db]" in advisories_by_label["db_connector"].scan_error


# ---------------------------------------------------------------------------
# Test 5 — config-disabled scanners stay silent (D-08)
# ---------------------------------------------------------------------------
def test_probe_silent_when_scanner_disabled():
    from quirk.util import optional_extra

    cfg = _make_cfg(
        enable_kerberos=False,
        enable_db=False,
        enable_gcp=False,
        enable_k8s=False,
        enable_vault=False,
    )
    error_endpoints = []

    with patch.object(optional_extra, "find_spec", return_value=None):
        optional_extra.probe_missing_extras(cfg, error_endpoints)

    # Only the dashboard entry (enabled_attrs=()) probes unconditionally.
    labels = [ep.host for ep in error_endpoints]
    assert "kerberos_scanner" not in labels
    assert "db_connector" not in labels
    assert "cloud_connectors" not in labels


# ---------------------------------------------------------------------------
# Test 6 — when extra is available, no advisory
# ---------------------------------------------------------------------------
def test_probe_silent_when_extra_available():
    from quirk.util import optional_extra

    cfg = _make_cfg(
        enable_kerberos=False,
        enable_db=True,
        enable_gcp=False,
        enable_k8s=False,
        enable_vault=False,
    )
    error_endpoints = []

    fake_spec = object()
    with patch.object(optional_extra, "find_spec", return_value=fake_spec):
        optional_extra.probe_missing_extras(cfg, error_endpoints)

    # All modules importable ⇒ zero advisories (incl. dashboard).
    assert len(error_endpoints) == 0


# ---------------------------------------------------------------------------
# Test 7 — INSTALL-01: probe never raises ImportError when extras absent
# ---------------------------------------------------------------------------
def test_no_importerror_when_extras_missing():
    from quirk.util import optional_extra

    cfg = _make_cfg(
        enable_kerberos=True,
        enable_db=True,
        enable_gcp=True,
        enable_k8s=True,
        enable_vault=True,
    )
    error_endpoints = []

    with patch.object(optional_extra, "find_spec", return_value=None):
        # Must not raise.
        optional_extra.probe_missing_extras(cfg, error_endpoints)


# ---------------------------------------------------------------------------
# Test 8 — run_scan.main wires probe exactly once + Phase 41 inline calls intact
# ---------------------------------------------------------------------------
def test_probe_invoked_in_run_scan_main():
    """run_scan.main() invokes probe_missing_extras exactly once after
    error_endpoints init. Asserts the call site exists by reading the source."""
    import run_scan

    src = inspect.getsource(run_scan)
    # Probe import must be present.
    assert "from quirk.util.optional_extra import probe_missing_extras" in src
    # Call must appear exactly once (not double-wired).
    assert src.count("probe_missing_extras(cfg, error_endpoints)") == 1
    # Existing Phase 41 inline advisories MUST still be present (D-11).
    assert '_emit_missing_extra_advisory("email_scanner", "motion"' in src
    assert '_emit_missing_extra_advisory("broker_scanner", "motion"' in src
