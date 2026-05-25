# Phase 105: ServiceNow Ticketing - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase lets a security team using ServiceNow auto-create one incident per finding,
carrying QRAMM evidence, via the SAME `TicketingChannel` abstraction and SHA256 fingerprint
dedup established in Phase 104 — NOT a parallel hand-built code path (TICKET-04). It is the
second backend that proves the abstraction.

In scope: TICKET-02 (ServiceNow incident/record per finding via the Table API, QRAMM evidence).
Inherits everything from Phase 104: the `TicketingChannel` ABC (`quirk/ticketing/base.py`),
`compute_fingerprint` (SHA256(host:port::title)), `build_ticket_evidence`, `dispatch_finding`
orchestration + `integration_deliveries` audit, the `[tickets]` extra + graceful-skip,
`safe_str`, and `validate_external_url`.

Out of scope: any change to base.py or jira.py (the ABC must absorb ServiceNow as a pure
subclass); bidirectional sync; ServiceNow-specific workflows beyond incident creation;
a new pip dependency (ServiceNow uses stdlib urllib per v5.3-D-06).
</domain>

<decisions>
## Implementation Decisions

### ServiceNow Backend (TICKET-02)
- Transport: stdlib `urllib` against the ServiceNow Table API (`POST /api/now/table/incident`) — zero new pip deps beyond the existing `[tickets]` extra (v5.3-D-06)
- Dedup key: the ServiceNow `correlation_id` field carries the SHA256 fingerprint; `find_by_fingerprint` does `GET /api/now/table/incident?sysparm_query=correlation_id=<fp>` (the natural ServiceNow idempotency mechanism — the "label" equivalent)
- Rediscovery: when an incident with the fingerprint correlation_id exists, append a `work_notes` entry to it (no duplicate incident)
- Incident fields: `short_description` = finding title, `description` = QRAMM evidence, `correlation_id` = fingerprint

### Config, Creds & CLI
- CLI: `quirk ticket create --backend servicenow` (default backend = jira); the shared `quirk ticket create` entrypoint dispatches on `--backend`
- Config: `[ticketing]` gains a `servicenow` sub-block (`instance_url`, `user_env`, `password_env`), mirroring the jira sub-block
- Auth: HTTP Basic auth (user + password/token resolved from env-var NAMES) over HTTPS
- Credentials referenced by env-var name only; never written to SQLite, scan JSON, or logs (criterion 3)

### Reuse & Safety (TICKET-04 inheritance)
- New `quirk/ticketing/servicenow.py::ServiceNowChannel(TicketingChannel)` implementing ONLY the 3 abstract methods (`find_by_fingerprint`, `create_issue_from_finding`, `add_rediscovery_comment`) — ZERO changes to base.py or jira.py (the Phase 104 verifier confirmed this is possible)
- Fingerprint is the identical `compute_fingerprint` from base (`SHA256(host:port::title)`) — same semantics as Jira so a finding has a consistent fingerprint across backends
- `validate_external_url(instance_url)` before any call; `safe_str` on all errors; missing `[tickets]` extra → graceful skip (already implemented in Phase 104 — ServiceNow needs no jira import, but the CLI extra-gate still applies; note urllib is stdlib so a ServiceNow-only user technically needs no third-party lib — confirm at plan time whether the [tickets] gate should apply to the servicenow backend)
- Audit: the shared `dispatch_finding` writes `integration_deliveries(destination="servicenow", finding_hash=fp)` — no new audit code

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (all from Phase 104)
- `quirk/ticketing/base.py::TicketingChannel` ABC — 3 abstract methods (find_by_fingerprint → Optional[str], create_issue_from_finding → str, add_rediscovery_comment → None) + shared compute_fingerprint (staticmethod), build_ticket_evidence, dispatch_finding (with integration_deliveries audit + WR-01 commit pattern). Verified to accept a ServiceNow subclass with zero base changes.
- `quirk/ticketing/jira.py::JiraChannel` — the analog subclass shape (lazy import, validate_external_url in __init__, the 3 methods).
- `quirk/ticketing/config.py` — JiraTicketingCfg + TicketingCfg + load_ticketing_config (env-var-name fields, SQLite-safe); add a ServiceNowTicketingCfg sub-block.
- `quirk/cli/ticket_cmd.py::run_ticket` — add `--backend {jira,servicenow}` dispatch.
- `quirk/util/safe_exc.py::safe_str` (now scrubs basic_auth/token_auth reprs), `quirk/util/url_allowlist.py::validate_external_url`.

### Established Patterns
- Phase 104 JiraChannel is the exact template; ServiceNow swaps the jira-lib calls for stdlib urllib Table API requests.
- ServiceNow Basic auth header: `Authorization: Basic base64(user:password)` — must be built from env-resolved creds, never logged.
- The Phase 103 webhook transport (quirk/siem/transport.py) and any existing urllib JSON POST helper are references for the HTTP mechanics + timeout.

### Integration Points
- New quirk/ticketing/servicenow.py (subclass only).
- quirk/ticketing/config.py (ServiceNowTicketingCfg sub-block).
- quirk/cli/ticket_cmd.py (--backend flag).
- No new pyproject extra (urllib is stdlib; [tickets] already exists).

</code_context>

<specifics>
## Specific Ideas

- ServiceNow Table API specifics need plan-time verification: the exact incident endpoint, the `sysparm_query=correlation_id=<fp>` dedup syntax, the response shape (sys_id), and work_notes update via PATCH `PUT/PATCH /api/now/table/incident/{sys_id}`.
- The fingerprint MUST be byte-identical to Phase 104's (SHA256(host:port::title)) — it comes from the shared base staticmethod, so this is guaranteed as long as ServiceNowChannel does not override compute_fingerprint.
- Confirm at plan time whether the `[tickets]` extra gate (is_extra_available) should apply to the servicenow backend — ServiceNow uses only stdlib urllib, so a ServiceNow-only user arguably needs no extra. Decision: keep the gate consistent for now (the CLI is shared) unless trivially separable.

</specifics>

<deferred>
## Deferred Ideas

- ServiceNow OAuth token flow (Basic auth this phase).
- ServiceNow-specific record types beyond incident (e.g. sn_si_incident security incident) — standard incident table this phase.
- Bidirectional sync / auto-close on finding resolution.
- Any refactor of the Phase 104 abstraction (it must absorb ServiceNow unchanged).

</deferred>
