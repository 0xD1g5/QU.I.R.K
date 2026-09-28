"""211-02 (DENOM-04 residual / 17-vs-18 divergence, leg 1) — cross-vocabulary
finding-title parity in `quirk.intelligence.evidence`.

**The defect.** `evidence.py::_finding_targets` matches finding titles with an
exact string comparison against CLI-canonical titles (e.g. "Plaintext HTTP
service detected"). The dashboard pipeline's `_derive_findings()` emits a
DIFFERENT vocabulary for the same condition (e.g. "Unencrypted HTTP service"
— see `quirk/dashboard/api/finding_title_bridge.py`'s module docstring for
why two vocabularies exist and must NOT be unified). Every exact-string match
in `_finding_targets` therefore silently returns zero when handed
dashboard-vocabulary findings, even though the underlying endpoint condition
is identical. `plaintext_http_count` is the concrete, measured instance:
10 on the report pipeline, 0 on the dashboard pipeline, for the identical
scan_run_id 2026-09-28T01:41:30.088508+00:00. That single counter accounts
for the Hygiene 17-vs-21 divergence (`scoring.py:481-484`) and, together with
Modern TLS's identical `scan_error_rate` dependency, the report-vs-dashboard
17-vs-18 headline divergence tracked at
`.planning/todos/pending/260928-hygiene-moderntls-subscores-diverge-report-vs-dashboard.md`.

**211-03 (leg 2) addendum.** `legacy_tls_count` -- the Modern TLS "Legacy TLS
versions present" driver -- is a DIFFERENT defect shape, not a title-bridging
problem: `scoring.py:448` computes it as
`max(0, _as_int(sev.get("LOW", 0)))`, a raw count of ALL LOW-severity findings
of ANY kind. The dashboard pipeline emits no LOW severity at all, so the
proxy is structurally 0 on that side regardless of the estate. Bridging
titles (leg 1, above) cannot reach this because `legacy_tls_count` never
looks at a title. The fix is to derive it from endpoint fields instead,
mirroring `findings_evaluator._has_legacy_tls_versions` exactly -- the same
shape every OTHER counter in this file (`motion_email_plaintext_count` and
siblings) already uses, and the only shape that produces parity by
construction across two independently-maintained finding generators.

**Why pinned absolutes, not `A == B`.** Both pipelines call the SAME
`build_evidence_summary` function. Once a bug lives inside a function two
surfaces share, an `assert A == B` comparing the two surfaces' outputs is
vacuous -- a regression moves both sides together and the assertion still
passes (Phase 210's two falsification attempts both initially PASSED for
exactly this reason; see `.continue-here.md`'s anti-pattern table). Every
count in this file is therefore asserted against a PINNED absolute integer,
independently, per pipeline. Equality between pipelines is asserted only as
a corroborating afterthought, never as the sole claim.

**Why both finding lists are generated from the REAL generators, not
hand-written title strings.** Hand-writing "Plaintext HTTP service detected"
and "Unencrypted HTTP service" as literals would make this test agree with
the AUTHOR's assumption about what each generator emits, not with the
generators themselves -- the exact failure mode this phase exists to correct
(CLAUDE.md's "measure with a method independent of the audited code").
`evaluate_endpoints()` (CLI) and `_derive_findings()` (dashboard) are called
directly over one shared `CryptoEndpoint` fixture list.
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

from quirk.dashboard.api.finding_title_bridge import canonical_cli_title
from quirk.dashboard.api.routes.scan import _derive_findings
from quirk.engine.findings_evaluator import evaluate_endpoints
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint


def _cfg():
    return SimpleNamespace(scan=SimpleNamespace(ports_tls=[443, 8443]))


def _ep(**kw):
    base = dict(
        id=1, host="10.0.0.1", port=443, protocol="TLS",
        scanned_at=datetime.datetime(2026, 9, 28, 12, 0, 0),
    )
    base.update(kw)
    return CryptoEndpoint(**base)


_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2030, 1, 1)

# Three plaintext-HTTP endpoints -- the exact condition behind the measured
# 10-vs-0 plaintext_http_count divergence.
_HTTP_1 = _ep(id=1, host="10.0.1.1", port=80, protocol="HTTP")
_HTTP_2 = _ep(id=2, host="10.0.1.2", port=80, protocol="HTTP")
_HTTP_3 = _ep(id=3, host="10.0.1.3", port=8080, protocol="HTTP")

# A clean TLS endpoint -- population noise, contributes to neither counter.
_TLS_CLEAN = _ep(
    id=4, host="10.0.2.1", port=443, protocol="TLS",
    cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=clean.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST, cert_not_after=_FUTURE,
)

# An mTLS-blocked TLS endpoint -- exercises evidence.py:211-212's
# endpoint-FIELD contribution to mtls_present_count, which is independent of
# any finding-title match (the `|=` at evidence.py:469 only ADDS to it).
_MTLS_BLOCKED = _ep(
    id=5, host="10.0.3.1", port=443, protocol="TLS",
    tls_blocker_reason="MTLS_REQUIRED",
)

_ALL_ENDPOINTS = [_HTTP_1, _HTTP_2, _HTTP_3, _TLS_CLEAN, _MTLS_BLOCKED]

# Endpoints covering the three identity-mapped bridge entries plus one
# non-identity bridged entry and one CLI-only condition, used for the
# translation-is-a-no-op-on-the-CLI-vocabulary assertions.
_SELF_SIGNED = _ep(
    id=6, host="10.0.4.1", port=443, protocol="TLS",
    cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=self.example", cert_issuer="CN=self.example",
    cert_not_before=_PAST, cert_not_after=_FUTURE,
)
_UNDERSIZED_RSA = _ep(
    id=7, host="10.0.4.2", port=443, protocol="TLS",
    cert_pubkey_alg="RSA", cert_pubkey_size=1024,
    cert_subject="CN=small.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST, cert_not_after=_FUTURE,
)
_EXPIRED = _ep(
    id=8, host="10.0.4.3", port=443, protocol="TLS",
    cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=old.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST, cert_not_after=_PAST,
)
_IDENTITY_ENDPOINTS = [_HTTP_1, _HTTP_2, _HTTP_3, _SELF_SIGNED, _UNDERSIZED_RSA, _EXPIRED]

# Two endpoints tripping `_has_legacy_tls_versions` two DIFFERENT ways --
# both must count, and both are exercised so a fix that only handles one
# branch of the predicate is caught.
_TLS_LEGACY_VIA_VERSION = _ep(
    id=9, host="10.0.5.1", port=443, protocol="TLS",
    tls_version="TLSv1.1",
)
_TLS_LEGACY_VIA_SUPPORTED = _ep(
    id=10, host="10.0.5.2", port=443, protocol="TLS",
    tls_version="TLSv1.3", tls_supported_versions="TLSv1,TLSv1.2,TLSv1.3",
)
_LEGACY_TLS_ENDPOINTS = _ALL_ENDPOINTS + [_TLS_LEGACY_VIA_VERSION, _TLS_LEGACY_VIA_SUPPORTED]

# Measured post-fix via compute_readiness_score() over _LEGACY_TLS_ENDPOINTS'
# evidence dicts (pinned, not re-derived at test time, per this project's
# "pinned oracles, not bare equality" rule). Unchanged from the pre-fix
# CLI-side value -- the CLI generator already emitted a LOW finding for both
# legacy-TLS endpoints, so its old severity-proxy and the new endpoint-derived
# counter agree at 2 either way; only the DASHBOARD side moves (0 -> 2).
_EXPECTED_MODERN_TLS_SUBSCORE = 18


def _cli_findings(endpoints):
    """The CLI/report-pipeline finding list -- real dicts from the real
    generator, exactly as `quirk/reports/writer.py:545` / `executive.py:169`
    hand them to `build_evidence_summary`."""
    return evaluate_endpoints(_cfg(), endpoints)


def _dashboard_findings(endpoints):
    """The dashboard-pipeline finding list -- real `FindingItem`s from the
    real generator, converted the same way the live route does it
    (`quirk/dashboard/api/routes/scan.py:1318`: `[f.model_dump() for f in
    findings]`)."""
    return [f.model_dump() for f in _derive_findings(endpoints)]


class TestPlaintextHttpCountCrossVocabularyParity:
    """The core defect: plaintext_http_count over the SAME three HTTP
    endpoints, computed from each pipeline's own finding vocabulary."""

    def test_cli_vocabulary_plaintext_http_count_is_pinned_at_three(self):
        summary = build_evidence_summary(_ALL_ENDPOINTS, _cli_findings(_ALL_ENDPOINTS))
        assert summary["plaintext_http_count"] == 3, (
            f"CLI-vocabulary plaintext_http_count expected 3, got "
            f"{summary['plaintext_http_count']}"
        )

    def test_dashboard_vocabulary_plaintext_http_count_is_pinned_at_three(self):
        """THE red assertion pre-fix: this pipeline's findings use the title
        'Unencrypted HTTP service', which `_finding_targets` (pre-fix) never
        matches against the CLI-canonical 'Plaintext HTTP service detected'
        -- so this returns 0 pre-fix, not 3. Baseline documentation case
        (211-02-PLAN.md behaviour bullet 5): if this ever regresses to 0
        again, it reproduces the exact 17-vs-18 defect measured live at
        scan_run_id 2026-09-28T01:41:30.088508+00:00.
        """
        summary = build_evidence_summary(_ALL_ENDPOINTS, _dashboard_findings(_ALL_ENDPOINTS))
        assert summary["plaintext_http_count"] == 3, (
            f"dashboard-vocabulary plaintext_http_count expected 3 (parity with the "
            f"CLI pipeline over the identical endpoint set), got "
            f"{summary['plaintext_http_count']}. A value of 0 here is the exact "
            f"17-vs-18 headline-score defect this plan fixes -- see this test's "
            f"docstring and .planning/todos/pending/"
            f"260928-hygiene-moderntls-subscores-diverge-report-vs-dashboard.md."
        )

    def test_both_pipelines_agree_corroborating_only(self):
        """Corroborating only -- NOT the test's sole claim. Both pinned
        absolute assertions above must pass independently first."""
        cli_count = build_evidence_summary(_ALL_ENDPOINTS, _cli_findings(_ALL_ENDPOINTS))["plaintext_http_count"]
        dash_count = build_evidence_summary(_ALL_ENDPOINTS, _dashboard_findings(_ALL_ENDPOINTS))["plaintext_http_count"]
        assert cli_count == dash_count


