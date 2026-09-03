"""Phase 181 Plan 05 (SURF-02) — writer.py's burndown loader and closure-refusal
statement, computed exactly once and reaching `ExecContent`.

Two units under test, both in `quirk/reports/writer.py`:

  - `_closure_refusal_from_counters(closure_counters)` — builds the refusal
    disclosure from the pipeline's ALREADY-COMPUTED `closure_counters` dict.
    It never calls `scans_are_comparable` or `compute_closure` — a second
    comparability evaluation on this side of the boundary could diverge from
    the one the pipeline already computed, which is the defect class this
    milestone has corrected repeatedly (T-181-12).

  - `_load_closure_burndown(db_path, scan_run_id)` — one non-fatal read of
    `compute_burndown()`'s per-deadline bucket aggregate, unmodified.

Plus an end-to-end `write_reports()` integration test against a real SQLite
database (mirrors `tests/test_cbom_vex.py::TestEndToEnd`'s pattern) — this
closes the integration gap where a helper silently returns empty in
production while direct-call unit tests pass green (Pitfall 2, named in that
file's own docstring).
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.models import CryptoEndpoint, RemediationItemFingerprint

CURRENT_SCAN_RUN_ID = "2026-09-02T00:00:00Z"


# ---------------------------------------------------------------------------
# Task 2 — _closure_refusal_from_counters
# ---------------------------------------------------------------------------


class TestClosureRefusalFromCounters:
    def test_none_returns_empty(self):
        from quirk.reports.writer import _closure_refusal_from_counters

        assert _closure_refusal_from_counters(None) == {}

    def test_empty_dict_returns_empty(self):
        from quirk.reports.writer import _closure_refusal_from_counters

        assert _closure_refusal_from_counters({}) == {}

    def test_per_item_refusal_counter_alone_returns_empty(self):
        """`refused_probe` and its siblings are per-item and already resolve to
        `not_observed` — they are NOT a scan-level refusal."""
        from quirk.reports.writer import _closure_refusal_from_counters

        assert _closure_refusal_from_counters({"refused_probe": 7}) == {}

    @pytest.mark.parametrize(
        "reason_key,expected_axis_fragment",
        [
            ("refused_no_prior", "no comparable prior scan"),
            ("refused_missing_signature", "scope signature is missing"),
            ("refused_signature_version_gap", "scope signature version differs"),
            ("refused_missing_target_set_digest", "target-set digest is absent"),
            ("refused_scope_mismatch", "scan scope differs"),
        ],
    )
    def test_each_scan_level_key_yields_a_distinct_nonempty_axis(
        self, reason_key, expected_axis_fragment
    ):
        from quirk.reports.writer import _closure_refusal_from_counters

        result = _closure_refusal_from_counters({reason_key: 1})

        assert result["refused"] is True
        assert result["reason_key"] == reason_key
        assert result["axis"], f"{reason_key} produced an empty axis phrase"
        assert expected_axis_fragment in result["axis"]
        assert result["statement"].startswith("Closure not computed: ")
        assert result["statement"].endswith(".")
        assert result["axis"] in result["statement"]

    def test_all_five_axes_are_distinct(self):
        """Each of the five reasons must produce a DISTINCT phrase — a shared
        generic phrase would defeat the purpose of naming the differing axis."""
        from quirk.reports.writer import _REFUSAL_AXIS, _SCAN_LEVEL_REFUSAL_KEYS

        axes = [_REFUSAL_AXIS[key] for key in _SCAN_LEVEL_REFUSAL_KEYS]
        assert len(axes) == len(set(axes)) == 5

    def test_first_non_zero_key_in_declared_order_wins(self):
        """When multiple scan-level counters are non-zero (should not happen in
        practice — comparability fails at the FIRST check — but the helper must
        still be deterministic), the first key in `_SCAN_LEVEL_REFUSAL_KEYS`
        order resolves."""
        from quirk.reports.writer import _closure_refusal_from_counters

        result = _closure_refusal_from_counters(
            {"refused_scope_mismatch": 1, "refused_no_prior": 1}
        )
        assert result["reason_key"] == "refused_no_prior"


# ---------------------------------------------------------------------------
# Task 2 — _load_closure_burndown
# ---------------------------------------------------------------------------


class TestLoadClosureBurndown:
    def test_none_db_path_and_scan_run_id_returns_empty(self):
        from quirk.reports.writer import _load_closure_burndown

        assert _load_closure_burndown(None, None) == {}

    def test_none_db_path_only_returns_empty(self):
        from quirk.reports.writer import _load_closure_burndown

        assert _load_closure_burndown(None, CURRENT_SCAN_RUN_ID) == {}

    def test_none_scan_run_id_only_returns_empty(self, tmp_path):
        from quirk.reports.writer import _load_closure_burndown

        assert _load_closure_burndown(str(tmp_path / "quirk.db"), None) == {}

    def test_missing_database_file_returns_empty_never_raises(self, tmp_path):
        from quirk.reports.writer import _load_closure_burndown

        result = _load_closure_burndown(
            str(tmp_path / "does-not-exist.db"), CURRENT_SCAN_RUN_ID
        )
        assert result == {}

    def test_real_database_returns_all_three_buckets_including_unmapped(self, tmp_path):
        from quirk.db import get_session, init_db
        from quirk.reports.writer import _load_closure_burndown

        db_path = str(tmp_path / "quirk.db")
        init_db(db_path)
        with get_session(db_path) as session:
            session.add(
                CryptoEndpoint(
                    host="example.com",
                    port=443,
                    protocol="TLS",
                    cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                    cert_sig_alg="sha256WithRSAEncryption",
                    cert_pubkey_alg="RSA",
                    scan_run_id=CURRENT_SCAN_RUN_ID,
                )
            )
            session.add(
                RemediationItemFingerprint(
                    remediation_item_id=None,
                    slug="weak-tls-cipher",
                    scan_run_id=CURRENT_SCAN_RUN_ID,
                    finding_fingerprint="fp-0001",
                    host="example.com",
                    port=443,
                    finding_title="Weak TLS cipher suite in use",
                    state="open",
                    observed_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        result = _load_closure_burndown(db_path, CURRENT_SCAN_RUN_ID)

        assert set(result.keys()) == {"key_establishment", "digital_signature", "unmapped"}
        # D-36: no top-level scalar anywhere in the return value.
        for bucket in result.values():
            assert isinstance(bucket, dict)


# ---------------------------------------------------------------------------
# End-to-end: write_reports() produces mutually exclusive burndown /
# closure_refusal payloads on ExecContent, for a refused vs. a computed scan.
# Mirrors tests/test_cbom_vex.py::TestEndToEnd's pattern.
# ---------------------------------------------------------------------------


def _e2e_endpoint(scan_run_id, host="example.com", port=443):
    return CryptoEndpoint(
        host=host,
        port=port,
        protocol="TLS",
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com",
        cert_issuer="CN=Example CA",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        scan_run_id=scan_run_id,
    )


def _e2e_cfg(tmp_path, db_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path), db_path=db_path),
        assessment=SimpleNamespace(
            name="Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )


def _stub_evidence(endpoints, findings):
    return {
        "total_endpoints": len(endpoints),
        "tls_endpoints": len(endpoints),
        "ssh_endpoints": 0,
        "http_endpoints": 0,
        "expired_certs": 0,
        "expiring_soon_certs": 0,
        "weak_ciphers": 0,
        "vulns_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "findings_count": len(findings or []),
        "scan_error_rate": 0.0,
    }


def _stub_score(evidence, **kwargs):
    return {
        "score": 55,
        "subscores": {"inventory": 50, "cipher": 50, "certificate": 50, "protocol": 50},
        "drivers": [{"reason": "Test driver", "impact": -5}],
    }


def _stub_confidence(evidence):
    return {"confidence_score": 70, "factor_breakdown": {}}


def _stub_roadmap(evidence, score):
    return {"items": [{"title": "Test Action", "why": "Because testing", "timeframe": "NOW"}]}


def _stub_waves(findings):
    return {"Wave 1": [], "Wave 2": [], "Wave 3": []}


def _seed_burndown_db(db_path):
    from quirk.db import get_session, init_db

    init_db(db_path)
    with get_session(db_path) as session:
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug="weak-tls-cipher",
                scan_run_id=CURRENT_SCAN_RUN_ID,
                finding_fingerprint="fp-0001",
                host="example.com",
                port=443,
                finding_title="Weak TLS cipher suite in use",
                state="open",
                observed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()


def _run_write_reports(cfg, endpoints, findings=None, closure_counters=None):
    from quirk.reports.writer import write_reports

    with (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch("quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap),
        patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence),
        patch("quirk.reports.writer.compute_readiness_score", side_effect=_stub_score),
        patch("quirk.reports.writer.build_evidence_summary", side_effect=_stub_evidence),
    ):
        return write_reports(cfg, endpoints, findings or [], closure_counters=closure_counters)


class TestWriteReportsEndToEnd:
    def test_computed_scan_populates_burndown_and_empty_refusal(self, tmp_path, capsys):
        db_path = str(tmp_path / "quirk.db")
        _seed_burndown_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        captured = {}
        real_build_exec_content = None
        from quirk.reports import content_model as _content_model

        real_build_exec_content = _content_model.build_exec_content

        def _spy_build_exec_content(*args, **kwargs):
            exec_content = real_build_exec_content(*args, **kwargs)
            captured["exec_content"] = exec_content
            return exec_content

        with patch(
            "quirk.reports.writer.build_exec_content", side_effect=_spy_build_exec_content
        ):
            _run_write_reports(cfg, endpoints, closure_counters=None)

        exec_content = captured["exec_content"]
        assert exec_content.closure_refusal == {}
        assert exec_content.burndown != {}
        assert set(exec_content.burndown.keys()) == {
            "key_establishment",
            "digital_signature",
            "unmapped",
        }

    def test_refused_scan_populates_refusal_and_empty_burndown(self, tmp_path):
        db_path = str(tmp_path / "quirk.db")
        _seed_burndown_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        captured = {}
        from quirk.reports import content_model as _content_model

        real_build_exec_content = _content_model.build_exec_content

        def _spy_build_exec_content(*args, **kwargs):
            exec_content = real_build_exec_content(*args, **kwargs)
            captured["exec_content"] = exec_content
            return exec_content

        with patch(
            "quirk.reports.writer.build_exec_content", side_effect=_spy_build_exec_content
        ):
            _run_write_reports(
                cfg,
                endpoints,
                closure_counters={"refused_scope_mismatch": 1},
            )

        exec_content = captured["exec_content"]
        assert exec_content.burndown == {}
        assert exec_content.closure_refusal["refused"] is True
        assert exec_content.closure_refusal["reason_key"] == "refused_scope_mismatch"
        assert exec_content.closure_refusal["statement"].startswith(
            "Closure not computed: "
        )

    def test_write_reports_still_produces_output_files(self, tmp_path):
        """Sanity: wiring the new payloads in did not break the existing
        report-generation pipeline."""
        db_path = str(tmp_path / "quirk.db")
        _seed_burndown_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        _run_write_reports(cfg, endpoints)

        md_files = glob.glob(os.path.join(str(tmp_path), "technical-findings-*.md"))
        assert md_files, "write_reports did not emit the CLI technical markdown report"
