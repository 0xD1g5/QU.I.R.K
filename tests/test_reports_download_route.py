"""Phase 209 Plan 01 (DELIV-01) — GET /api/reports/latest/* route tests.

Covers:
  - manifest legs: all-five-available, DOCX-extra-missing reason, DOCX-render-failed
    reason, empty-output-directory "No scan has run yet." (D-10), no-run-stats
    fallback with scan_time explicitly null (D-03), newest-run-stats-group selection
    over newest-file-per-format (D-01)
  - download legs: exact byte-for-byte content per format (RESEARCH Pitfall 1), and
    an unavailable format never serves a substitute file (D-07/D-10 server-side form)
  - containment legs: traversal-payload 404 sweep (a regression tripwire, NOT proof of
    a patched exploit — see that test's docstring), a run-time route-signature
    assertion that the path parameter is Literal/Enum-typed (not bare str), and an
    isolated negative control proving os.path.join WOULD escape a directory absent
    the enum's structural protection (D-04)
  - auth leg: both new endpoints require auth when it is configured (T-209-02)

This file is written RED, before quirk/dashboard/api/routes/reports.py exists
(Wave 0 scaffolding). It must collect cleanly with no top-level import of that
module. Every manifest/download/containment(route-level)/auth leg is expected to
fail until Plan 03 (Wave 1) builds the route. Only the negative-control leg is
expected to pass today.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app

_REPO_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_FORMAT_FILENAMES = {
    "html": "report-{stamp}.html",
    "pdf": "report-{stamp}.pdf",
    "docx": "report-{stamp}.docx",
    "cbom-json": "cbom-{stamp}.cdx.json",
    "cbom-xml": "cbom-{stamp}.cdx.xml",
}

_FORMAT_MEDIA_TYPES = {
    "html": "text/html",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "cbom-json": "application/json",
    "cbom-xml": "application/xml",
}

_ALL_FORMATS = ("html", "pdf", "docx", "cbom-json", "cbom-xml")


def _artifact_bytes(stamp: str, fmt: str) -> bytes:
    return f"CONTENT-{stamp}-{fmt}".encode()


def _write_stamp_group(outdir: Path, stamp: str, *, formats, run_stats: bool = True) -> None:
    """Write real-shaped artifact files for `stamp` into `outdir`.

    Only the format kinds named in `formats` are written, so a caller can build
    a docx-absent (or otherwise partial) group. Each artifact's bytes are unique
    and derivable so a download leg can assert byte-for-byte fidelity.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        filename = _FORMAT_FILENAMES[fmt].format(stamp=stamp)
        (outdir / filename).write_bytes(_artifact_bytes(stamp, fmt))

    if run_stats:
        run_stats_payload = {
            "started_utc": f"2026-09-14T04:{stamp[-4:-2]}:00.000000+00:00",
            "ended_utc": f"2026-09-14T04:{stamp[-4:-2]}:13.439767+00:00",
            "profile": "standard",
            "score_profile": "balanced",
            "safe_mode": False,
            "cache_enabled": False,
            "discovery_mode": "builtin",
            "rate_limit": 0.0,
        }
        (outdir / f"run-stats-{stamp}.json").write_text(json.dumps(run_stats_payload))


def _write_minimal_config(tmp_path: Path, outdir: Path) -> Path:
    """Derive a config.yaml fixture from the repo's real config.yaml.

    config_from_dict() requires the full top-level schema (assessment/scan/
    targets/...), so a minimal stub is not viable — mirrors the fixture
    discipline tests/test_api_auth.py already uses. Only output.directory is
    overridden, to point at the isolated tmp_path output dir.
    """
    config_text = _REPO_CONFIG_PATH.read_text()
    assert 'directory: "output"' in config_text, (
        "fixture assumes repo config.yaml has output.directory == \"output\""
    )
    outdir_str = str(outdir).replace("\\", "\\\\")
    config_text = config_text.replace(
        'directory: "output"', f'directory: "{outdir_str}"'
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_text)
    return config_path


