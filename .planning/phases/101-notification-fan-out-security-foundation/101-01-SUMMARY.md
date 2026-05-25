---
phase: 101-notification-fan-out-security-foundation
plan: "01"
subsystem: integration-security-foundation
tags: [isec, notify, safe_exc, schema, packaging]
dependency_graph:
  requires: []
  provides: [safe_exc-integration-patterns, integration_deliveries-table, notify-extra]
  affects: [quirk/util/safe_exc.py, quirk/models.py, quirk/db.py, pyproject.toml]
tech_stack:
  added: [slack-sdk>=3.33.0]
  patterns: [_SENSITIVE_PATTERNS extension, SQLAlchemy model + idempotent migration, pip dry-run CI guard]
key_files:
  created:
    - tests/test_notify_safe_str_secrets.py
    - tests/test_integration_deliveries_schema.py
    - tests/test_install_all_includes_notify.py
  modified:
    - quirk/util/safe_exc.py
    - quirk/models.py
    - quirk/db.py
    - pyproject.toml
decisions:
  - "notify joins [all] — pip dry-run confirmed slack-sdk 3.42.0 resolves cleanly; aiohttp dep under [optional] extra only; no httpx downgrade chain"
metrics:
  duration_minutes: 4
  completed_date: "2026-05-25"
  tasks_completed: 3
  files_changed: 7
---

# Phase 101 Plan 01: Security Foundation + Packaging Summary

**One-liner:** Slack token/webhook/SMTP secret scrubbing in safe_str, IntegrationDelivery audit table via idempotent init_db migration, and slack-sdk [notify] extra bundled into [all] — the shared ANCHOR primitives for all v5.3 integration phases.

## What Was Built

### Task 1 — Extend safe_str with integration secret patterns (ISEC-02)

Three new regexes appended to `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py`:

- `xox[bpoa]-[0-9A-Za-z\-]{10,}` — Slack bot/user/app tokens
- `hooks\.slack\.com/services/[A-Za-z0-9/]+` — Slack incoming webhook URLs
- `smtps?://[^:@\s]+:[^@\s]+@` — SMTP connection strings with embedded credentials

The `safe_str` function body is unchanged — it already iterates `_SENSITIVE_PATTERNS` on every call. Five TDD guards in `tests/test_notify_safe_str_secrets.py` confirm redaction of all three shapes plus a no-over-redaction test for plain messages.

**Commit:** 5c63e86

### Task 2 — Add IntegrationDelivery model + idempotent migration (NOTIFY-07)

`class IntegrationDelivery(Base)` added to `quirk/models.py` with `__tablename__ = "integration_deliveries"` and the agreed 7-column schema:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | Integer PK autoincrement | NO | |
| scan_id | String(64) | NO | indexed — ISO ts from current_session_ts |
| finding_hash | String(64) | YES | SHA256 dedup key (future phases) |
| destination | String(64) | NO | "slack" \| "email" \| "webhook" |
| status | String(16) | NO | "ok" \| "failed" |
| attempted_at | DateTime | NO | |
| error_summary | Text | YES | always safe_str(exc) — never raw exc |

`_ensure_integration_deliveries_table(engine)` added to `quirk/db.py` (exact analog of `_ensure_scheduled_tables`) and wired into the `init_db` chain immediately after `_ensure_scan_checkpoints_table`. Five TDD schema guards in `tests/test_integration_deliveries_schema.py` verify table existence, column set, nullable constraints, scan_id index, and idempotency.

**Commit:** a0bf753

### Task 3 — [notify] extra + [all] inclusion + CI guard (packaging)

`notify = ["slack-sdk>=3.33.0"]` added to `[project.optional-dependencies]` in `pyproject.toml` (inserted after `docx` block). `"quirk-scanner[notify]"` added to the `[all]` meta-extra.

**Dependency conflict check (Open Question 1 from RESEARCH, recorded here per PLAN):**
- pip dry-run of `.[all,notify]` exited 0; slack-sdk 3.42.0 resolved
- slack-sdk's aiohttp dep is under `[optional]` extra — NOT a required transitive dep
- No conflict with core `httpx>=0.28.0`; no cryptography downgrade chain
- Decision: **notify JOINS [all]** (no exclusion needed)

`tests/test_install_all_includes_notify.py` added as a `@pytest.mark.slow` CI inclusion guard modeled on `test_install_all_excludes_impacket.py`. Asserts `slack-sdk` is present in the resolved `[all]` set.

**Commit:** b8196e1

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-dep | pyproject.toml | slack-sdk added to [notify]/[all]; slopcheck [OK] per 101-RESEARCH Package Legitimacy Audit; no cryptography downgrade |

No new network endpoints, auth paths, or file access patterns introduced. The `integration_deliveries` table is an internal audit log — no external surface.

## Known Stubs

None. All deliverables are complete primitives with no placeholder values or wired-but-empty data flows.

## Self-Check: PASSED

Files created/modified:
- FOUND: quirk/util/safe_exc.py
- FOUND: quirk/models.py
- FOUND: quirk/db.py
- FOUND: pyproject.toml
- FOUND: tests/test_notify_safe_str_secrets.py
- FOUND: tests/test_integration_deliveries_schema.py
- FOUND: tests/test_install_all_includes_notify.py

Commits verified:
- FOUND: 5c63e86 (feat(101-01): extend safe_str)
- FOUND: a0bf753 (feat(101-01): add IntegrationDelivery model)
- FOUND: b8196e1 (feat(101-01): add [notify] extra)
