"""Identity Surface TDD RED scaffold — Phase 21, Plan 01.

Tests define the expected behavior for IDENT-01 through IDENT-04:
  - IDENT-01: Evidence counters and scoring weights for Kerberos/SAML/DNSSEC
  - IDENT-02: IdentityFinding Pydantic model and TypeScript interface contract
  - IDENT-03: Identity finding derivation from scan endpoints
  - IDENT-04: Identity findings surfaced in main findings table

Static/import tests PASS after Task 2. Functional evidence/scoring tests are RED.
Derivation tests SKIP (awaiting _derive_identity_findings in Plan 02).
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from typing import Optional

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import SCORE_WEIGHTS, compute_readiness_score
from quirk.dashboard.api.schemas import IdentityFinding, ScanLatestResponse

# ---------------------------------------------------------------------------
# Conditional import for derivation function — SKIP if not yet implemented
# ---------------------------------------------------------------------------
try:
    from quirk.dashboard.api.routes.scan import _derive_identity_findings  # noqa: F401
    _HAS_DERIVE = True
except ImportError:
    _HAS_DERIVE = False


# ---------------------------------------------------------------------------
# Shared endpoint dataclass — extends _Ep pattern with service_detail
# ---------------------------------------------------------------------------

@dataclass
class _Ep:
    host: str
    port: int
    protocol: str
    cert_pubkey_alg: Optional[str] = None
    cert_pubkey_size: Optional[int] = None
    service_detail: Optional[str] = None
    scanned_at: Optional[object] = None
    scan_error: Optional[str] = None
    tls_blocker_reason: Optional[str] = None
    cert_not_after: Optional[object] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _kerberos_rc4_ep() -> _Ep:
    return _Ep(
        host="dc.example.com",
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg="rc4-hmac",
        service_detail="etype:23:rc4-hmac:HIGH",
    )


def _kerberos_aes256_ep() -> _Ep:
    return _Ep(
        host="dc.example.com",
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg="aes256-cts-hmac-sha1-96",
        service_detail="etype:18:aes256-cts-hmac-sha1-96:SAFE",
    )


def _saml_weak_ep() -> _Ep:
    return _Ep(
        host="idp.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
        service_detail="https://idp.example.com|use=signing|serial=ABC",
    )


def _saml_sha1_ep() -> _Ep:
    return _Ep(
        host="idp.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="SHA1",
        cert_pubkey_size=None,
        service_detail=(
            "https://idp.example.com"
            "|algo_uri=http://www.w3.org/2000/09/xmldsig#sha1"
            "|source=SignatureMethod"
        ),
    )


def _saml_safe_ep() -> _Ep:
    return _Ep(
        host="idp.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=4096,
        service_detail="https://idp.example.com|use=signing|serial=DEF",
    )


def _dnssec_rsasha1_ep() -> _Ep:
    return _Ep(
        host="example.com",
        port=53,
        protocol="DNSSEC",
        cert_pubkey_alg="RSASHA1",
        service_detail="dnskey:tag=12345:role=ZSK",
    )


def _dnssec_ecdsa_ep() -> _Ep:
    return _Ep(
        host="example.com",
        port=53,
        protocol="DNSSEC",
        cert_pubkey_alg="ECDSAP256SHA256",
        service_detail="dnskey:tag=67890:role=KSK",
    )


def _tls_baseline_ep() -> _Ep:
    return _Ep(
        host="web.example.com",
        port=443,
        protocol="TLS",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
    )


# ---------------------------------------------------------------------------
# Helper: base evidence dict with identity counters zeroed
# ---------------------------------------------------------------------------

def _base_evidence_with_identity(**overrides) -> dict:
    base = {
        "totals": {"endpoints": 5, "findings": 0},
        "protocol_counts": {"TLS": 1, "HTTP": 0, "SSH": 0, "UNKNOWN": 0},
        "plaintext_http_count": 0,
        "http_on_tls_port_count": 0,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 1, "ECDSA": 0},
        "certificate_observations": {
            "certs_observed": 0,
            "expired_count": 0,
            "expiring_count": 0,
            "self_signed_count": 0,
        },
        "scan_error": {"count": 0, "rate": 0.0},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        },
        "identity_weak_etype_count": 0,
        "saml_weak_signing_count": 0,
        "dnssec_weak_algo_count": 0,
    }
    base.update(overrides)
    return base


# ===========================================================================
# Class 1: IDENT-01 Evidence Counter Tests (will FAIL RED — keys missing)
# ===========================================================================

class IdentityEvidenceCounterTests(unittest.TestCase):
    """RED tests for evidence counters added by Plan 02.

    build_evidence_summary does not yet return identity_weak_etype_count,
    saml_weak_signing_count, or dnssec_weak_algo_count — these will raise
    KeyError until evidence.py is updated in Plan 02.
    """

    def test_kerberos_weak_etype_counted(self) -> None:
        """IDENT-01: RC4-HMAC Kerberos etype increments identity_weak_etype_count."""
        endpoints = [_kerberos_rc4_ep(), _tls_baseline_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertGreaterEqual(
            summary["identity_weak_etype_count"],
            1,
            "Expected identity_weak_etype_count >= 1 for RC4-HMAC endpoint",
        )

    def test_saml_weak_signing_counted_rsa_small(self) -> None:
        """IDENT-01: RSA-1024 SAML signing cert increments saml_weak_signing_count."""
        endpoints = [_saml_weak_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertGreaterEqual(
            summary["saml_weak_signing_count"],
            1,
            "Expected saml_weak_signing_count >= 1 for RSA-1024 SAML endpoint",
        )

    def test_saml_weak_signing_counted_sha1(self) -> None:
        """IDENT-01: SHA-1 SAML SignatureMethod URI increments saml_weak_signing_count."""
        endpoints = [_saml_sha1_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertGreaterEqual(
            summary["saml_weak_signing_count"],
            1,
            "Expected saml_weak_signing_count >= 1 for SHA-1 SAML endpoint",
        )

    def test_dnssec_weak_algo_counted(self) -> None:
        """IDENT-01: RSASHA1 DNSSEC algorithm increments dnssec_weak_algo_count."""
        endpoints = [_dnssec_rsasha1_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertGreaterEqual(
            summary["dnssec_weak_algo_count"],
            1,
            "Expected dnssec_weak_algo_count >= 1 for RSASHA1 DNSSEC endpoint",
        )

    def test_safe_identity_endpoints_zero_counters(self) -> None:
        """IDENT-01: Quantum-safe identity endpoints produce zero weak counters."""
        endpoints = [_kerberos_aes256_ep(), _saml_safe_ep(), _dnssec_ecdsa_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertEqual(
            summary["identity_weak_etype_count"],
            0,
            "Safe Kerberos etype should not increment identity_weak_etype_count",
        )
        self.assertEqual(
            summary["saml_weak_signing_count"],
            0,
            "Safe SAML signing cert should not increment saml_weak_signing_count",
        )
        self.assertEqual(
            summary["dnssec_weak_algo_count"],
            0,
            "Safe DNSSEC algorithm should not increment dnssec_weak_algo_count",
        )

    def test_no_identity_endpoints_zero_counters(self) -> None:
        """IDENT-01: Non-identity endpoints produce zero identity counters."""
        endpoints = [_tls_baseline_ep()]
        summary = build_evidence_summary(endpoints, [])
        self.assertEqual(summary["identity_weak_etype_count"], 0)
        self.assertEqual(summary["saml_weak_signing_count"], 0)
        self.assertEqual(summary["dnssec_weak_algo_count"], 0)


# ===========================================================================
# Class 2: IDENT-01 Scoring Tests (will FAIL RED — weight keys missing)
# ===========================================================================

class IdentityScoringTests(unittest.TestCase):
    """RED tests for identity scoring weights added by Plan 02.

    SCORE_WEIGHTS does not yet contain the three identity weight keys.
    """

    def test_score_weights_contain_identity_keys(self) -> None:
        """IDENT-01: SCORE_WEIGHTS must contain all three identity weight keys."""
        expected_keys = [
            "identity_kerberos_weak_etype_ratio",
            "identity_saml_weak_signing_ratio",
            "identity_dnssec_weak_algo_ratio",
        ]
        for key in expected_keys:
            self.assertIn(
                key,
                SCORE_WEIGHTS,
                f"SCORE_WEIGHTS missing required identity key: {key}",
            )

    def test_weak_kerberos_lowers_score(self) -> None:
        """IDENT-01: Evidence with weak Kerberos etypes scores lower than safe evidence."""
        safe = _base_evidence_with_identity()
        risky = _base_evidence_with_identity(identity_weak_etype_count=3)

        safe_score = compute_readiness_score(safe)["score"]
        risky_score = compute_readiness_score(risky)["score"]
        self.assertLess(
            risky_score,
            safe_score,
            f"Risky score ({risky_score}) should be < safe score ({safe_score})",
        )

    def test_all_three_weak_lowers_score(self) -> None:
        """IDENT-01: Evidence with all three identity weaknesses scores lower."""
        safe = _base_evidence_with_identity()
        risky = _base_evidence_with_identity(
            identity_weak_etype_count=2,
            saml_weak_signing_count=2,
            dnssec_weak_algo_count=2,
        )

        safe_score = compute_readiness_score(safe)["score"]
        risky_score = compute_readiness_score(risky)["score"]
        self.assertLess(
            risky_score,
            safe_score,
            f"Risky score ({risky_score}) should be < safe score ({safe_score})",
        )


# ===========================================================================
# Class 3: IDENT-02 Model Tests (PASS after Task 2 adds IdentityFinding)
# ===========================================================================

class IdentityFindingModelTests(unittest.TestCase):
    """Tests for the IdentityFinding Pydantic model and ScanLatestResponse contract.

    These become GREEN after Task 2 (schemas.py + api.ts updates).
    """

    def test_identity_finding_importable(self) -> None:
        """IDENT-02: IdentityFinding can be imported from schemas."""
        self.assertIsNotNone(IdentityFinding, "IdentityFinding import should not be None")

    def test_identity_finding_fields(self) -> None:
        """IDENT-02: IdentityFinding accepts all required fields including algorithm."""
        finding = IdentityFinding(
            host="dc.example.com",
            port=88,
            severity="HIGH",
            title="Weak Kerberos etype: rc4-hmac",
            protocol="KERBEROS",
            algorithm="rc4-hmac",
        )
        self.assertEqual(finding.host, "dc.example.com")
        self.assertEqual(finding.port, 88)
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(finding.title, "Weak Kerberos etype: rc4-hmac")
        self.assertEqual(finding.protocol, "KERBEROS")
        self.assertEqual(finding.algorithm, "rc4-hmac")

    def test_scan_latest_response_has_identity_findings(self) -> None:
        """IDENT-02: ScanLatestResponse accepts identity_findings list."""
        from quirk.dashboard.api.schemas import (
            ScanMeta,
            ScoreData,
            SubScores,
            ConfidenceData,
            RoadmapData,
        )

        finding = IdentityFinding(
            host="idp.example.com",
            port=443,
            severity="CRITICAL",
            title="SAML RSA-1024 signing cert",
            protocol="SAML",
            algorithm="RSA-1024",
        )

        response = ScanLatestResponse(
            meta=ScanMeta(
                scan_id="2026-01-01T00:00:00",
                total_endpoints=1,
                total_findings=1,
            ),
            score=ScoreData(
                score=75,
                rating="GOOD",
                subscores=SubScores(
                    hygiene=25,
                    modern_tls=25,
                    identity_trust=25,
                    agility_signals=0,
                ),
                drivers=[],
            ),
            confidence=ConfidenceData(
                confidence_score=80,
                confidence_rating="HIGH",
            ),
            findings=[],
            certificates=[],
            cbom_components=[],
            roadmap=RoadmapData(nodes=[], edges=[]),
            identity_findings=[finding],
        )

        self.assertEqual(len(response.identity_findings), 1)
        self.assertEqual(response.identity_findings[0].algorithm, "RSA-1024")
        self.assertEqual(response.identity_findings[0].protocol, "SAML")


# ===========================================================================
# Class 4: IDENT-03 + IDENT-04 Derivation Tests (SKIP — function not yet present)
# ===========================================================================

@unittest.skipUnless(_HAS_DERIVE, "awaiting _derive_identity_findings in Plan 02")
class IdentityDerivationTests(unittest.TestCase):
    """RED/SKIP tests for _derive_identity_findings in scan.py.

    All tests in this class are skipped until Plan 02 implements the function.
    Once the function exists, these tests drive the GREEN implementation.
    """

    def test_kerberos_finding_derived(self) -> None:
        """IDENT-03: RC4-HMAC Kerberos endpoint produces IdentityFinding with correct fields."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        results = _derive_identity_findings([_kerberos_rc4_ep()])
        self.assertEqual(len(results), 1, "Expected 1 finding for RC4-HMAC endpoint")
        finding = results[0]
        self.assertEqual(finding.algorithm, "rc4-hmac")
        self.assertEqual(finding.protocol, "KERBEROS")

    def test_saml_finding_derived(self) -> None:
        """IDENT-03: Weak SAML endpoint produces IdentityFinding with SAML protocol."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        results = _derive_identity_findings([_saml_weak_ep()])
        self.assertGreater(len(results), 0, "Expected findings for RSA-1024 SAML endpoint")
        protocols = {f.protocol for f in results}
        self.assertIn("SAML", protocols)

    def test_dnssec_finding_derived(self) -> None:
        """IDENT-03: RSASHA1 DNSSEC endpoint produces IdentityFinding with correct fields."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        results = _derive_identity_findings([_dnssec_rsasha1_ep()])
        self.assertEqual(len(results), 1, "Expected 1 finding for RSASHA1 DNSSEC endpoint")
        finding = results[0]
        self.assertEqual(finding.algorithm, "RSASHA1")
        self.assertEqual(finding.protocol, "DNSSEC")

    def test_identity_findings_have_required_fields(self) -> None:
        """IDENT-03: Each derived finding has all required non-empty fields."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        endpoints = [_kerberos_rc4_ep(), _saml_weak_ep(), _dnssec_rsasha1_ep()]
        results = _derive_identity_findings(endpoints)
        self.assertGreater(len(results), 0, "Expected at least one finding")
        for finding in results:
            self.assertTrue(finding.host, "host must be non-empty")
            self.assertGreater(finding.port, 0, "port must be > 0")
            self.assertTrue(finding.severity, "severity must be non-empty")
            self.assertTrue(finding.title, "title must be non-empty")
            self.assertTrue(finding.protocol, "protocol must be non-empty")
            self.assertTrue(finding.algorithm, "algorithm must be non-empty")

    def test_safe_endpoints_produce_no_findings(self) -> None:
        """IDENT-03: Quantum-safe identity endpoints produce no findings."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        endpoints = [_kerberos_aes256_ep(), _saml_safe_ep(), _dnssec_ecdsa_ep()]
        results = _derive_identity_findings(endpoints)
        self.assertEqual(
            len(results),
            0,
            f"Expected 0 findings for safe endpoints, got {len(results)}",
        )


