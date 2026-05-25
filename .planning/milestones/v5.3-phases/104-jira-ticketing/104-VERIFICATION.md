---
phase: 104-jira-ticketing
verified: 2026-05-25T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Configure a real [ticketing] YAML block with Jira Cloud credentials (jira_url, jira_user_env, jira_token_env, project_key). Export env vars. Run `quirk ticket create` after a completed scan."
    expected: "Exactly one Jira issue created per finding. Issue description contains QRAMM evidence (title, severity, host, port, description, recommendation). Issue has a label equal to the SHA-256 fingerprint (64-char hex). Exit code 0."
    why_human: "Requires a live Jira Cloud or Server instance and a real API token. Cannot mock end-to-end Jira REST calls in automated tests."
  - test: "With the same [ticketing] config and the same findings file, run `quirk ticket create` a second time."
    expected: "Zero new issues created. Each existing issue receives exactly one rediscovery comment containing the fingerprint. Total issue count in Jira is unchanged. Exit code 0."
    why_human: "Dedup path (JQL label search → add_comment branch) requires a live Jira instance to confirm the real JQL resolves and add_comment fires against the correct issue."
  - test: "Uninstall [tickets] extra (`pip uninstall jira -y`). Run `quirk ticket create`."
    expected: "stderr prints the advisory `pip install quirk[tickets]`. Process exits 2. No ImportError traceback appears."
    why_human: "Advisory behavior requires the real import to be absent; the automated test mocks it. A human should confirm no traceback leaks on a truly absent install."
  - test: "With [ticketing] configured for a Jira Server (Data Center) instance using a Personal Access Token (auth_mode: server), run `quirk ticket create`."
    expected: "Issues created successfully via token_auth PAT path. No credentials appear in any log output or the integration_deliveries error_summary column."
    why_human: "Requires a real Jira Server/DC instance to test the token_auth code path. Credential scrubbing in real error output can only be confirmed by human inspection of logs."
---

# Phase 104: Jira Ticketing Verification Report

