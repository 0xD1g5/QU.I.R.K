"""Tests for evaluate_email_endpoints() risk-engine findings + apply_profile() gating.

Phase 32 / Plan 04 — TDD RED -> GREEN.

Behavior coverage:
  Y1: EMAIL-08 — port=25 SMTP-STARTTLS w/ TLS negotiated -> exactly one MEDIUM
      finding titled "STARTTLS downgrade risk on SMTP".
  Y2: EMAIL-08 negative — port=587 SMTP-STARTTLS -> no STARTTLS-downgrade finding.
  Y3: EMAIL-09 HIGH — cipher="TLS_RSA_WITH_AES_128_CBC_SHA" -> HIGH "Weak cipher
      suite on email TLS endpoint".
  Y4: EMAIL-09 HIGH — cipher="AES256-SHA" (legacy openssl name) -> HIGH.
  Y5: EMAIL-09 MEDIUM — pfs=False, tls_version="TLSv1.2", cipher includes "ECDHE"
      -> MEDIUM "Non-PFS cipher suite on email TLS endpoint".
  Y6: D-11 layering — port=25 + cipher="AES256-SHA" -> BOTH MEDIUM downgrade-risk
      AND HIGH weak-cipher findings present (two distinct entries).
  Y7: Profile gating — apply_profile(cfg, "standard"|"deep") sets
      cfg.connectors.enable_email True; "quick" leaves it False.
"""
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ep(host="m.example.com", port=25, protocol="SMTP-STARTTLS",
        cipher_suite="", tls_version="TLSv1.2", tls_pfs_supported=True):
    return SimpleNamespace(
        host=host,
        port=port,
        protocol=protocol,
        cipher_suite=cipher_suite,
        tls_version=tls_version,
        tls_pfs_supported=tls_pfs_supported,
    )


def _mk_cfg():
    """Construct a minimal AppConfig with default ConnectorsCfg.enable_email=False."""
    from quirk.config import (
        AppConfig, AssessmentCfg, ScanCfg, TargetsCfg,
        ConnectorsCfg, OutputCfg, IntelligenceCfg,
    )
    # AssessmentCfg requires positional args; use minimal placeholders.
    assessment = AssessmentCfg(
        name="test",
        data_classification="internal",
        report_owner="test",
        timezone="UTC",
    )
    return AppConfig(
        assessment=assessment,
        scan=ScanCfg(),
        targets=TargetsCfg(),
        connectors=ConnectorsCfg(),
        output=OutputCfg(),
        intelligence=IntelligenceCfg(),
    )


# ---------------------------------------------------------------------------
# Y1 — EMAIL-08 STARTTLS downgrade (port 25)
# ---------------------------------------------------------------------------

def test_y1_starttls_downgrade_emitted_on_port_25():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=25, protocol="SMTP-STARTTLS",
            cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
            tls_version="TLSv1.2", tls_pfs_supported=True),
    ])
    starttls = [f for f in findings if f["title"] == "STARTTLS downgrade risk on SMTP"]
    assert len(starttls) == 1, f"Expected 1 STARTTLS-downgrade MEDIUM, got {findings}"
    assert starttls[0]["severity"] == "MEDIUM"
    assert starttls[0]["port"] == 25


# ---------------------------------------------------------------------------
# Y2 — EMAIL-08 negative (port 587 should NOT emit downgrade-risk)
# ---------------------------------------------------------------------------

def test_y2_no_downgrade_finding_on_port_587():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=587, protocol="SMTP-STARTTLS",
            cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
            tls_version="TLSv1.2", tls_pfs_supported=True),
    ])
    assert all("STARTTLS downgrade risk" not in f["title"] for f in findings), findings


# ---------------------------------------------------------------------------
# Y3 — EMAIL-09 HIGH (TLS_RSA_WITH_*)
# ---------------------------------------------------------------------------

def test_y3_weak_cipher_high_for_tls_rsa_with():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=993, protocol="IMAPS",
            cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA",
            tls_version="TLSv1.2", tls_pfs_supported=False),
    ])
    weak = [f for f in findings if f["title"] == "Weak cipher suite on email TLS endpoint"]
    assert len(weak) == 1, f"Expected 1 HIGH weak-cipher, got {findings}"
    assert weak[0]["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# Y4 — EMAIL-09 HIGH (AES256-SHA legacy openssl name)
# ---------------------------------------------------------------------------

def test_y4_weak_cipher_high_for_legacy_openssl_aes256_sha():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=993, protocol="IMAPS",
            cipher_suite="AES256-SHA",
            tls_version="TLSv1.2", tls_pfs_supported=False),
    ])
    weak = [f for f in findings if f["title"] == "Weak cipher suite on email TLS endpoint"]
    assert len(weak) == 1
    assert weak[0]["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# Y5 — EMAIL-09 MEDIUM (non-PFS ECDHE w/o TLS 1.3)
# ---------------------------------------------------------------------------

def test_y5_non_pfs_medium_for_ecdhe_without_tls13():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=993, protocol="IMAPS",
            cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
            tls_version="TLSv1.2", tls_pfs_supported=False),
    ])
    nonpfs = [f for f in findings if f["title"] == "Non-PFS cipher suite on email TLS endpoint"]
    assert len(nonpfs) == 1, f"Expected 1 MEDIUM non-PFS, got {findings}"
    assert nonpfs[0]["severity"] == "MEDIUM"


# ---------------------------------------------------------------------------
# Y6 — D-11 layering (port 25 + AES256-SHA -> BOTH findings)
# ---------------------------------------------------------------------------

def test_y6_layered_findings_on_port_25_with_weak_cipher():
    from quirk.engine.risk_engine import evaluate_email_endpoints
    findings = evaluate_email_endpoints([
        _ep(port=25, protocol="SMTP-STARTTLS",
            cipher_suite="AES256-SHA",
            tls_version="TLSv1.2", tls_pfs_supported=False),
    ])
    titles = sorted(f["title"] for f in findings)
    assert "STARTTLS downgrade risk on SMTP" in titles, titles
    assert "Weak cipher suite on email TLS endpoint" in titles, titles
    assert len(findings) == 2, f"Expected exactly 2 layered findings, got {findings}"


# ---------------------------------------------------------------------------
# Y7 — Profile gating
# ---------------------------------------------------------------------------

def test_y7a_standard_profile_enables_email():
    from quirk.engine.profiles import apply_profile
    cfg = _mk_cfg()
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is True


def test_y7b_deep_profile_enables_email():
    from quirk.engine.profiles import apply_profile
    cfg = _mk_cfg()
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_email is True


def test_y7c_quick_profile_leaves_email_disabled():
    from quirk.engine.profiles import apply_profile
    cfg = _mk_cfg()
    apply_profile(cfg, "quick")
    assert cfg.connectors.enable_email is False
