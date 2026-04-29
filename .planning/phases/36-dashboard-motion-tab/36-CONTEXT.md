# Phase 36: Dashboard Motion Tab — Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface the email + broker TLS posture (already produced by Phases 32–35 in scanners, scoring, and CBOM) inside the React dashboard. Scope is **dashboard rendering + the API contract that feeds it** — no scanner, scoring, or CBOM changes.

**In scope:**
- New `/motion` React route + sidebar entry (DASH-01).
- Email section: per-port table with TLS evidence and STARTTLS warning badge on port 25 (DASH-02).
- Broker section: per-broker-family grouped subsections (Kafka / AMQP / Redis) with plaintext-exposed flag (DASH-03).
- Executive Summary card: add **Data in Motion** as the 6th `ScoreGauge` reading `score.subscores.data_in_motion` (DASH-04).
- Extend `SubScores` TypeScript interface in `src/dashboard/src/types/api.ts` to include `data_in_motion: number`.
- FastAPI `/api/scan/latest` response: add `motion_findings: list[MotionFinding]` parallel to `identity_findings` (DASH-05).
- Empty-state messaging when a scan has no email or no broker endpoints.
- Mandatory phase close-out tasks per CLAUDE.md: Obsidian phase note, `docs/UAT-SERIES.md` update, vault sync, commit.

