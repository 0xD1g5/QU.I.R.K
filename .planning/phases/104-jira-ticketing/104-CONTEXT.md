# Phase 104: Jira Ticketing - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase lets a security team auto-create one Jira issue per finding, each carrying the
relevant QRAMM dimension evidence, with idempotent dedup so re-scans never proliferate
duplicate tickets. It ALSO builds the shared `TicketingChannel` abstraction (TICKET-04)
that Phase 105 (ServiceNow) reuses — Jira and ServiceNow must NOT be two parallel
hand-built code paths.

In scope: TICKET-01 (Jira issue per finding + QRAMM evidence, via `jira` lib behind a
`[tickets]` extra), TICKET-03 (idempotent dedup via stable fingerprint searched before
create), TICKET-04 (the shared ticketing abstraction + fingerprint/dedup + evidence-payload
logic). Inherits Phase 101: `integration_deliveries` table (the `finding_hash` column was
added there "for future phases" — this is that phase), `safe_str`, the optional-extra
lazy-import discipline (`quirk/util/optional_extra.py::is_extra_available`), and
`validate_external_url`.

Out of scope: ServiceNow backend (TICKET-02 → Phase 105, which subclasses the abstraction
built here); bidirectional sync; ticket close-on-resolution; custom field mapping beyond
project/issuetype.
</domain>

<decisions>
## Implementation Decisions

### Ticketing Abstraction (TICKET-04 — built here, reused by 105)
- A `TicketingChannel` ABC in `quirk/ticketing/base.py` with `create_or_update(finding, fingerprint, evidence)` and `find_by_fingerprint(fp)` — Jira and ServiceNow each subclass it
- The shared layer owns: fingerprint computation, dedup orchestration, evidence-payload build, and `integration_deliveries` audit writes; ONLY the backend API calls are subclass-specific
- A shared `build_ticket_evidence(finding)` sources the QRAMM dimension evidence (via `quirk/qramm/evidence_bridge.py`) and feeds both backends identically
- Module layout: `quirk/ticketing/{base,jira,servicenow}.py` — Phase 105 adds servicenow.py only, no changes to base/jira

### Jira Backend (TICKET-01)
- `jira>=3.10.5` behind a new `[tickets]` extra, lazy-imported with graceful skip (ISEC-04)
- `[tickets]` JOINS `[all]` with a CI guard test (like `[notify]`); verify no dependency conflict via pip dry-run at execute time
- Issue fields: project key + issue type from `[ticketing]` config; summary = finding title; description = QRAMM evidence + the fingerprint label
- One Jira issue per finding (criterion 1)

### Idempotent Dedup (TICKET-03)
- Fingerprint = `SHA256(host:port:protocol:category)` (hex), stored as a Jira **label** AND in `integration_deliveries.finding_hash`
- Dedup: JQL label search before create; if a matching ticket is found → update it with a "rediscovery" comment instead of creating a duplicate (criterion 2)
- Second run against the same scan / same findings adds rediscovery comments, creates zero new issues
- Each attempt writes an `integration_deliveries` row (destination="jira", finding_hash=fingerprint, status ok/failed)

### Config, Creds & Safety
- CLI: `quirk ticket create` reading a completed scan's findings (latest in output dir or `--input <path>`)
- Jira URL / user / API-token resolved from env vars (names referenced in a `[ticketing]` config block); credentials NEVER written to SQLite or logs (criterion 3)
- A missing `[tickets]` extra → `is_extra_available("tickets")` advisory + graceful skip, never an ImportError (ISEC-04)
- All errors routed through `safe_str`; validate the Jira base URL with `validate_external_url` (allowing the configured host — Jira Cloud is public, self-hosted may be internal) for SSRF safety

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `integration_deliveries` table (quirk/models.py:256) — the `finding_hash = Column(String(64))` "SHA256 dedup key (future phases)" column is exactly TICKET-03's fingerprint store.
- `quirk/util/optional_extra.py::is_extra_available(extra)` (find_spec-based, no import) — reuse for `[tickets]` graceful skip (ISEC-04).
- `quirk/qramm/evidence_bridge.py` — the QRAMM dimension evidence source for ticket descriptions.
- `quirk/util/safe_exc.py::safe_str` + `quirk/util/url_allowlist.py::validate_external_url` (Phase 101).
- Phase 101 `quirk/notify/dispatcher.py` per-channel try/except + audit-row pattern, and the `[notify]`→`[all]` + CI-guard precedent (pyproject.toml line 54-71) — mirror for `[tickets]`.
- CLI subcommand registration via the run_scan.py interception block (the `export` block added in Phase 103 is the freshest analog).

### Established Patterns
- `[notifications]`/`[siem]` YAML config + loader (quirk/notify/config.py, quirk/siem/config.py) — mirror for `[ticketing]`.
- Findings are a list of dicts with severity/host/port/title/category persisted to findings-*.json.
- Zero-secret-persistence + env-var-name references (Phase 101 NOTIFY-06).

### Integration Points
- New `quirk/ticketing/` package (base.py ABC + jira.py backend).
- New `quirk/cli/ticket_cmd.py` + run_scan.py interception for `quirk ticket create`.
- New `[ticketing]` config block.
- pyproject.toml: new `tickets = ["jira>=3.10.5"]` extra + join `[all]`.
- `integration_deliveries.finding_hash` finally used for dedup.

</code_context>

<specifics>
## Specific Ideas

- jira-lib API needs plan-time research: verify Jira Cloud REST v3 JQL label-filter syntax and the create_issue() field map (STATE.md pending todo for Phase 104).
- The TicketingChannel ABC is the load-bearing artifact for Phase 105 — design it so ServiceNow drops in as a subclass with ONLY its Table API calls differing. Phase 105 must require no changes to base.py or jira.py.
- Fingerprint must be identical to whatever Phase 105 uses (SHA256(host:port:protocol:category)) so a finding ticketed in Jira and ServiceNow shares the same fingerprint semantics.

</specifics>

<deferred>
## Deferred Ideas

- ServiceNow backend (TICKET-02) — Phase 105.
- Bidirectional sync / ticket auto-close on finding resolution.
- Custom Jira field mapping beyond project + issue type.
- Per-schedule ticketing routing (global config only, consistent with v5.3-D-07).

</deferred>
