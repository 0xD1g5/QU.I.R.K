"""D-19: the browser-E2E seed certificate must never expire on a real clock.

The harness used to fix scanned_at at 2026-09-26, so the web01 cert expired
(not_after = scanned_at + 45d) on 2026-11-10 against the wall clock the findings
route uses, turning required Dashboard Quality CI red. The seed now follows the
wall clock. This test runs under plain pytest (no Chromium) so it is collected in
Linux Full Suite.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from quirk.models import CryptoEndpoint


def _frozen(at_utc: datetime):
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return at_utc.replace(tzinfo=None)
            return at_utc.astimezone(tz)

    return _Frozen


def _seed_and_findings(tmp_path, monkeypatch, at_utc):
    # Phase 236 D-10: findings_for_endpoint now lives in finding_derivation and
    # reads ITS OWN module-global ``datetime``; patching routes.scan no longer lands.
    import quirk.dashboard.api.finding_derivation as derivation_mod
    from tests import browser_e2e_harness as harness

    frozen = _frozen(at_utc)
    monkeypatch.setattr(harness, "datetime", frozen)
    monkeypatch.setattr(derivation_mod, "datetime", frozen)

    db_path = tmp_path / "q.db"
    harness.seed_dashboard_db(db_path)
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with sessionmaker(bind=engine)() as db:
            ep = db.execute(
                select(CryptoEndpoint).where(
                    CryptoEndpoint.host == "web01.seed.local",
                    CryptoEndpoint.port == 443,
                )
            ).scalar_one()
            # A missed patch would silently read the real clock; fail loudly instead.
            assert derivation_mod.datetime is frozen
            findings = derivation_mod.findings_for_endpoint(ep)
            scanned_at = ep.scanned_at
    finally:
        engine.dispose()
    return findings, scanned_at


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc),
        datetime(2027, 6, 1, 9, 0, tzinfo=timezone.utc),
        # Past-dated (run-time computed): only a landing clock patch keeps the 45d
        # cert unexpired; the real clock would read it ~75 days expired.
        datetime.now(timezone.utc) - timedelta(days=120),
    ],
    ids=["2026-11-15", "2027-06-01", "past-120d"],
)
def test_seed_cert_valid_on_forward_clock(tmp_path, monkeypatch, now):
    findings, _ = _seed_and_findings(tmp_path, monkeypatch, now)
    bad = [
        f for f in findings
        if "expired" in f.title.lower() or "expiring" in f.title.lower()
    ]
    assert not bad, f"seed cert reads as expired/expiring at {now}: {[f.title for f in bad]}"


def test_seed_scanned_at_tracks_clock(tmp_path, monkeypatch):
    now = datetime(2027, 3, 3, 14, 30, 45, tzinfo=timezone.utc)
    _, scanned_at = _seed_and_findings(tmp_path, monkeypatch, now)
    delta = now.replace(tzinfo=None) - scanned_at
    assert timedelta(0) <= delta <= timedelta(hours=2)
