---
phase: 200
slug: report-branding-templates
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-11
---

# Phase 200 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend only — no dashboard UI work this phase) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest -q tests/test_report_template_sandbox.py tests/test_report_branding.py tests/test_report_branding_cli.py tests/test_report_path_guard.py tests/test_report_profiles.py` |
| **Full suite command** | `.venv/bin/python -m pytest -q -m ""` |
| **Estimated runtime** | quick ~90s; full ~18min |

---

## Sampling Rate

- **After every task commit:** scoped quick command for the touched surface + `.venv/bin/python -m compileall -q quirk`
- **After every plan wave:** the five new test files plus the report regression set
  (`tests/test_html_report.py tests/test_docx_report.py tests/test_reports_writer.py
  tests/test_report_injection_hardening.py tests/test_report_sanitization.py
  tests/test_report_render_parity.py tests/test_cross_surface_parity.py
  tests/test_report_coverage_parity.py tests/test_score_render_parity.py
  tests/test_config.py tests/test_profiles.py tests/test_error_codes_freshness.py`)
- **Before verification:** full suite green (failing-node SET empty — compare SETS, never raw counts)
- **Max feedback latency:** 90 seconds (scoped runs)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 200-01-T1 | 01 | 1 | RPT-02 | T-200-01/02/03 | SSTI corpus + override/fallback/autoescape/sanitize legs written against the real pipeline; RED first | unit | `.venv/bin/python -m pytest -q tests/test_report_template_sandbox.py` | ❌ W0 | ⬜ pending |
| 200-01-T2 | 01 | 1 | RPT-02 | T-200-01/02 | `SandboxedEnvironment` unconditional at the single env site; autoescape + sanitize preserved on the same instance; ChoiceLoader override | unit | `.venv/bin/python -m compileall -q quirk/reports/html_renderer.py && .venv/bin/python -m pytest -q tests/test_report_template_sandbox.py` | ❌ W0 | ⬜ pending |
| 200-01-T3 | 01 | 1 | RPT-02 | T-200-01 | Packaged template unregressed under the sandbox; written GO/NO-GO verdict with per-payload evidence | regression | `.venv/bin/python -m pytest -q tests/test_html_report.py tests/test_report_injection_hardening.py tests/test_report_sanitization.py tests/test_report_render_parity.py tests/test_cross_surface_parity.py tests/test_reports_writer.py` | ✅ | ⬜ pending |
| 200-02-T1 | 02 | 1 | RPT-01, RPT-04 | — | `report:` section loads with all-optional fields; absent block = today's behaviour; flattened `_user_set_fields` stamped; both YAML surfaces changed in lockstep | unit | `.venv/bin/python -m pytest -q tests/test_config.py tests/test_profiles.py` + the inline `CONFIG_OK` assertion script | ✅ | ⬜ pending |
| 200-02-T2 | 02 | 1 | RPT-03 | T-200-05/08 | One named path guard rejecting `..` with a coded `CONFIG-003` error naming field + value; `logo_path` warn-not-fail asymmetry; `docs/error-codes.md` regenerated | unit + CI gate | `.venv/bin/python -m pytest -q tests/test_error_codes_freshness.py` + the inline `GUARD_OK` assertion script | ✅ | ⬜ pending |
| 200-02-T3 | 02 | 1 | RPT-03 | T-200-06 | Runtime-enumeration sweep over every `schemas.py` BaseModel, every `_KNOWN_*_OVERLAY_KEYS`, and `_SECTION_TITLES`; non-vacuous; demonstrated able to fail | guard | `.venv/bin/python -m pytest -q tests/test_report_path_guard.py` | ❌ W0 | ⬜ pending |
| 200-03-T1 | 03 | 2 | RPT-01 | T-200-09/10/11 | HTML/PDF cover logo + identity block, per-field conditional, logo fallback order, no `\| safe` on branding | unit | `.venv/bin/python -m pytest -q tests/test_html_report.py tests/test_report_template_sandbox.py tests/test_report_injection_hardening.py` | ✅ | ⬜ pending |
| 200-03-T2 | 03 | 2 | RPT-01 | T-200-10 | DOCX cover logo + identity + header/footer; all `docx` imports lazy (AST-verified); never crashes the render | unit | `.venv/bin/python -m pytest -q tests/test_docx_report.py tests/test_cross_surface_parity.py` + the inline `LAZY_IMPORT_OK` AST check | ✅ | ⬜ pending |
| 200-03-T3 | 03 | 2 | RPT-01 | T-200-09 | Presence-based cross-surface branding, partial-field absence, logo precedence, degradation, escaping | unit | `.venv/bin/python -m pytest -q tests/test_report_branding.py` | ❌ W0 | ⬜ pending |
| 200-04-T1 | 04 | 2 | RPT-01 | T-200-12/14 | Identity text on executive + scorecard + console; no logo on CLI; congruence regions untouched | unit | `.venv/bin/python -m pytest -q tests/test_reports_writer.py tests/test_report_render_parity.py tests/test_cross_surface_parity.py tests/test_score_render_parity.py` | ✅ | ⬜ pending |
| 200-04-T2 | 04 | 2 | RPT-01 | T-200-12 | CLI-surface presence/absence legs incl. byte-identical absent-branding comparison and the no-logo negative | unit | `.venv/bin/python -m pytest -q tests/test_report_branding_cli.py` | ❌ W0 | ⬜ pending |
| 200-05-T1 | 05 | 2 | RPT-04 | T-200-15/16/17/18 | Profile name validated before path construction; `safe_load`/`safe_dump` only; merge gates on `_user_set_fields` | unit | `.venv/bin/python -m compileall -q quirk/report_profiles.py` + the inline `PROFILE_MODULE_OK` assertion script | ❌ W0 | ⬜ pending |
| 200-05-T2 | 05 | 2 | RPT-04 | T-200-15 | `quirk report profile save\|list` + `--report-profile`; coded errors instead of tracebacks; applied before any report is written | integration | `QUIRK_PROFILES_DIR=$(mktemp -d) .venv/bin/python run_scan.py report profile list && .venv/bin/python run_scan.py --help \| grep -q report-profile` | ✅ | ⬜ pending |
| 200-05-T3 | 05 | 2 | RPT-04 | T-200-15/16/17/18 | Round-trip, precedence (both halves), name rejection, traversal-in-profile-file, unsafe-YAML non-execution, CLI round trip | unit | `.venv/bin/python -m pytest -q tests/test_report_profiles.py` | ❌ W0 | ⬜ pending |
| 200-06-T1 | 06 | 3 | RPT-05 | T-200-21/22 | All nine parity files named with measured counts; congruence raising site stated correctly; no source touched | manual + gate | `test -f .planning/backlog/999.105-customizable-reporting-engine/TIER2-GO-NO-GO.md && git status --porcelain quirk/ tests/` (must be empty) | — | ⬜ pending |
| 200-06-T2 | 06 | 3 | RPT-05 | T-200-20 | Verdict + sizing written; substance landed in the TRACKED HORIZON.md 999.105 row | manual + gate | `grep -n '^\*\*Verdict:\*\* \(GO\|NO-GO\|GO-WITH-CONDITIONS\)' .planning/backlog/999.105-customizable-reporting-engine/TIER2-GO-NO-GO.md && grep -c TIER2-GO-NO-GO .planning/HORIZON.md` | — | ⬜ pending |
| 200-07-T1 | 07 | 4 | RPT-01..RPT-04 | T-200-25 | Config keys, CLI commands, flag disambiguation, and the sandbox/autoescape/sanitize posture documented | doc gate | `grep -c "report.branding" docs/configuration.md && grep -c "report-profile" docs/operators-guide.md && grep -c "quirk report profile" docs/getting-started.md` | ✅ | ⬜ pending |
| 200-07-T2 | 07 | 4 | RPT-01..RPT-05 | T-200-23 | UAT Series 200 fully dispositioned; every DEFERRED citation `--collect-only` resolvable; visual cases honest GAPs | CI gate | `.venv/bin/python -m pytest -q tests/test_uat_zero_undispositioned_gate.py tests/test_uat_disposition_integrity.py tests/test_error_codes_freshness.py` | ✅ | ⬜ pending |
| 200-07-T3 | 07 | 4 | RPT-01..RPT-05 | T-200-24/26 | Vault bodies byte-identical to sources; phase note complete; validation closed before the ROADMAP flip; no mutating GSD verb | gate | `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-200-Report-Branding-Templates.md" && diff <(tail -n +9 "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md") docs/UAT-SERIES.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_report_template_sandbox.py` — RPT-02 SSTI containment gate + loader/override/autoescape legs (build FIRST; it is the phase's internal go/no-go)
- [ ] `tests/test_report_path_guard.py` — RPT-03 guard units + runtime-enumeration dashboard-exclusion sweep
- [ ] `tests/test_report_branding.py` — RPT-01 HTML/DOCX cross-surface presence
- [ ] `tests/test_report_branding_cli.py` — RPT-01 executive/scorecard/console identity text
- [ ] `tests/test_report_profiles.py` — RPT-04 round-trip, precedence, name/YAML rejection

No framework install needed. No shared-fixture gap: report tests build cfg objects inline per
existing convention — pin the `report` attribute explicitly on every fixture cfg (spec-mock
auto-vivify trap).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Branded HTML/PDF + DOCX visual appearance (logo placement, cover identity block, running header/footer) | RPT-01 | Render tests assert presence, not appearance (project convention) | Generate a report with a test logo + full branding set; visually inspect cover/header/footer on HTML and DOCX. Recorded as UAT-200-01/02 GAP legs. |
| Tier 2 go/no-go document quality (is the verdict actually argued from the evidence?) | RPT-05 | A decision document has no automatable truth condition | Human review of `TIER2-GO-NO-GO.md` against the congruence-guard and parity-suite evidence sections, plus the HORIZON.md 999.105 row diff. Recorded as UAT-200-11. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
