# Phase 36: Dashboard Motion Tab — Research

**Researched:** 2026-04-28
**Domain:** React 19 + FastAPI dashboard surface for already-emitted motion (email/broker) findings
**Confidence:** HIGH (codebase-verified via direct file inspection)

## Summary

Phase 36 is a **pure presentation phase**: scanners (Phase 32–33), evidence + scoring (Phase 34), and CBOM integration (Phase 35) are complete. `quirk/intelligence/scoring.py:237` already returns `data_in_motion` in `subscores`. `quirk/intelligence/evidence.py` already counts the six `motion_*` evidence buckets. CryptoEndpoint rows are tagged with the canonical protocol labels (`SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S`, `KAFKA-TLS`, `KAFKA-PLAIN`, `AMQPS`, `AMQPS/Azure-ServiceBus`, `AMQP-PLAIN`, `REDIS-TLS`, `REDIS-PLAIN`, `HTTPS/AWS-SQS`).

What does NOT yet exist and Phase 36 must add:

1. A `_derive_motion_findings(endpoints)` function in `quirk/dashboard/api/routes/scan.py` (parallel to existing `_derive_identity_findings`, lines 184–330) that emits `MotionFinding` rows from CryptoEndpoint state.
2. A `MotionFinding` Pydantic model in `quirk/dashboard/api/schemas.py` (parallel to `IdentityFinding`, lines 80–90).
3. `motion_findings: List[MotionFinding] = []` on `ScanLatestResponse` (line 131 currently terminates the model with `identity_findings`).
4. `data_in_motion: int = 0` on the `SubScores` Pydantic model (`schemas.py:20–25`) AND in the manual constructor in `scan.py:595–601` — currently five fields only, so the new subscore is silently dropped today.
5. `data_in_motion` on the TS `SubScores` (`src/dashboard/src/types/api.ts:1–7`) and `motion_findings: MotionFinding[]` on `ScanLatestResponse` (line 99–108).
6. New `MotionPage` component at `src/dashboard/src/pages/motion.tsx` + `/motion` route in `App.tsx` (line 27–36) + sidebar entry in `components/sidebar.tsx` `NAV_ITEMS` (lines 19–27).
7. 6th `<ScoreGauge>` on `executive.tsx` after line 150.

