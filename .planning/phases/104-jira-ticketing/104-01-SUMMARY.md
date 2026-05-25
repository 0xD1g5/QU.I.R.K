---
phase: 104-jira-ticketing
plan: "01"
subsystem: ticketing
tags: [abc, fingerprint, dedup, audit, config, integration]
dependency_graph:
  requires: [quirk.models.IntegrationDelivery, quirk.util.safe_exc.safe_str]
  provides: [quirk.ticketing.TicketingChannel, quirk.ticketing.TicketingCfg, quirk.ticketing.load_ticketing_config]
  affects: [Phase 105 ServiceNow — inherits TicketingChannel with zero base.py changes]
tech_stack:
  added: [quirk/ticketing/__init__.py, quirk/ticketing/base.py, quirk/ticketing/config.py, tests/test_ticketing_base.py]
  patterns: [ABC abstractmethod, SHA256 fingerprint, WR-01 commit-outside-try, safe_str ISEC-02, exfiltration whitelist, SQLite-safe config loader]
key_files:
  created:
    - quirk/ticketing/__init__.py
    - quirk/ticketing/base.py
    - quirk/ticketing/config.py
    - tests/test_ticketing_base.py
  modified: []
decisions:
  - "Fingerprint formula locked as SHA256(host:port::title) — NOT protocol:category (findings JSON lacks those keys); title is category proxy; formula is a @staticmethod in base.py that subclasses MUST NOT override"
  - "build_ticket_evidence uses finding-dict fields only (whitelist: title/severity/host/port/description/recommendation/quantum_risk); never evidence_bridge.populate_cvi_suggestions which is scan-level not per-finding"
  - "__init__.py exports TicketingChannel + config only (no JiraChannel import) until Plan 02; preserves clean import without [tickets] installed"
  - "safe_str scrubs Authorization Bearer patterns from exception messages; test plants a jira-style auth leak to prove ISEC-02 enforcement"
metrics:
  duration: 15
  completed_date: "2026-05-25"
  tasks: 2
  files: 4
---

# Phase 104 Plan 01: TicketingChannel ABC + Config + Fingerprint Summary

**One-liner:** SHA256(host:port::title) fingerprint ABC with WR-01 audit, exfiltration whitelist, and SQLite-safe YAML config loader — Phase 105 reuses with zero base.py changes.

## What Was Built

### Task 1: TicketingChannel ABC + config dataclasses + loader

**`quirk/ticketing/base.py`** — The load-bearing abstraction (TICKET-04):
- `class TicketingChannel(ABC)` with `destination: str = "unknown"` class attr
- Three `@abstractmethod`s returning generic types only (`Optional[str]`, `str`, `None`) — no `jira.*` types anywhere in base.py
- `@staticmethod compute_fingerprint(finding: dict) -> str` — locked formula `SHA256(f"{host}:{port}::{title}")` using `str(finding.get(k) or "")` for all keys; docstring prohibits subclass override
- `@staticmethod build_ticket_evidence(finding: dict) -> str` — exfiltration whitelist (title, severity, host, port, description, recommendation, quantum_risk only; check_id/compliance/PEM excluded)
- `dispatch_finding(finding, db, scan_id) -> None` — computes fp + evidence, calls find_by_fingerprint → dedup branch or create branch, catches all exceptions into `error_summary = safe_str(exc)`, builds `IntegrationDelivery` row, `db.add(row)`, then commits in a separate try block **outside** the delivery try/except (WR-01)

**`quirk/ticketing/config.py`** — Config loader (mirrors notify/config.py + siem/config.py):
- `@dataclass JiraTicketingCfg` — env-var-NAME fields only (jira_user_env, jira_token_env are names not values); allow_internal for self-hosted; auth_mode "cloud"/"server"
- `@dataclass TicketingCfg` — `jira: Optional[JiraTicketingCfg] = None`
- `load_ticketing_config(path=None) -> TicketingCfg | None` — priority: explicit > QUIRK_CONFIG_PATH > None; `except Exception: return None` SQLite-safe guard
- `_parse_ticketing_cfg` + `_parse_jira_cfg` helpers; auth_mode lowercased; returns None if no jira_url

