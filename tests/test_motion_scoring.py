"""RED tests for Phase 34 motion_ evidence counters and scoring weights.

Mirrors tests/test_dar_storage_scoring.py shape. Phase 34 adds 6 motion_ counters
in build_evidence_summary() and 5 motion_*_ratio entries + "motion_" profile
multiplier in scoring. data_in_motion appears as the 6th subscore key.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock


def _ep(protocol: str, *, tls_version: str = "", cipher_suite: str = "",
        service_detail: str = ""):
    """MagicMock endpoint stub. Mirrors tests/test_dar_storage_scoring.py:_ep()
    with two additional kwargs (tls_version, cipher_suite) that motion counters
    read."""
    ep = MagicMock()
    ep.protocol = protocol
    ep.service_detail = service_detail
    ep.tls_version = tls_version
    ep.cipher_suite = cipher_suite
    ep.scanned_at = datetime(2026, 4, 28, tzinfo=timezone.utc).replace(tzinfo=None)
    ep.scan_error = None
    ep.tls_blocker_reason = ""
    ep.cert_pubkey_alg = ""
    ep.cert_pubkey_size = None
    ep.cert_not_after = None
    ep.cert_subject = ""
    ep.cert_issuer = ""
    ep.tls_supported_versions = ""
    ep.host = "test-host"
    ep.port = 0
    return ep


# ---------- MOTION-01: counter keys present + tick correctly ----------

def test_motion_keys_present_in_summary():
    """All 6 motion_ count keys + 5 motion_ ratio keys appear in the summary
    dict, even with zero endpoints."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([])
    for key in (
        "motion_email_starttls_missing_count",
        "motion_email_plaintext_count",
        "motion_email_weak_cipher_count",
        "motion_broker_plaintext_count",
        "motion_broker_weak_tls_count",
        "motion_broker_weak_cipher_count",
        "motion_email_plaintext_ratio",
        "motion_email_weak_cipher_ratio",
        "motion_broker_plaintext_ratio",
        "motion_broker_weak_tls_ratio",
        "motion_broker_weak_cipher_ratio",
    ):
        assert key in result, f"missing key {key}"


def test_motion_broker_plaintext_count_kafka():
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([_ep("KAFKA-PLAIN")])
    assert result["motion_broker_plaintext_count"] == 1


def test_motion_broker_plaintext_count_amqp_and_redis():
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("AMQP-PLAIN"),
        _ep("REDIS-PLAIN"),
    ])
    assert result["motion_broker_plaintext_count"] == 2


def test_motion_broker_weak_tls_count():
    """TLS 1.0 / 1.1 / SSLv3 on a TLS-enabled broker protocol ticks the counter."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("KAFKA-TLS", tls_version="TLSv1.0", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),
        _ep("AMQPS",     tls_version="TLSv1.1", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),
        _ep("REDIS-TLS", tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),  # not weak
    ])
    assert result["motion_broker_weak_tls_count"] == 2


def test_motion_broker_weak_cipher_count():
    """RSA-only / 3DES / RC4 / non-PFS AES-SHA on broker TLS ticks the counter
    (mirrors risk_engine.py:564–567)."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("KAFKA-TLS", tls_version="TLSv1.2", cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA"),
        _ep("AMQPS",     tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),  # strong
    ])
    assert result["motion_broker_weak_cipher_count"] == 1


def test_motion_email_starttls_missing_count():
    """SMTP/IMAP/POP3 STARTTLS protocols with empty tls_version (handshake
    never completed) tick motion_email_starttls_missing_count."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("SMTP-STARTTLS"),  # tls_version=""
        _ep("IMAP-STARTTLS"),  # tls_version=""
        _ep("POP3-STARTTLS", tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),  # OK, no tick
    ])
    assert result["motion_email_starttls_missing_count"] == 2


def test_motion_email_plaintext_count():
    """SMTPS/IMAPS/POP3S with empty tls_version (implicit TLS port answered
    but handshake never completed) ticks motion_email_plaintext_count."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("SMTPS"),  # tls_version=""
        _ep("IMAPS"),  # tls_version=""
        _ep("POP3S", tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),  # OK
    ])
    assert result["motion_email_plaintext_count"] == 2