**Primary recommendation:** Mirror the IdentityPage pattern (file: `src/dashboard/src/pages/identity.tsx`) verbatim — same imports, same severity HSL constants, same Skeleton/error pattern, same Card+Table composition. Do NOT introduce Vitest/Jest in this phase: the dashboard has no test framework installed and CONTEXT.md D-07 says "mirror existing test conventions if `tests/dashboard/` exists" — it does not. Verify behavior via the existing pytest backend test (`tests/test_dashboard_api.py` pattern) plus manual UAT (D-09).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** Single `/motion` page with two stacked sections (Email on top, Broker below). New file `src/dashboard/src/pages/motion.tsx`. Route added in `App.tsx` between `/identity` and `/certificates`. Sidebar entry added in `components/sidebar.tsx`. Sidebar icon: Claude's discretion from `lucide-react` (UI-SPEC chose `Activity`).
- **D-02** `MotionFinding` schema mirrors `IdentityFinding` plus motion-specific evidence. Pydantic model must have non-optional `plaintext_exposed: bool` and `starttls_warning: bool` (default `False`). Tables render directly from row fields; UI never parses `description`. Carry the scanner-emitted `protocol` label verbatim (no normalization of `AMQPS/Azure-ServiceBus`).
- **D-03** Three broker subsections, fixed order: **Kafka, AMQP, Redis**. Family detection by `protocol` prefix (`KAFKA-*` → Kafka, `AMQP-*` / `AMQPS*` → AMQP, `REDIS-*` → Redis). Cloud chip when `protocol` contains `/`.
- **D-04** Reuse identity.tsx severity styling (inline HSL `bg-[hsl(...)]`). STARTTLS warning = MEDIUM amber `hsl(38 92% 50%)` text-black `⚠ STARTTLS`. Plaintext exposed = HIGH orange `hsl(24 95% 53%)` text-white `☠ PLAINTEXT`. Healthy TLS rows render no badge. Do NOT add new variants to `components/ui/badge.tsx`.
- **D-05** Always render both sections. Empty state = muted Card with copy. Detection: filter `motion_findings` by `isEmailProtocol` / broker family.
- **D-06** Add 6th `<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />` last in the flex-wrap row in `executive.tsx` (~line 150). Extend `SubScores` TS interface.
- **D-07** Component-level RTL tests for motion.tsx — IF tests/dashboard/ exists; otherwise mirror existing convention (verified: it does not exist; defer to backend test + manual UAT).
- **D-08** API contract test asserting `/api/scan/latest` includes `motion_findings: list` and is populated when motion evidence non-zero. Goes in `tests/test_dashboard_api.py`.
- **D-09** Manual UAT against v4.4 chaos labs (`docker compose --profile email up`, `--profile broker up`) plus empty-state UAT.
- **D-10** Obsidian phase note created at start, updated per wave, finalized on completion at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md`.
- **D-11** New UAT cases in `docs/UAT-SERIES.md` for `/motion` route, port-25 STARTTLS badge, plaintext broker badge, 6 ScoreGauges, empty-state cards.
- **D-12** `UAT-SERIES.md` synced to vault and committed per CLAUDE.md flow.

### Claude's Discretion

- Sidebar icon from `lucide-react` (UI-SPEC chose `Activity`).
- Whether broker subsections collapse (default: always-expanded).
- Per-row Sheet detail drawer (include only if ≤30 LOC).
- Top-of-page KPI strip (nice-to-have).
- RTL test file naming if introduced.

### Deferred Ideas (OUT OF SCOPE)

- **DEF-36-A** Print page (`pages/print.tsx`) updates for the 6th score line — Phase 37 polish or follow-on ticket.
- **DEF-36-B** Per-row Sheet detail drawer (small lift only; otherwise v4.5).
- **DEF-36-C** Renaming the 5 subscore keys (Phase 34 D-05 deferred to v4.5+).
- **DEF-36-D** Endpoint-density-based switch from grouped to flat broker table.
- **DEF-36-E** Top-of-page Motion KPI strip.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | New `/motion` React route + sidebar nav | Verified anchor sites: `App.tsx:27–36`, `sidebar.tsx:19–27`. Pattern: mirror `IdentityPage` import + `<Route>` registration. |
| DASH-02 | Motion tab Email surface — per-port table + STARTTLS badge | UI-SPEC §"Email Table columns" + D-04. Source data already on `CryptoEndpoint` (host, port, protocol, tls_version, cipher_suite, cert_not_after). Email protocol set: `{SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S}`. STARTTLS trigger: `port == 25 AND protocol == "SMTP-STARTTLS"` (matches `risk_engine.py:468`). |
| DASH-03 | Motion tab Broker surface — grouped by family + plaintext flag | Family detection deterministic from `protocol` prefix (D-03). Plaintext set: `{KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN}` (verified `evidence.py:226`). TLS set: `{KAFKA-TLS, AMQPS, AMQPS/Azure-ServiceBus, HTTPS/AWS-SQS, REDIS-TLS}` (verified `evidence.py:230`). |
| DASH-04 | Executive summary 6th `data_in_motion` gauge | Anchor site verified `executive.tsx:128–151`. `score.subscores.data_in_motion` already returned by `scoring.py:237`. **Currently silently dropped** by Pydantic SubScores in `schemas.py:20–25` and TS `SubScores` in `types/api.ts:1–7` — both need extending. |
| DASH-05 | `/api/scan/latest` response gains `motion_findings: list[MotionFinding]` | Anchor site verified `scan.py:633–647` (response build), `schemas.py:123–131` (model). Mirror identity_findings wiring at `scan.py:540, 646`. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Motion finding derivation (CryptoEndpoint → MotionFinding) | API / Backend | — | Findings are derived at request time from DB rows in `scan.py:_derive_*` (existing pattern); deriving in browser would re-implement domain rules. |
| Motion finding shape (Pydantic + TS) | API / Backend (Pydantic) | Frontend (TS mirror) | Pydantic is the source of truth (`schemas.py`); TS in `types/api.ts` mirrors. |
| Family grouping (Kafka/AMQP/Redis) | Frontend Server / Browser (TS) | — | Pure presentation grouping; protocol label is the input, ordering & section headers are UI concerns. |
| Severity / warning badges | Browser (Tailwind utility classes) | — | Inline HSL convention from `identity.tsx:23–29`. No backend involvement. |
| Score gauge rendering | Browser | API (delivers the scalar) | `ScoreGauge` is a presentation component; the score scalar comes from `scoring.py`. |
| Empty-state copy + detection | Browser | — | Pure UI; derived by filtering `motion_findings` client-side. |

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python changes (Pydantic model + scan.py derivation).
- **Minimal diffs** — no refactors of `_derive_findings` or `_derive_identity_findings`; add `_derive_motion_findings` next to them.
- After changes: `python -m compileall` + relevant tests (the existing `tests/test_dashboard_api.py` extension and any new motion-derivation test).
- **Mandatory phase close-out** (CLAUDE.md §"Mandatory Phase Completion Steps") MUST appear as explicit tasks in PLAN.md, not as afterthoughts:
  1. Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md` (write to vault filesystem directly; file too large for `obsidian CLI content=`).
  2. Update `docs/UAT-SERIES.md` with the 5 new UAT cases (D-11).
  3. Sync UAT-SERIES.md to vault using the documented `printf + cp` pattern.
  4. Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs commit`.
- **Vault targeting:** all Obsidian operations pass `vault="Digs"`, paths under `20_Dev-Work/QUIRK/`, use `silent` flag.
- Frontmatter standard: `project: QU.I.R.K.`, `type: phase`, `status: complete|active|draft`, `source` (repo path), `updated: YYYY-MM-DD`.

## Standard Stack

### Core (already installed — NO new dependencies in Phase 36)

| Library | Version (verified `package.json`) | Purpose | Why Standard |
|---------|------------------------|---------|--------------|
| react | ^19.2.4 | UI runtime | Existing project standard |
| react-router-dom | ^7.4.0 | Routing | Already wired in `App.tsx` |
| @tanstack/react-table | ^8.21.3 | Table sort/filter | Used by `identity.tsx`, `findings.tsx`, etc. |
| lucide-react | ^0.474.0 | Icons | Sidebar nav icons; UI-SPEC selects `Activity` |
| @radix-ui/react-tooltip | ^1.2.8 | Tooltip primitives | Used by sidebar collapsed state |
| tailwindcss | ^3.4.19 | Styling — JIT picks up `bg-[hsl(...)]` arbitrary classes | Verified working in `identity.tsx:23–29` |
| fastapi | >=0.128.8 (`pyproject.toml:35`) | API framework | Existing |
| pydantic | (transitive via FastAPI) | Response models | Existing pattern in `schemas.py` |

### Supporting (already used by `identity.tsx`)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `@/components/ui/{card,badge,table,skeleton,sheet}` | shadcn primitives | All Phase 36 UI |
| `@/components/gauges/ScoreGauge` | The gauge component | 6th gauge in executive.tsx |
| `@/hooks/useScanData` | fetch+cache for `/api/scan/latest` | Reuse on motion page (no new hook — `motion_findings` rides on the same response) |
| `@/context/ScanContext` (`useSelectedScan`) | scan_id propagation | Already consumed transitively via `useScanData` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Filtering motion_findings in the browser | Adding `email_findings` and `broker_findings` server-side | Browser filter chosen by D-02 (single response field). Backend split would add API surface area for no benefit since the derivation logic is trivial. |
| Vitest + RTL component tests | No frontend tests in this phase | CONTEXT.md D-07 requires existing convention; none exists. Backend pytest + manual UAT covers DASH-01..05. Introducing Vitest is a v4.5 polish item. |

**Installation:** `# none — all dependencies already in src/dashboard/package.json and pyproject.toml`

