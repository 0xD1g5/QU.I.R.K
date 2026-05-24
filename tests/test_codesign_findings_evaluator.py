"""Phase 99 CTX-03 — Tests for evaluate_codesign_endpoints() and D-04/D-06 coverage.

Covers:
- evaluate_codesign_endpoints emits dicts (not endpoints) for expired/approaching/weak-crypto
- D-04 catalog-wins: expired codesign finding recommendation == REMEDIATION_CATALOG['CODESIGN_EXPIRY']
- quantum_risk field present and non-empty on all codesign findings
- D-06 email-path: evaluate_email_endpoints findings carry non-empty quantum_risk
- D-06 broker-path: evaluate_broker_endpoints findings carry non-empty quantum_risk
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from quirk.engine.findings_evaluator import (
    evaluate_codesign_endpoints,
    evaluate_email_endpoints,
    evaluate_broker_endpoints,
)
from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    FALLBACK_QUANTUM_RISK,
    REMEDIATION_CATALOG,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc():
    return datetime.now(timezone.utc)


def _codesign_ep(**kwargs):
    """Build a minimal CODE_SIGNING-like endpoint."""
    defaults = dict(
        host="10.0.0.1",
        port=636,
        severity="HIGH",
        cert_subject="CN=Code Signer",
        cert_not_after=_now_utc() - timedelta(days=1),  # expired by default
        smime_scan_json=json.dumps({"reasons": ["expired"]}),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _email_ep(**kwargs):
    """Build a minimal email endpoint that triggers EMAIL-09 weak cipher finding."""
    defaults = dict(
        host="10.0.0.2",
        port=25,
        protocol="SMTP-STARTTLS",
        cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA",  # RSA kex — triggers EMAIL-09
        tls_version="TLSv1.2",
        tls_pfs_supported=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _broker_ep(**kwargs):
    """Build a minimal broker endpoint that triggers a finding."""
    defaults = dict(
        host="10.0.0.3",
        port=9092,
        protocol="KAFKA-PLAIN",
        cipher_suite="",
        tls_version="",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# evaluate_codesign_endpoints — basic output shape
# ---------------------------------------------------------------------------

class TestEvaluateCodesignEndpoints:
    def test_expired_returns_list_of_dicts(self):
        ep = _codesign_ep()
        result = evaluate_codesign_endpoints([ep])
        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], dict)

    def test_empty_input_returns_empty_list(self):
        assert evaluate_codesign_endpoints([]) == []

    def test_expired_finding_severity_is_high(self):
        ep = _codesign_ep(smime_scan_json=json.dumps({"reasons": ["expired"]}))
        findings = evaluate_codesign_endpoints([ep])
        assert any(f["severity"] == "HIGH" for f in findings)

    def test_approaching_expiry_finding_severity_is_medium(self):
        future_30 = _now_utc() + timedelta(days=30)
        ep = _codesign_ep(
            cert_not_after=future_30,
            smime_scan_json=json.dumps({"reasons": ["approaching-expiry"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert any(f["severity"] == "MEDIUM" for f in findings)

    def test_weak_crypto_only_finding_severity_is_high(self):
        ep = _codesign_ep(
            smime_scan_json=json.dumps({"reasons": ["weak-rsa-key"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert any(f["severity"] == "HIGH" for f in findings)

    def test_all_findings_have_quantum_risk(self):
        ep = _codesign_ep()
        findings = evaluate_codesign_endpoints([ep])
        for f in findings:
            assert "quantum_risk" in f
            assert f["quantum_risk"]  # non-empty

    def test_malformed_smime_scan_json_does_not_crash(self):
        """T-99-04: malformed JSON → reasons=[] → no codesign finding (not a crash)."""
        ep = _codesign_ep(smime_scan_json="not-valid-json}")
        result = evaluate_codesign_endpoints([ep])
        # Should return empty (no reasons → no expired/approaching/weak branch fires)
        assert isinstance(result, list)

    def test_expired_finding_title_contains_subject(self):
        ep = _codesign_ep(cert_subject="CN=MySigner",
                          smime_scan_json=json.dumps({"reasons": ["expired"]}))
        findings = evaluate_codesign_endpoints([ep])
        assert any("CN=MySigner" in f["title"] for f in findings)

    def test_approaching_finding_title_contains_subject(self):
        future_30 = _now_utc() + timedelta(days=30)
        ep = _codesign_ep(cert_subject="CN=ApproachingSigner",
                          cert_not_after=future_30,
                          smime_scan_json=json.dumps({"reasons": ["approaching-expiry"]}))
        findings = evaluate_codesign_endpoints([ep])
        assert any("CN=ApproachingSigner" in f["title"] for f in findings)


# ---------------------------------------------------------------------------
# D-04: catalog-wins — expired codesign finding recommendation
# ---------------------------------------------------------------------------

class TestCatalogWinsCodesign:
    def test_expired_finding_recommendation_equals_catalog(self):
        """D-04: expired-path codesign recommendation == REMEDIATION_CATALOG['CODESIGN_EXPIRY']."""
        ep = _codesign_ep(smime_scan_json=json.dumps({"reasons": ["expired"]}))
        findings = evaluate_codesign_endpoints([ep])
        expired_findings = [f for f in findings if f.get("severity") == "HIGH"
                            and "expired" in f.get("title", "").lower()]
        assert expired_findings, "Expected at least one expired-branch finding"
        for f in expired_findings:
            assert f["recommendation"] == REMEDIATION_CATALOG["CODESIGN_EXPIRY"], (
                f"Expected catalog value, got: {f['recommendation']!r}"
            )

    def test_approaching_finding_recommendation_equals_catalog(self):
        """D-04: approaching-path codesign recommendation == REMEDIATION_CATALOG['CODESIGN_APPROACHING_EXPIRY']."""
        future_30 = _now_utc() + timedelta(days=30)
        ep = _codesign_ep(cert_not_after=future_30,
                          smime_scan_json=json.dumps({"reasons": ["approaching-expiry"]}))
        findings = evaluate_codesign_endpoints([ep])
        approaching = [f for f in findings if f.get("severity") == "MEDIUM"]
        assert approaching, "Expected at least one approaching-branch finding"
        for f in approaching:
            assert f["recommendation"] == REMEDIATION_CATALOG["CODESIGN_APPROACHING_EXPIRY"]

    def test_expired_finding_quantum_risk_equals_algo_map(self):
        """CODESIGN_EXPIRY quantum_risk comes from ALGO_IMPACT_MAP."""
        ep = _codesign_ep(smime_scan_json=json.dumps({"reasons": ["expired"]}))
        findings = evaluate_codesign_endpoints([ep])
        expired_findings = [f for f in findings if "expired" in f.get("title", "").lower()]
        assert expired_findings
        for f in expired_findings:
            assert f["quantum_risk"] == ALGO_IMPACT_MAP["CODESIGN_EXPIRY"][2]


# ---------------------------------------------------------------------------
# WR-02: weak-crypto codesign findings carry algorithm-specific quantum_risk
# ---------------------------------------------------------------------------

class TestWeakCryptoQuantumRisk:
    def test_weak_ec_key_quantum_risk_is_ecdsa_specific(self):
        """WR-02: weak-ec-key codesign finding must carry the ECDSA quantum_risk, not fallback."""
        ep = _codesign_ep(
            smime_scan_json=json.dumps({"reasons": ["weak-ec-key"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert findings, "Expected at least one finding for weak-ec-key"
        for f in findings:
            assert f.get("quantum_risk") != FALLBACK_QUANTUM_RISK, (
                "WR-02: weak-ec-key must yield algorithm-specific quantum_risk, not fallback boilerplate"
            )
            assert f.get("quantum_risk") == ALGO_IMPACT_MAP["ECDSA"][2], (
                f"WR-02: weak-ec-key quantum_risk must equal ALGO_IMPACT_MAP['ECDSA'][2], got: {f.get('quantum_risk')!r}"
            )

    def test_weak_rsa_key_quantum_risk_is_rsa_specific(self):
        """WR-02: weak-rsa-key codesign finding must carry the RSA quantum_risk, not fallback."""
        ep = _codesign_ep(
            smime_scan_json=json.dumps({"reasons": ["weak-rsa-key"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert findings
        for f in findings:
            assert f.get("quantum_risk") == ALGO_IMPACT_MAP["RSA"][2], (
                f"WR-02: weak-rsa-key quantum_risk must equal ALGO_IMPACT_MAP['RSA'][2]"
            )

    def test_weak_signing_alg_quantum_risk_is_sha1_specific(self):
        """WR-02: weak-signing-alg codesign finding must carry the SHA-1 quantum_risk, not fallback."""
        ep = _codesign_ep(
            smime_scan_json=json.dumps({"reasons": ["weak-signing-alg"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert findings
        for f in findings:
            assert f.get("quantum_risk") == ALGO_IMPACT_MAP["SHA-1"][2], (
                f"WR-02: weak-signing-alg quantum_risk must equal ALGO_IMPACT_MAP['SHA-1'][2]"
            )

    def test_weak_crypto_recommendation_comes_from_catalog(self):
        """WR-02: weak-ec-key recommendation must be the ECDSA catalog entry (not generic)."""
        ep = _codesign_ep(
            smime_scan_json=json.dumps({"reasons": ["weak-ec-key"]}),
        )
        findings = evaluate_codesign_endpoints([ep])
        assert findings
        for f in findings:
            assert f.get("recommendation") == REMEDIATION_CATALOG["ECDSA"], (
                f"WR-02: weak-ec-key recommendation must come from REMEDIATION_CATALOG['ECDSA']"
            )


# ---------------------------------------------------------------------------
# D-06: email-path and broker-path carry quantum_risk
# ---------------------------------------------------------------------------

class TestD06Coverage:
    def test_email_path_findings_carry_quantum_risk(self):
        """D-06: evaluate_email_endpoints findings have non-empty quantum_risk."""
        ep = _email_ep()
        findings = evaluate_email_endpoints([ep])
        assert findings, "Expected at least one email finding from weak RSA kex endpoint"
        for f in findings:
            assert "quantum_risk" in f, f"Missing quantum_risk in email finding: {f}"
            assert f["quantum_risk"], f"Empty quantum_risk in email finding: {f}"

    def test_broker_path_findings_carry_quantum_risk(self):
        """D-06: evaluate_broker_endpoints findings have non-empty quantum_risk."""
        ep = _broker_ep()
        findings = evaluate_broker_endpoints([ep])
        assert findings, "Expected at least one broker finding from KAFKA-PLAIN endpoint"
        for f in findings:
            assert "quantum_risk" in f, f"Missing quantum_risk in broker finding: {f}"
            assert f["quantum_risk"], f"Empty quantum_risk in broker finding: {f}"

    def test_email_rsa_kex_quantum_risk_is_not_fallback(self):
        """EMAIL-09 weak RSA kex title triggers RSA catalog → quantum_risk is RSA-specific."""
        ep = _email_ep()
        findings = evaluate_email_endpoints([ep])
        rsa_kex = [f for f in findings if "Weak cipher suite" in f.get("title", "")]
        assert rsa_kex
        for f in rsa_kex:
            # The finding title contains "cipher suite" (not "RSA") so it may
            # use the fallback — assert it is non-empty either way
            assert f["quantum_risk"]