class TestMtlsEndpointFieldContributionPreserved:
    """evidence.py:212's endpoint-field mtls_targets contribution must
    survive the bridge change untouched -- it is not vocabulary-dependent at
    all, it fires off `tls_blocker_reason`, and the `|=` at :469 only adds to
    it, never replaces it."""

    def test_mtls_present_count_counts_endpoint_with_no_mtls_finding(self):
        # No mTLS finding in this list at all (dashboard has no "mTLS
        # required" equivalent finding generator) -- the endpoint-field path
        # alone must count it.
        summary = build_evidence_summary(_ALL_ENDPOINTS, _dashboard_findings(_ALL_ENDPOINTS))
        assert summary["mtls_present_count"] == 1, (
            f"expected the MTLS_REQUIRED-blocked endpoint to be counted via "
            f"evidence.py:211-212's endpoint-field path alone, got "
            f"{summary['mtls_present_count']}"
        )


class TestTranslationIsANoOpOnCliVocabulary:
    """D-behaviour bullet 4: no CLI title is altered by passing through the
    bridge. Pin the CLI-vocabulary counters computed via `_finding_targets`
    (indirectly, via build_evidence_summary) and independently pin
    `canonical_cli_title`'s direct behaviour on every title the CLI
    generator actually emits over this fixture."""

    def test_every_cli_emitted_title_is_unaffected_by_bridge_translation(self):
        """canonical_cli_title() must return either None (no match) or the
        SAME string (an identity row) for every title the CLI generator
        emits -- never a DIFFERENT string. A different string would mean the
        CLI pipeline's own titles get silently rewritten, breaking every
        existing CLI-vocabulary consumer (remediation fingerprinting,
        storyline lookups, this file's own CLI-side pinned counts)."""
        cli_titles = {f["title"] for f in _cli_findings(_IDENTITY_ENDPOINTS)}
        assert cli_titles, "fixture produced no CLI findings -- fixture is broken"
        for title in cli_titles:
            translated = canonical_cli_title(title)
            assert translated in (None, title), (
                f"CLI title {title!r} was translated to {translated!r} -- "
                f"translation must be a no-op (None or identity) on the CLI "
                f"vocabulary, never a rewrite"
            )

    def test_cli_vocabulary_counters_pinned_identical_with_and_without_bridge_call(self):
        """Pinned-absolute proof that routing CLI titles through
        `canonical_cli_title(raw) or raw` inside `_finding_targets` produces
        the IDENTICAL counters as a hypothetical bypass, for a fixture that
        exercises three distinct CLI conditions plus the three plaintext-HTTP
        endpoints."""
        findings = _cli_findings(_IDENTITY_ENDPOINTS)
        summary = build_evidence_summary(_IDENTITY_ENDPOINTS, findings)
        # 3 plaintext-HTTP endpoints -> 3.
        assert summary["plaintext_http_count"] == 3
        # self-signed / undersized-RSA / expired are NOT plaintext_http,
        # http_on_tls_port, or mTLS conditions -- none of them should move
        # either of the other two title-matched counters.
        assert summary["http_on_tls_port_count"] == 0
        assert summary["mtls_present_count"] == 0