**Phase Goal:** A security team can auto-create one Jira issue per finding carrying QRAMM evidence, with idempotent dedup so re-scans never proliferate duplicate tickets — built on a shared TicketingChannel abstraction Phase 105 (ServiceNow) reuses.
**Verified:** 2026-05-25
**Status:** human_needed (all automated checks PASS; 4 live-Jira tests deferred to human UAT)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `compute_fingerprint(finding)` returns a stable 64-char SHA256(host:port::title) hex identical on repeated calls | VERIFIED | `base.py:74-78` implements the locked formula; `test_fingerprint_stable`, `test_fingerprint_formula` pass; manual spot-check confirms SHA256(b"h:443::Some Title") equality |
| 2 | `build_ticket_evidence(finding)` returns a non-empty description sourced from whitelisted fields (title/severity/host/port/description/recommendation/quantum_risk) — never check_id/compliance/PEM | VERIFIED | `base.py:81-102` implements the whitelist; `test_build_ticket_evidence` asserts check_id absent |
| 3 | `dispatch_finding()` writes exactly one IntegrationDelivery row per finding with `finding_hash == compute_fingerprint(finding)`, never raises into the caller | VERIFIED | `base.py:104-144`; `db.commit()` is outside the delivery try/except (WR-01: line 141-143); `test_audit_row_finding_hash`, `test_dispatch_failure_isolation` pass |
| 4 | A subclass implementing only the 3 abstract methods inherits all shared logic with zero base.py changes (Phase 105 forward-compat) | VERIFIED | All 3 abstract methods return generic types (`Optional[str]`, `str`, `None`); `grep -n "jira\." base.py` returns only a comment reference — zero jira.* imports or types in base.py; `_StubChannel` in test suite proves subclass-only contract |
| 5 | JiraChannel lazy-imports `from jira import JIRA` inside `__init__` only — package imports cleanly with [tickets] NOT installed | VERIFIED | `jira.py:54-59` shows lazy try/except inside `__init__`; `grep "^from jira\|^import jira" jira.py` returns nothing; `python -c "import quirk.ticketing.jira; from quirk.ticketing import JiraChannel; print('ok')"` prints ok |
| 6 | On first run a finding with no existing fingerprint label results in exactly one create_issue call carrying QRAMM evidence + fingerprint label | VERIFIED (mocked) | `jira.py:103-127`; `test_create_issue_per_finding`, `test_dedup_creates_once_then_comments` pass with mocked JIRA client; requires live Jira for end-to-end (human UAT) |
| 7 | On re-scan the same fingerprint is found via JQL label search and add_comment is called — zero new issues created | VERIFIED (mocked) | `jira.py:84-101` JQL: `project = "KEY" AND labels = "fp"` double-quoted; `test_dedup_creates_once_then_comments` drives two dispatch_finding calls against real tmp DB, asserts create called once and add_comment called on second; live Jira dedup is human UAT |
| 8 | Jira credentials resolve from env vars at `__init__` time and never appear in any error_summary (safe_str enforced) | VERIFIED | `jira.py:72-73` reads env vars by name; `base.py:124` uses `safe_str(exc)` exclusively; `test_credentials_not_in_logs` plants `Authorization: Bearer FAKE_JIRA_TOKEN_abc123xyz` in exception, asserts absent from error_summary |
| 9 | `quirk ticket create` dispatches one issue per finding through JiraChannel; missing [tickets] → advisory + exit 2, no traceback | VERIFIED | `ticket_cmd.py:87-92` is_extra_available guard → print advisory + sys.exit(2); `test_missing_extra_advisory` asserts exit 2 + advisory text; `test_exit_0_all_dispatched` confirms happy path |
| 10 | `quirk ticket` is intercepted in run_scan.py before scan argparse, using `return` | VERIFIED | `run_scan.py:502-506`; grep confirms `_sys.argv[1] == "ticket"` + `return` after the export block |
| 11 | `jira>=3.10.5` is in [tickets] extra and joined into [all]; CI guard asserts pip resolution | VERIFIED | `pyproject.toml:92-93` `tickets = ["jira>=3.10.5"]`; line 108 `"quirk-scanner[tickets]"` in all; `tests/test_install_all_includes_tickets.py` slow CI guard exists |
| 12 | Documentation describes the ticketing config block, env-var-NAME credential model, cloud/server auth, SSRF, and `quirk ticket create` usage | VERIFIED | `docs/configuration.md` contains "quirk ticket create", "allow_internal", "jira_token_env"; `docs/sample-config.yaml` contains "jira_token_env"; UAT-SERIES.md contains "ticket create" |

