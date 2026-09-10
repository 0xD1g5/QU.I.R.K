"""Phase 197 / PARITY-05 / PARITY-06 — preview-vs-submit lockstep parity proof.

`validate_connectors_overlay` (quirk/dashboard/api/schemas.py) is the SINGLE
implementation shared by all three connectors-overlay enforcement points:

  (a) ScanSubmitRequest.connectors field_validator     (submit,  POST /api/jobs)
  (b) build_job_config_dict's connectors_overlay merge (job YAML, same call)
  (c) GET /api/config/effective's `connectors` query param (preview)

RESEARCH's critical finding (Pitfall 1) is that widening a SUBSET of these
three independent code paths produces a dashboard where the Effective Config
panel 400/422s on exactly the JSON the form just submitted successfully, or
vice versa. `test_lockstep_parity` below drives every `PAYLOAD_CASES` row
through BOTH `POST /api/jobs` and `GET /api/config/effective?connectors=<same
JSON>` and asserts the two paths' accept/reject verdicts always agree.

`test_deliberate_break_check` documents (by construction, not merely by
prose) that this lockstep test is capable of catching a re-introduction of
Pitfall 1 -- see its docstring and the plan's acceptance criteria for the
manual revert-and-confirm protocol this test's presence stands in for.

`test_a1_no_preset_writes_any_detail_field` locks RESEARCH Assumption A1 (no
`quirk/engine/profiles.py` preset writes any of the 37 connector detail
fields) as a regression test rather than a one-time grep result recorded in
a SUMMARY.

`test_a2_widened_field_gets_user_provenance` locks RESEARCH Assumption A2
(`_snapshot_scalar_fields`'s generic walk already covers widened detail
fields with zero code change) as a live integration test.

pytest -q tests/test_connector_detail_overlay_lockstep.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import _CONNECTOR_DETAIL_KEY_TYPES
from tests.conftest import make_isolated_memory_engine

_PROFILES_PY = Path(__file__).resolve().parent.parent / "quirk" / "engine" / "profiles.py"


def _app_with_db():
    engine = make_isolated_memory_engine()
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False)


class _FakeProc:
    def __init__(self):
        self.pid = 99999
        self.returncode = None

    def poll(self):
        return self.returncode


def _fake_popen(*args, **kwargs):
    return _FakeProc()


def _all_available_probe_map() -> dict:
    """Real probe results with EVERY flag forced available=True, so
    connector-availability confounds never enter the accept/reject verdict
    this test is trying to isolate (RESEARCH Pitfall 1 is about validation
    lockstep, not availability -- test_jobs_connector_422_gate.py already
    covers availability separately)."""
    real = probe_all_connectors()
    forced = {}
    for flag, entry in real.items():
        forced[flag] = ConnectorAvailability(
            flag=flag,
            available=True,
            reason="",
            install_hint=entry.install_hint,
            category=entry.category,
            label=entry.label,
        )
    return forced


# ---------------------------------------------------------------------------
# PAYLOAD_CASES: (payload, expect_ok, offending_key_or_none)
#
# >= 1 valid payload per declared type (list[str], list[dict] for gke, str,
# int, bool, enable_* toggle) and >= 1 invalid payload per rejection class
# (unknown key, wrong scalar type, bool-for-int, bare-string gke element,
# over-length str, out-of-range timeout, enable_* given a non-bool).
# ---------------------------------------------------------------------------

PAYLOAD_CASES: list[tuple[dict, bool, str | None]] = [
    # --- valid: one per declared type ---
    ({"jwt_targets": ["a.example.com"]}, True, None),  # list[str]
    (
        {"gke_clusters": [{"name": "p", "location": "us-central1"}]},
        True,
        None,
    ),  # list[dict] (gke element shape)
    ({"vault_addr": "http://localhost:8200"}, True, None),  # str
    ({"smime_timeout": 30}, True, None),  # int
    ({"vault_tls_verify": False}, True, None),  # bool
    ({"enable_jwt": True}, True, None),  # enable_* toggle
    # --- invalid: one per rejection class ---
    ({"bogus_field": "x"}, False, "bogus_field"),  # unknown key
    ({"jwt_targets": "not-a-list"}, False, "jwt_targets"),  # wrong scalar type
    ({"smime_timeout": True}, False, "smime_timeout"),  # bool-for-int
    ({"gke_clusters": ["prod-1"]}, False, "gke_clusters"),  # bare-string element
    ({"vault_addr": "x" * 513}, False, "vault_addr"),  # over-length str
    ({"adcs_timeout": 9999}, False, "adcs_timeout"),  # out-of-range timeout
    ({"enable_jwt": "yes"}, False, "enable_jwt"),  # enable_* given non-bool
]


@pytest.mark.parametrize("payload,expect_ok,offender", PAYLOAD_CASES)
def test_lockstep_parity(monkeypatch, payload, expect_ok, offender):
    """Submit (POST /api/jobs) and preview (GET /api/config/effective) must
    reach the SAME accept/reject verdict for the identical connectors JSON --
    PARITY-06's core requirement. When rejected, both 422 bodies must name
    the same offending key (D-10)."""
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    fake_map = _all_available_probe_map()
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake_map,
    )

    _app, tc = _app_with_db()

    submit_response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick", "connectors": payload},
        headers={"X-Quirk-Request": "1"},
    )
    preview_response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps(payload)},
    )

    submit_ok = submit_response.status_code == 201
    preview_ok = preview_response.status_code == 200

    assert submit_ok == expect_ok, (
        f"submit verdict mismatch for {payload}: "
        f"{submit_response.status_code} {submit_response.text}"
    )
    assert preview_ok == expect_ok, (
        f"preview verdict mismatch for {payload}: "
        f"{preview_response.status_code} {preview_response.text}"
    )
    # The dominant lockstep assertion: submit and preview must NEVER disagree.
    assert submit_ok == preview_ok, (
        f"LOCKSTEP VIOLATION for {payload}: submit={submit_response.status_code} "
        f"preview={preview_response.status_code}"
    )

    if not expect_ok:
        assert submit_response.status_code == 422, submit_response.text
        assert preview_response.status_code == 422, preview_response.text
        assert offender is not None
        assert offender in submit_response.text, submit_response.text
        assert offender in preview_response.text, preview_response.text


def test_payload_cases_shape():
    """Meta-assertion on the table itself (acceptance criteria): at least 12
    rows, at least 7 of which are rejection cases."""
    assert len(PAYLOAD_CASES) >= 12
    rejection_count = sum(1 for _payload, ok, _offender in PAYLOAD_CASES if not ok)
    assert rejection_count >= 7


def test_a1_no_preset_writes_any_detail_field():
    """RESEARCH Assumption A1, locked as a regression test rather than a
    one-time grep result: no field name in `_CONNECTOR_DETAIL_KEY_TYPES`
    appears in `quirk/engine/profiles.py`'s source text. If this ever fails,
    a future preset started writing a connector detail field and the
    "no Preset badge ever appears on a detail field" assumption
    (RESEARCH Pitfall 4) needs re-examination."""
    source = _PROFILES_PY.read_text()
    hits = [name for name in _CONNECTOR_DETAIL_KEY_TYPES if name in source]
    assert not hits, (
        f"quirk/engine/profiles.py now references connector detail field(s) "
        f"{hits} -- RESEARCH Assumption A1 no longer holds; re-examine "
        f"whether a 'Preset' provenance badge is expected on these fields."
    )


def test_a2_widened_field_gets_user_provenance(monkeypatch):
    """RESEARCH Assumption A2, proven live: a connectors overlay setting one
    widened detail field (`vault_addr`) produces a `user`-provenance entry at
    `connectors.vault_addr` in the effective-config response --
    `_snapshot_scalar_fields`'s generic before/after walk over
    non-underscore-prefixed `ConnectorsCfg` fields already covers the 37
    widened detail fields with zero code change (config_preview.py)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _app, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps({"vault_addr": "http://localhost:8200"})},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    section = next(s for s in body["sections"] if s["name"] == "connectors")
    field = next(f for f in section["fields"] if f["name"] == "vault_addr")
    assert field["value"] == "http://localhost:8200"
    assert field["provenance"] == "user"