class TestLegacyTlsCountCrossVocabularyParity:
    """211-03 leg 2: `legacy_tls_count` must be endpoint-derived, identical
    across both pipelines for the same endpoints, and immune to an unrelated
    LOW-severity finding -- the exact contamination the old severity-proxy
    was vulnerable to (and which caught nothing on the CLI side either)."""

    def test_cli_vocabulary_legacy_tls_count_is_pinned_at_two(self):
        summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _cli_findings(_LEGACY_TLS_ENDPOINTS))
        assert summary["legacy_tls_count"] == 2, (
            f"CLI-side legacy_tls_count expected 2 (one endpoint matching via "
            f"tls_version, one via tls_supported_versions), got "
            f"{summary['legacy_tls_count']}"
        )

    def test_dashboard_vocabulary_legacy_tls_count_is_pinned_at_two(self):
        """THE red assertion pre-fix: the dashboard pipeline emits no LOW
        severity at all, so the pre-fix `sev.get('LOW', 0)` proxy in
        scoring.py measures 0 here regardless of the endpoint population --
        and pre-fix, evidence.py does not even emit a `legacy_tls_count` key,
        so this raises KeyError. A value of 0 (or a KeyError) here is the
        Modern TLS half of the 17-vs-18 headline-score defect."""
        summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _dashboard_findings(_LEGACY_TLS_ENDPOINTS))
        assert summary["legacy_tls_count"] == 2, (
            f"dashboard-side legacy_tls_count expected 2 (parity with the CLI "
            f"pipeline over the identical endpoint set), got "
            f"{summary['legacy_tls_count']}"
        )

    def test_pinned_count_agrees_with_cli_generators_own_finding_set(self):
        """Independent cross-check, computed from the generator at test time
        (never hardcoded twice): the pinned integer above must equal the
        number of distinct (host, port) pairs the CLI generator itself
        emits under the legacy-TLS finding title."""
        findings = _cli_findings(_LEGACY_TLS_ENDPOINTS)
        generator_pairs = {
            (f["host"], f["port"]) for f in findings
            if f["title"] == "Legacy TLS versions allowed (TLS 1.0/1.1)"
        }
        summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, findings)
        assert summary["legacy_tls_count"] == len(generator_pairs), (
            f"legacy_tls_count ({summary['legacy_tls_count']}) disagrees with "
            f"the CLI generator's own legacy-TLS finding set "
            f"({len(generator_pairs)} distinct (host, port) pairs)"
        )
        assert len(generator_pairs) == 2

    def test_unrelated_low_severity_finding_does_not_move_legacy_tls_count(self):
        """Contamination guard: an unrelated LOW-severity finding must NOT
        move legacy_tls_count. This is the assertion that fails if anyone
        reinstates the severity proxy -- it also would have caught the
        original defect on the CLI side, where the proxy over-counted
        rather than under-counted."""
        findings = list(_cli_findings(_LEGACY_TLS_ENDPOINTS))
        baseline = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, findings)["legacy_tls_count"]

        contaminated = findings + [{
            "host": "10.0.9.9", "port": 9999, "severity": "LOW",
            "title": "Unrelated LOW-severity finding (contamination guard)",
            "description": "Not a legacy-TLS condition.",
            "recommendation": "N/A",
        }]
        contaminated_summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, contaminated)
        assert contaminated_summary["legacy_tls_count"] == baseline, (
            f"an unrelated LOW-severity finding moved legacy_tls_count from "
            f"{baseline} to {contaminated_summary['legacy_tls_count']} -- the "
            f"severity proxy has been reinstated"
        )

    def test_legacy_tls_count_key_always_present_including_no_findings(self):
        """Fallback-can-never-fire assertion: the key must always be present,
        for both pipelines' finding lists AND when findings=None, so
        scoring.py's legacy-dict compatibility fallback is unreachable for
        either real pipeline."""
        cli_summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _cli_findings(_LEGACY_TLS_ENDPOINTS))
        dash_summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _dashboard_findings(_LEGACY_TLS_ENDPOINTS))
        none_summary = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, None)
        assert "legacy_tls_count" in cli_summary
        assert "legacy_tls_count" in dash_summary
        assert "legacy_tls_count" in none_summary

    def test_both_pipelines_agree_corroborating_only(self):
        """Corroborating only -- NOT the test's sole claim. Both pinned
        absolute assertions above must pass independently first."""
        cli_count = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _cli_findings(_LEGACY_TLS_ENDPOINTS))["legacy_tls_count"]
        dash_count = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _dashboard_findings(_LEGACY_TLS_ENDPOINTS))["legacy_tls_count"]
        assert cli_count == dash_count

    def test_modern_tls_subscore_identical_across_pipelines(self):
        """compute_readiness_score over both evidence dicts yields the SAME
        Modern TLS subscore, each asserted against a pinned absolute value
        first (Phase 210's lesson: a bare A == B across a shared function is
        vacuous on its own)."""
        cli_evidence = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _cli_findings(_LEGACY_TLS_ENDPOINTS))
        dash_evidence = build_evidence_summary(_LEGACY_TLS_ENDPOINTS, _dashboard_findings(_LEGACY_TLS_ENDPOINTS))
        cli_modern_tls = compute_readiness_score(cli_evidence)["subscores"]["modern_tls"]
        dash_modern_tls = compute_readiness_score(dash_evidence)["subscores"]["modern_tls"]
        assert cli_modern_tls == _EXPECTED_MODERN_TLS_SUBSCORE, (
            f"CLI-side Modern TLS subscore expected "
            f"{_EXPECTED_MODERN_TLS_SUBSCORE}, got {cli_modern_tls}"
        )
        assert dash_modern_tls == _EXPECTED_MODERN_TLS_SUBSCORE, (
            f"dashboard-side Modern TLS subscore expected "
            f"{_EXPECTED_MODERN_TLS_SUBSCORE}, got {dash_modern_tls}"
        )
        assert cli_modern_tls == dash_modern_tls


class TestFastapiFreeImport:
    """T-211-02-01: the new cross-layer import
    (`quirk.intelligence.evidence` -> `quirk.dashboard.api.finding_title_bridge`)
    must cost nothing at import time for a minimal install. Verified by
    subprocess, not by inspection, per this plan's binding constraint 7 --
    `sys.modules` state from THIS test process is contaminated by whatever
    else pytest already imported."""

    def test_importing_evidence_does_not_pull_fastapi_into_sys_modules(self):
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable, "-c",
                "import sys, quirk.intelligence.evidence; "
                "assert 'fastapi' not in sys.modules, "
                "'evidence.py now drags FastAPI into every import'; "
                "print('import cost OK')",
            ],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"subprocess import check failed:\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        assert "import cost OK" in result.stdout
