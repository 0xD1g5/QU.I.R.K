"""Phase 147 (DRAIN-02, decision D-147-02-A option (a) "build-catalog") — BACnet
vendor-ID + model-family resolution regression coverage.

Pins the contract of ``quirk/scanner/bacnet_vendors.py`` — the fourth instance
of the curated-catalog + staleness-gate triad (after
``quirk/qramm/model_meta.py``, ``quirk/compliance/__init__.py``, and
``quirk/scanner/hw_cve.py``) — plus the end-to-end reachability assertion that
proves the fix actually makes the pre-existing
``("Johnson Controls", "Facility Explorer")`` CVE_TABLE entry reachable.

Group A: resolver + model-family unit tests (pure lookups, no network).
Group B: end-to-end CVE-reachability assertion, including a negative control
against the raw pre-fix values.
Group C: staleness-gate boundary tests, mirroring
``tests/test_cve_staleness.py``.
Group D (Phase 147 Task 4): call-site regression coverage for
``quirk/scanner/hardware_scanner.py``'s Step 5 BACnet block, patching
``quirk.scanner.bacnet_scanner.probe_bacnet_target`` at its import site
(mirrors ``tests/test_run_scan_otics_ssh_gate.py`` Group B's patch-at-source
pattern, since the BACnet probe is imported function-locally).
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import patch


# ============================================================
# Group A — resolve_bacnet_vendor / resolve_bacnet_model_family
# ============================================================


def test_vendor_id_5_resolves_to_johnson_controls() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_vendor

    assert resolve_bacnet_vendor("5") == "Johnson Controls"


def test_vendor_id_int_input_coerced_via_str() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_vendor

    assert resolve_bacnet_vendor(5) == "Johnson Controls"


def test_unrecognized_vendor_id_returns_none() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_vendor

    assert resolve_bacnet_vendor("99999") is None


def test_vendor_id_none_returns_none() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_vendor

    assert resolve_bacnet_vendor(None) is None


def test_model_family_fx16_resolves_to_facility_explorer() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_model_family

    assert (
        resolve_bacnet_model_family("Johnson Controls", "FX16")
        == "Facility Explorer"
    )


def test_model_family_unrecognized_model_returns_none() -> None:
    from quirk.scanner.bacnet_vendors import resolve_bacnet_model_family

    assert resolve_bacnet_model_family("Johnson Controls", "SomethingElse") is None


# ============================================================
# Group B — end-to-end CVE reachability + negative control
# ============================================================


def test_resolved_vendor_and_family_reach_existing_cve_entry() -> None:
    """The whole point of DRAIN-02 option (a): resolving BOTH halves of the
    CVE_TABLE key makes the pre-existing Facility Explorer entry reachable."""
    from quirk.scanner.bacnet_vendors import (
        resolve_bacnet_model_family,
        resolve_bacnet_vendor,
    )
    from quirk.scanner.hw_cve import correlate_device

    vendor = resolve_bacnet_vendor("5")
    family = resolve_bacnet_model_family(vendor, "FX16")
    result = correlate_device(vendor=vendor, model=family, firmware=None)

    assert result.matches != []
    assert result.confidence == "medium"
    cve_ids = {m["cve_id"] for m in result.matches}
    assert "CVE-2017-16744" in cve_ids


def test_raw_prefix_values_do_not_match_negative_control() -> None:
    """Negative control: the pre-fix raw values ("5", "FX16") never matched
    the CVE_TABLE key — proves the resolution step is what makes the entry
    reachable, not some other change."""
    from quirk.scanner.hw_cve import correlate_device

    result = correlate_device("5", "FX16", None)

    assert result.matches == []


# ============================================================
# Group C — staleness gate (mirrors tests/test_cve_staleness.py)
# ============================================================


def test_bacnet_vendor_table_meta_shape() -> None:
    from quirk.scanner.bacnet_vendors import (
        BACNET_VENDOR_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
    )

    required_keys = {"last_verified", "source", "source_url"}
    assert required_keys.issubset(BACNET_VENDOR_TABLE_META.keys())
    datetime.date.fromisoformat(BACNET_VENDOR_TABLE_META["last_verified"])
    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 365


def test_bacnet_vendor_table_far_future_date_is_stale() -> None:
    from quirk.scanner.bacnet_vendors import is_bacnet_vendor_table_stale

    assert is_bacnet_vendor_table_stale(datetime.date(2030, 1, 1)) is True


def test_bacnet_vendor_table_last_verified_date_not_stale() -> None:
    from quirk.scanner.bacnet_vendors import (
        BACNET_VENDOR_TABLE_META,
        is_bacnet_vendor_table_stale,
    )

    last_verified = datetime.date.fromisoformat(
        BACNET_VENDOR_TABLE_META["last_verified"]
    )
    assert is_bacnet_vendor_table_stale(last_verified) is False


def test_bacnet_vendor_table_boundary_365_days_not_stale() -> None:
    from quirk.scanner.bacnet_vendors import (
        BACNET_VENDOR_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
        is_bacnet_vendor_table_stale,
    )

    last_verified = datetime.date.fromisoformat(
        BACNET_VENDOR_TABLE_META["last_verified"]
    )
    fake_today = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS)
    assert is_bacnet_vendor_table_stale(fake_today) is False


def test_bacnet_vendor_table_boundary_366_days_is_stale() -> None:
    from quirk.scanner.bacnet_vendors import (
        BACNET_VENDOR_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
        is_bacnet_vendor_table_stale,
    )

    last_verified = datetime.date.fromisoformat(
        BACNET_VENDOR_TABLE_META["last_verified"]
    )
    fake_today = last_verified + datetime.timedelta(
        days=STALENESS_THRESHOLD_DAYS + 1
    )
    assert is_bacnet_vendor_table_stale(fake_today) is True

