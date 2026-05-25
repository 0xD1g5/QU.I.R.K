---
phase: 104-jira-ticketing
plan: "04"
subsystem: ticketing-docs
tags: [docs, configuration, uat, obsidian, jira, ticketing]
dependency_graph:
  requires:
    - phase: 104-01
      provides: JiraTicketingCfg field names (jira_url, jira_user_env, jira_token_env, project_key, issue_type, auth_mode, allow_internal)
    - phase: 104-02
      provides: JiraChannel SSRF guard, cloud/server auth, JQL dedup semantics
    - phase: 104-03
      provides: quirk ticket create CLI usage, [tickets] extra, optional_extra REGISTRY
  provides:
    - docs/configuration.md Jira Ticketing section
    - docs/sample-config.yaml ticketing.jira block (env-var NAMES only)
    - docs/UAT-SERIES.md Series 104 (UAT-104-01..04)
    - Obsidian Phase-104 note (status: complete)
    - Obsidian UAT-Series.md vault sync
  affects:
    - Phase 105 ServiceNow — docs/configuration.md Jira Ticketing section notes ServiceNow arrives in Phase 105 reusing the same abstraction
tech_stack:
  added: []
  patterns:
    - "Credential isolation: config holds env-var NAMES only; docs explicitly state no values are persisted/logged"
    - "SSRF note in docs: jira_url validated by validate_external_url; allow_internal: true for self-hosted RFC1918"
    - "Sample-config pattern: commented block with env-var NAMES only (QUIRK_JIRA_USER, QUIRK_JIRA_TOKEN)"
    - "UAT Series 104 mirrors Series 103 format: automated + HUMAN-UAT mixed series"
    - "Obsidian phase note written directly to vault filesystem (file too large for CLI content=)"
    - "UAT-SERIES.md committed via gsd-tools (CLAUDE.md Step 4 recurring miss)"
key_files:
  created: []
  modified:
    - docs/configuration.md
    - docs/sample-config.yaml
    - docs/UAT-SERIES.md
decisions:
  - "ServiceNow note in docs: ticketing.jira block documented here does not change when Phase 105 ServiceNow is added"
  - "Sample config uses QUIRK_JIRA_USER/QUIRK_JIRA_TOKEN as recommended env var name convention — operators can use any name"
  - "UAT-104-02 marked HUMAN-UAT (live Jira instance + API token required) — matches Series 103 live-infra UAT pattern"
  - "SSRF test UAT-104-04 uses automated gate (mocked tests in test_ticketing_jira.py) rather than live blocking"
metrics:
  duration: 12
  completed_date: "2026-05-25"
  tasks: 2
  files: 3
requirements-completed: [TICKET-01, TICKET-03, TICKET-04]
---

# Phase 104 Plan 04: Docs + UAT-SERIES + Obsidian Phase Note Summary

**One-liner:** Jira ticketing docs (credential isolation model, cloud/server auth, SSRF note, dedup semantics, CLI usage), Series 104 UAT cases, and mandatory CLAUDE.md phase-completion steps — all four steps executed including the recurring-miss UAT-SERIES.md gsd-tools commit.

## What Was Built

### Task 1: Configuration docs + sample config

**`docs/configuration.md`** — "Jira Ticketing (v5.3+)" section added before the Compliance Frameworks section:

- **`ticketing.jira` config block table** — all seven `JiraTicketingCfg` fields with names matching the dataclass exactly (`jira_url`, `jira_user_env`, `jira_token_env`, `project_key`, `issue_type`, `auth_mode`, `allow_internal`), types, defaults, and required flags
- **Credential isolation model** — explains that the config holds env-var NAMES only; QUIRK reads the actual credential from the environment at run time; credentials are never written to YAML/SQLite/logs/CBOM/PDF. Table maps field → env var name → example value.
- **Cloud vs server auth table** — `auth_mode: cloud` (Jira Cloud, email + API token, `basic_auth=(user, token)`) vs `auth_mode: server` (Data Center/Server, PAT, `token_auth=token`)
- **SSRF protection** — `jira_url` validated by `validate_external_url()` before any connection; loopback/RFC1918/metadata IPs blocked by default; `allow_internal: true` for self-hosted instances
- **`quirk ticket create` CLI usage** — three forms (`--input`, `--output-dir`, default glob), prerequisites, exit codes (0/1/2)
- **Dedup and rediscovery behavior** — SHA-256 fingerprint formula, first-run vs re-run semantics (create vs rediscovery comment, zero duplicate issues)
- **Audit log** — `integration_deliveries` table schema, sqlite3 query example