**Out of scope (other phases or backlog):**
- Any change to `quirk/scanner/email_scanner.py`, `quirk/scanner/broker_scanner.py`, scoring, or CBOM (Phases 32–35).
- Renaming the existing 5 subscore keys (Phase 34 D-05 deferred to v4.5+).
- Print page (`pages/print.tsx`) updates for the 6th score line — capture as deferred, address in Phase 37 polish or a separate ticket.
- Per-finding detail Sheet drawer (mirroring identity.tsx's row-click → Sheet) — not required by DASH-01..05; planner may include if cheap.

</domain>

<decisions>
## Implementation Decisions

### Page composition (DASH-01, DASH-02, DASH-03)
- **D-01:** **Single `/motion` page with two stacked sections** — Email on top, Broker below, both visible in one scroll. Mirrors `pages/identity.tsx`'s "status pills + findings table" pattern. Easier to print/screenshot for client deliverables; cheapest to build.
- File: new `src/dashboard/src/pages/motion.tsx`. Route added in `src/dashboard/src/App.tsx` between `/identity` and `/certificates`. Sidebar entry added in `src/dashboard/src/components/sidebar.tsx`.
- **Sidebar icon:** **Claude's discretion** from `lucide-react` — strongest candidates are `Activity`, `Radio`, `Send`, or `Waves`. Pick whichever reads "data in motion" most clearly to a fresh viewer; do not invent a new icon system.

### MotionFinding API schema (DASH-05)
- **D-02:** **Motion-extended schema** — mirror IdentityFinding's base fields and add motion-specific evidence inline. Authoritative TypeScript shape:
  ```ts
  interface MotionFinding {
    host: string
    port: number
    severity: string
    title: string
    protocol?: string         // SMTPS, SMTP-STARTTLS, KAFKA-TLS, AMQP-PLAIN, AMQPS/Azure-ServiceBus, ...
    description?: string
    remediation?: string
    quantum_risk?: string
    source?: string
    tls_version?: string      // "TLSv1.2" | undefined when plaintext
    cipher_suite?: string
    cert_not_after?: string   // ISO date
    plaintext_exposed: boolean
    starttls_warning: boolean // true only on port-25 SMTP-STARTTLS
  }
  ```
- The Pydantic model in FastAPI must match this shape and be **non-optional** for `plaintext_exposed` and `starttls_warning` (booleans default to `false`). Tables render directly from rows — UI never parses `description` for evidence.
- **Protocol label preservation:** carry the scanner-emitted label verbatim (Phase 35 D-03). Do **not** normalize `AMQPS/Azure-ServiceBus` — surface it via a row badge inside the AMQP family section (D-03 below).

### Broker grouping (DASH-03)
- **D-03:** **Grouped subsections per broker family** — three subsections in fixed order: **Kafka**, **AMQP** (combines RabbitMQ + Azure Service Bus, since both speak AMQP), **Redis**. Each subsection header shows a status pill: `<Family> · N endpoint(s) · M plaintext`.
- **Family detection** — derive family from `protocol` label prefix:
  - `KAFKA-*` → Kafka
  - `AMQP-*` / `AMQPS*` (including `AMQPS/Azure-ServiceBus`) → AMQP
  - `REDIS-*` → Redis
- **Cloud distinction** — when `protocol` contains `/` (e.g., `AMQPS/Azure-ServiceBus`), render a small cloud chip (`☁ Azure`) on that row. The slash never appears in user-facing text — split on `/`, take suffix as cloud annotation.

### Status / warning badges (DASH-02, DASH-03)
- **D-04:** **Reuse `pages/identity.tsx` severity styling** — the inline-HSL convention (`bg-[hsl(...)]`). Specifically:
  - **STARTTLS warning** (port 25 only): MEDIUM amber `bg-[hsl(38_92%_50%)] text-black` + `⚠` glyph + label `STARTTLS`.
  - **Plaintext exposed** (broker only): HIGH orange `bg-[hsl(24_95%_53%)] text-white` + `☠` glyph + label `PLAINTEXT`.
  - **Healthy TLS rows:** no badge — neutral `tls_version` text only.
- Do **not** add new variants to `components/ui/badge.tsx`. Match identity.tsx exactly so the dashboard stays one badge vocabulary.

### Empty state (UX gap inferred from DASH-01)
- **D-05:** **Always render both sections.** When a scan has no email endpoints, the Email section shows a muted empty-state card: `"No email endpoints scanned in this session — enable the email scanner in your config or scan a mail server."` Same pattern for broker. Layout is predictable across scans and teaches users which surfaces exist.
- Detection: derive `motion_findings.filter(f => isEmailProtocol(f.protocol))` and the broker counterpart; empty array → empty-state card.

### Executive Summary 6th subscore (DASH-04)
- **D-06:** Add a 6th `<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />` to the existing flex-wrap row in `pages/executive.tsx` (~line 150). Position: **last in the row** (after Data at Rest). The flex-wrap container already handles 6 gauges without layout changes.
- Extend `SubScores` interface in `types/api.ts` to add `data_in_motion: number`.
- Phase 34 D-04 already locked the key as `data_in_motion` — no naming question.

### Verification approach
- **D-07:** **Component-level RTL tests** for `pages/motion.tsx` rendering — fixture-driven (`MotionFinding[]` mocks) covering: (a) email-only scan, (b) broker-only scan, (c) mixed, (d) empty (both empty-states render). Mirror existing test conventions if `tests/dashboard/` exists; planner verifies and decides Vitest vs Jest based on `package.json`.
- **D-08:** **API contract test** asserting `/api/scan/latest` response includes `motion_findings` as a list, with at least one row populated when `motion_*` evidence counters are non-zero. Backend test goes alongside existing `tests/api/` patterns.
- **D-09:** **Manual UAT** against the v4.4 chaos labs (`docker compose --profile email up` + `--profile broker up` from Phases 32–33), plus an empty-state UAT that scans a host with neither email nor broker endpoints. Documented as new test cases in `docs/UAT-SERIES.md`.

### Documentation updates (mandatory per CLAUDE.md)
- **D-10:** Obsidian phase note created at phase start, updated per wave, finalized on completion at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md`.
- **D-11:** `docs/UAT-SERIES.md` gains UAT cases for: (a) `/motion` route loads and shows both sections, (b) port-25 STARTTLS warning badge renders, (c) plaintext broker shows red ☠ badge, (d) executive summary shows 6 ScoreGauges including Data in Motion, (e) empty-state cards render when scanner profiles are off.
- **D-12:** `UAT-SERIES.md` synced to vault and committed per the standard CLAUDE.md flow.

### Claude's Discretion
- Sidebar icon choice from `lucide-react` (D-01).
- Whether each broker subsection collapses (radix accordion) or always-expanded — default to always-expanded, but planner may switch if endpoint counts are typically large.
- Per-row click → `Sheet` detail drawer mirroring `identity.tsx` lines 60–63 — include if it's <30 LOC and reuses existing `Sheet`; otherwise defer.
- Whether to add a small "Total motion endpoints" KPI strip above the Email section (analogous to identity.tsx's protocol status cards) — nice-to-have if a single source of truth exists in the API response.
- File naming for the new RTL tests — likely `src/dashboard/src/pages/__tests__/motion.test.tsx`; planner verifies convention from existing tests.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (locked)
- `.planning/REQUIREMENTS.md` §"Dashboard" — DASH-01, DASH-02, DASH-03, DASH-04, DASH-05 are LOCKED.
- `.planning/ROADMAP.md` Phase 36 entry — Dashboard Motion Tab goal + 5 success criteria.

### React dashboard pattern templates (read before writing UI)
- `src/dashboard/src/pages/identity.tsx` (entire file, ~140 lines) — **closest analog**. Source of: severity color HSL constants (lines 23–29), status-pill convention (lines 33–43, 45–50), tanstack-table column setup, fetch + skeleton pattern.
- `src/dashboard/src/pages/executive.tsx` (~lines 125–153) — score gauges flex-wrap row. **D-06 modifies this file** to add the 6th gauge.
- `src/dashboard/src/components/sidebar.tsx` — `NAV_ITEMS` array (lines 19–27). Add Motion entry between Identity and Certificates (or position planner deems best). Use a `lucide-react` icon (existing imports: `LayoutDashboard`, `AlertTriangle`, `Shield`, `Database`, `GitBranch`, `Fingerprint`, `TrendingUp`).
- `src/dashboard/src/App.tsx` — `<Routes>` block (lines 27–36). Add `<Route path="/motion" element={<MotionPage />} />`.
- `src/dashboard/src/types/api.ts` — `SubScores` (lines 1–7), `IdentityFinding` (lines 80–91), `ScanLatestResponse` (lines 99–108). **D-02 + D-06 extend these.**
- `src/dashboard/src/hooks/useScanData.ts` — fetch + cache pattern; reuse for motion data (no new hook needed; `motion_findings` rides on `ScanLatestResponse`).

### shadcn/ui components (already installed — reuse, don't add)
- `components/ui/{tabs,card,badge,table,skeleton,sheet}.tsx` — all present in `src/dashboard/src/components/ui/`. The Motion page uses `Card`, `Badge`, `Table`, `Skeleton`. (Sheet is optional per Claude's discretion above.)
- `package.json` deps already include `@radix-ui/react-tabs`, `@radix-ui/react-tooltip`, `@tanstack/react-table`, `lucide-react`, `react-router-dom@^7`. No new dependencies required for Phase 36.

### Backend / API contract
- FastAPI app — locate via `quirk/dashboard/server.py` and `quirk/dashboard/api/`. The `/api/scan/latest` route returns the response that the `ScanLatestResponse` TS type mirrors. **D-02 adds `motion_findings: list[MotionFinding]` to the Pydantic response model.**
- `quirk/intelligence/scoring.py` already returns `data_in_motion` as the 6th subscore (Phase 34 D-04). **No backend score code change in Phase 36** — the dashboard just consumes the existing key.

### Carry-forward decisions (read before deciding edge cases)
- **Phase 32:** 6 email TLS labels emitted: `SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S`. Port 25 always emits `SMTP-STARTTLS` regardless of STARTTLS success — that is the trigger for the STARTTLS warning badge (D-04).
- **Phase 33:** broker labels follow `<TYPE>-TLS` / `<TYPE>-PLAIN` convention. Cloud variant: `AMQPS/Azure-ServiceBus` (Phase 35 D-03 preserved this verbatim). UI honors the slash and surfaces it as a cloud chip (D-03).
- **Phase 34 D-04:** subscore key is `data_in_motion`. **Do not rename** the existing 5 keys to roadmap-text names (`tls`/`ssh`/`api`/...) — that's a v4.5+ deferred idea.
- **Phase 34 D-05:** legacy scans without `motion_*` evidence return `data_in_motion = 100`; UI must render that gracefully (no special "no data" UI for the gauge — the 100 is correct).
- **Phase 35 D-03:** `AMQPS/Azure-ServiceBus` slash is preserved through Pass 1/2/3 of the CBOM. Phase 36 inherits.

### Project rules (CLAUDE.md)
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note, `docs/UAT-SERIES.md` update, vault sync, commit are required end-of-phase tasks (D-10..D-12). Plan tasks for these in the phase plan, not as afterthoughts.
- `CLAUDE.md` §"Code Standards" — PEP 8 for Python; minimal diffs; run `python -m compileall` and relevant tests after changes; update `labs/*/expected_results.md` if detection logic changes (not applicable in Phase 36).

### Chaos labs for manual UAT
- `labs/email/` (Postfix+Dovecot, weak TLS) + `docker-compose --profile email up` — exercises the email per-port table and STARTTLS warning.
- `labs/broker/` (Kafka + RabbitMQ + Redis, plaintext + TLS listeners) + `docker-compose --profile broker up` — exercises the broker grouped sections and plaintext badge.

### Downstream consumers (informational; not modified in Phase 36)
- Phase 37 will reference Phase 36's UI in the v4.4.0 release polish (version-string visibility, Nyquist VALIDATION.md). Stable component names and a stable `motion_findings` schema are inputs to Phase 37.

</canonical_refs>

<deferred>
## Deferred Ideas

- **DEF-36-A:** Print page (`pages/print.tsx`) updated to render the 6th score line and a motion summary. Scope creep for Phase 36 (which targets the live dashboard); pull into Phase 37 polish or a follow-on ticket.
- **DEF-36-B:** Per-row Sheet detail drawer for motion findings (mirroring `identity.tsx`'s row → Sheet pattern) — include only if it's a small lift; otherwise capture as a v4.5 polish item.
- **DEF-36-C:** Renaming the 5 existing subscore keys to roadmap-text names (`tls`/`ssh`/`api`/`identity`/`data_at_rest` + `data_in_motion`). Phase 34 D-05 already deferred this to v4.5+ because it breaks the existing API contract and saved scan reports.
- **DEF-36-D:** Endpoint-density-based switch from grouped subsections to a flat sortable broker table — only worth doing if real-world scans typically produce 10+ broker endpoints per family. Revisit in v4.5 if usage data shows it.
- **DEF-36-E:** Top-of-page Motion KPI strip ("N email endpoints · M brokers · K plaintext exposures") for at-a-glance summary above the two sections. Listed as Claude's discretion in D-01; capture here if not picked up.

</deferred>

[Roadmap](../../ROADMAP.md)