**Score:** 12/12 truths verified (10 fully automated; 2 verified with mocked tests and require live-Jira human UAT for end-to-end confirmation)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/ticketing/base.py` | TicketingChannel ABC: 3 abstractmethods + compute_fingerprint @staticmethod + build_ticket_evidence @staticmethod + dispatch_finding + audit row | VERIFIED | 145 lines; all structure confirmed; zero jira.* references |
| `quirk/ticketing/config.py` | JiraTicketingCfg + TicketingCfg dataclasses + load_ticketing_config loader (env-var-NAME-only, SQLite-safe) | VERIFIED | 93 lines; `except Exception: return None` guard present |
| `quirk/ticketing/__init__.py` | Package init re-exporting TicketingChannel, TicketingCfg, load_ticketing_config, JiraChannel | VERIFIED | 24 lines; __all__ exports all four; JiraChannel import does not trigger jira lazy-import |
| `quirk/ticketing/jira.py` | JiraChannel(TicketingChannel): lazy jira import + SSRF guard + cloud/server auth + JQL dedup + create_issue + add_comment | VERIFIED | 144 lines (> 50 min_lines); all required structure confirmed |
| `quirk/cli/ticket_cmd.py` | run_ticket(argv) + _find_latest_findings; argparse create subcommand; missing-extra/config/file exits; per-finding dispatch loop | VERIFIED | 151 lines; full flow confirmed |
| `quirk/util/optional_extra.py` | tickets entry in REGISTRY (modules=("jira",), enabled_attrs=()) | VERIFIED | `extra="tickets"`, `modules=("jira",)`, `enabled_attrs=()` confirmed |
| `pyproject.toml` | [tickets] = jira>=3.10.5 extra joined into [all] | VERIFIED | Both entries present; [identity] exclusion comment preserved |
| `tests/test_ticketing_base.py` | 8 ABC-contract unit tests | VERIFIED | 8 tests collected and passing |
| `tests/test_ticketing_jira.py` | 5 mocked-JIRA unit tests | VERIFIED | 5 tests collected and passing |
| `tests/test_ticket_cmd.py` | 5 CLI tests | VERIFIED | 5 tests collected and passing |
| `tests/test_install_all_includes_tickets.py` | slow CI guard: jira in quirk[all] resolved set | VERIFIED | File exists; @pytest.mark.slow guard confirmed |
| `docs/configuration.md` | [ticketing] config block reference + quirk ticket create usage | VERIFIED | grep confirms all required content present |
| `docs/sample-config.yaml` | ticketing.jira sample block (env-var NAMES only) | VERIFIED | jira_token_env + jira_user_env confirmed |
| `docs/UAT-SERIES.md` | Jira ticketing UAT case + updated Last Updated date | VERIFIED | "ticket create" found |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/ticketing/base.py::dispatch_finding` | `quirk.models.IntegrationDelivery` | `IntegrationDelivery(...)` construction + `db.add(row)` | VERIFIED | `base.py:132-140` |
| `quirk/ticketing/base.py::dispatch_finding` | `quirk.util.safe_exc.safe_str` | `error_summary = safe_str(exc)` | VERIFIED | `base.py:124,144`; never str(exc) or repr(exc) |
| `quirk/ticketing/base.py::dispatch_finding` | db.commit() outside delivery try/except | Separate try block at line 141 | VERIFIED | WR-01 pattern confirmed |
| `quirk/ticketing/jira.py::JiraChannel.__init__` | `quirk.util.url_allowlist.validate_external_url` | `result = validate_external_url(cfg.jira_url, allow_internal=cfg.allow_internal)` | VERIFIED | `jira.py:62-66` — called before any JIRA() construction |
| `quirk/ticketing/jira.py::find_by_fingerprint` | Jira search_issues JQL | `project = "KEY" AND labels = "fp"` double-quoted | VERIFIED | `jira.py:97-98` |
| `run_scan.py` | `quirk.cli.ticket_cmd.run_ticket` | `argv[1] == "ticket"` interception + `return` | VERIFIED | `run_scan.py:503-506`; uses `return` not `_sys.exit` |
| `quirk/cli/ticket_cmd.py::run_ticket` | `JiraChannel.dispatch_finding` | per-finding loop inside `get_session` context | VERIFIED | `ticket_cmd.py:141-143` |

---

## TICKET-04 Forward-Design Confirmation: Phase 105 ServiceNow

**The TicketingChannel ABC is ready for a ServiceNow subclass with zero changes to base.py or jira.py.**

Evidence:
1. All three abstract methods use generic Python types only: `find_by_fingerprint → Optional[str]`, `create_issue_from_finding → str`, `add_rediscovery_comment → None`. No jira.* types appear anywhere in base.py.
2. `grep "jira" quirk/ticketing/base.py` returns only a comment in the docstring (line 44: `"jira" or "servicenow"`). Zero functional jira references.
3. `compute_fingerprint` and `build_ticket_evidence` are `@staticmethod`s with no backend-specific logic — they operate on plain finding dicts.
4. `dispatch_finding` calls only the 3 abstract methods by their generic interfaces. A ServiceNow subclass returning a sys_id string satisfies the contract identically.
5. Phase 105 adds `quirk/ticketing/servicenow.py` only. It uses stdlib `urllib` (no new optional-extra) and sets `destination = "servicenow"`. The existing `TicketingCfg` dataclass already has `jira: Optional[JiraTicketingCfg] = None` — Phase 105 adds `servicenow: Optional[ServiceNowCfg] = None` to `TicketingCfg` in config.py only. No changes to base.py or jira.py are required.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package imports without [tickets] installed | `python -c "from quirk.ticketing import TicketingChannel, TicketingCfg, load_ticketing_config; assert hasattr(TicketingChannel,'compute_fingerprint'); print('ok')"` | ok | PASS |
| JiraChannel importable without [tickets] installed | `python -c "import quirk.ticketing.jira; from quirk.ticketing import JiraChannel; print('ok')"` | ok | PASS |
| Fingerprint formula pins correct value | `compute_fingerprint({'host':'h','port':443,'title':'Some Title'}) == hashlib.sha256(b'h:443::Some Title').hexdigest()` | confirmed | PASS |
| All 18 unit tests pass | `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py tests/test_ticket_cmd.py -q` | 18 passed in 0.22s | PASS |
| run_scan.py interception uses return | `grep 'argv\[1\] == "ticket"' run_scan.py` + surrounding context | return on line 506 | PASS |
| pyproject [tickets] + [all] correct | `tomllib` parse asserts | ok | PASS |
| compileall clean | `python -m compileall quirk/ticketing/ quirk/cli/ticket_cmd.py -q` | COMPILE CLEAN | PASS |

