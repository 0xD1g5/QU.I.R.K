---
phase: 104-jira-ticketing
plan: "02"
subsystem: ticketing
tags: [jira, ticketing, abc, dedup, fingerprint, ssrf, lazy-import, optional-extra, jql]

dependency_graph:
  requires:
    - phase: 104-01
      provides: TicketingChannel ABC (find_by_fingerprint / create_issue_from_finding / add_rediscovery_comment abstract methods); JiraTicketingCfg (jira_url, jira_user_env, jira_token_env, project_key, issue_type, auth_mode, allow_internal); dispatch_finding orchestration; safe_str ISEC-02
  provides:
    - quirk.ticketing.JiraChannel — concrete jira backend; lazy jira import; SSRF guard; cloud/server auth; JQL label dedup
    - tests/test_ticketing_jira.py — 5 mocked-JIRA unit tests covering create, dedup, missing-extra, creds scrubbing, JQL quoting
  affects:
    - Phase 105 ServiceNow — adds servicenow.py only; zero changes to base.py or jira.py required

tech-stack:
  added: [quirk/ticketing/jira.py, tests/test_ticketing_jira.py]
  patterns:
    - "Lazy import pattern: from jira import JIRA inside __init__ only (optional-extra import trap guard)"
    - "SSRF guard before any connection: validate_external_url(cfg.jira_url, allow_internal=cfg.allow_internal)"
    - "JQL double-quoting: project = \"KEY\" AND labels = \"fp\" (Pitfall 4 prevention)"
    - "Mock pattern: patch.dict(sys.modules, {jira: MagicMock(JIRA=mock_cls)}) for lazy-import tests"
    - "Bearer token scrubbing test: plant Authorization: Bearer TOKEN in exc; assert absent from error_summary"

key-files:
  created:
    - quirk/ticketing/jira.py
    - tests/test_ticketing_jira.py
  modified:
    - quirk/ticketing/__init__.py

key-decisions:
  - "JiraChannel lazy-imports 'from jira import JIRA' inside __init__ only — module-scope import forbidden (optional-extra import trap)"
  - "SSRF guard passes allow_internal=cfg.allow_internal to validate_external_url — self-hosted Jira on RFC1918 is operator-controlled"
  - "Cloud auth: JIRA(server=url, basic_auth=(user, token)); Server auth: JIRA(server=url, token_auth=token)"
  - "JQL: project = \"KEY\" AND labels = \"fp\" — both sides double-quoted (project_key for multi-word safety; fp is 64-char hex, safe to embed)"
  - "test_missing_extra_graceful_skip uses patch.dict(sys.modules, {'jira': None}) to force ImportError at lazy-import site"
  - "test_credentials_not_in_logs plants 'Authorization: Bearer FAKE_JIRA_TOKEN_abc123xyz' in exc — matches safe_str Bearer pattern"

patterns-established:
  - "Lazy-import + SSRF guard + auth construction: see JiraChannel.__init__ for the canonical shape Phase 105 should mirror"
  - "Test helper _build_channel: patches sys.modules during construction only, allows normal use after"

requirements-completed: [TICKET-01, TICKET-03]

duration: 20min
completed: "2026-05-25"
---

# Phase 104 Plan 02: JiraChannel Backend + JQL Label Dedup Summary

**JiraChannel(TicketingChannel) delivering per-finding Jira issue creation with SHA256-label JQL dedup, lazy jira import, SSRF guard, and Bearer-token safe_str scrubbing — Phase 105 ServiceNow requires zero changes to jira.py or base.py.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-25T04:20:00Z
- **Completed:** 2026-05-25T04:43:50Z
- **Tasks:** 2
- **Files modified:** 3 (created 2, modified 1)

## Accomplishments

- `quirk/ticketing/jira.py` — 121-line JiraChannel subclass with lazy `from jira import JIRA` inside `__init__`, SSRF guard via `validate_external_url(cfg.jira_url, allow_internal=cfg.allow_internal)`, cloud vs server auth paths, JQL dedup (`project = "KEY" AND labels = "fp"`), and rediscovery comment body
- `tests/test_ticketing_jira.py` — 5 mocked-JIRA unit tests covering all TICKET-01/03 behaviors and ISEC-02/04 security properties
- `quirk/ticketing/__init__.py` — re-exports JiraChannel without triggering the jira import until instantiation

