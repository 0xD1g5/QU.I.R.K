"""Phase 49 D-04 gate 3 (COMPLY-07): no entry older than STALENESS_THRESHOLD_DAYS."""
from __future__ import annotations

import datetime


def test_no_entry_older_than_threshold():
    from quirk.compliance import COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS

    today = datetime.date.today()
    stale: list[tuple[str, str, int]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            try:
                verified = datetime.date.fromisoformat(entry["last_verified"])
            except (KeyError, TypeError, ValueError):
                # Schema test owns this failure mode; skip here.
                continue
            age = (today - verified).days
            if age > STALENESS_THRESHOLD_DAYS:
                stale.append((title, entry["last_verified"], age))
    assert not stale, (
        f"Stale compliance entries (>{STALENESS_THRESHOLD_DAYS} days): {stale}. "
        f"Re-verify each source_url against current regulator publication and "
        f"bump last_verified to today's date."
    )