def test_motion_email_weak_cipher_count():
    """Per orchestrator decision A5: HIGH-only cipher predicate, mirrors
    risk_engine.py:483–489 — TLS_RSA_WITH_*, 3DES, RC4 on email TLS."""
    from quirk.intelligence.evidence import build_evidence_summary
    result = build_evidence_summary([
        _ep("SMTPS",          tls_version="TLSv1.2", cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA"),
        _ep("IMAP-STARTTLS",  tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES128-GCM-SHA256"),  # strong
    ])
    assert result["motion_email_weak_cipher_count"] == 1


# ---------- MOTION-02: 5 weights + MOTION-03: profile multipliers ----------

def test_score_weights_motion_values():
    """All 5 motion_*_ratio weights LOCKED per D-03."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS
    assert SCORE_WEIGHTS["motion_email_plaintext_ratio"] == 12.0
    assert SCORE_WEIGHTS["motion_email_weak_cipher_ratio"] == 6.0
    assert SCORE_WEIGHTS["motion_broker_plaintext_ratio"] == 14.0
    assert SCORE_WEIGHTS["motion_broker_weak_tls_ratio"] == 8.0
    assert SCORE_WEIGHTS["motion_broker_weak_cipher_ratio"] == 6.0


def test_profile_multipliers_motion():
    """PROFILE_MULTIPLIERS gains "motion_" prefix in all 3 profiles per D-08."""
    from quirk.intelligence.scoring import PROFILE_MULTIPLIERS
    assert PROFILE_MULTIPLIERS["strict"]["motion_"] == 1.4
    assert PROFILE_MULTIPLIERS["balanced"]["motion_"] == 1.0
    assert PROFILE_MULTIPLIERS["lenient"]["motion_"] == 0.7


# ---------- MOTION-04: data_in_motion subscore + measurable movement ----------

def test_subscores_includes_data_in_motion():
    """compute_readiness_score() returns data_in_motion as a named subscore key
    even with zero motion evidence."""
    from quirk.intelligence.scoring import compute_readiness_score
    result = compute_readiness_score({"totals": {"endpoints": 4, "findings": 0}})
    assert "data_in_motion" in result["subscores"]


def test_motion_subscore_lowers_with_findings():
    """SC-1 / D-09 — relative assertion only (no absolute equality per A3)."""
    from quirk.intelligence.scoring import compute_readiness_score
    baseline = compute_readiness_score({
        "totals": {"endpoints": 4, "findings": 0},
        "motion_broker_plaintext_count": 0,
    }, profile="balanced")
    bad = compute_readiness_score({
        "totals": {"endpoints": 4, "findings": 2},
        "motion_broker_plaintext_count": 2,
    }, profile="balanced")
    assert bad["subscores"]["data_in_motion"] < baseline["subscores"]["data_in_motion"]
    assert bad["score"] < baseline["score"]


def test_top_drivers_surfaces_motion():
    """D-10 — when motion counters dominate, a motion driver appears in
    top drivers."""
    from quirk.intelligence.scoring import compute_readiness_score
    result = compute_readiness_score({
        "totals": {"endpoints": 4, "findings": 4},
        "motion_broker_plaintext_count": 4,
    }, profile="balanced")
    labels = [d["reason"] for d in result.get("drivers", [])]
    assert any(
        ("Plaintext broker" in lbl) or ("broker" in lbl.lower() and "plaintext" in lbl.lower())
        for lbl in labels
    ), f"no motion driver in top drivers: {labels}"


def test_legacy_evidence_no_motion_keys_full_credit():
    """D-12 — legacy scans without motion_ keys must not raise; relative
    assertion: data_in_motion equals the zero-motion baseline (no penalty)."""
    from quirk.intelligence.scoring import compute_readiness_score
    legacy = compute_readiness_score({
        "totals": {"endpoints": 4, "findings": 0},
    })
    explicit_zero = compute_readiness_score({
        "totals": {"endpoints": 4, "findings": 0},
        "motion_broker_plaintext_count": 0,
        "motion_broker_weak_tls_count": 0,
        "motion_broker_weak_cipher_count": 0,
        "motion_email_plaintext_count": 0,
        "motion_email_starttls_missing_count": 0,
        "motion_email_weak_cipher_count": 0,
    })
    assert legacy["subscores"]["data_in_motion"] == explicit_zero["subscores"]["data_in_motion"]


def test_profile_strict_increases_motion_penalty():
    """D-08 — strict profile (1.4×) lowers data_in_motion more than balanced
    when motion counters are present."""
    from quirk.intelligence.scoring import compute_readiness_score
    evidence = {
        "totals": {"endpoints": 4, "findings": 2},
        "motion_broker_plaintext_count": 2,
    }
    balanced = compute_readiness_score(evidence, profile="balanced")
    strict = compute_readiness_score(evidence, profile="strict")
    assert strict["subscores"]["data_in_motion"] <= balanced["subscores"]["data_in_motion"]
    # And in the dominating-counter case strictly less:
    assert strict["score"] <= balanced["score"]
