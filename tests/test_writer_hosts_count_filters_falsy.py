"""Phase 77 D-14 / cbom-intel-reports/IN-08 — hosts_count must filter falsy
host values before set construction so None / "" collapse to nothing rather
than a spurious single empty-string member.
"""
from __future__ import annotations

import pytest


def _get_unique_hosts():
    from quirk.reports import writer
    fn = getattr(writer, "_unique_hosts", None)
    if fn is None:
        pytest.fail(
            "Phase 77 D-14: quirk/reports/writer.py must expose `_unique_hosts(hosts)` "
            "helper that filters falsy hosts before set construction "
            "(cbom-intel-reports/IN-08)"
        )
    return fn


def test_unique_hosts_filters_none_and_empty_string() -> None:
    _unique_hosts = _get_unique_hosts()
    hosts = [None, "", "host1", "host1", "host2", None]
    result = _unique_hosts(hosts)
    assert result == {"host1", "host2"}, (
        "Phase 77 D-14: falsy hosts (None, '') must be excluded from the unique-set "
        "construction (cbom-intel-reports/IN-08)"
    )
    assert len(result) == 2


def test_unique_hosts_handles_empty_input() -> None:
    _unique_hosts = _get_unique_hosts()
    assert _unique_hosts([]) == set()
    assert _unique_hosts(None) == set()