**Version verification:** Versions read directly from `src/dashboard/package.json` (read in this session) and `pyproject.toml:35`. No registry queries required because no new packages are added.

`[VERIFIED: src/dashboard/package.json]` `[VERIFIED: pyproject.toml]`

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────┐
│ run_scan.py     │  (already produces CryptoEndpoint rows for email + broker —
│ scanner phase   │   Phase 32/33 complete)
└──────┬──────────┘
       │  writes
       ▼
┌─────────────────┐
│ SQLite          │  CryptoEndpoint(host, port, protocol, tls_version,
│ data/quirk.db   │   cipher_suite, cert_not_after, service_detail, ...)
└──────┬──────────┘
       │
       │  GET /api/scan/latest
       ▼
┌──────────────────────────────────────────────────────────┐
│ quirk/dashboard/api/routes/scan.py                        │
│   _derive_findings(endpoints)            (existing)       │
│   _derive_identity_findings(endpoints)   (existing)       │
│   _derive_motion_findings(endpoints)     ── NEW Phase 36  │
│   compute_readiness_score(evidence)      (existing — already returns data_in_motion) │
│                                                           │
│   ScanLatestResponse {                                    │
│     ...                                                   │
│     identity_findings: [...]                              │
│     motion_findings:   [...]   ── NEW                     │
│     score.subscores.data_in_motion ── NEW (wire-up)       │
│   }                                                       │
└──────┬───────────────────────────────────────────────────┘
       │
       │  JSON
       ▼
