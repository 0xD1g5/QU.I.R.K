---
phase: 105-servicenow-ticketing
verified: 2026-05-25T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Configure [ticketing.servicenow] with a real ServiceNow developer instance (instance_url, QUIRK_SNOW_USER env, QUIRK_SNOW_PASSWORD env). Run `quirk ticket create --backend servicenow --input findings.json`. Confirm one incident is created per finding, that short_description matches the finding title, description contains QRAMM evidence, and correlation_id equals the SHA256 fingerprint."
    expected: "One incident per unique finding in the ServiceNow incidents table. INC record has short_description = finding title, description contains QRAMM evidence fields, correlation_id = hex fingerprint."
    why_human: "Requires a live ServiceNow instance (Table API) — cannot be mocked end-to-end without a real SNOW tenant. Incident creation and field population require visual confirmation in the SNOW UI."
  - test: "Run `quirk ticket create --backend servicenow` a second time against the same findings. Confirm no duplicate incidents are created and instead a work_notes journal entry is appended to the existing incident."
    expected: "Incident count unchanged. Each existing incident has a new work_notes entry containing 'Rediscovery: QUIRK re-detected...' and the SHA256 fingerprint."
    why_human: "Dedup (GET correlation_id → PATCH work_notes) requires a live SNOW tenant with the prior incident still present. The PATCH journal visibility also requires visual confirmation in the SNOW task UI (KB0623936 distinction)."
---

# Phase 105: ServiceNow Ticketing Verification Report

