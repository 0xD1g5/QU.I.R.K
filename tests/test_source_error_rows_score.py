"""Score + domain-assessment pin for per-target SOURCE error rows (235.1-03, D-09/D-07).

Rows come from the REAL ``scan_source_targets`` (fake semgrep binary), then go
through the real pipeline: ``derive_report_findings`` -> ``build_evidence_summary`` with
``findings=`` -> ``compute_readiness_score``. The pre-235.1 comparison shape is
what ``run_scan._wrapped_phase`` produced when the first failure re-raised: one
``protocol="ERROR"`` row and zero SOURCE rows.

Run with ``-s`` to print the measured deltas (quoted in CHANGELOG [5.28.1]).
"""
import json
import os
import subprocess
import sys

import pytest

from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint
from quirk.scanner.source_scanner import scan_source_targets

from tests.test_source_scanner import SAMPLE_SEMGREP_OUTPUT


@pytest.fixture
def fake_semgrep_repos(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    real_run = subprocess.run

    def _fork_safe_run(*args, **kwargs):
        kwargs.setdefault("close_fds", False)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _fork_safe_run)

    def _install(spec: dict) -> list:
        repos, table = [], {}
        for name, (stdout, code) in spec.items():
            (tmp_path / name).mkdir()
            repos.append(str(tmp_path / name))
            table[name] = [stdout, code]
        exe = bindir / "semgrep"
        exe.write_text(
            f"#!{sys.executable}\nimport os, sys, time\nTABLE = {table!r}\n"
            "out, code = TABLE[os.path.basename(sys.argv[-1])]\n"
            "if out == 'TIMEOUT':\n    time.sleep(30)\n"
            "sys.stdout.write(out)\nsys.exit(code)\n"
        )
        os.chmod(exe, 0o755)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        return repos

    return _install


def _tls():
    return CryptoEndpoint(
        host="10.0.0.1", port=443, protocol="TLS",
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
    )


def _measure(eps):
    findings = derive_report_findings(eps, None)
    ev = build_evidence_summary(eps, findings=findings)
    return ev, compute_readiness_score(ev)


def _scan_error_count(ev):
    """Evidence scan_error_count: build_evidence_summary exposes it as scan_error.count."""
    return ev["scan_error"]["count"]


def _pre_235_1_error_row():
    return CryptoEndpoint(
        host="source_scanner", port=0, protocol="ERROR",
        scan_error="SourceScanError: source scan failed",
        scan_error_category="exception",
    )


def _mixed(fake):
    a, b, c = fake({
        "a": (json.dumps(SAMPLE_SEMGREP_OUTPUT), 0),
        "b": ("TIMEOUT", 0),
        "c": ("invalid json", 1),
    })
    return scan_source_targets([a, b, c], timeout=1)


def _error_only(fake):
    body = {"results": [], "errors": [
        {"code": 2, "level": "error", "type": "SemgrepError", "message": "x"}]}
    (a,) = fake({"a": (json.dumps(body), 0)})
    return scan_source_targets([a])


def test_mixed_two_of_three_failed(fake_semgrep_repos):
    src = _mixed(fake_semgrep_repos)
    assert len(src) == 4  # 2 findings + 2 error rows
    ev, s = _measure([_tls()] + src)
    print(f"\n[235.1-03] mixed: score={s['score']} sub={s['subscores']} "
          f"domains={s['domains_assessed']}/{s['domains_total']} "
          f"errs={_scan_error_count(ev)} assessable={ev['assessable_endpoint_count']}")
    assert _scan_error_count(ev) == 2
    assert ev["protocol_counts"]["SOURCE"] == 4  # 2 findings + 2 error rows
    assert ev["assessable_endpoint_count"] == 1 + 4
    assert (s["score"], s["domains_assessed"]) == EXPECT["mixed"]


def test_mixed_vs_pre_235_1_error_row_shape(fake_semgrep_repos):
    src = _mixed(fake_semgrep_repos)
    ev_new, s_new = _measure([_tls()] + src)
    ev_old, s_old = _measure([_tls(), _pre_235_1_error_row()])
    print(f"\n[235.1-03] mixed new={s_new['score']} old(ERROR row)={s_old['score']} "
          f"delta={s_new['score'] - s_old['score']}; domains new={s_new['domains_assessed']} "
          f"old={s_old['domains_assessed']}")
    assert _scan_error_count(ev_old) == 1
    assert ev_old["protocol_counts"]["SOURCE"] == 0
    assert s_old["score"] == EXPECT["mixed_old"][0]
    assert s_old["domains_assessed"] == EXPECT["mixed_old"][1]
    assert s_new["score"] - s_old["score"] == EXPECT["mixed_delta"]


def test_error_only_alone_and_with_tls(fake_semgrep_repos):
    src = _error_only(fake_semgrep_repos)
    assert len(src) == 1 and src[0].protocol == "SOURCE" and src[0].scan_error
    ev, s = _measure(src)
    print(f"\n[235.1-03] error-only alone: score={s['score']} "
          f"domains={s['domains_assessed']}/{s['domains_total']} errs={_scan_error_count(ev)}")
    assert _scan_error_count(ev) == 1
    assert (s["score"], s["domains_assessed"]) == EXPECT["error_only_alone"]

    ev_b, s_b = _measure([_tls()])
    ev_t, s_t = _measure([_tls()] + src)
    print(f"\n[235.1-03] error-only +TLS: baseline={s_b['score']}/{s_b['domains_assessed']} "
          f"with row={s_t['score']}/{s_t['domains_assessed']}")
    assert _scan_error_count(ev_t) == 1
    assert (s_b["score"], s_b["domains_assessed"]) == EXPECT["tls_baseline"]
    assert (s_t["score"], s_t["domains_assessed"]) == EXPECT["error_only_tls"]
    # Pin explicitly whether the error row changes domains_assessed.
    assert (s_t["domains_assessed"] == s_b["domains_assessed"]) is EXPECT["domains_unchanged"]


def test_error_rows_are_assessable_not_assessed_crypto(fake_semgrep_repos):
    src = _error_only(fake_semgrep_repos)
    ev_b, _ = _measure([_tls()])
    ev_t, _ = _measure([_tls()] + src)
    assert ev_t["assessable_endpoint_count"] == ev_b["assessable_endpoint_count"] + 1
    assert ev_t["assessed_crypto_count"] == ev_b["assessed_crypto_count"]


# Measured 2026-11-04 (real pipeline, findings=derive_report_findings(...)).
# TLS-only baseline: one TLS 1.3 endpoint -> 3 of 6 domains assessed, headline 84
# (capped by the "no PQ key exchange" ceiling).
# mixed (TLS + 2 SOURCE findings + 2 SOURCE error rows): hygiene and modern_tls
# each 25 -> 24 via _count_curve(2 errors) * scan_error_rate weights, headline 81.
# Pre-235.1 shape (TLS + one ERROR row): the count curve is the same step, so the
# headline is also 81 -> delta 0; the new rows do not change the score here, they
# change what is visible (2 SOURCE rows + findings kept instead of one ERROR row).
EXPECT = {
    "mixed": (81, 3),
    "mixed_old": (81, 3),
    "mixed_delta": 0,
    "error_only_alone": (81, 3),
    "tls_baseline": (84, 3),
    "error_only_tls": (81, 3),
    "domains_unchanged": True,
}