┌──────────────────────────────────────────────────────────┐
│ src/dashboard/src/                                        │
│   hooks/useScanData       (existing — fetches once)       │
│   pages/motion.tsx        ── NEW: filters motion_findings │
│     ├── EmailTable        (isEmailProtocol filter)        │
│     └── BrokerSections    (Kafka / AMQP / Redis grouping) │
│   pages/executive.tsx     (modified: +1 ScoreGauge)       │
│   components/sidebar.tsx  (modified: +Motion nav)         │
│   App.tsx                 (modified: +Route /motion)      │
└──────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| File | Responsibility | Change |
|------|---------------|--------|
| `quirk/dashboard/api/schemas.py` | Pydantic response contract | Add `MotionFinding`; add `data_in_motion: int = 0` to `SubScores`; add `motion_findings: List[MotionFinding] = []` to `ScanLatestResponse` |
| `quirk/dashboard/api/routes/scan.py` | Endpoint → response derivation | Add `_derive_motion_findings()`; populate `subscores.data_in_motion` (currently dropped at lines 595–601); pass `motion_findings=...` in response build (line 633–647) |
| `tests/test_dashboard_api.py` | Backend contract test | Add motion_findings + data_in_motion assertions (D-08) |
| `src/dashboard/src/types/api.ts` | TS type mirror | Extend `SubScores`; add `MotionFinding`; add `motion_findings` to `ScanLatestResponse` |
| `src/dashboard/src/pages/motion.tsx` | New page | Create — mirror identity.tsx structure |
| `src/dashboard/src/pages/executive.tsx` | Score gauges row | Add 6th gauge after line 150 |
| `src/dashboard/src/components/sidebar.tsx` | Nav | Insert `{ path: "/motion", label: "Motion", Icon: Activity }` between Identity and Certificates |
| `src/dashboard/src/App.tsx` | Routes | Add `<Route path="/motion" element={<MotionPage />} />` |
| `docs/UAT-SERIES.md` | UAT documentation | Add 5 UAT cases (D-11) |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md` | Vault phase note | Create (D-10) |

### Recommended Project Structure

No new directories — all changes are additions inside existing trees. New files:
```
quirk/dashboard/api/{schemas.py, routes/scan.py}        # extended in place
src/dashboard/src/pages/motion.tsx                      # NEW
tests/test_dashboard_api.py                             # extended in place
```

### Pattern 1: identity.tsx → motion.tsx mirror

**What:** Copy the structural skeleton of `IdentityPage` and substitute the data type + columns.
**When to use:** Any new findings-table page in this dashboard.
**Example (verified at `src/dashboard/src/pages/identity.tsx:23–29, 58–101`):**

```tsx
// Source: src/dashboard/src/pages/identity.tsx (verbatim — copy these constants)
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}

// Loading + error pattern (lines 99–100):
if (loading) return <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) =>
  <Skeleton key={i} className="h-10 w-full" />)}</div>
if (error) return <p className="text-muted-foreground text-sm">{error}</p>
```

### Pattern 2: Pydantic findings derivation

**What:** Read CryptoEndpoint rows; emit a typed list of finding records with rule-driven severity and remediation strings.
**When to use:** Whenever a `*_findings` field is added to `ScanLatestResponse`.
**Example (verified at `quirk/dashboard/api/routes/scan.py:184–330`):**

```python
# Source: quirk/dashboard/api/routes/scan.py — _derive_identity_findings() pattern
def _derive_motion_findings(endpoints: list[CryptoEndpoint]) -> list[MotionFinding]:
    EMAIL_PROTOS = {"SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS",
                    "POP3-STARTTLS", "POP3S"}
    BROKER_PLAIN = {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}
    BROKER_TLS = {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus",
                  "HTTPS/AWS-SQS", "REDIS-TLS"}

    results: list[MotionFinding] = []
    for ep in endpoints:
        proto = ep.protocol or ""
        if proto not in EMAIL_PROTOS | BROKER_PLAIN | BROKER_TLS:
            continue
        plaintext = proto in BROKER_PLAIN
        starttls_warning = (ep.port == 25 and proto == "SMTP-STARTTLS")
        results.append(MotionFinding(
            host=ep.host, port=ep.port,
            severity=...,        # derive from rules below
            title=...,           # human label
            protocol=proto,      # verbatim — preserve "AMQPS/Azure-ServiceBus"
            tls_version=ep.tls_version or None,
            cipher_suite=ep.cipher_suite or None,
            cert_not_after=ep.cert_not_after.isoformat() if ep.cert_not_after else None,
            quantum_risk=...,
            plaintext_exposed=plaintext,
            starttls_warning=starttls_warning,
            source="motion",
        ))
    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return results