**`quirk/ticketing/__init__.py`** — Package init:
- Re-exports `TicketingChannel`, `TicketingCfg`, `load_ticketing_config`
- No `jira.py` import (Plan 02 adds JiraChannel)

### Task 2: Wave-0 unit tests for the ABC contract

**`tests/test_ticketing_base.py`** — 8 tests, all green:
- `_StubChannel` — implements only 3 abstractmethods, records created/commented calls
- `_RaisingChannel` — raises from create with Authorization Bearer token in message
- `test_fingerprint_stable` — same dict → same 64-char hex on repeat
- `test_fingerprint_formula` — pins exact `SHA256(b"h:443::Some Title")` value
- `test_fingerprint_missing_fields` — empty dict → `SHA256(b":::")` (3 colons)
- `test_build_ticket_evidence` — whitelist enforced; check_id absent
- `test_dispatch_creates_issue` — find=None → create called once
- `test_dispatch_dedup` — find=existing → comment called; create NOT called
- `test_audit_row_finding_hash` — `IntegrationDelivery.finding_hash == compute_fingerprint(finding)`; destination="stub"; status="ok"
- `test_dispatch_failure_isolation` — raises with Bearer token → no caller raise; status="failed"; `FAKE_JIRA_TOKEN_abc123xyz` NOT in error_summary (safe_str ISEC-02 enforced)

## Verification

```
python -m compileall quirk/ticketing/ -q  # clean
python -c "from quirk.ticketing import TicketingChannel, TicketingCfg, load_ticketing_config; assert hasattr(TicketingChannel,'compute_fingerprint'); print('ok')"  # ok
python -m pytest tests/test_ticketing_base.py -x -q  # 8 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_fingerprint_missing_fields expected wrong hash**
- **Found during:** Task 2 test run
- **Issue:** Test expected `SHA256(b"::")` (2 colons) for empty finding dict. The actual formula `f"{host}:{port}::{title}"` with all-empty strings produces `":::"` (3 chars: colon + colon + double-colon-separator), giving `SHA256(b":::")`.
- **Fix:** Updated expected value in test to `hashlib.sha256(b":::").hexdigest()`
- **Files modified:** tests/test_ticketing_base.py
- **Commit:** bb1399b

**2. [Rule 1 - Bug] test_dispatch_failure_isolation: planted token not scrubbed by safe_str**
- **Found during:** Task 2 test run
- **Issue:** Plain `"FAKE_TOKEN_abc123xyz"` doesn't match any `safe_str` sensitive pattern — safe_str only scrubs recognized patterns (vault tokens, Basic/Bearer auth headers, connection strings with passwords). A bare random string passes through unchanged.
- **Fix:** Changed the planted exception to embed `Authorization: Bearer FAKE_JIRA_TOKEN_abc123xyz` — matching the regex `Authorization:\s*(Bearer|Basic)\s+\S+` — which safe_str correctly scrubs to class-name-only.
- **Files modified:** tests/test_ticketing_base.py
- **Commit:** bb1399b

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond the plan's threat model.

## Self-Check: PASSED

- [x] `quirk/ticketing/__init__.py` — FOUND
- [x] `quirk/ticketing/base.py` — FOUND (143 lines, > 90 min_lines)
- [x] `quirk/ticketing/config.py` — FOUND
- [x] `tests/test_ticketing_base.py` — FOUND, contains `def test_fingerprint_formula`
- [x] Commit ccab2a4 — feat(104-01): TicketingChannel ABC + config dataclasses + loader
- [x] Commit bb1399b — test(104-01): Wave-0 unit tests for TicketingChannel ABC contract
- [x] `python -m compileall quirk/ticketing/ -q` — clean
- [x] `python -m pytest tests/test_ticketing_base.py -x -q` — 8 passed
