---
phase: 49-compliance-mapping
verified: 2026-05-05T00:00:00Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 49: Compliance Mapping — Verification Report

**Phase Goal:** QUIRK findings are mapped to PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3 control references via a new `quirk/compliance/` module, with a "Compliance Summary" section in HTML/PDF reports and freshness metadata to prevent silent map rot.
**Verified:** 2026-05-05
**Status:** PASS
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | `quirk/compliance/` exports `COMPLIANCE_MAP`, `UNMAPPED_TITLES`, `TITLE_PREFIX_ALIASES`, `STALENESS_THRESHOLD_DAYS`, `status_report` | VERIFIED | `quirk/compliance/__init__.py:237-243` `__all__` lists all 5 symbols; module imports resolve and all are populated |
| 2  | Every emitted finding title is mapped or in `UNMAPPED_TITLES` (title-join gate) | VERIFIED | `tests/test_compliance_title_join.py` 2/2 PASS |
| 3  | Every `COMPLIANCE_MAP` entry has framework + control + version + last_verified (≤365d) + https:// source_url | VERIFIED | `tests/test_compliance_schema.py` 4/4 PASS; `tests/test_compliance_freshness.py` 1/1 PASS; `_pci/_hipaa/_fips` factory fns at `__init__.py:39-66` enforce schema; all `_PHASE_49_VERIFIED = "2026-05-05"` (0 days old) |
| 4  | Every finding from `risk_engine._build_finding` carries `compliance: list[dict]` | VERIFIED | `quirk/engine/risk_engine.py:91-92` — `"compliance": COMPLIANCE_MAP.get(_normalize_for_compliance(title), [])` injected at chokepoint; `_normalize_for_compliance` (line 27) handles f-string title prefixes |
| 5  | FindingItem DTO declares `compliance: list[dict] = []` | VERIFIED | `quirk/dashboard/api/schemas.py:65` — `compliance: List[Dict[str, Any]] = []` |
| 6  | Rendered HTML report contains "Compliance Summary" with PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3 subsections + "Findings without compliance mapping" | VERIFIED | `quirk/reports/templates/report.html.j2:245` `<h2>Compliance Summary</h2>`; line 251 framework list `['PCI-DSS 4.0.1', 'HIPAA 45 CFR', 'FIPS 140-3']` rendered as `<h3>` per framework; line 287/297 `<h3>Findings without compliance mapping</h3>`; `tests/test_compliance_report_section.py` 2/2 PASS |
| 7  | `quirk compliance status` exits 0 with text + JSON output | VERIFIED | Smoke: `python run_scan.py compliance status` and `--format json` both produce expected output (3 frameworks: FIPS 140-3, HIPAA 45 CFR, PCI-DSS 4.0.1) and exit 0; `tests/test_compliance_cli.py` 3/3 PASS |
| 8  | `docs/report-interpretation.md` has Compliance Summary subsection | VERIFIED | `docs/report-interpretation.md:163-178` — "Compliance Summary" content + assessor handoff guidance + freshness verification instructions |
| 9  | `docs/UAT-SERIES.md` has UAT-49-01..05 + bumped Last Updated date | VERIFIED | Line 4 `Last Updated: 2026-05-05 (Phase 49 wrap: UAT-49-01..05 added...)`; UAT-49-01 (line 6415), UAT-49-02 (6438), UAT-49-03 (6461), UAT-49-04 (6484), UAT-49-05 referenced in note line 6409 |
| 10 | Obsidian vault phase note exists, hub links it, UAT-Series mirror refreshed | VERIFIED | `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md` exists (status: complete); `_QUIRK-Hub.md:14,30` links `[[Phase-49-Compliance-Mapping]]`; `UAT-Series.md` mirror present |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `quirk/compliance/__init__.py` | Module with COMPLIANCE_MAP, UNMAPPED_TITLES, TITLE_PREFIX_ALIASES, STALENESS_THRESHOLD_DAYS, status_report | VERIFIED | 244 lines; all 5 symbols in `__all__`; STALENESS_THRESHOLD_DAYS=365 |
| `quirk/engine/risk_engine.py` | `_build_finding` injects `compliance` via `_normalize_for_compliance` | VERIFIED | line 91-92 wires lookup; line 27 normalizer handles f-string title prefixes |
| `quirk/dashboard/api/schemas.py` | FindingItem.compliance field | VERIFIED | line 65 declared with default `[]` |
| `quirk/reports/templates/report.html.j2` | Compliance Summary section + 3 framework subsections + unmapped subsection | VERIFIED | lines 244-299 |
| `tests/test_compliance_schema.py` | Schema gate | VERIFIED | 4 tests pass |
| `tests/test_compliance_title_join.py` | Title-join gate | VERIFIED | 2 tests pass |
| `tests/test_compliance_freshness.py` | Staleness gate (≤365d) | VERIFIED | 1 test passes |
| `tests/test_compliance_report_section.py` | HTML report section | VERIFIED | 2 tests pass |
| `tests/test_compliance_cli.py` | CLI smoke (text + json) | VERIFIED | 3 tests pass |
| `run_scan.py` compliance subcommand | argparse pre-dispatch for `compliance status` | VERIFIED | lines 223-244 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `_build_finding` | `COMPLIANCE_MAP` | `_normalize_for_compliance(title)` lookup | WIRED | risk_engine.py:91-92, normalizer at line 27, import at line 7 |
| `report.html.j2` | finding `compliance` field | `f.get('compliance', [])` per-framework filter | WIRED | template lines 254-258 (mapped) + 281-285 (unmapped) |
| `run_scan compliance status` | `quirk.compliance.status_report` | argparse intercept + import | WIRED | run_scan.py:242-243; smoke check produces 3-framework output |
| `FindingItem` DTO | `compliance` field on dict | Pydantic field with default `[]` | WIRED | schemas.py:65 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Pytest gates pass | `pytest test_compliance_*.py test_pqc_terminology_gate.py test_risk_engine.py` | 50 passed in 1.04s | PASS |
| Compileall | `python -m compileall quirk/ run_scan.py` | clean | PASS |
| CLI text output | `python run_scan.py compliance status` | 3-framework table, exit 0 | PASS |
| CLI JSON output | `python run_scan.py compliance status --format json \| python -m json.tool` | valid JSON, 3 keys, exit 0 | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| COMPLY-01 | `quirk/compliance/` module with COMPLIANCE_MAP | SATISFIED | module exists, marked Complete in REQUIREMENTS.md:129 |
| COMPLY-02 | PCI-DSS 4.0.1 controls 4.2.1/4.2.1.1/6.3.3/8.3.2 | SATISFIED | all 4 controls present in COMPLIANCE_MAP entries |
| COMPLY-03 | HIPAA §164.312(a)(2)(iv)/(e)(1)/(e)(2)(ii) | SATISFIED | all 3 controls present |
| COMPLY-04 | FIPS 140-3 approved/not-approved | SATISFIED | `_fips()` entries with SP 800-131A/SP 800-186/NIST IR 8547 markers |
| COMPLY-05 | HTML+PDF Compliance Summary section | SATISFIED | template lines 244-299; PDF inherits via Playwright |
| COMPLY-06 | Schema test enforces `version` key | SATISFIED | test_compliance_schema.py 4/4 pass |
| COMPLY-07 | `last_verified` + `source_url` per entry | SATISFIED | factory fns enforce; schema test passes |
| COMPLY-08 | CI staleness check (>12 months) | SATISFIED | test_compliance_freshness.py implements 365d gate, passes; **NB:** REQUIREMENTS.md:136 still shows "Pending" — see Warning below |
| COMPLY-09 | `quirk compliance status` CLI | SATISFIED | run_scan.py:223-244; smoke checks pass |

### Anti-Patterns Found

None. Module has docstring, factory functions, well-commented `UNMAPPED_TITLES`, no TODO/FIXME stubs in delivered code (only the forward-pointer `# TODO Phase 50` for operators-guide.md maintenance cadence — intentional, documented in CONTEXT).

### Human Verification Required

None — all criteria are programmatically verifiable and verified.

### Gaps Summary

No blockers. One minor inconsistency:

**Warning (non-blocking):** `.planning/REQUIREMENTS.md:136` lists COMPLY-08 status as "Pending" although the staleness gate is fully implemented (`STALENESS_THRESHOLD_DAYS=365` constant + `tests/test_compliance_freshness.py` walking every entry, currently green). The phase note at `.planning/phases/49-compliance-mapping/Phase-49-Compliance-Mapping.md` (Obsidian) and the closure log treat COMPLY-08 as complete. Recommend bumping REQUIREMENTS.md:136 to "Complete" in a follow-up housekeeping commit. This does not affect the Phase 49 goal.

---

*Verified: 2026-05-05*
*Verifier: Claude (gsd-verifier)*