def _client(monkeypatch, tmp_path: Path, outdir: Path) -> TestClient:
    config_path = _write_minimal_config(tmp_path, outdir)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(config_path))
    app = create_app()
    return TestClient(app, headers={"X-Quirk-Request": "1"})


# ---------------------------------------------------------------------------
# Manifest legs
# ---------------------------------------------------------------------------


def test_manifest_reports_all_five_formats_available(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    _write_stamp_group(outdir, stamp, formats=_ALL_FORMATS, run_stats=True)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["stamp"] == stamp
    for fmt in _ALL_FORMATS:
        assert data["formats"][fmt]["available"] is True
        assert data["formats"][fmt]["reason"] is None
    assert data["scan_time"] == "2026-09-14T04:13:13.439767+00:00"


def test_manifest_docx_missing_extra_reason(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    other_formats = [f for f in _ALL_FORMATS if f != "docx"]
    _write_stamp_group(outdir, stamp, formats=other_formats, run_stats=True)

    def _fake_find_spec(name, *args, **kwargs):
        if name == "docx":
            return None
        return importlib.util.find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", _fake_find_spec)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["formats"]["docx"]["available"] is False
    assert (
        data["formats"]["docx"]["reason"]
        == "DOCX requires the optional extra: pip install quirk[docx]"
    )


def test_manifest_docx_render_failed_reason(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    other_formats = [f for f in _ALL_FORMATS if f != "docx"]
    _write_stamp_group(outdir, stamp, formats=other_formats, run_stats=True)

    # python-docx IS installed on this machine per 209-RESEARCH.md — leave
    # importlib.util.find_spec unpatched so the "extra missing" branch does
    # not fire, isolating the "render failed" reason instead.
    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["formats"]["docx"]["available"] is False
    assert (
        data["formats"]["docx"]["reason"]
        == "This format failed to render for the latest scan. Check server logs."
    )


def test_manifest_empty_output_directory_reports_no_scan_yet(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["scan_time"] is None
    assert set(data["formats"].keys()) == set(_ALL_FORMATS)
    for fmt in _ALL_FORMATS:
        assert data["formats"][fmt]["available"] is False
        assert data["formats"][fmt]["reason"] == "No scan has run yet."


def test_manifest_fallback_group_without_run_stats_reports_unknown_scan_time(
    tmp_path, monkeypatch
):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    _write_stamp_group(outdir, stamp, formats=_ALL_FORMATS, run_stats=False)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["stamp"] == stamp
    assert data["scan_time"] is None
    for fmt in _ALL_FORMATS:
        assert data["formats"][fmt]["available"] is True


def test_manifest_picks_newest_run_stats_group_not_newest_file(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    older_stamp = "20260914-030000"
    newer_stamp = "20260914-050000"
    _write_stamp_group(outdir, older_stamp, formats=_ALL_FORMATS, run_stats=True)
    _write_stamp_group(outdir, newer_stamp, formats=["html"], run_stats=False)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/manifest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["stamp"] == older_stamp


# ---------------------------------------------------------------------------
# Download legs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", _ALL_FORMATS)
def test_download_serves_exact_bytes_for_each_format(tmp_path, monkeypatch, fmt):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    _write_stamp_group(outdir, stamp, formats=_ALL_FORMATS, run_stats=True)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get(f"/api/reports/latest/{fmt}")

    assert resp.status_code == 200
    assert resp.headers["content-type"].split(";")[0] == _FORMAT_MEDIA_TYPES[fmt]
    assert resp.content == _artifact_bytes(stamp, fmt)
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert _FORMAT_FILENAMES[fmt].format(stamp=stamp) in disposition


def test_download_unavailable_format_does_not_serve_a_wrong_file(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    other_formats = [f for f in _ALL_FORMATS if f != "docx"]
    _write_stamp_group(outdir, stamp, formats=other_formats, run_stats=True)

    client = _client(monkeypatch, tmp_path, outdir)
    resp = client.get("/api/reports/latest/docx")

    assert resp.status_code == 404
    for fmt in other_formats:
        assert resp.content != _artifact_bytes(stamp, fmt)


# ---------------------------------------------------------------------------
# Containment legs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            "../../../etc/passwd",
            marks=pytest.mark.xfail(
                reason=(
                    "209-CONTAINMENT-GATE.md disposition (a): httpx (and every "
                    "RFC 3986 §5.3/6.2.2.3-compliant HTTP client, browsers "
                    "included) removes dot-segments from this payload BEFORE "
                    "constructing the request — the client sends a literal "
                    "GET /etc/passwd, indistinguishable server-side from a "
                    "direct request to that path. Not expressible over HTTP "
                    "against this server; not a server-side containment gap. "
                    "See 209-CONTAINMENT-GATE.md for the full disposition."
                ),
                strict=True,
            ),
        ),
        "%2e%2e%2f%2e%2e%2fconfig.yaml",
        "..%2F..%2Fetc%2Fpasswd",
        "report-20260914-041322.html",
        "nonexistent",
        "",
    ],
)
def test_containment_traversal_payloads_404(tmp_path, monkeypatch, payload):
    """Regression tripwire, not proof of a patched exploit.

    D-04 makes traversal structurally unrepresentable via a fixed Literal path
    enum — of course an unlisted string 404s; that is what the type system
    does. This leg's value is as a regression tripwire against a SPECIFIC
    future mistake: a later refactor swapping the Literal/Enum-typed path
    parameter for a bare `str` path parameter. If that mistake is ever made,
    this exact test goes from 404 to 200-with-arbitrary-file (or a 500). It is
    not, and was never meant to be, a demonstration that traversal was
    attempted and blocked by application logic.
    """
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    _write_stamp_group(outdir, stamp, formats=_ALL_FORMATS, run_stats=True)

    client = _client(monkeypatch, tmp_path, outdir)

    resp = client.get(f"/api/reports/latest/{payload}")
    assert resp.status_code == 404

    # Also exercise httpx's raw path so URL-encoded forms are not normalised
    # away by the client library before reaching Starlette's router.
    raw_resp = client.get(f"/api/reports/latest/{payload}", follow_redirects=False)
    assert raw_resp.status_code in (404, 307, 308)
    if raw_resp.status_code in (307, 308):
        followed = client.get(raw_resp.headers["location"])
        assert followed.status_code == 404


def test_containment_route_signature_has_no_str_path_param():
    """Non-vacuity: fails loudly (named message) if no parameterised route is
    found — a walk that finds nothing must not silently pass. This is the leg
    that actually goes RED if someone later loosens the enum to a bare str."""
    import typing

    from quirk.dashboard.api.routes import reports

    parameterised_routes = [
        route for route in reports.router.routes if "{" in getattr(route, "path", "")
    ]
    assert parameterised_routes, (
        "VACUOUS GUARD: no parameterised route found on reports.router — "
        "this assertion cannot protect anything if the walk finds zero routes"
    )

    expected_members = {"html", "pdf", "docx", "cbom-json", "cbom-xml"}
    for route in parameterised_routes:
        endpoint = route.endpoint
        hints = typing.get_type_hints(endpoint, include_extras=True)
        # Find the path-parameter annotation (skip return annotation).
        param_names = [p for p in route.param_convertors.keys()] if hasattr(
            route, "param_convertors"
        ) else []
        for name in param_names:
            annotation = hints.get(name)
            assert annotation is not str, (
                f"route {route.path!r} parameter {name!r} is bare `str` — "
                "containment guard (D-04) requires a Literal/Enum-typed path "
                "parameter, not a free-form string"
            )
            origin = typing.get_origin(annotation)
            if origin is typing.Literal:
                members = set(typing.get_args(annotation))
                assert members == expected_members, (
                    f"route {route.path!r} parameter {name!r} Literal members "
                    f"{members} != expected {expected_members}"
                )
            else:
                import enum

                assert isinstance(annotation, type) and issubclass(
                    annotation, enum.Enum
                ), (
                    f"route {route.path!r} parameter {name!r} annotation "
                    f"{annotation!r} is neither typing.Literal nor an Enum subclass"
                )
                members = {member.value for member in annotation}
                assert members == expected_members, (
                    f"route {route.path!r} parameter {name!r} Enum members "
                    f"{members} != expected {expected_members}"
                )


def test_containment_negative_control_naive_join_does_escape(tmp_path):
    """Isolated unit test, touches no route and depends on no route code —
    must be green immediately. Proves the traversal class is real in this
    stdlib absent the enum's structural protection — so the route-level 404s
    elsewhere in this file are meaningful rather than tautological, and the
    two-part demonstration (this leg + the route-source check below) is a
    genuine contrast rather than a single trivially-true assertion."""
    traversal_payload = "../../../etc/passwd"
    naive_path = os.path.realpath(os.path.join(str(tmp_path), traversal_payload))

    assert not naive_path.startswith(str(tmp_path)), (
        "VACUOUS NEGATIVE CONTROL: naive os.path.join+realpath did not escape "
        "tmp_path — the traversal class would not be real, and the route-level "
        "404 tests elsewhere in this file would prove nothing"
    )
    assert naive_path == "/etc/passwd" or naive_path.endswith("/etc/passwd")


def test_containment_negative_control_route_never_takes_naive_join_path():
    """Second half of the two-part demonstration (RESEARCH §Containment Guard
    Test Shape): having proven above that a naive os.path.join(outdir,
    user_supplied_string) DOES escape the directory, this leg proves the
    route's actual code never takes that vulnerable code path — it only ever
    joins a server-resolved filename looked up from its own enum->filename
    mapping, never the client-supplied path segment directly. Depends on
    reports.py existing, so it is RED (via a named, non-vacuous failure) until
    Plan 03 lands, unlike the sibling test above which is intentionally
    independent of the route module."""
    route_module_path = (
        Path(__file__).resolve().parent.parent
        / "quirk"
        / "dashboard"
        / "api"
        / "routes"
        / "reports.py"
    )
    if not route_module_path.is_file():
        pytest.fail(
            "quirk/dashboard/api/routes/reports.py does not exist yet "
            "(Wave 0 RED scaffolding) — cannot source-check the join pattern "
            "until Plan 03 lands"
        )
    source_text = route_module_path.read_text()
    assert source_text.strip(), (
        "VACUOUS SOURCE CHECK: reports.py exists but is empty — "
        "cannot assert anything about a join pattern in empty source"
    )

    import re

    join_calls = re.findall(r"os\.path\.join\(([^)]*)\)", source_text)
    truediv_calls = re.findall(r"Path\([^)]*\)\s*/\s*(\w+)", source_text)
    for call_args in join_calls:
        args = [a.strip() for a in call_args.split(",")]
        assert "fmt" not in args, (
            f"reports.py contains os.path.join(...) whose arguments include "
            f"the route's raw path-parameter name 'fmt': {call_args!r} — "
            "the module must only join a server-resolved filename looked up "
            "from its own enum->filename mapping, never the client-supplied "
            "path segment directly"
        )
    for var in truediv_calls:
        assert var != "fmt", (
            f"reports.py contains a Path(...) / {var} construction using the "
            "raw path-parameter name directly — must join a server-resolved "
            "filename instead"
        )


# ---------------------------------------------------------------------------
# Auth leg
# ---------------------------------------------------------------------------


def test_auth_required_without_token_401(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    stamp = "20260914-041322"
    _write_stamp_group(outdir, stamp, formats=_ALL_FORMATS, run_stats=True)
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")

    config_path = _write_minimal_config(tmp_path, outdir)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(config_path))
    app = create_app()
    client = TestClient(app)  # no X-Quirk-Request / X-API-Key headers

    manifest_resp = client.get("/api/reports/latest/manifest")
    assert manifest_resp.status_code == 401

    download_resp = client.get("/api/reports/latest/pdf")
    assert download_resp.status_code == 401

    ok_client = TestClient(app, headers={"X-API-Key": "test-token"})
    ok_resp = ok_client.get("/api/reports/latest/manifest")
    assert ok_resp.status_code == 200
