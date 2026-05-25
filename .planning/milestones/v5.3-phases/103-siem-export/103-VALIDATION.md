---
phase: 103
slug: siem-export
status: planned
nyquist_compliant: true
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
| **Quick run command** | `python -m pytest tests/test_siem_cef.py tests/test_siem_payload_whitelist.py tests/test_siem_config.py tests/test_siem_transport.py -q` |
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 103-01 | 1 | SIEM-02 | T-103-01/02 | CEF escaping + whitelist tests fail RED | unit | `python -m pytest tests/test_siem_cef.py tests/test_siem_payload_whitelist.py -q` | ❌ W0 | ⬜ pending |
| 01-T2 | 103-01 | 1 | SIEM-02 | T-103-01/02/03 | Two-fn escaping (backslash-first), severity map, explicit whitelist | unit | `python -m pytest tests/test_siem_cef.py tests/test_siem_payload_whitelist.py -q` | ✅ after 01-T1 | ⬜ pending |
| 02-T1 | 103-02 | 1 | SIEM-01 | T-103-04/05 | Config + transport tests fail RED | unit | `python -m pytest tests/test_siem_config.py tests/test_siem_transport.py -q` | ❌ W0 | ⬜ pending |
| 02-T2 | 103-02 | 1 | SIEM-01 | T-103-04/05/06 | DB-path trap → None; UDP/TCP send; host/port format-only validation (no loopback block) | unit | `python -m pytest tests/test_siem_config.py tests/test_siem_transport.py -q` | ✅ after 02-T1 | ⬜ pending |
| 03-T1 | 103-03 | 2 | SIEM-01/02 | T-103-07/08/09 | Dispatcher + CLI-wiring tests fail RED | unit | `python -m pytest tests/test_siem_dispatcher.py tests/test_siem_export_cmd.py -q` | ❌ W0 | ⬜ pending |
| 03-T2 | 103-03 | 2 | SIEM-01/02 | T-103-07/08/09 | One event/finding; per-batch audit row; failure isolation; hook fire/no-op | unit | `python -m pytest tests/test_siem_dispatcher.py tests/test_siem_export_cmd.py -q` | ✅ after 03-T1 | ⬜ pending |
| 03-T3 | 103-03 | 2 | SIEM-01/02 | T-103-07/SC | run_scan interception + scheduler hook (isolating try/except) | unit | `python -m compileall run_scan.py quirk/cli/scheduler_cmd.py -q && python -m pytest tests/test_siem_export_cmd.py -q` | ✅ after 03-T2 | ⬜ pending |
| 04-T1 | 103-04 | 3 | SIEM-01/02 | T-103-10 | Config + CLI docs + sample [siem] block | doc-grep | `grep -iq 'export --siem' docs/configuration.md && grep -q siem docs/sample-config.yaml` | ✅ docs | ⬜ pending |
| 04-T2 | 103-04 | 3 | SIEM-01/02 | T-103-10/11 | UAT cases + vault sync + commit | doc-grep | `grep -iq siem docs/UAT-SERIES.md && test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | ✅ docs | ⬜ pending |
| 04-T3 | 103-04 | 3 | SIEM-01/02 | T-103-11 | Obsidian phase note | doc-grep | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-103-SIEM-Export.md` | ✅ docs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_siem_cef.py` — SIEM-02 CEF header field count, escaping (header vs extension, backslash-first), severity 10/8/5/3 mapping, signature slug fallback (Plan 01-T1)
- [ ] `tests/test_siem_payload_whitelist.py` — SIEM-02 cert PEM/SANs/private-key/compliance exclusion; host/port inclusion (Plan 01-T1)
- [ ] `tests/test_siem_config.py` — SIEM-01 SiemCfg loader, QUIRK_CONFIG_PATH, DB-path/binary trap → None (Plan 02-T1)
- [ ] `tests/test_siem_transport.py` — SIEM-01 UDP/TCP socketserver capture, unreachable → OSError, host/port format validation, loopback not blocked (Plan 02-T1)
- [ ] `tests/test_siem_dispatcher.py` — SIEM-01/02 one-event-per-finding, per-batch audit row, failure isolation, after-scan hook fire/no-op (Plan 03-T1)
- [ ] `tests/test_siem_export_cmd.py` — SIEM-02 run_export argparse, no-flag exit 1, --input/latest discovery, run_scan interception, missing-file clear error (Plan 03-T1)

*Each Wave-0 test file is created by the first (RED) task of its plan and made green by the second.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CEF events appear in a real SIEM (Splunk/Elastic/QRadar) | SIEM-01 | Requires a live syslog-ingesting platform | Configure [siem] target, run `quirk export --siem`, confirm one CEF event per finding in the receiving platform's event log with correct severity/host/signature/evidence |

*CEF formatting + transport are unit-tested with in-process socketserver capture; live SIEM ingestion is human-UAT.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planning)