```

Severity rules (derived from `risk_engine.py` and `evidence.py` to stay consistent):
- `proto in BROKER_PLAIN` → HIGH (mirrors `risk_engine.py:539–559` which emits HIGH for kafka/amqp/redis-plaintext-listener).
- `port == 25 AND proto == "SMTP-STARTTLS"` → at least MEDIUM (the STARTTLS-downgrade-risk EMAIL-08 finding).
- `proto in BROKER_TLS AND tls_version in {TLSv1, TLSv1.1}` → HIGH.
- Healthy TLS row → LOW or INFO (presence-only).

### Anti-Patterns to Avoid

- **Adding new variants to `components/ui/badge.tsx`** — D-04 explicitly forbids this. Use inline `className="bg-[hsl(...)]"` exactly as identity.tsx does.
- **Inventing a parallel `useMotionData` hook** — `motion_findings` rides on the existing `ScanLatestResponse`; reuse `useScanData()`.
- **Normalizing `AMQPS/Azure-ServiceBus`** — Phase 35 D-03 preserves the slash; the UI splits on `/` for display only (cloud chip).
- **Sorting/grouping in the API layer** — keep ordering logic in `motion.tsx`. Backend returns a flat list.
- **Browser-side severity overrides** — severity comes from the Pydantic record; the UI only maps it to a Tailwind class.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Findings-table sort/filter | Custom array filter + state | `@tanstack/react-table` (already used by `identity.tsx`) | Sort indicator, pagination, accessibility already wired |
| Loading skeleton | Custom shimmer divs | `@/components/ui/skeleton` | Matches identity.tsx visual rhythm |
| Severity HSL palette | New CSS classes | Inline `bg-[hsl(...)]` from identity.tsx | Single badge vocabulary across dashboard (D-04) |
| Fetch + scan_id propagation | New `useEffect` block | `useScanData()` hook | Already handles loading/error/cancellation/scan_id query string |
| Family detection regex | Complex regex of cloud labels | Simple `startsWith` checks per UI-SPEC §"Family Detection Logic" | Covers `KAFKA-*`, `AMQP-*`, `AMQPS*`, `REDIS-*`; unknown → skip |
| Empty-state component | New `<NoData>` component | Inline muted Card matching D-05 copy | One-time use; CONTEXT.md provides exact copy |

**Key insight:** Every primitive Phase 36 needs is already installed and used by an analog page (`identity.tsx`). The phase is structurally a **substitution exercise**, not a build-from-scratch.

## Common Pitfalls

### Pitfall 1: Pydantic `SubScores` silently drops `data_in_motion`

**What goes wrong:** `quirk/intelligence/scoring.py:237` returns `subscores={"data_in_motion": motion_score, ...}`, but `quirk/dashboard/api/routes/scan.py:595–601` constructs `SubScores(...)` with only 5 named kwargs. Today the field is silently dropped before the response leaves the API. Adding the TS field without also extending the Pydantic constructor will leave the gauge reading `undefined` → React renders `0`.
**Why it happens:** Pydantic doesn't surface "you forgot a field"; the constructor is positional/keyword and the manual mapping in scan.py omits motion.
**How to avoid:** PLAN.md must include both edits in the same task: `schemas.py` `SubScores` extension AND `scan.py:595–601` `SubScores(...)` constructor extension to read `subscores_raw.get("data_in_motion", 0)`.
**Warning signs:** Gauge displays `0` even when scoring.py prints a non-zero `motion_score`.

### Pitfall 2: TS interface drift from Pydantic schema

**What goes wrong:** TS interface says `motion_findings: MotionFinding[]` (non-optional) while Pydantic emits an empty list when no motion endpoints exist. If TS is wrong, runtime `data.motion_findings.filter(...)` throws.
**Why it happens:** Pydantic default `[]` and TS non-optional field are compatible; Pydantic missing field and TS non-optional are NOT.
**How to avoid:** Both layers default to `[]`. Schema test in `tests/test_dashboard_api.py` asserts `"motion_findings" in data` and `isinstance(data["motion_findings"], list)` (D-08).
**Warning signs:** A scan with no email/broker scanners enabled crashes the page, not the empty-state card.

### Pitfall 3: Tailwind JIT and `bg-[hsl(38_92%_50%)]` arbitrary value purging

**What goes wrong:** Some Tailwind setups don't pick up arbitrary HSL classes that aren't in source files at build time.
**Why it happens:** JIT scans `content` globs (`tailwind.config.ts:5–8`).
**How to avoid:** Verified — `tailwind.config.ts:5–8` includes `./src/**/*.{ts,tsx,js,jsx}`, and `identity.tsx` has been using `bg-[hsl(...)]` successfully in production. Use **the same string values** as identity.tsx — copy/paste the constants, do not template them.
**Warning signs:** Badge background renders white in production but works in dev.

### Pitfall 4: react-router-dom v7 layout

**What goes wrong:** v7 changed import paths and outlet behavior in some situations.
**Why it happens:** v7 is a major version.
**How to avoid:** Verified — `App.tsx:1` imports `{ BrowserRouter, Routes, Route } from "react-router-dom"` and `<Routes>` renders sibling `<Route>` elements without an `<Outlet />`. Use the same flat pattern. v7 Outlet quirks do not apply because there is no nested layout route.
**Warning signs:** `/motion` resolves but renders blank; usually a typo in `path` or a missing import.

### Pitfall 5: Cipher_suite / cert_not_after attribute existence on CryptoEndpoint

**What goes wrong:** `MotionFinding.cipher_suite` reads `ep.cipher_suite`. Older endpoint rows from non-email/non-broker scans may not have this populated.
**Why it happens:** `cipher_suite` is set by the email/broker scanners; legacy endpoints set only `tls_version`.
**How to avoid:** All accessors use `getattr(ep, "cipher_suite", None) or None` (matches existing `getattr` style at `risk_engine.py:213, 462, 537`).
**Warning signs:** `AttributeError` on the API call when a mixed scan is queried.

### Pitfall 6: `useScanData` cache and the new field

**What goes wrong:** None — `useScanData` (`hooks/useScanData.ts:11–58`) refetches on `selectedScanId` change and stores the entire response in component state. There is no normalized cache that would need invalidation.
**Why it happens (theoretical):** Worth noting that switching scans via `ScanSelector` triggers a full refetch — `motion_findings` updates atomically with the rest.
**How to avoid:** Nothing to do.

## Runtime State Inventory

> Phase 36 is presentation-only. No rename/refactor/migration. **Section omitted (does not apply).**

## Code Examples

### Example 1: Pydantic `MotionFinding` model (mirror IdentityFinding)

```python
# Source: extend quirk/dashboard/api/schemas.py — pattern from IdentityFinding (lines 80–90)
class MotionFinding(BaseModel):
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None
    tls_version: Optional[str] = None
    cipher_suite: Optional[str] = None
    cert_not_after: Optional[str] = None    # ISO date string, not datetime — UI displays directly
    plaintext_exposed: bool = False         # NON-OPTIONAL per D-02
    starttls_warning: bool = False          # NON-OPTIONAL per D-02
