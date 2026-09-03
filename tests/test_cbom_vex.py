"""Phase 181 Plan 01 (SURF-01) — executable specification for the CBOM VEX surface.

Written BEFORE any builder code exists. `quirk/cbom/builder.py` currently emits
ZERO `vulnerabilities` — Plan 181-03 implements `_VEX_STATE_MAP` and
`_make_vex_entry` against the locked contract asserted here. Every test in this
module is expected to fail RED today (ImportError / AttributeError / TypeError
naming `_make_vex_entry` or `_VEX_STATE_MAP`), proving the specification exists
before the implementation that could violate it.

T-181-01 is the single most consequential assertion in this milestone: a
`not_observed` remediation item means "we did not verify" — it must map to
`ImpactAnalysisState.IN_TRIAGE` and NEVER to `ImpactAnalysisState.NOT_AFFECTED`.
`NOT_AFFECTED` asserts safety that was never established. Mapping one to the
other would publish an unverified safety claim inside a machine-readable
artifact that a client may feed straight into their own vulnerability-management
tooling — the exact overclaiming this entire milestone exists to prevent, at
the one point where it becomes externally consumable. A future reader must not
be able to "fix" a failing test here by relaxing this boundary; the module
docstring says so explicitly, in prose, so the intent survives any refactor.

Companion assertions locked by `.planning/phases/181-surfacing/181-CONTEXT.md`:
  - `closed` -> RESOLVED; `open` and `resurfaced` -> EXPLOITABLE.
  - `resurfaced` is distinguished from `open` via `VulnerabilityAnalysis.detail`
    plus `first_issued`/`last_updated`, never via a different enum state.
  - One VEX entry per REMEDIATION ITEM, never per constituent fingerprint.
  - Refused scans and the `unmapped` bucket emit NOTHING — an entry there would
    imply an assessment we explicitly declined to perform.
  - No fabricated CVE id / source / ratings. The CycloneDX 1.6 JSON schema's
    `definitions.vulnerability` has no `"required"` key, so a minimal, honest
    entry is fully legal and nothing needs to be invented to satisfy it.
  - `affects` stays empty and `id` is the slug — no `BomTarget`, so no estate
    identifier (host/port) ever enters the published artifact.

Mirrors `tests/test_vendor_trend_render_sections.py`'s module-docstring +
dict-factory idiom (Phase 161 HWLC-19 precedent).
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import pytest


def _item(**overrides) -> dict:
    item = {
        "slug": "plaintext-http-exposure",
        "title": "Eliminate plaintext HTTP exposure",
        "state": "open",
        "first_seen": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "last_updated": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "detail": None,
    }
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# Task 1 — T-181-01: not_observed -> IN_TRIAGE, never NOT_AFFECTED
# ---------------------------------------------------------------------------

def test_not_observed_maps_to_in_triage():
    from quirk.cbom.builder import _make_vex_entry
    from cyclonedx.model.impact_analysis import ImpactAnalysisState

    entry = _make_vex_entry(_item(state="not_observed"))

    assert entry.analysis.state is ImpactAnalysisState.IN_TRIAGE, (
        "T-181-01: a not_observed remediation item means 'we did not verify' "
        "and must map to IN_TRIAGE. Mapping it to NOT_AFFECTED would publish "
        "an unverified safety claim inside a machine-readable artifact."
    )
    assert entry.analysis.state is not ImpactAnalysisState.NOT_AFFECTED, (
        "T-181-01: not_observed must never resolve to NOT_AFFECTED — that is "
        "an unverified safety claim, and not_observed exists precisely to "
        "avoid making it."
    )


def test_not_affected_is_absent_from_the_entire_state_map():
    from quirk.cbom.builder import _VEX_STATE_MAP
    from cyclonedx.model.impact_analysis import ImpactAnalysisState

    assert ImpactAnalysisState.NOT_AFFECTED not in set(_VEX_STATE_MAP.values()), (
        "T-181-01: ImpactAnalysisState.NOT_AFFECTED must not appear as a value "
        "for ANY key in _VEX_STATE_MAP, not just 'not_observed' — this is an "
        "unverified safety claim and no future closure state may be routed to "
        "it, ever."
    )


def test_builder_source_never_names_not_affected():
    """Comment-stripped source scan — a third, independent gate on the same
    invariant. A comment explaining the ban must not itself trip the ban
    (grep-gate hygiene), so `#`-prefixed lines are filtered before the check."""
    import quirk.cbom.builder as builder_module

    source = pathlib.Path(builder_module.__file__).read_text()
    stripped = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )

    assert "NOT_AFFECTED" not in stripped, (
        "T-181-01: quirk/cbom/builder.py must never name NOT_AFFECTED in live "
        "source — this is an unverified safety claim that must not enter the "
        "published VEX surface, by construction, not by review."
    )


# ---------------------------------------------------------------------------
# Task 2 — state mapping, item-level cardinality, resurfaced narrative
# ---------------------------------------------------------------------------

class TestStateMapping:
    """The three non-not_observed rows of the locked _VEX_STATE_MAP table."""

    @pytest.mark.parametrize(
        "state, expected_attr",
        [
            ("closed", "RESOLVED"),
            ("open", "EXPLOITABLE"),
            ("resurfaced", "EXPLOITABLE"),
        ],
    )
    def test_state_maps_to_expected_impact_analysis_state(self, state, expected_attr):
        from quirk.cbom.builder import _make_vex_entry
        from cyclonedx.model.impact_analysis import ImpactAnalysisState

        entry = _make_vex_entry(_item(state=state))
        assert entry.analysis.state is getattr(ImpactAnalysisState, expected_attr)


def test_resurfaced_retains_narrative_and_timestamps():
    from quirk.cbom.builder import _make_vex_entry

    detail = "Closed 2026-08-15; detected again 2026-09-01"
    first_seen = datetime(2026, 8, 15, tzinfo=timezone.utc)
    last_updated = datetime(2026, 9, 1, tzinfo=timezone.utc)

    resurfaced_entry = _make_vex_entry(
        _item(
            state="resurfaced",
            detail=detail,
            first_seen=first_seen,
            last_updated=last_updated,
        )
    )
    open_entry = _make_vex_entry(_item(state="open"))

    assert resurfaced_entry.analysis.detail == detail
    assert resurfaced_entry.analysis.first_issued == first_seen
    assert resurfaced_entry.analysis.last_updated == last_updated

    # T-181-02: resurfaced and open collapse to the SAME ImpactAnalysisState —
    # CycloneDX has no dedicated resurfaced state. The regression history
    # (that this item came back rather than never having been fixed) lives
    # in `detail`/timestamps, not in the enum. This is the locked decision,
    # not an accident, and this assertion exists to prove it stays that way.
    assert resurfaced_entry.analysis.state == open_entry.analysis.state


def test_one_entry_per_remediation_item_not_per_fingerprint():
    from quirk.cbom.builder import build_cbom

    items = [
        _item(slug="plaintext-http-exposure", state="open"),
        _item(slug="weak-tls-cipher-suite", state="closed"),
        _item(slug="ssh-host-key-rsa1024", state="not_observed"),
    ]

    bom = build_cbom([], remediation_items=items)
    vulns = list(bom.vulnerabilities)

    # A per-fingerprint implementation would iterate RemediationItemFingerprint
    # rows instead of RemediationItem rows and produce thousands of entries,
    # nearly all IN_TRIAGE. This cardinality assertion exists to catch exactly
    # that regression — one entry per ITEM, never per constituent finding.
    assert len(vulns) == 3
    assert {v.id for v in vulns} == {item["slug"] for item in items}


def test_no_remediation_items_leaves_bom_unchanged():
    """Byte-for-byte the pre-Phase-181 behavior: no remediation_items argument
    means no vulnerabilities on the BOM, so existing CBOM golden fixtures
    (which never touch `vulnerabilities`) stay valid without regeneration."""
    from quirk.cbom.builder import build_cbom

    bom = build_cbom([])
    assert list(bom.vulnerabilities) == []


# ---------------------------------------------------------------------------
# Task 3 — silence for refused/unmapped, and no fabricated identity
# ---------------------------------------------------------------------------

class TestSilence:
    """An entry for a refused-scan or unmapped item would imply we assessed
    something we explicitly declined to compare. Silence is the correct,
    honest output — not a fabricated IN_TRIAGE placeholder."""

    @pytest.mark.parametrize("state", ["unmapped", None, "totally-unknown-state"])
    def test_unmapped_or_unknown_state_returns_none(self, state):
        from quirk.cbom.builder import _make_vex_entry

        result = _make_vex_entry(_item(state=state))
        assert result is None, (
            "An entry for an unmapped or unknown closure state would imply we "
            "assessed items we explicitly declined to compare — the caller "
            "must receive None and emit nothing."
        )


def test_refused_scan_emits_no_vulnerabilities():
    """writer.py (Plan 181-03) owns the refusal decision and hands build_cbom
    an empty remediation_items list for a refused scan — see 181-CONTEXT.md:
    'Emit NOTHING for refused scans or the unmapped bucket.' This test asserts
    the builder honors an empty handover rather than inventing entries; it
    does not assert anything about writer.py's own refusal logic."""
    from quirk.cbom.builder import build_cbom

    bom = build_cbom([], remediation_items=[])
    assert list(bom.vulnerabilities) == []