**`docs/sample-config.yaml`** — commented `ticketing:` → `jira:` block using env-var NAMES only (`QUIRK_JIRA_USER`, `QUIRK_JIRA_TOKEN`). Security preamble explains the env-var NAME convention. TCP framing caveat preserved for the existing `siem:` block below.

### Task 2: UAT-SERIES.md + Obsidian sync + UAT-SERIES commit + Phase 104 note

**(Step 2) `docs/UAT-SERIES.md`** — Last Updated bumped to 2026-05-25 (Phase 104 wrap); Series 104 added (UAT-104-01..04):

- **UAT-104-01** (Automated) — 18 automated ticketing tests (8 ABC + 5 JiraChannel + 5 CLI) + slow `[all]` CI guard; security assertions (no module-scope `from jira`, SSRF guard present, compileall clean)
- **UAT-104-02** (HUMAN-UAT, live Jira) — live issue creation + dedup walkthrough: configure `ticketing.jira` block, export credentials, run `quirk ticket create`, verify N issues in Jira with QRAMM evidence; re-run → zero duplicates + rediscovery comments; audit log query
- **UAT-104-03** (Automated + optional manual) — missing `[tickets]` extra: `test_missing_extra_advisory` asserts exit 2 + `pip install quirk[tickets]` advisory, no `ImportError:` line
- **UAT-104-04** (Automated) — SSRF guard: `validate_external_url` present in `jira.py`, `allow_internal` wired; mocked SSRF tests pass

**(Step 3)** UAT-SERIES.md synced to Obsidian vault at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` via the `printf`+`cat` recipe (file too large for CLI `content=`).

**(Step 4 — DO NOT SKIP)** `docs/UAT-SERIES.md` committed via `node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-104): update UAT-SERIES.md" --files docs/UAT-SERIES.md`. Commit: `05f67e8`.

**(Step 1)** Phase 104 Obsidian note written directly to vault filesystem at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-104-Jira-Ticketing.md` (status: complete). Contains: frontmatter (status: complete, type: phase, source, updated), Goal, Requirements Covered (TICKET-01/03/04), Success Criteria, What Was Built (one subsection per plan 104-01..04 sourced from SUMMARY.md files), `[[Roadmap]]` link.

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: config docs + sample config | `ecaff7f` | docs(104-04): add [ticketing] config block + sample config + quirk ticket create CLI reference |
| Task 2: UAT-SERIES.md + gsd-tools commit | `05f67e8` | docs(phase-104): update UAT-SERIES.md |

## Verification

```
grep -q "quirk ticket create" docs/configuration.md && echo "config ok"   # ok
grep -q "jira_token_env" docs/sample-config.yaml && echo "sample ok"      # ok
grep -q "allow_internal" docs/configuration.md && echo "ssrf note ok"     # ok
grep -q "ticket create" docs/UAT-SERIES.md && echo "UAT ok"               # ok
test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-104-Jira-Ticketing.md" && echo "phase note ok"  # ok
test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md" && echo "vault sync ok"  # ok
```

## Deviations from Plan

None — plan executed exactly as written. All four CLAUDE.md mandatory phase-completion steps executed in order (step 1 last as specified by the plan). Field names in docs match `JiraTicketingCfg` dataclass exactly (verified against `quirk/ticketing/config.py`).

## Known Stubs

None — all documentation sections are complete. No placeholder text, TODO markers, or wired-but-empty sections.

## Threat Flags

None — documentation changes only. T-104-11 (credential isolation — sample config must not store raw credentials) is mitigated: the `docs/sample-config.yaml` block uses env-var NAMES only (`QUIRK_JIRA_USER`, `QUIRK_JIRA_TOKEN`) with an explicit security preamble. No new network endpoints, auth paths, or schema changes introduced by this plan.

## Self-Check: PASSED

- [x] `docs/configuration.md` — contains "quirk ticket create"
- [x] `docs/configuration.md` — contains "allow_internal"
- [x] `docs/configuration.md` — contains "jira_token_env"
- [x] `docs/sample-config.yaml` — contains "jira_token_env"
- [x] `docs/UAT-SERIES.md` — contains "ticket create"
- [x] `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-104-Jira-Ticketing.md` — FOUND
- [x] `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — FOUND
- [x] Commit `ecaff7f` — docs(104-04): add [ticketing] config block + sample config
- [x] Commit `05f67e8` — docs(phase-104): update UAT-SERIES.md (gsd-tools commit, CLAUDE.md Step 4)
- [x] CLAUDE.md Step 1 (Obsidian phase note) — DONE
- [x] CLAUDE.md Step 2 (UAT-SERIES.md update) — DONE
- [x] CLAUDE.md Step 3 (vault sync) — DONE
- [x] CLAUDE.md Step 4 (gsd-tools commit) — DONE (commit 05f67e8)