```

### Example 2: SubScores Pydantic + TS extension

```python
# quirk/dashboard/api/schemas.py:20–25 — extend
class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int
    data_at_rest: int = 0
    data_in_motion: int = 0   # NEW — Phase 36 D-06
```

```typescript
// src/dashboard/src/types/api.ts:1–7 — extend
export interface SubScores {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number     // NEW — Phase 36 D-06
}
```

### Example 3: Wiring data_in_motion into the response

```python
# quirk/dashboard/api/routes/scan.py:595–601 — extend the manual constructor
score = ScoreData(
    score=score_raw.get("score", 0),
    rating=score_raw.get("rating", "POOR"),
    subscores=SubScores(
        hygiene=subscores_raw.get("hygiene", 0),
        modern_tls=subscores_raw.get("modern_tls", 0),
        identity_trust=subscores_raw.get("identity_trust", 0),
        agility_signals=subscores_raw.get("agility_signals", 0),
        data_at_rest=subscores_raw.get("data_at_rest", 0),
        data_in_motion=subscores_raw.get("data_in_motion", 0),   # NEW
    ),
    drivers=score_raw.get("drivers", []),
)
```

### Example 4: Sidebar nav entry

```tsx
// src/dashboard/src/components/sidebar.tsx:11–13 — add Activity to imports
import { LayoutDashboard, AlertTriangle, Shield, Database, GitBranch,
         Fingerprint, TrendingUp, Activity } from "lucide-react"

// src/dashboard/src/components/sidebar.tsx:19–27 — insert between Identity and Certificates
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/motion", label: "Motion", Icon: Activity },          // NEW
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },
]
```

### Example 5: 6th ScoreGauge

```tsx
// src/dashboard/src/pages/executive.tsx:146–151 — add the 6th line
<ScoreGauge score={score.subscores.hygiene} label="Hygiene" size={120} />
<ScoreGauge score={score.subscores.modern_tls} label="Modern TLS" size={120} />
<ScoreGauge score={score.subscores.identity_trust} label="Identity" size={120} />
<ScoreGauge score={score.subscores.agility_signals} label="Agility" size={120} />
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} /> {/* NEW */}
```

Also update the loading skeleton block at `executive.tsx:60–67` from `length: 5` → `length: 6`.

### Example 6: Family detection (mirror UI-SPEC §"Family Detection Logic")

```ts
// In src/dashboard/src/pages/motion.tsx
function getBrokerFamily(protocol: string): "Kafka" | "AMQP" | "Redis" | null {
  if (protocol.startsWith("KAFKA-")) return "Kafka"
  if (protocol.startsWith("AMQP-") || protocol.startsWith("AMQPS")) return "AMQP"
  if (protocol.startsWith("REDIS-")) return "Redis"
  return null
}

