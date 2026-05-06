---
phase: 49
slug: compliance-mapping
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-05
updated: 2026-05-05
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `pytest tests/test_compliance_*.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~5 min (full) |

---

## Sampling Rate

- **After every task commit:** Run quick run command for changed compliance tests
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 0 | COMPLY-01/02/03/04/06/07 | T-49-01 | Static AST read of project source only | scaffold | `python -m compileall -q tests/fixtures/chaos_lab_findings.py tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py && pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py --collect-only -q && python -c "from tests.fixtures.chaos_lab_findings import collect_emitted_titles; assert len(collect_emitted_titles()) >= 24"` | ❌ W0 → ✅ Plan 49-01 | ⬜ pending |
| 49-01-02 | 01 | 0 | COMPLY-05/08 | T-49-02, T-49-03 | Bounded subprocess (timeout=30); fixed argv list | scaffold | `python -m compileall -q tests/test_compliance_report_section.py tests/test_compliance_cli.py && pytest tests/test_compliance_report_section.py tests/test_compliance_cli.py --collect-only -q` | ❌ W0 → ✅ Plan 49-01 | ⬜ pending |
| 49-02-01 | 02 | 1 | COMPLY-01/02/03/04/06/07 | T-49-04, T-49-05, T-49-06 | https-only source URLs; static map; 12-month staleness gate | unit | `python -m compileall -q quirk/compliance/__init__.py && pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py -x -q` | ❌ W0 → ✅ Plan 49-02 | ⬜ pending |
| 49-02-02 | 02 | 1 | COMPLY-01 | T-49-07 | Single-pass longest-prefix-first lookup against TITLE_PREFIX_ALIASES; fixed-string titles (incl. parens-in-key) bypass normalization; pqc terminology gate stays green | unit + integration | `python -m compileall -q quirk/engine/risk_engine.py quirk/dashboard/api/schemas.py && pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py tests/test_pqc_terminology_gate.py -x -q && python -c "from quirk.engine.risk_engine import _build_finding; assert _build_finding(severity='HIGH',host='h',port=443,title='Plaintext HTTP service detected',description='x',recommendation='y')['compliance']; assert _build_finding(severity='LOW',host='h',port=443,title='Legacy TLS versions allowed (TLS 1.0/1.1)',description='x',recommendation='y')['compliance']; assert _build_finding(severity='HIGH',host='h',port=443,title='End-of-life OpenSSL 1.0.2 in container image',description='x',recommendation='y')['compliance']; assert _build_finding(severity='LOW',host='h',port=443,title='Container image uses quantum-vulnerable crypto library (libssl@1.1.1)',description='x',recommendation='y')['compliance']; assert _build_finding(severity='LOW',host='h',port=443,title='Unmapped',description='x',recommendation='y')['compliance']==[]"` | ❌ W0 → ✅ Plan 49-02 | ⬜ pending |
| 49-03-01 | 03 | 2 | COMPLY-05 | T-49-08, T-49-09, T-49-10 | Jinja2 autoescape; plain table markup safe for Playwright PDF | smoke (render) | `pytest tests/test_compliance_report_section.py -x -q && pytest tests/test_compliance_*.py tests/test_pqc_terminology_gate.py -x -q` | ❌ W0 → ✅ Plan 49-03 | ⬜ pending |
| 49-04-01 | 04 | 2 | COMPLY-08/09 | T-49-11, T-49-12, T-49-13 | argparse `choices=[...]` constrains --format; subparser required=True; lazy import | smoke (CLI) | `python -m compileall -q run_scan.py && pytest tests/test_compliance_cli.py -x -q && python run_scan.py compliance status \| grep -q "PCI-DSS" && python run_scan.py compliance status --format json \| python -c "import sys, json; d=json.load(sys.stdin); assert isinstance(d, dict)" && python run_scan.py --version \| grep -q "QU.I.R.K."` | ❌ W0 → ✅ Plan 49-04 | ⬜ pending |
| 49-05-01 | 05 | 3 | COMPLY-05 | — | Doc-only; no runtime surface | doc-grep | `grep -q "Compliance Summary" docs/report-interpretation.md && grep -q "PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3" docs/report-interpretation.md && grep -q "quirk compliance status" docs/report-interpretation.md && grep -q "Findings without compliance mapping" docs/report-interpretation.md` | ✅ exists | ⬜ pending |
| 49-05-02 | 05 | 3 | COMPLY-09 | — | Doc-only; UAT-SERIES update | doc-grep | `test $(grep -c "UAT-49-0[1-5]" docs/UAT-SERIES.md) -ge 5 && grep -q "quirk compliance status" docs/UAT-SERIES.md && head -30 docs/UAT-SERIES.md \| grep -E "Last Updated:.*202[6-9]" -q` | ✅ exists | ⬜ pending |
| 49-05-03 | 05 | 3 | (process gate) | T-49-14, T-49-15 | One-way write to vault; staging via /tmp; no vault content flows back | doc + git | `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md" && grep -q "type: phase" "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md" && grep -q "status: complete" "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md" && grep -q "UAT-49-0" "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md" && grep -q "Phase-49-Compliance-Mapping" "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md" && git -C "/Volumes/Digs-1TB/Development/quantum-apps/QUIRK" log -1 --format=%s \| grep -q "phase-49"` | ❌ produced by Plan 49-05 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/fixtures/chaos_lab_findings.py` — `collect_emitted_titles()` aggregator (Plan 49-01 Task 1)
- [x] `tests/test_compliance_schema.py` — D-04 gate 1 / COMPLY-06 (Plan 49-01 Task 1)
- [x] `tests/test_compliance_freshness.py` — D-04 gate 3 / COMPLY-07 (Plan 49-01 Task 1)
- [x] `tests/test_compliance_title_join.py` — D-04 gate 2 / COMPLY-02/03/04 (Plan 49-01 Task 1)
- [x] `tests/test_compliance_report_section.py` — COMPLY-05 smoke (Plan 49-01 Task 2)
- [x] `tests/test_compliance_cli.py` — COMPLY-08 smoke (Plan 49-01 Task 2)

All Wave 0 test files land in Plan 49-01 in RED state and are turned GREEN incrementally by Plans 49-02 (schema/freshness/title-join), 49-03 (report-render), and 49-04 (CLI).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual inspection of Compliance Summary section in rendered HTML | COMPLY-05 | Layout/readability is subjective | UAT-49-05 (Plan 49-05): run `lab.sh up tls-cert-defects` + `python run_scan.py --target 127.0.0.1 --report html`; open `quirk-output/<run>/report.html`; confirm Compliance Summary renders cleanly grouped by framework |
| Source URL link integrity | COMPLY-01 | URLs may change without notice | Click each `source_url` in COMPLIANCE_MAP; confirm no 404 or generic-landing-page redirect. The 12-month staleness gate (test_compliance_freshness.py) is the structural mitigation. |
| PDF rendering of Compliance Summary section | COMPLY-05 | Playwright PDF subtle-CSS failures need eye check | UAT-49-05: after the HTML check above, also confirm the PDF report generated by `--report pdf` includes the section without misalignment. Fix path if missing: revisit Plan 49-03 markup (no flex/grid/sticky/color-mix). |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has one)
- [x] Wave 0 covers all MISSING references (6 files in Plan 49-01)
- [x] No watch-mode flags (all `pytest -x -q` one-shot)
- [x] Feedback latency < 30s (compliance test suite is small)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (planner sign-off 2026-05-05; awaiting executor)
