# Requirements: v5.3 Adoption & Integration Surface

**Milestone goal:** Make QU.I.R.K. load-bearing inside someone else's workflow — findings and scheduled-scan drift events flow into the tools security teams already use (Slack/email/webhook, syslog/CEF SIEM, Jira + ServiceNow tickets), behind a team-shareable authenticated dashboard.

**Source of truth for forward outlook:** `.planning/HORIZON.md` (v5.3 section). Research: `.planning/research/SUMMARY.md`.

---

## v5.3 Requirements

### Notification Fan-Out (NOTIFY) — ANCHOR
- [x] **NOTIFY-01**: A completed scheduled scan computes its drift (`TrendReport`) and dispatches a notification when the configured trigger fires — closing the gap where drift events are emitted but never delivered
- [x] **NOTIFY-02**: Notifications fire on a conservative default trigger — a new HIGH/CRITICAL finding OR a score regression beyond a configurable floor (default −5) — never on every scan and never on MEDIUM-only by default
- [x] **NOTIFY-03**: A user can deliver notifications to Slack via an incoming-webhook URL (one summary message per scan, not one per finding)
- [x] **NOTIFY-04**: A user can deliver notifications via email (stdlib SMTP) to one or more recipients
- [x] **NOTIFY-05**: A user can deliver notifications to a generic outbound webhook (JSON POST) for custom integrations
- [x] **NOTIFY-06**: Notification channels and trigger thresholds are configured in one global config block (applies to all scheduled scans); secrets are referenced by env-var name, never stored in config or persisted state
- [x] **NOTIFY-07**: A delivery failure (unreachable endpoint, auth error, timeout) is logged and isolated — it never aborts or corrupts the scan/report run, and each delivery attempt is recorded for observability

### Integration Security Foundation (ISEC) — load-bearing for all integration phases
- [x] **ISEC-01**: Every user-configured outbound URL (webhook, SIEM, ticketing) is validated against SSRF at DELIVERY time (not only config-load), rejecting internal/loopback/metadata targets
- [x] **ISEC-02**: Integration secret shapes (Slack `xoxb-`/webhook URLs, `Authorization: Splunk`, SMTP auth errors, Jira/ServiceNow tokens) are scrubbed from logs and error messages by the existing `safe_str` discipline
- [x] **ISEC-03**: A single whitelist defines exactly which finding/cert/drift fields are safe to send to a third party — sensitive material is redacted before any outbound payload is built
- [x] **ISEC-04**: Every integration client library is an optional extra with lazy import + graceful skip — a missing/absent integration dependency never breaks the minimal install or a scan

### SIEM / Observability Export (SIEM)
- [ ] **SIEM-01**: A user can export findings to a SIEM in syslog/CEF format (vendor-neutral) — landing in any syslog-ingesting platform (Splunk, Elastic, QRadar, etc.)
- [ ] **SIEM-02**: SIEM export is a findings-push (distinct from drift notifications) with correct CEF field mapping (severity, host, signature/category, evidence), invokable from the CLI and optionally after a scan

### Ticketing Integration (TICKET)
- [ ] **TICKET-01**: A user can auto-create a Jira issue per finding, carrying QRAMM evidence in the description, via the `jira` library behind a `[tickets]` extra
- [ ] **TICKET-02**: A user can auto-create a ServiceNow incident/record per finding (Table API), carrying QRAMM evidence
- [ ] **TICKET-03**: Ticket creation is idempotent across re-scans — a stable finding fingerprint (e.g. `SHA256(host:port:protocol:category)`) is searched before create so re-scans do not proliferate duplicate tickets
- [ ] **TICKET-04**: Jira and ServiceNow share one ticketing abstraction (sink/channel) and the same fingerprint/dedup + evidence-payload logic — not two parallel hand-built code paths

### Dashboard Team Auth (AUTH)
- [ ] **AUTH-01**: A user can generate and rotate a dashboard API token via the CLI (`quirk token`/`auth` command, stdlib `secrets`)
- [ ] **AUTH-02**: The dashboard accepts an `X-API-Key` header (in addition to the existing bearer token), with timing-safe comparison; all data-returning routes are protected and a CI test enforces route coverage so new routes can't ship unprotected
- [ ] **AUTH-03**: The dashboard presents a login form and a clear authenticated/unauthenticated state so a team can share a single-tenant instance

### Report Consistency Tax (TRANS) — folded from v5.2
- [ ] **TRANS-04**: The CLI executive markdown sources its score (total, band, subscores) from the shared `exec_content` rather than re-deriving it locally, and a cross-surface parity test asserts the score number is identical across CLI/HTML/PDF/DOCX

---

## Future Requirements (deferred)

- Splunk HEC native export (token-based event endpoint) — syslog/CEF covers the SIEM-push validation for v5.3; HEC is a fast follow if a Splunk-specific ask surfaces
- Elasticsearch/ECS native client export — rejected for v5.3 as client-library overkill; revisit in v5.4
- Per-schedule notification routing (each schedule → its own channel/threshold) — needs a schedules-table schema change; global config ships first
- Notification digest/rollup across multiple scans, and richer Block Kit formatting
- Token expiry / per-user keys / scopes for dashboard auth — single static rotatable key is sufficient for single-tenant team sharing
- SaaS multi-tenancy + distributed multi-node (999.22) — gated on a real adoption signal; HORIZON v5.4

---

## Out of Scope (v5.3)

| Feature | Reason |
|---------|--------|
| SaaS multi-tenant dashboard | Single-tenant team auth only; multi-tenancy is v5.4, gated on adoption signal |
| OAuth app / Slack bot-token flows | Incoming webhook needs no workspace-admin approval; bot tokens add OAuth complexity for no v5.3 benefit |
| Inbound integrations (pull from SIEM/ticketing) | v5.3 is outbound delivery only |
| Real-time streaming / message-queue delivery | Post-scan batch dispatch is sufficient; no task queue introduced (that's SaaS-era) |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NOTIFY-01 | Phase 101 | Complete |
| NOTIFY-02 | Phase 101 | Complete |
| NOTIFY-03 | Phase 101 | Complete |
| NOTIFY-04 | Phase 101 | Complete |
| NOTIFY-05 | Phase 101 | Complete |
| NOTIFY-06 | Phase 101 | Complete |
| NOTIFY-07 | Phase 101 | Complete |
| ISEC-01 | Phase 101 | Complete |
| ISEC-02 | Phase 101 | Complete |
| ISEC-03 | Phase 101 | Complete |
| ISEC-04 | Phase 101 | Complete |
| SIEM-01 | Phase 103 | Pending |
| SIEM-02 | Phase 103 | Pending |
| TICKET-01 | Phase 104 | Pending |
| TICKET-02 | Phase 105 | Pending |
| TICKET-03 | Phase 104 | Pending |
| TICKET-04 | Phase 104 | Pending |
| AUTH-01 | Phase 102 | Pending |
| AUTH-02 | Phase 102 | Pending |
| AUTH-03 | Phase 102 | Pending |
| TRANS-04 | Phase 102 | Pending |
