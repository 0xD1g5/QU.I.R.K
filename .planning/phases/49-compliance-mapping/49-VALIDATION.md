---
phase: 49
slug: compliance-mapping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
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

*To be filled by gsd-planner. One row per task in PLAN.md files. Each row maps task → requirement → automated test command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 0 | COMPLY-01 | — | N/A | unit | `pytest tests/test_compliance_map_completeness.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_compliance_map_completeness.py` — asserts every COMPLIANCE_MAP entry has version + last_verified + source_url (COMPLY-01, COMPLY-06)
- [ ] `tests/test_compliance_staleness.py` — asserts no entry's last_verified is older than 12 months (COMPLY-07)
- [ ] `tests/test_compliance_report_section.py` — asserts HTML and PDF reports contain "Compliance Summary" section (COMPLY-05)
- [ ] `tests/test_compliance_cli.py` — asserts `quirk compliance status` prints per-framework version, last_verified, source_url (COMPLY-08)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual inspection of Compliance Summary section in rendered HTML | COMPLY-05 | Layout/readability is subjective | Run `quirk scan --target localhost --report html`, open `quirk-output/<run>/report.html`, confirm Compliance Summary renders cleanly grouped by framework |
| Source URL link integrity | COMPLY-01 | URLs may change without notice | Click each `source_url` in COMPLIANCE_MAP, confirm no 404 or redirect to a generic landing page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