const EMAIL_PROTOS = new Set([
  "SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS", "POP3-STARTTLS", "POP3S",
])
function isEmailProtocol(protocol?: string): boolean {
  return EMAIL_PROTOS.has(protocol ?? "")
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Findings stored in a table, queried directly | Findings derived from CryptoEndpoint at request time (`_derive_*` functions) | Phase 4–5 (initial dashboard) | Phase 36 mirrors this — no Findings table changes |
| Identity rendered inside the main Findings page | Dedicated `/identity` page with per-protocol summary cards | Phase 25 | Phase 36 follows the same dedicated-page pattern |
| 5 subscores | 6 subscores (added `data_at_rest` then `data_in_motion`) | v4.3 + v4.4 | UI must accommodate 6 gauges in flex-wrap row (already does — verified `executive.tsx:128`) |

**Deprecated/outdated:** none — all referenced patterns are current as of HEAD of `QUIRK-v4`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Severity rules for `_derive_motion_findings` (HIGH for plaintext, MEDIUM for STARTTLS port-25, etc.) mirror `risk_engine.py` decisions and produce the same ordering as the existing finding emission paths. | Architecture Patterns → Pattern 2 | If wrong: planner picks different severity; UAT visual matches but main `findings` list and `motion_findings` could disagree on the same endpoint. **Recommend planner reviews `risk_engine.py:483–567` and confirms before locking the rules.** `[ASSUMED]` |
| A2 | The dashboard does **not** yet use Vitest/Jest (verified via `package.json` scripts and absence of any test files outside `node_modules`). | Standard Stack → Alternatives | If a test framework was added since the last commit reviewed (HEAD `6ca624d`), the planner should pick that framework instead of "no frontend tests." `[VERIFIED: src/dashboard/package.json]` |
| A3 | `cipher_suite` and `cert_not_after` are present on CryptoEndpoint rows produced by Phase 32–33 scanners. | Common Pitfalls → Pitfall 5 | If absent, MotionFinding will surface `null` cells (acceptable per UI-SPEC table spec). Mitigation already coded into the example. `[CITED: risk_engine.py:213, 462, 537 — same getattr pattern used elsewhere]` |
| A4 | Motion endpoints are tagged with `service_detail` like `"SMTP-STARTTLS:587"` (EMAIL-10), but the UI does NOT need this — it parses `protocol` directly. | Phase Requirements (DASH-02) | Low — even if service_detail format changes, motion.tsx never reads it. `[VERIFIED: src/dashboard/src/pages/motion.tsx will parse protocol field, per CONTEXT.md D-02]` |

## Open Questions (RESOLVED)

1. **Should `motion_findings` include healthy TLS rows, or only "interesting" rows?**
   - **RESOLVED:** Emit one MotionFinding per email/broker endpoint regardless of severity (LOW/INFO for healthy rows). Plan 01 Task 3 (`_derive_motion_findings`) implements this — page reads "this is what was scanned," not just problems. Locked.

2. **Where does `MotionFinding.cipher_suite` come from?**
   - **RESOLVED:** Use `getattr(ep, "cipher_suite", None)` defensively per Pitfall 5 — if the column is absent the field surfaces as `None` and the table renders an empty cell, which the UI-SPEC permits. Plan 01 Task 3 wires this. No Wave 0 column-introspection required.

3. **Sidebar position when sidebar is collapsed (icon-only, <1024px)?**
   - **RESOLVED:** Use `Activity` icon per UI-SPEC (Plan 02 Task 3). Revisit only if manual UAT flags icon collision with `TrendingUp` (Trends).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node toolchain (`vite`, `tsc`) | `npm run build`/`dev` for the dashboard | Assumed available (project standard) | per package.json devDependencies | — |
| Python 3.11+ | Backend FastAPI + tests | Project requirement | 3.11+ | — |
| pytest | `tests/test_dashboard_api.py` extension | In project (existing tests run) | — | — |
| Docker Compose | Manual UAT (chaos labs) | User provides — required for D-09 manual UAT only | — | Empty-state UAT can run without Docker |
| Obsidian CLI (`obsidian` skill) | Vault sync (D-10, D-12) | Skill present per CLAUDE.md instructions | — | Direct filesystem write to `/Users/digs/vaults/Digs/...` (CLAUDE.md mandates this for large files) |
| `gsd-tools.cjs commit` | Commit UAT-SERIES.md update (D-12) | Per CLAUDE.md | — | Plain `git commit` |

**Missing dependencies with no fallback:** none for execution (Docker for UAT only; UAT-1 cases without Docker still verify the static rendering path).
**Missing dependencies with fallback:** none — all primary tooling is in place.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python). **No frontend test framework** — defer to v4.5 polish per CONTEXT.md D-07. |
| Config file | `pyproject.toml` (pytest section) + `tests/conftest.py` |
| Quick run command | `pytest tests/test_dashboard_api.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-05 | `/api/scan/latest` returns `motion_findings` as a list | unit (FastAPI TestClient) | `pytest tests/test_dashboard_api.py::test_motion_findings_endpoint -x` | ❌ Wave 0 |
| DASH-04 | `/api/scan/latest` returns `subscores.data_in_motion` as int | unit | `pytest tests/test_dashboard_api.py::test_data_in_motion_subscore -x` | ❌ Wave 0 |
| DASH-05 | `_derive_motion_findings` emits HIGH for `KAFKA-PLAIN` endpoint | unit (no client — direct call) | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_plaintext -x` | ❌ Wave 0 |
| DASH-05 | `_derive_motion_findings` sets `starttls_warning=true` only for port-25 SMTP-STARTTLS | unit | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_starttls -x` | ❌ Wave 0 |
| DASH-05 | `_derive_motion_findings` preserves `AMQPS/Azure-ServiceBus` slash | unit | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_azure -x` | ❌ Wave 0 |
| DASH-01 | `/motion` route renders without crashing in production build | manual / UAT | `npm run build && open http://localhost:8000/motion` after `quirk serve` | manual-only (no RTL framework) |
| DASH-02 | Email per-port table renders with STARTTLS badge on port 25 | manual UAT against `labs/email/` | docs/UAT-SERIES.md UAT-36-02 (NEW) | ❌ Wave 0 |
| DASH-03 | Broker grouped sections render with plaintext badge | manual UAT against `labs/broker/` | docs/UAT-SERIES.md UAT-36-03 (NEW) | ❌ Wave 0 |
| DASH-04 | Executive summary shows 6 ScoreGauges | manual UAT | docs/UAT-SERIES.md UAT-36-04 (NEW) | ❌ Wave 0 |
| Empty-state | Both empty-state cards render when no email/broker findings | manual UAT | docs/UAT-SERIES.md UAT-36-05 (NEW) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_dashboard_api.py -x` (≤10s)
- **Per wave merge:** `pytest tests/ -x` (full suite, including `tests/test_intelligence_*` to confirm Phase 34 wiring still green)
- **Phase gate:** Full suite green + `tsc -b` green + manual UAT-36-01..05 sign-off in `docs/UAT-SERIES.md` before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_dashboard_api.py` — extend with 5 new test cases (above). Reuse existing `dashboard_client` fixture from `tests/conftest.py:75`.
- [ ] `tests/conftest.py` — add a fixture/helper that seeds CryptoEndpoint rows for motion protocols if the dashboard_client tests need real DB rows (existing email/broker scanner tests do this in-process; consider extracting a `seed_motion_endpoints(db)` helper).
- [ ] `docs/UAT-SERIES.md` — add UAT-36-01..05 cases (D-11). New series block, dated 2026-04-29 or later.
- [ ] No Vitest install — explicitly out of scope per D-07 + verified absence.

