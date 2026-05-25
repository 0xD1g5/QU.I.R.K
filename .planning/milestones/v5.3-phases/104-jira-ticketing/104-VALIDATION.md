---
phase: 104
slug: jira-ticketing
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-25
---

# Phase 104 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture) |
| **Quick run command** | `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py tests/test_ticket_cmd.py tests/test_install_all_includes_tickets.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~30s targeted (slow CI guard ~30-180s) |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched module
- **After every plan wave:** Run the phase's test files
- **Before `/gsd:verify-work`:** Full suite green
- **Max feedback latency:** 30 seconds (excluding the @slow CI guard)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P01-T1 | 104-01 | 1 | TICKET-04, TICKET-03 | T-104-01/02/03/04 | safe_str error_summary; evidence field whitelist; dedup orchestration; hex fingerprint | unit | `python -m compileall quirk/ticketing/ -q && python -c "from quirk.ticketing import TicketingChannel,load_ticketing_config"` | ❌ W0 | ⬜ pending |
| P01-T2 | 104-01 | 1 | TICKET-04, TICKET-03 | T-104-01/03 | fingerprint formula pinned; dedup proven; failure isolation; token absent | unit | `python -m pytest tests/test_ticketing_base.py -x -q` | ❌ W0 | ⬜ pending |
| P02-T1 | 104-02 | 2 | TICKET-01, TICKET-03 | T-104-05/06/07/08 | SSRF guard; lazy jira import; double-quoted JQL | unit | `python -m compileall quirk/ticketing/jira.py -q && python -c "import quirk.ticketing.jira; from quirk.ticketing import JiraChannel"` | ❌ W0 | ⬜ pending |
| P02-T2 | 104-02 | 2 | TICKET-01, TICKET-03 | T-104-06/07 | create-once + comment; missing-extra skip; creds not logged | unit | `python -m pytest tests/test_ticketing_jira.py tests/test_ticketing_base.py -x -q` | ❌ W0 | ⬜ pending |
| P03-T1 | 104-03 | 3 | TICKET-01 | T-104-SC | jira slopcheck OK; [identity] exclusion preserved | unit | `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb'))"` (jira in tickets+all) | n/a | ⬜ pending |
| P03-T2 | 104-03 | 3 | TICKET-01, TICKET-03 | T-104-09/10 | graceful missing-extra exit; safe_str; return-pattern interception | unit | `python -m compileall quirk/cli/ticket_cmd.py run_scan.py -q && grep -q 'argv\[1\] == "ticket"' run_scan.py` | ❌ W0 | ⬜ pending |
| P03-T3 | 104-03 | 3 | TICKET-01, TICKET-03 | T-104-09/SC | exit codes; advisory; [all] pulls jira | unit + slow | `python -m pytest tests/test_ticket_cmd.py -x -q && python -m pytest tests/test_install_all_includes_tickets.py -m slow -q` | ❌ W0 | ⬜ pending |
| P04-T1 | 104-04 | 4 | TICKET-01 | T-104-11 | sample uses env-var NAMES only | doc | `grep -q "quirk ticket create" docs/configuration.md && grep -q "jira_token_env" docs/sample-config.yaml` | n/a | ⬜ pending |
| P04-T2 | 104-04 | 4 | TICKET-01/03/04 | T-104-11 | UAT case synced+committed; phase note written | doc | `grep -q "ticket create" docs/UAT-SERIES.md && test -f .../Phase-104-Jira-Ticketing.md` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ticketing_base.py` (Plan 01 T2) — TICKET-04 ABC contract; fingerprint = SHA256(host:port::title) stability/formula; shared dedup orchestration; integration_deliveries audit hash; failure isolation
- [ ] `tests/test_ticketing_jira.py` (Plan 02 T2) — TICKET-01/03 Jira create_issue (mocked) once on first run; JQL label search + rediscovery comment on second; creds never logged; missing-[tickets] graceful skip; JQL project-key quoting
- [ ] `tests/test_ticket_cmd.py` (Plan 03 T3) — `quirk ticket create` reads findings json; one issue per finding; missing-extra/missing-file/missing-config exits; happy-path exit 0
- [ ] `tests/test_install_all_includes_tickets.py` (Plan 03 T3) — [tickets] joins [all] CI guard (jira in resolved set), @pytest.mark.slow

*Confirmed during planning against existing pytest infrastructure (mirrors test_install_all_includes_notify.py).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Jira issue creation + dedup | TICKET-01/03 | Requires a real Jira Cloud/Server instance + API token | Configure [ticketing], run `quirk ticket create`, confirm one issue per finding with QRAMM evidence; re-run, confirm rediscovery comment instead of duplicates |

*Jira API is unit-tested with a mocked client; live issue creation is human-UAT.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (targeted; slow CI guard excluded)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned 2026-05-25
