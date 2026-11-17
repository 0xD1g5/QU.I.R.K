"""Phase 237 COUNT-07: a full connector outage is visible in Trends and in notify.

Ledger 261107-trends-hide-full-connector-outage (B-WR-07). Sessions are built
from the REAL ``run_scan._classify_connector_outcomes`` (not a hand-written
detail string) and read back through the real ``compute_trend_report``.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import sessionmaker

import run_scan
from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings
from quirk.db import init_db
from quirk.intelligence.trends import compute_trend_report
from quirk.models import CryptoEndpoint
from quirk.scanner.target_outcome import (
    OUTCOME_ANSWERED,
    OUTCOME_UNREACHABLE,
    TargetOutcomes,
)

PREV_TS = datetime(2026, 1, 1, 10, 0, 0)
CUR_TS = datetime(2026, 1, 2, 10, 0, 0)
LABELS = ["jwt_scanner", "saml_scanner", "dnssec_scanner"]
VAULT_DETAIL = "connectors.vault_token / VAULT_TOKEN not set"


def _classify(label: str, total: int, down: int):
    """Run the real classifier: `down` of `total` targets unreachable."""
    targets = [f"t{i}.example.test" for i in range(total)]
    outcomes = TargetOutcomes(targets)
    for i, t in enumerate(outcomes.expected):
        if i < down:
            outcomes.record(t, OUTCOME_UNREACHABLE, "timed out")
        else:
            outcomes.record(t, OUTCOME_ANSWERED, "")
    error_endpoints: list = []
    run_scan._classify_connector_outcomes(
        label, outcomes, [], error_endpoints, run_scan._PhaseRecorder()
    )
    return error_endpoints


def _persist(db, ts, run_id, extra_rows):
    db.add(CryptoEndpoint(
        host="10.0.0.1", port=443, protocol="tls", scanned_at=ts, scan_run_id=run_id,
    ))
    for ep in extra_rows:
        ep.scanned_at = ts
        ep.scan_run_id = run_id
        db.add(ep)
    db.commit()


def _report(db):
    return compute_trend_report(
        CUR_TS, PREV_TS, db, findings_deriver=derive_dashboard_scoring_findings
    )


@pytest.fixture
def make_db(tmp_path):
    engine = init_db(str(tmp_path / "t.db"))
    maker = sessionmaker(bind=engine)
    with maker() as db:
        yield db


@pytest.mark.parametrize("label", LABELS)
def test_full_outage_counts_at_least_partial(tmp_path, label):
    counts = {}
    for name, down in (("partial", 1), ("full", 4)):
        engine = init_db(str(tmp_path / f"{name}.db"))
        with sessionmaker(bind=engine)() as db:
            _persist(db, PREV_TS, "run-prev", [])
            _persist(db, CUR_TS, "run-cur", _classify(label, 4, down))
            counts[name] = _report(db).scan_errors_new_count
    assert counts["full"] >= counts["partial"]
    assert counts["partial"] == 1
    assert counts["full"] == 4


def test_failed_target_count_contract():
    from quirk.scanner.target_outcome import failed_target_count

    rows = _classify("jwt_scanner", 4, 4)
    advisory = [r for r in rows if r.protocol == "ADVISORY"]
    assert len(advisory) == 1
    assert failed_target_count(advisory[0].scan_error) == 4
    assert failed_target_count(VAULT_DETAIL) is None
    assert failed_target_count("") is None
    assert failed_target_count(None) is None


def test_full_unexpected_response_outage_weighs_n(make_db):
    """Phase 238 D-10: four SAML targets that all answered with the wrong document weigh 4."""
    from quirk.scanner.target_outcome import failed_target_count

    outcomes = TargetOutcomes([f"https://idp{i}.example/metadata" for i in range(4)])
    for t in outcomes.expected:
        outcomes.record(t, "unexpected_response", "HTTP 404")
    rows: list = []
    run_scan._classify_connector_outcomes(
        "saml_scanner", outcomes, [], rows, run_scan._PhaseRecorder()
    )
    advisory = [r for r in rows if r.protocol == "ADVISORY"]
    assert len(advisory) == 1
    assert failed_target_count(advisory[0].scan_error) == 4

    db = make_db
    _persist(db, PREV_TS, "run-prev", [])
    _persist(db, CUR_TS, "run-cur", rows)
    assert _report(db).scan_errors_new_count == 4


def test_vault_missing_token_counts_one(make_db):
    db = make_db
    _persist(db, PREV_TS, "run-prev", [])
    _persist(db, CUR_TS, "run-cur", [CryptoEndpoint(
        host="vault_scanner", port=0, protocol="ADVISORY",
        scan_error=VAULT_DETAIL, scan_error_category="missing_credentials",
    )])
    assert _report(db).scan_errors_new_count == 1


@pytest.mark.parametrize(
    "category", ["missing_extra", "missing_binary", "internal_target_refused"]
)
def test_environment_categories_stay_zero(make_db, category):
    db = make_db
    _persist(db, PREV_TS, "run-prev", [])
    _persist(db, CUR_TS, "run-cur", [CryptoEndpoint(
        host="x_scanner", port=0, protocol="ADVISORY",
        scan_error="4 of 4 targets were refused", scan_error_category=category,
    )])
    assert _report(db).scan_errors_new_count == 0


# ---------------------------------------------------------------------------
# Notify (D-16, D-21, D-23)
# ---------------------------------------------------------------------------

def _outage_db(tmp_path):
    engine = init_db(str(tmp_path / "n.db"))
    maker = sessionmaker(bind=engine)
    db = maker()
    _persist(db, PREV_TS, "run-prev", [])
    _persist(db, CUR_TS, "run-cur", _classify("jwt_scanner", 4, 4))
    return db


def test_outage_notify_actually_sends(tmp_path, monkeypatch):
    import quirk.notify.channels.email as email_mod
    import quirk.notify.channels.slack as slack_mod
    from quirk.cli.scheduler_cmd import _utcnow_naive
    from quirk.models import ScheduledRun, ScheduledScan
    from quirk.notify import dispatcher
    from quirk.notify.config import EmailNotifyCfg, NotifyCfg, SlackNotifyCfg

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
        email=EmailNotifyCfg(
            smtp_host="smtp.example.com",
            smtp_from="quirk@example.com",
            recipients=["sec@example.com"],
        ),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)

    slack_sent, email_sent = [], []
    monkeypatch.setattr(
        slack_mod, "send_slack",
        lambda c, summary: slack_sent.append(slack_mod._format_slack_text(summary)),
    )
    monkeypatch.setattr(
        email_mod, "send_email",
        lambda c, subject, body: email_sent.append((subject, body)),
    )

    db = _outage_db(tmp_path)
    report = _report(db)
    assert report.new_high == 0
    assert report.scan_errors_new_count == 4

    schedule = ScheduledScan(
        name="s", cron_expr="* * * * *", target="127.0.0.1", enabled=True,
        created_at=_utcnow_naive(),
    )
    db.add(schedule)
    db.commit()
    run = ScheduledRun(
        schedule_id=schedule.id, dispatched_at=_utcnow_naive(),
        status="completed", scan_output_path=None, scan_id=None,
    )
    db.add(run)
    db.commit()

    dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)

    assert len(slack_sent) == 1, "Slack message was never sent"
    assert len(email_sent) == 1, "email was never sent"
    assert "Scan errors: 4 new" in slack_sent[0]
    subject, body = email_sent[0]
    assert "Scan errors: 4 new" in body
    assert "new HIGH finding" not in subject


def test_webhook_payload_carries_count_only(make_db):
    from quirk.notify.payload import to_integration_payload

    db = make_db
    _persist(db, PREV_TS, "run-prev", [])
    _persist(db, CUR_TS, "run-cur", _classify("jwt_scanner", 4, 4))
    payload = to_integration_payload(_report(db))
    assert payload["scan_errors_new_count"] == 4
    assert "jwt_scanner" not in repr(payload) and "t0.example.test" not in repr(payload)

    from tests.test_notify_payload_whitelist import EXPECTED_KEYS

    assert set(payload) == set(EXPECTED_KEYS)


def _trend(**kw):
    from quirk.intelligence.trends import TrendReport

    base = dict(
        current_session_ts=CUR_TS, previous_session_ts=None, current_score=70,
        previous_score=None, score_delta=None, new_high=0, new_medium=0,
        new_low=0, resolved_high=0, resolved_medium=0, resolved_low=0,
        scan_errors_new_count=3, scan_errors_resolved_count=0,
    )
    base.update(kw)
    return TrendReport(**base)


def test_scan_error_trigger_requires_previous_session():
    from quirk.notify.dispatcher import should_notify

    assert should_notify(_trend(previous_session_ts=None)) is False
    assert should_notify(_trend(previous_session_ts=PREV_TS)) is True


def _summary(new_high, errors):
    from quirk.notify.payload import DriftSummary

    return DriftSummary(
        current_score=70, previous_score=70, score_delta=0, score_band="MEDIUM",
        new_high=new_high, new_medium=0, new_low=0, scan_id="x",
        dashboard_url=None, scan_errors_new_count=errors,
    )


def test_slack_first_line_names_outage_when_no_new_high():
    from quirk.notify.channels.slack import _format_slack_text

    lines = _format_slack_text(_summary(0, 4)).split("\n")
    assert "Scan-Coverage Alert" in lines[0]
    assert not any("new HIGH" in ln for ln in lines)


def test_slack_first_line_unchanged_with_new_high():
    from quirk.notify.channels.slack import _format_slack_text

    lines = _format_slack_text(_summary(2, 4)).split("\n")
    assert lines[0] == "*QUIRK Quantum-Readiness Alert* — Score Band: MEDIUM"
    assert any("Scan errors: 4 new" in ln for ln in lines)


def test_email_subject_unchanged_with_new_high(monkeypatch):
    import quirk.notify.channels.email as email_mod
    from quirk.notify import dispatcher

    sent = []
    monkeypatch.setattr(email_mod, "send_email", lambda c, subject, body: sent.append(subject))
    dispatcher._channel_send_email(object(), _summary(2, 4))
    assert sent == ["QUIRK Alert: 2 new HIGH finding(s) — score 70"]
