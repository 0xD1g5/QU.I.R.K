# Roadmap: QU.I.R.K. — Quantum Infrastructure Readiness Kit

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 17 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- ✅ **v4.3 Data at Rest** — Phases 25–31, 24 plans (shipped 2026-04-26) → `.planning/milestones/v4.3-ROADMAP.md`
- ✅ **v4.4 Data in Motion** — Phases 32–37, 33 plans (shipped 2026-04-29) → `.planning/milestones/v4.4-ROADMAP.md`
- ✅ **v4.5 Reliability & Gap Closure** — Phases 38–44, 40 plans (shipped 2026-05-03) → `.planning/milestones/v4.5-ROADMAP.md`
- ✅ **v4.6 Enterprise Readiness** — Phases 45–50, 24 plans (shipped 2026-05-05) → `.planning/milestones/v4.6-ROADMAP.md`
- ✅ **v4.7 Governance & Compliance** — Phases 51–56 (shipped 2026-05-08) → `.planning/milestones/v4.7-ROADMAP.md`
- ✅ **v4.8 Pre-Primetime** — Phases 57–68, 53 plans (shipped 2026-05-14) → `.planning/milestones/v4.8-ROADMAP.md`
- ✅ **v4.9 Audit Depth** — Phases 69–77, 38 plans (shipped 2026-05-15) → `.planning/milestones/v4.9-ROADMAP.md`
- ✅ **v4.10 Launch Readiness** — Phases 78–85, 31 plans (shipped 2026-05-21) → `.planning/milestones/v4.10-ROADMAP.md`
- ✅ **v4.10.1 Scoring Correctness Hotfix** — Phase 86, 3 plans (shipped 2026-05-22) → `.planning/milestones/v4.10.1-ROADMAP.md`
- ✅ **v5.0 Stabilization + Tech Debt Sweep** — Phases 87–92, 16 plans (shipped 2026-05-22) → `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v5.1 Authenticated Scanning + API Surface Depth** — Phases 93–96, 16 plans (shipped 2026-05-23) → `.planning/milestones/v5.1-ROADMAP.md`
- ✅ **v5.2 Consulting-Grade Reporting** — Phases 97–100, 12 plans (shipped 2026-05-24) → `.planning/milestones/v5.2-ROADMAP.md`
- 🚧 **v5.3 Adoption & Integration Surface** — Phases 101–105 (in progress)

---

<details>
<summary>✅ v3.9–v5.2 (Phases 1–100) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. The next milestone continues from Phase 101.

</details>

---

### 🚧 v5.3 Adoption & Integration Surface (In Progress)

**Milestone Goal:** Make QU.I.R.K. load-bearing inside someone else's workflow — findings and scheduled-scan drift events flow into the tools security teams already use (Slack/email/webhook, syslog/CEF SIEM, Jira + ServiceNow tickets), behind a team-shareable authenticated dashboard.

## Phases

- [x] **Phase 101: Notification Fan-Out + Security Foundation** — Drift-event delivery (Slack, email, webhook) wired into the scheduler seam, plus all integration security primitives inherited by every downstream phase (completed 2026-05-25)
- [ ] **Phase 102: Dashboard Auth UX + Score Tax** — X-API-Key header support, token generate/rotate CLI, React login form, and CLI exec-score sourced from shared content model
- [ ] **Phase 103: SIEM Export** — Per-scan per-finding batch push to syslog/CEF (vendor-neutral) and Splunk HEC, zero new pip deps
- [ ] **Phase 104: Jira Ticketing** — Per-finding Jira issue creation with shared ticketing abstraction, SHA256 fingerprint dedup, and QRAMM evidence in descriptions
- [ ] **Phase 105: ServiceNow Ticketing** — ServiceNow incident/record creation reusing the Phase 104 ticketing abstraction and dedup infrastructure

## Phase Details

### Phase 101: Notification Fan-Out + Security Foundation
**Goal**: Scheduled-scan drift events are delivered to operators — Slack summary, email, and generic webhook — with all integration security primitives locked in so downstream phases inherit a safe, isolated delivery layer
**Depends on**: Nothing (first phase of milestone; Phase 63/64 scheduler + trends exist)
**Requirements**: NOTIFY-01, NOTIFY-02, NOTIFY-03, NOTIFY-04, NOTIFY-05, NOTIFY-06, NOTIFY-07, ISEC-01, ISEC-02, ISEC-03, ISEC-04
**Success Criteria** (what must be TRUE):
  1. After a scheduled scan completes, a Slack message summarizing the drift event (score band, delta, finding counts, dashboard link) appears in the configured channel — without any manual action
  2. No notification fires when the scan produces no new HIGH/CRITICAL findings and the score change is within the configured threshold (default ±5) — no alert fatigue
  3. A delivery failure (misconfigured Slack URL, SMTP timeout, unreachable webhook) is logged at WARNING level and the scan record remains clean — the scan completes successfully regardless
  4. Secrets (Slack webhook URL, SMTP password, HMAC signing key) are never written to SQLite, scan JSON, or log output — they resolve from environment variables at dispatch time
  5. A missing `[notify]` extra (slack-sdk absent) degrades gracefully with an advisory log line rather than an ImportError that breaks the minimal install
**Plans**: 4 plans
- [x] 101-01-PLAN.md — Foundation: safe_str secret patterns, integration_deliveries table, [notify] extra (ISEC-02, NOTIFY-07)
- [x] 101-02-PLAN.md — Security primitives: NotifyCfg loader + to_integration_payload whitelist + DriftSummary (NOTIFY-06, ISEC-03)
- [x] 101-03-PLAN.md — Channels: Slack/email/webhook senders with delivery-time SSRF + lazy import (NOTIFY-03/04/05, ISEC-01, ISEC-04)
- [x] 101-04-PLAN.md — Dispatcher + scheduler wiring + docs/Obsidian/UAT (NOTIFY-01/02/07, ISEC-02)
**UI hint**: yes

### Phase 102: Dashboard Auth UX + Score Tax
**Goal**: A team can share a single-tenant dashboard instance via a rotatable API token and a login form, and the CLI executive report sources its score numbers from the same shared content model as HTML/PDF
**Depends on**: Phase 101 (route-coverage CI test established there)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, TRANS-04
**Success Criteria** (what must be TRUE):
  1. An operator can run `quirk token generate` to get a fresh API token and `quirk token rotate` to replace it — the old token stops working immediately after rotation
  2. The dashboard accepts `X-API-Key: <token>` as an alternative to `Authorization: Bearer <token>` on all protected routes, and a CI test confirms no data-returning route is unprotected
  3. An unauthenticated browser opening the dashboard sees a login form rather than a silent 401 — after entering the correct token the full dashboard loads
  4. The score totals, band, and subscore breakdowns in the CLI executive markdown are numerically identical to the HTML and PDF report for the same scan
**Plans**: 5 plans
- [x] 102-01-PLAN.md — AUTH-01 token CLI (generate/rotate/show) + YAML write-back
- [ ] 102-02-PLAN.md — AUTH-02 X-API-Key auth extension + route-coverage CI gate
- [ ] 102-03-PLAN.md — TRANS-04 CLI executive score sourced from exec_content + parity test
- [ ] 102-04-PLAN.md — AUTH-03 React login form, AuthProvider, Sign out + statics rebuild
- [ ] 102-05-PLAN.md — Docs (configuration.md) + UAT-SERIES.md + Obsidian phase note sync
**UI hint**: yes

### Phase 103: SIEM Export
**Goal**: Security teams can push QU.I.R.K. findings into their existing SIEM (Splunk, Elastic, QRadar, or any syslog-ingesting platform) without installing additional pip packages
**Depends on**: Phase 101 (to_integration_payload whitelist, safe_str patterns, integration_deliveries table)
**Requirements**: SIEM-01, SIEM-02
**Success Criteria** (what must be TRUE):
  1. Running `quirk export --siem` against a completed scan submits one CEF-formatted event per finding to the configured syslog target or Splunk HEC endpoint — verifiable in the receiving platform's event log
  2. A SIEM export triggered after a scheduled scan completes delivers findings with correct CEF field mapping (severity, host, signature/category, evidence) — no raw cert PEM or internal PKI topology is included in the payload
  3. A misconfigured or unreachable SIEM endpoint produces a clear error message and does not abort or corrupt the scan record
**Plans**: TBD

### Phase 104: Jira Ticketing
**Goal**: A security team can auto-create one Jira issue per finding carrying QRAMM evidence, with idempotent dedup so re-scans never proliferate duplicate tickets
**Depends on**: Phase 101 (to_integration_payload whitelist, integration_deliveries idempotency table)
**Requirements**: TICKET-01, TICKET-03, TICKET-04
**Success Criteria** (what must be TRUE):
  1. Running `quirk ticket create` against a completed scan opens one Jira issue per finding, each carrying the relevant QRAMM dimension evidence in the description
  2. Running `quirk ticket create` a second time against the same scan (or a follow-up scan with the same findings) does not create duplicate issues — the SHA256 fingerprint label is found via JQL and the existing ticket is updated with a rediscovery comment instead
  3. Jira credentials are never written to SQLite or logs — they resolve from environment variables; a missing `[tickets]` extra degrades gracefully without an ImportError
**Plans**: TBD

### Phase 105: ServiceNow Ticketing
**Goal**: A security team using ServiceNow can auto-create incidents per finding via the same ticketing abstraction and dedup logic established in Phase 104 — no parallel code path
**Depends on**: Phase 104 (TicketingChannel abstraction, fingerprint dedup, integration_deliveries table, to_integration_payload)
**Requirements**: TICKET-02
**Success Criteria** (what must be TRUE):
  1. Running `quirk ticket create --backend servicenow` against a completed scan creates one ServiceNow incident per finding carrying QRAMM evidence, using the Table API with stdlib urllib (no new pip dep beyond the `[tickets]` extra)
  2. Re-running against the same findings does not open duplicate incidents — the same SHA256 fingerprint dedup logic from Phase 104 is applied via the shared TicketingChannel abstraction
  3. ServiceNow credentials (instance URL, username, password/token) resolve from environment variables and are never written to SQLite, scan JSON, or logs
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 101. Notification Fan-Out + Security Foundation | 4/4 | Complete   | 2026-05-25 |
| 102. Dashboard Auth UX + Score Tax | 1/5 | In Progress|  |
| 103. SIEM Export | 0/TBD | Not started | - |
| 104. Jira Ticketing | 0/TBD | Not started | - |
| 105. ServiceNow Ticketing | 0/TBD | Not started | - |