# ===========================================================================
# Class 5: ISSUE-3 Scan-Window Regression Test
# ===========================================================================

class Issue3ScanWindowRegressionTest(unittest.TestCase):
    """ISSUE-3: Verify GET /api/scan/latest returns all 3 identity protocols
    even when Kerberos endpoints have a later scanned_at than DNSSEC/SAML.

    This test simulates the production failure mode:
    - DNSSEC + SAML endpoints stamped at T (early)
    - Kerberos endpoints stamped at T+30s (late, simulating timeout delay)
    - GET /api/scan/latest should return findings from all 3 protocols

    Before the fix: scan-window query anchors on MAX(scanned_at) = T+30s,
    and the 1-second window [T+30, T+31) excludes DNSSEC/SAML at T.
    """

    def test_issue3_scan_window_returns_all_identity_protocols(self):
        """ISSUE-3 regression: all 3 identity protocols visible in /api/scan/latest."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from quirk.dashboard.api.app import create_app
            from quirk.dashboard.api.deps import get_db
            from quirk.models import Base, CryptoEndpoint
            from fastapi.testclient import TestClient
            from datetime import datetime, timedelta
        except ImportError:
            self.skipTest("Dashboard dependencies not available")

        # In-memory SQLite (mirrors conftest.py pattern)
        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # Timestamps simulating the ISSUE-3 failure mode
        early_ts = datetime(2026, 1, 15, 12, 0, 0)      # DNSSEC + SAML
        late_ts = datetime(2026, 1, 15, 12, 0, 30)       # Kerberos (30s later)

        # Insert endpoints into DB
        db = TestingSession()
        try:
            # DNSSEC endpoint (early)
            db.add(CryptoEndpoint(
                host="example.com",
                port=53,
                protocol="DNSSEC",
                cert_pubkey_alg="RSASHA1",
                service_detail="dnskey:tag=12345:role=ZSK",
                scanned_at=early_ts,
            ))
            # SAML endpoint (early)
            db.add(CryptoEndpoint(
                host="idp.example.com",
                port=443,
                protocol="SAML",
                cert_pubkey_alg="RSA",
                cert_pubkey_size=1024,
                service_detail="https://idp.example.com|use=signing|serial=ABC",
                scanned_at=early_ts,
            ))
            # Kerberos endpoint (late — simulates timeout delay)
            db.add(CryptoEndpoint(
                host="dc.example.com",
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg="rc4-hmac",
                service_detail="etype:23:rc4-hmac:HIGH",
                scanned_at=late_ts,
            ))
            db.commit()
        finally:
            db.close()

        # Call the API
        resp = client.get("/api/scan/latest")
        self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}: {resp.text}")

        data = resp.json()

        # Extract protocols from identity_findings
        identity_protocols = {f["protocol"] for f in data.get("identity_findings", [])}

        # Assert all 3 protocols present — this is the core ISSUE-3 assertion
        self.assertIn("KERBEROS", identity_protocols,
                       f"KERBEROS missing from identity_findings protocols: {identity_protocols}")
        self.assertIn("SAML", identity_protocols,
                       f"SAML missing from identity_findings protocols: {identity_protocols}")
        self.assertIn("DNSSEC", identity_protocols,
                       f"DNSSEC missing from identity_findings protocols: {identity_protocols}")

    def _make_client_and_session(self):
        """Return (TestClient, TestingSession factory) backed by a fresh in-memory SQLite DB."""
        try:
            import uuid
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from quirk.dashboard.api.app import create_app
            from quirk.dashboard.api.deps import get_db
            from quirk.models import Base
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("Dashboard dependencies not available")

        # Use a unique named shared-cache URI per test so the app's get_db override
        # and the test's direct session share the same in-memory SQLite instance.
        db_name = f"test_{uuid.uuid4().hex}"
        engine = create_engine(
            f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        return client, TestingSession

    def test_saml_visible_with_earlier_dnssec(self):
        """Bracket edge case: DNSSEC at T-60s and SAML at T are both visible in identity_findings."""
        from quirk.models import CryptoEndpoint
        from datetime import datetime

        client, TestingSession = self._make_client_and_session()

        early_ts = datetime(2026, 1, 15, 12, 0, 0)   # DNSSEC — 60s before SAML
        saml_ts = datetime(2026, 1, 15, 12, 1, 0)    # SAML — MAX(scanned_at)

        db = TestingSession()
        try:
            db.add(CryptoEndpoint(
                host="example.com",
                port=53,
                protocol="DNSSEC",
                cert_pubkey_alg="RSASHA1",
                service_detail="dnskey:tag=12345:role=ZSK",
                scanned_at=early_ts,
            ))
            db.add(CryptoEndpoint(
                host="idp.example.com",
                port=443,
                protocol="SAML",
                cert_pubkey_alg="RSA",
                cert_pubkey_size=1024,
                service_detail="https://idp.example.com|use=signing|serial=ABC",
                scanned_at=saml_ts,
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/scan/latest")
        self.assertEqual(resp.status_code, 200,
                         f"Expected 200, got {resp.status_code}: {resp.text}")

        protocols = {f["protocol"] for f in resp.json().get("identity_findings", [])}
        self.assertIn("SAML", protocols,
                      f"SAML missing from identity_findings protocols: {protocols}")
        self.assertIn("DNSSEC", protocols,
                      f"DNSSEC missing from identity_findings protocols: {protocols}")

    def test_explicit_scan_id_uses_exact_second(self):
        """Guard: explicit ?scan_id= branch was NOT widened — it still uses 1-second window."""
        from quirk.models import CryptoEndpoint
        from datetime import datetime

        client, TestingSession = self._make_client_and_session()

        ts_a = datetime(2026, 1, 15, 12, 0, 0)   # older scan
        ts_b = datetime(2026, 1, 15, 12, 5, 0)   # newer scan, 5 minutes later

        db = TestingSession()
        try:
            db.add(CryptoEndpoint(
                host="dc-old.example.com",
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg="rc4-hmac",
                service_detail="etype:23:rc4-hmac:HIGH",
                scanned_at=ts_a,
            ))
            db.add(CryptoEndpoint(
                host="dc-new.example.com",
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg="rc4-hmac",
                service_detail="etype:23:rc4-hmac:HIGH",
                scanned_at=ts_b,
            ))
            db.commit()
        finally:
            db.close()

        # Use ts_a's ISO string as the explicit scan_id
        scan_id = ts_a.isoformat()
        resp = client.get(f"/api/scan/latest?scan_id={scan_id}")
        self.assertEqual(resp.status_code, 200,
                         f"Expected 200, got {resp.status_code}: {resp.text}")

        hosts = {f["host"] for f in resp.json().get("identity_findings", [])}
        self.assertIn("dc-old.example.com", hosts,
                      f"dc-old.example.com missing from identity_findings hosts: {hosts}")
        self.assertNotIn("dc-new.example.com", hosts,
                         f"dc-new.example.com should NOT be in identity_findings: {hosts}")


if __name__ == "__main__":
    unittest.main()
