---
phase: 103
slug: siem-export
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-24
---

# Phase 103 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture) |
| **Quick run command** | `python -m pytest tests/test_siem_cef.py tests/test_siem_transport.py tests/test_siem_export_cmd.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~30s targeted |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched module
- **After every plan wave:** Run the phase's test files
- **Before `/gsd:verify-work`:** Full suite green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Populated by gsd-planner during planning.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_siem_cef.py` — SIEM-02 CEF formatting: header/extension escaping, severity 10/8/5/3 mapping, signature fallback to slugified title, NO cert PEM/SANs in payload
- [ ] `tests/test_siem_transport.py` — SIEM-01 syslog UDP + TCP send (in-test socketserver capture or mock socket); timeout/unreachable handling
- [ ] `tests/test_siem_export_cmd.py` — `quirk export --siem` reads findings json, one event per finding, failure isolation (unreachable endpoint → error + audit row, scan record intact)

*Confirmed during planning against existing pytest infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CEF events appear in a real SIEM (Splunk/Elastic/QRadar) | SIEM-01 | Requires a live syslog-ingesting platform | Configure [siem] target, run `quirk export --siem`, confirm one CEF event per finding in the receiving platform's event log with correct severity/host/signature/evidence |

*CEF formatting + transport are unit-tested with in-process capture; live SIEM ingestion is human-UAT.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