**Phase Goal:** A security team using ServiceNow can auto-create incidents per finding via the same ticketing abstraction and dedup logic established in Phase 104 — no parallel code path.
**Verified:** 2026-05-25
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | First-scan finding becomes one ServiceNow incident via POST carrying QRAMM evidence and correlation_id=fingerprint | VERIFIED | `create_issue_from_finding` in servicenow.py POSTs `{"short_description":..., "description": evidence, "correlation_id": fp}` to `/api/now/table/{table}`; `test_create_incident` asserts method=="POST", body correlation_id==compute_fingerprint, title in short_description; test passes green |
| 2 | Second scan of same finding appends work_notes (PATCH) instead of duplicate incident | VERIFIED | `add_rediscovery_comment` uses `method="PATCH"` to `/api/now/table/{table}/{sys_id}`; `test_dedup_then_work_notes` asserts POST called once across two dispatch_finding runs, PATCH called once on second run; test passes green |
| 3 | ServiceNow Basic-auth credentials resolve from env-var names only and never appear in SQLite, scan JSON, or logs | VERIFIED | `__init__` calls `os.environ.get(cfg.user_env)` / `os.environ.get(cfg.password_env)` at construction; stores only `self._auth_header`; `test_credentials_not_in_logs` plants a 40+ char Basic auth string in a raised HTTPError and asserts it is absent from `error_summary` (safe_str enforcement); test passes green |
| 4 | An http:// instance_url is rejected at config parse time (returns None) | VERIFIED | `_parse_servicenow_cfg` at line 153 of config.py: `if not str(instance_url).startswith("https://"): return None`; `test_http_instance_url_rejected` asserts `_parse_servicenow_cfg({"instance_url":"http://..."})` is None; passes green |
| 5 | A loopback/internal instance_url is blocked by validate_external_url at construction | VERIFIED | `__init__` calls `validate_external_url(cfg.instance_url, allow_internal=cfg.allow_internal)` and raises `ValueError(f"SSRF blocked...")` on failure; `test_ssrf_guard` passes `instance_url="https://127.0.0.1/"` and asserts `ValueError` matching "SSRF"; passes green |
| 6 | quirk/ticketing/base.py and quirk/ticketing/jira.py are byte-for-byte unchanged | VERIFIED | `git diff --quiet quirk/ticketing/base.py quirk/ticketing/jira.py` exits 0 — no modifications to either file |
| 7 | `quirk ticket create --backend servicenow` dispatches findings through ServiceNowChannel | VERIFIED | ticket_cmd.py line 87: `add_argument("--backend", choices=["jira","servicenow"], default="jira")`; line 147–156: `if args.backend == "servicenow": ... from quirk.ticketing.servicenow import ServiceNowChannel; channel = ServiceNowChannel(cfg.servicenow)`; `test_backend_servicenow` passes green |
| 8 | `quirk ticket create` with no --backend defaults to jira (backward compatible) | VERIFIED | `default="jira"` in argparse; `test_default_backend_uses_jira` regression test passes green |
| 9 | Missing [ticketing.servicenow] block with --backend servicenow exits with clear error | VERIFIED | Line 148–153 of ticket_cmd.py: `if cfg.servicenow is None: print("ERROR: [ticketing.servicenow] block not configured...") → exit 2`; `test_backend_servicenow_missing_config` asserts SystemExit code 2; passes green |
| 10 | The missing-[tickets]-extra advisory message is backend-neutral | VERIFIED | Line 97 of ticket_cmd.py: `"ERROR: Ticketing skipped — run \`pip install quirk[tickets]\` to enable."`; "Jira ticketing skipped" text is absent from the file |
| 11 | docs/configuration.md documents the ServiceNow ticketing backend | VERIFIED | `grep -qi servicenow docs/configuration.md` matches; `grep -qi "backend servicenow" docs/configuration.md` matches; section covers instance_url, user_env, password_env, https-only, --backend servicenow, correlation_id/work_notes dedup |
| 12 | docs/sample-config.yaml has a ticketing.servicenow example block | VERIFIED | `grep -qi servicenow docs/sample-config.yaml` matches; commented servicenow sub-block under ticketing: with env-var NAMES (QUIRK_SNOW_USER, QUIRK_SNOW_PASSWORD) |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/ticketing/servicenow.py` | ServiceNowChannel(TicketingChannel) implementing only the 3 abstract methods + _NoRedirectHandler | VERIFIED | File exists; class ServiceNowChannel(TicketingChannel) defined; find_by_fingerprint, create_issue_from_finding, add_rediscovery_comment all present; `grep 'def compute_fingerprint' servicenow.py` returns nothing (inheritance intact) |
| `quirk/ticketing/config.py` | ServiceNowTicketingCfg dataclass + _parse_servicenow_cfg + servicenow field on TicketingCfg | VERIFIED | ServiceNowTicketingCfg dataclass at line 44; _parse_servicenow_cfg at line 138; TicketingCfg.servicenow field at line 66; _parse_ticketing_cfg wires servicenow_raw at line 101–104 |
| `tests/test_ticketing_servicenow.py` | Wave 0 mocked-urllib tests for TICKET-02 behaviors + config validation | VERIFIED | 9 tests collected and all pass: test_create_incident, test_dedup_then_work_notes, test_correlation_id_is_fingerprint, test_http_instance_url_rejected, test_missing_instance_url, test_missing_env_fields_rejected, test_https_valid_config, test_ssrf_guard, test_credentials_not_in_logs |
| `quirk/cli/ticket_cmd.py` | --backend {jira,servicenow} flag + conditional dispatch + neutral extra-gate message | VERIFIED | `choices=["jira","servicenow"]` at line 87; lazy ServiceNowChannel import in servicenow branch at line 155; "Ticketing skipped" at line 97; "Jira ticketing skipped" absent |
| `tests/test_ticket_cmd.py` | test_backend_servicenow + default-jira regression + missing-config exit-2 | VERIFIED | test_backend_servicenow, test_default_backend_uses_jira, test_backend_servicenow_missing_config all present and pass green |
| `docs/configuration.md` | ServiceNow Ticketing documentation section | VERIFIED | Contains servicenow, "backend servicenow", https-only, env-var-name creds, dedup/work_notes |
| `docs/sample-config.yaml` | ticketing.servicenow example block | VERIFIED | servicenow sub-block under ticketing: present |
| `docs/UAT-SERIES.md` | Series 105 ServiceNow ticketing UAT cases | VERIFIED | "## Series 105: ServiceNow Ticketing" present; committed as 306353a |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/ticketing/servicenow.py` | `quirk/ticketing/base.py::TicketingChannel` | subclass inheriting compute_fingerprint/build_ticket_evidence/dispatch_finding | WIRED | `class ServiceNowChannel(TicketingChannel)` confirmed; no compute_fingerprint override; all inherited methods flow through base |
| `quirk/ticketing/servicenow.py` | ServiceNow Table API | `urllib.request.build_opener(_NoRedirectHandler).open(req, timeout=10)` | WIRED | All three methods use `build_opener(_NoRedirectHandler)` and `opener.open(req, timeout=10)` |
| `quirk/cli/ticket_cmd.py` | `quirk/ticketing/servicenow.py::ServiceNowChannel` | lazy import in the --backend servicenow branch | WIRED | `from quirk.ticketing.servicenow import ServiceNowChannel` inside the `args.backend == "servicenow"` branch at line 155 |

