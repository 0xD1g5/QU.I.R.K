"""Phase 193 / Plan 01: run-time-derived D-06 completeness guard for
``quirk/dashboard/api/connector_availability.py``.

The expected `enable_*` flag set is regenerated from
``dataclasses.fields(ConnectorsCfg)`` at TEST-RUN TIME in every test below --
never hand-listed -- per this repo's standing lesson (CLAUDE.md's "GSD
`state.*` Verb Integrity" clause (e): "a written list of known sites is not
a safeguard") and mirroring ``tests/test_config_connector_drift.py``'s own
``_connector_field_names()`` idiom (``dataclasses.fields(ConnectorsCfg)``).
A future `enable_*` field added to `ConnectorsCfg` with no corresponding
`CONNECTOR_AVAILABILITY_MAP` entry fails
`test_every_connector_flag_has_a_disposition` immediately, with zero edits
to this file.
"""
from __future__ import annotations

import dataclasses

from quirk.config import ConnectorsCfg
from quirk.dashboard.api.connector_availability import (
    CONNECTOR_AVAILABILITY_MAP,
    probe_all_connectors,
)
from quirk.util.optional_extra import REGISTRY

_UI_SPEC_CATEGORIES = frozenset(
    {"Identity", "Cloud", "Database", "Email & Broker", "OT/ICS", "Source & API"}
)


def _connector_enable_field_names() -> set[str]:
    """Derive the real `enable_*` field set from `ConnectorsCfg` at call
    time -- the same expression `tests/test_config_connector_drift.py`'s
    `_connector_field_names()` uses, scoped to `enable_*` fields only."""
    return {
        f.name
        for f in dataclasses.fields(ConnectorsCfg)
        if f.name.startswith("enable_")
    }


def test_every_connector_flag_has_a_disposition() -> None:
    """D-06: every real `ConnectorsCfg.enable_*` field must have exactly one
    `CONNECTOR_AVAILABILITY_MAP` entry, and vice versa -- the symmetric
    difference (both missing and extra members) is reported by name."""
    expected = _connector_enable_field_names()
    actual = set(CONNECTOR_AVAILABILITY_MAP)
    missing = expected - actual
    extra = actual - expected
    assert not missing and not extra, (
        f"missing dispositions: {sorted(missing)}; "
        f"unknown/stale map entries: {sorted(extra)}"
    )


def test_no_flag_is_silently_unmapped() -> None:
    """Every map entry must either be `always_available=True` OR declare at
    least one of `extra` / `module_flags` / `binary`. A mapping with all of
    these empty and `always_available=False` is the silent-no-op failure
    mode D-02/D-06 exist to prevent."""
    problems = []
    for flag, source in CONNECTOR_AVAILABILITY_MAP.items():
        if source.always_available:
            continue
        has_real_source = bool(
            source.extra or source.module_flags or getattr(source, "binary", None)
        )
        if not has_real_source:
            problems.append(flag)
    assert not problems, (
        f"flags with no real availability source and always_available=False: "
        f"{problems}"
    )


def test_always_available_dispositions_are_the_two_known_behavior_flags() -> None:
    """Locks the `always_available` bucket to exactly the two pure behavior
    toggles this plan names explicitly -- a future flag cannot be quietly
    parked here to dodge a real probe."""
    always_available_flags = {
        flag
        for flag, source in CONNECTOR_AVAILABILITY_MAP.items()
        if source.always_available
    }
    assert always_available_flags == {
        "enable_authenticated_mode",
        "enable_recurring_otics",
    }, always_available_flags


def test_probe_returns_a_record_for_every_mapped_flag() -> None:
    """`probe_all_connectors()` must cover every mapped flag with no gaps,
    and every unavailable record must carry a non-empty reason."""
    results = probe_all_connectors()
    assert set(results) == set(CONNECTOR_AVAILABILITY_MAP)
    for flag, record in results.items():
        if not record.available:
            assert record.reason, f"{flag}: unavailable record has empty reason"


def test_unavailable_entries_with_an_extra_carry_the_registry_install_hint() -> None:
    """D-02: for every map entry with a non-None `extra`, if the probed
    record is unavailable, its `install_hint` must be exactly the matching
    `optional_extra.REGISTRY` entry's `install_hint` string -- verbatim, not
    paraphrased."""
    results = probe_all_connectors()
    registry_hints = {entry.extra: entry.install_hint for entry in REGISTRY}

    checked_any_unavailable_with_extra = False
    for flag, source in CONNECTOR_AVAILABILITY_MAP.items():
        if source.extra is None:
            continue
        record = results[flag]
        if record.available:
            continue
        checked_any_unavailable_with_extra = True
        assert source.extra in registry_hints, (
            f"{flag}: declares extra={source.extra!r} which has no "
            "optional_extra.REGISTRY entry"
        )
        assert record.install_hint == registry_hints[source.extra], (
            flag,
            record.install_hint,
            registry_hints[source.extra],
        )
    # Convention-blindness guard: this repo's live environment is expected to
    # have at least one extra-gated connector currently unavailable (e.g. no
    # `identity`/`db` extras installed in a bare dev checkout). If that ever
    # stops being true, the assertion body above would pass vacuously --
    # flag it rather than silently reading as "everything is fine".
    assert checked_any_unavailable_with_extra, (
        "no extra-gated connector was found unavailable in this environment -- "
        "the verbatim install_hint assertion above never actually ran; this "
        "test needs a live gap to be meaningful"
    )


def test_categories_are_drawn_from_the_ui_spec_set() -> None:
    """Every `category` value must be one of the frozen six 193-UI-SPEC
    strings -- never a seventh, invented category."""
    bad = {
        flag: source.category
        for flag, source in CONNECTOR_AVAILABILITY_MAP.items()
        if source.category not in _UI_SPEC_CATEGORIES
    }
    assert not bad, bad