def test_entry_fabricates_no_cve_identity():
    from quirk.cbom.builder import _make_vex_entry

    item = _item(state="open")
    entry = _make_vex_entry(item)

    # The CycloneDX 1.6 JSON schema's definitions.vulnerability carries no
    # "required" key (verified against the schema itself, not merely the
    # Python constructor) — a minimal, honest entry is fully legal, so
    # nothing needs to be invented (no CVE id, no source, no ratings) to
    # satisfy the schema.
    assert entry.id == item["slug"]
    assert not entry.id.upper().startswith("CVE-")
    assert entry.source is None
    assert len(list(entry.ratings)) == 0
    assert len(list(entry.affects)) == 0


def test_entry_carries_no_host_or_port():
    from quirk.cbom.builder import _make_vex_entry

    item = _item(state="open")
    entry = _make_vex_entry(item)

    # "203.0.113." and ":443" are deliberately absent from the item dict —
    # assert positively instead that no estate identifier surface exists:
    # affects is empty (no BomTarget/bom_ref), and the only free-text field
    # on the entry is a title the consultant already publishes elsewhere.
    assert list(entry.affects) == []
    assert entry.description == item["title"]


# ---------------------------------------------------------------------------
# TestEndToEnd — Plan 181-03 Task 3: real database, real write_reports,
# real CycloneDX 1.6 schema validation. Closes Pitfall 2: a helper that
# silently returns empty in production while unit tests calling it with
# explicit arguments pass green.
# ---------------------------------------------------------------------------