### Probe Execution

No conventional probe files declared for this phase. Substituted test-suite execution.

| Test suite | Command | Result | Status |
|------------|---------|--------|--------|
| ServiceNow tests | `python -m pytest tests/test_ticketing_servicenow.py -q` | 9 passed | PASS |
| Jira tests | `python -m pytest tests/test_ticketing_jira.py -q` | passes | PASS |
| Base tests | `python -m pytest tests/test_ticketing_base.py -q` | passes | PASS |
| CLI dispatch tests | `python -m pytest tests/test_ticket_cmd.py -q` | 8 passed | PASS |
| Combined suite | all 4 test files | 33 passed in 0.26s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TICKET-02 | 105-01, 105-02, 105-03 | A user can auto-create a ServiceNow incident/record per finding (Table API), carrying QRAMM evidence | SATISFIED | ServiceNowChannel creates incidents via POST with QRAMM evidence in description; correlation_id = SHA256 fingerprint; dedup via GET + PATCH work_notes; CLI --backend servicenow; documented in configuration.md |
| TICKET-04 | 105-01 (proven by zero-diff constraint) | Jira and ServiceNow share one ticketing abstraction and the same fingerprint/dedup logic | SATISFIED | `git diff --quiet quirk/ticketing/base.py quirk/ticketing/jira.py` exits 0; ServiceNowChannel subclasses TicketingChannel (inherits compute_fingerprint, build_ticket_evidence, dispatch_finding); no duplicate dedup code path |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No debt markers (TBD/FIXME/XXX), no stubs, no empty returns in phase-modified files | — | Clean |

### Human Verification Required

### 1. Live ServiceNow Incident Creation

**Test:** Configure `[ticketing.servicenow]` in QUIRK_CONFIG_PATH with a real ServiceNow developer instance (`instance_url` = https://yourinstance.service-now.com, `user_env` = QUIRK_SNOW_USER, `password_env` = QUIRK_SNOW_PASSWORD). Set env vars. Run `quirk ticket create --backend servicenow --input findings.json`.

**Expected:** One incident per unique finding appears in the ServiceNow incidents table. Each INC record has `short_description` = finding title (truncated to 255 chars), `description` = QRAMM evidence block, `correlation_id` = 64-char SHA256 hex fingerprint.

**Why human:** Requires a live ServiceNow instance (Table API). Incident creation and field population can only be confirmed with a real SNOW tenant. Field-level visual confirmation in SNOW UI is required.

### 2. Work-Notes Dedup (Second Scan)

**Test:** Immediately after test 1, run `quirk ticket create --backend servicenow --input findings.json` a second time against the same findings file.

**Expected:** No new incidents are created. Each existing INC has a new `work_notes` journal entry reading "Rediscovery: QUIRK re-detected this finding on a subsequent scan." followed by the fingerprint. The journal entry is visible in the SNOW task UI (not a hidden private note).

**Why human:** Dedup (GET by correlation_id, then PATCH work_notes) requires the prior incident to be present in a live SNOW tenant. The work_notes visibility distinction (KB0623936 — PATCH vs POST) can only be confirmed visually in the SNOW task UI.

### Gaps Summary

No gaps. All 12 automated must-haves are verified against the codebase. The full 33-test suite passes green. The two human verification items require a live ServiceNow tenant and cannot be automated without one.

---

_Verified: 2026-05-25_
_Verifier: Claude (gsd-verifier)_