---

## Anti-Patterns Found

No TBD/FIXME/XXX markers found in any phase 104 files. No stub patterns (return null, return {}, return [], placeholder text) found. No hardcoded empty data that flows to user-visible output. No module-scope jira import in any file.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TICKET-01 | 104-02, 104-03 | Auto-create a Jira issue per finding carrying QRAMM evidence via jira [tickets] extra | SATISFIED | JiraChannel.create_issue_from_finding + ticket_cmd.py dispatch loop wired and tested |
| TICKET-03 | 104-01, 104-02, 104-03 | Idempotent dedup via SHA256 fingerprint label search before create; re-scans → rediscovery comment only | SATISFIED | compute_fingerprint locked formula; JQL label search in find_by_fingerprint; dedup test passes |
| TICKET-04 | 104-01 | Shared ticketing abstraction (TicketingChannel ABC) reused by both Jira and ServiceNow — not two parallel code paths | SATISFIED | ABC confirmed; zero jira.* in base.py; Phase 105 forward-compat confirmed above |

REQUIREMENTS.md traceability table shows all three marked `[x] Complete` for Phase 104.

---

## Human Verification Required

### 1. Live Jira Issue Creation (HUMAN-UAT)

**Test:** Configure `~/.quirk-config.yaml` with a real `[ticketing.jira]` block (Jira Cloud or Server). Set `QUIRK_JIRA_USER` and `QUIRK_JIRA_TOKEN` env vars. Run a scan to generate `output/findings-*.json`, then run `quirk ticket create`.
**Expected:** One Jira issue created per finding. Issue description contains the QRAMM evidence fields (title, severity, host, port, description, recommendation). The issue label is the 64-char SHA-256 fingerprint. Exit code 0.
**Why human:** Requires a live Jira instance and real API credentials. Automated tests use a mocked JIRA client.

### 2. Dedup Behavior on Re-Scan (HUMAN-UAT)

**Test:** Using the same config and findings file as UAT-1 above, run `quirk ticket create` a second time.
**Expected:** Zero new issues created in Jira. Each pre-existing issue has exactly one new comment containing "Rediscovery" and the fingerprint. Total issue count in the Jira project is unchanged from after UAT-1.
**Why human:** The JQL label search → add_comment dedup path must resolve against real Jira issue state. The automated test drives this against a mocked client.

### 3. Graceful Missing-Extra Behavior (optional manual confirm)

**Test:** With `jira` uninstalled (`pip uninstall jira -y`), run `quirk ticket create`.
**Expected:** stderr shows `ERROR: Jira ticketing skipped — run \`pip install quirk[tickets]\` to enable.` Process exits 2. No `ImportError:` traceback appears in output.
**Why human:** The automated test mocks `is_extra_available`. A human confirms the behavior on a truly absent install without the mock.

### 4. Server/Data Center Auth Mode (HUMAN-UAT)

**Test:** Configure `auth_mode: server` and a Jira Data Center PAT token in the `[ticketing.jira]` block. Run `quirk ticket create`.
**Expected:** Issues created via the `token_auth` PAT path. No credential values appear in any log output. The `integration_deliveries` table `error_summary` column is NULL for successful dispatches.
**Why human:** Requires a real Jira Server/DC instance. Credential scrubbing in live error output can only be confirmed by human log inspection.

---

## Gaps Summary

None. All automated must-haves are verified. The 4 human verification items above are inherent to live third-party service integration and are correctly classified as HUMAN-UAT rather than gaps.

---

_Verified: 2026-05-25_
_Verifier: Claude (gsd-verifier)_