import glob
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

from quirk.models import CryptoEndpoint, RemediationItem

CURRENT_SCAN_RUN_ID = "2026-09-02T00:00:00Z"
OTHER_SCAN_RUN_ID = "2026-08-01T00:00:00Z"


def _e2e_endpoint(scan_run_id, host="example.com", port=443):
    return CryptoEndpoint(
        host=host, port=port, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
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
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
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


def _seed_db(db_path):
    from quirk.db import get_session, init_db

    init_db(db_path)
    with get_session(db_path) as session:
        session.add_all(
            [
                RemediationItem(
                    slug="plaintext-http-exposure",
                    scan_run_id=CURRENT_SCAN_RUN_ID,
                    title="Eliminate plaintext HTTP exposure",
                    state="open",
                    created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                ),
                RemediationItem(
                    slug="weak-tls-cipher-suite",
                    scan_run_id=CURRENT_SCAN_RUN_ID,
                    title="Replace weak TLS cipher suite",
                    state="closed",
                    created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                ),
                RemediationItem(
                    slug="ssh-host-key-rsa1024",
                    scan_run_id=CURRENT_SCAN_RUN_ID,
                    title="Rotate weak SSH host key",
                    state="not_observed",
                    created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                ),
                # Different scan — must not leak into the current CBOM.
                RemediationItem(
                    slug="other-scan-item",
                    scan_run_id=OTHER_SCAN_RUN_ID,
                    title="Item belonging to an earlier scan",
                    state="open",
                    created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()


def _patched_write_reports():
    return (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch("quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap),
        patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence),
        patch("quirk.reports.writer.compute_readiness_score", side_effect=_stub_score),
        patch("quirk.reports.writer.build_evidence_summary", side_effect=_stub_evidence),
    )


def _run_write_reports(cfg, endpoints, findings=None, closure_counters=None):
    from quirk.reports.writer import write_reports

    patchers = _patched_write_reports()
    with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4]:
        write_reports(
            cfg, endpoints, findings or [], closure_counters=closure_counters
        )


def _latest_cbom_json(tmp_path):
    json_files = sorted(glob.glob(os.path.join(str(tmp_path), "cbom-*.cdx.json")))
    assert json_files, f"no cbom-*.cdx.json produced in {tmp_path}"
    return json_files[-1]


class TestEndToEnd:
    """Real SQLite database, real write_reports(), real CycloneDX 1.6 schema
    validation — the integration gap Pitfall 2 names: a helper that silently
    returns empty in production while unit tests calling it with explicit
    arguments pass green."""

    def test_current_scan_items_emitted_other_scan_item_absent(self, tmp_path):
        db_path = str(tmp_path / "quirk.db")
        _seed_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        _run_write_reports(cfg, endpoints)

        cbom_json = json.loads(pathlib.Path(_latest_cbom_json(tmp_path)).read_text())
        vulns = cbom_json.get("vulnerabilities", [])

        assert len(vulns) == 3, f"expected 3 current-scan items, got: {vulns}"
        slugs = {v["id"] for v in vulns}
        assert slugs == {
            "plaintext-http-exposure",
            "weak-tls-cipher-suite",
            "ssh-host-key-rsa1024",
        }
        # The scan-scoping decision, made explicit rather than assumed.
        assert "other-scan-item" not in slugs

        not_observed_entry = next(
            v for v in vulns if v["id"] == "ssh-host-key-rsa1024"
        )
        assert not_observed_entry["analysis"]["state"] == "in_triage"

        raw_text = pathlib.Path(_latest_cbom_json(tmp_path)).read_text()
        assert "not_affected" not in raw_text

    def test_refused_scan_produces_no_vulnerabilities_key_end_to_end(self, tmp_path):
        db_path = str(tmp_path / "quirk.db")
        _seed_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        _run_write_reports(
            cfg, endpoints, closure_counters={"refused_scope_mismatch": 1}
        )

        cbom_json = json.loads(pathlib.Path(_latest_cbom_json(tmp_path)).read_text())
        assert "vulnerabilities" not in cbom_json

    def test_emitted_cbom_validates_against_1_6_schema(self, tmp_path):
        from cyclonedx.schema import SchemaVersion
        from cyclonedx.validation.json import JsonStrictValidator

        db_path = str(tmp_path / "quirk.db")
        _seed_db(db_path)
        cfg = _e2e_cfg(tmp_path, db_path)
        endpoints = [_e2e_endpoint(CURRENT_SCAN_RUN_ID)]

        _run_write_reports(cfg, endpoints)

        raw_text = pathlib.Path(_latest_cbom_json(tmp_path)).read_text()
        cbom_json = json.loads(raw_text)
        assert "vulnerabilities" in cbom_json and cbom_json["vulnerabilities"]

        validator = JsonStrictValidator(SchemaVersion.V1_6)
        err = validator.validate_str(raw_text)
        assert err is None, f"CycloneDX 1.6 schema validation failed: {err}"