## Sources

### Primary (HIGH confidence — verified by direct file read in this session)

- `src/dashboard/src/pages/identity.tsx` — full file, lines 1–240. Source of severity HSL constants, table+sheet pattern, loading/error pattern, TanStack Table wiring.
- `src/dashboard/src/pages/executive.tsx` — full file, lines 1–185. Score gauges row at lines 128–151; loading skeleton at 60–67.
- `src/dashboard/src/components/sidebar.tsx` — full file. NAV_ITEMS at lines 19–27; lucide-react imports at 5–13.
- `src/dashboard/src/App.tsx` — full file. Routes block at 27–36.
- `src/dashboard/src/types/api.ts` — full file. SubScores at 1–7; IdentityFinding at 80–91; ScanLatestResponse at 99–108.
- `src/dashboard/src/hooks/useScanData.ts` — full file. Confirmed cache-by-scanId behavior; no invalidation needed.
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — confirmed prop shape `{score, label, size?, strokeColor?, isOverall?}`.
- `src/dashboard/package.json` — full deps + devDeps. **No Vitest/Jest installed.** Confirmed React 19.2.4, react-router-dom 7.4.0, @tanstack/react-table 8.21.3, tailwindcss 3.4.19, lucide-react 0.474.0.
- `src/dashboard/tailwind.config.ts` — JIT content globs cover `src/**/*.{ts,tsx,js,jsx}` → arbitrary `bg-[hsl(...)]` classes work.
- `quirk/dashboard/api/schemas.py` — Pydantic SubScores at 20–25, IdentityFinding at 80–90, ScanLatestResponse at 123–131.
- `quirk/dashboard/api/routes/scan.py` — `_derive_findings` at 42–181, `_derive_identity_findings` at 184–330, response build at 633–647, **SubScores constructor at 595–601** (drops data_in_motion today).
- `quirk/intelligence/scoring.py:200–240` — `data_in_motion` is the 6th subscore key, already returned.
- `quirk/intelligence/evidence.py:91–356` — motion counters and protocol set membership.
- `quirk/engine/risk_engine.py:462–567` — severity rules for email STARTTLS-downgrade and broker plaintext findings.
- `quirk/scanner/email_scanner.py:383–500` — protocol_label assignment confirms verbatim labels reach `ep.protocol`.
- `tests/conftest.py:75–112` — `dashboard_client` fixture pattern (FastAPI TestClient + in-memory SQLite).
- `tests/test_dashboard_api.py` — existing pattern for asserting against `/api/scan/latest`.
- `pyproject.toml:35` — `fastapi>=0.128.8`.
- `.planning/phases/36-dashboard-motion-tab/36-CONTEXT.md` — locked decisions D-01..D-12.
- `.planning/phases/36-dashboard-motion-tab/36-UI-SPEC.md` — visual contract.
- `.planning/REQUIREMENTS.md` — DASH-01..DASH-05 lines 124–128.
- `CLAUDE.md` — mandatory phase close-out.

### Secondary (MEDIUM confidence)

- React Router v7 `<Routes>`/`<Route>` flat-rendering pattern — verified by inspection of `App.tsx` already shipping in production.
- Tailwind JIT arbitrary-value support — verified by `identity.tsx` shipping `bg-[hsl(...)]` classes.

### Tertiary (LOW confidence)

- None — all critical claims verified against codebase HEAD.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — `package.json` and `pyproject.toml` read directly.
- Architecture: HIGH — anchor sites (file:line) verified for every modification target.
- Pitfalls: HIGH — Pitfall 1 (data_in_motion drop) discovered by reading `scan.py:595–601`, not assumed.
- Validation: MEDIUM — frontend manual-UAT path is intentional (no RTL framework); rests on CONTEXT.md D-07.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable codebase, locked decisions; revisit if Phase 36 isn't started within 30 days or if Phase 37 changes the API surface)

## RESEARCH COMPLETE