## Task Commits

1. **RED gate** — `bfe0b9b` test(104-02): RED gate — JiraChannel import fails before jira.py exists
2. **Task 1: JiraChannel backend + dedup** — `04470de` feat(104-02): JiraChannel backend — lazy jira import + SSRF guard + cloud/server auth + JQL dedup
3. **Task 2: Mocked-JIRA unit tests** — `b36827c` test(104-02): Mocked-JIRA unit tests — create, dedup-once-then-comment, missing-extra, creds scrubbing, JQL quoting
4. **Cleanup** — `e5dbe2c` chore(104-02): remove TDD RED gate file

## Files Created/Modified

- `quirk/ticketing/jira.py` — JiraChannel(TicketingChannel): lazy jira import + SSRF guard + cloud/server auth + JQL dedup + create_issue + add_comment (121 lines)
- `tests/test_ticketing_jira.py` — 5 mocked-JIRA unit tests; real tmp DB for dedup test (287 lines)
- `quirk/ticketing/__init__.py` — added JiraChannel to re-exports and __all__

## Decisions Made

- Lazy import placed at the top of `__init__` (try/except around `from jira import JIRA`) before SSRF guard — ensures ImportError is raised immediately with the advisory message, not after URL validation work
- `allow_internal=cfg.allow_internal` passed to `validate_external_url` — self-hosted Jira operators on RFC1918 set `allow_internal: true` in YAML; metadata IPs are always blocked regardless
- `test_missing_extra_graceful_skip` uses `patch.dict("sys.modules", {"jira": None})` — setting a module to `None` causes `from jira import JIRA` to raise `ImportError`, matching real absent-package behavior
- `test_credentials_not_in_logs` plants `Authorization: Bearer FAKE_JIRA_TOKEN_abc123xyz` (not a bare token) to match safe_str's Bearer regex pattern, matching the fix established in Plan 01 deviation #2

## Deviations from Plan

None — plan executed exactly as written. The mock pattern, SSRF guard signature, JQL double-quoting, and Bearer-token test approach all matched the PATTERNS.md reference exactly.

## Issues Encountered

None.

## Verification

```
python -m compileall quirk/ticketing/jira.py -q  # clean
python -c "import quirk.ticketing.jira; from quirk.ticketing import JiraChannel; print('ok')"  # ok
python -m pytest tests/test_ticketing_jira.py tests/test_ticketing_base.py -x -q  # 13 passed
```

## Known Stubs

None — all three abstract methods are fully implemented; no placeholder returns.

## Threat Flags

None — no new network endpoints or auth paths beyond the plan's threat model. SSRF guard (T-104-05) and credential scrubbing (T-104-06) are implemented and tested. Lazy import (T-104-07) and JQL safety (T-104-08) verified.

## Next Phase Readiness

- JiraChannel is complete and ready for Phase 105 ServiceNow to subclass TicketingChannel independently
- `quirk/ticketing/__init__.py` exports both TicketingChannel and JiraChannel safely
- Phase 103 CLI pattern (ticket_cmd.py) can now wire JiraChannel.dispatch_finding in a subsequent plan

## Self-Check: PASSED

- [x] `quirk/ticketing/jira.py` — FOUND (121 lines, > 50 min_lines)
- [x] `tests/test_ticketing_jira.py` — FOUND, contains `def test_dedup_creates_once_then_comments`
- [x] `quirk/ticketing/__init__.py` — FOUND, exports JiraChannel
- [x] No module-scope `import jira` or `from jira` in jira.py (grep confirmed)
- [x] JQL double-quotes project key and fp in find_by_fingerprint
- [x] validate_external_url called before JIRA() construction
- [x] Commit 04470de — feat(104-02): JiraChannel backend
- [x] Commit b36827c — test(104-02): Mocked-JIRA unit tests
- [x] `python -m pytest tests/test_ticketing_jira.py tests/test_ticketing_base.py -x -q` — 13 passed
