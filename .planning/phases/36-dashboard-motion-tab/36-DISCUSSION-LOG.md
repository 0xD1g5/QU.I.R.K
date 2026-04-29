# Phase 36: Dashboard Motion Tab — Discussion Log

**Logged:** 2026-04-28
**Mode:** discuss (default)
**Areas selected:** Page composition · MotionFinding schema · Broker row grouping · Status / warning badges · Empty state

This document captures the user-facing Q&A that produced `36-CONTEXT.md`. It is for human reference (audits, retrospectives) and is **not consumed** by downstream agents.

---

## Area 1: Page composition

**Question:** How should the `/motion` page be composed?
**Options presented:**
- Single page, stacked sections (Recommended)
- Single page with sub-tabs
- Two sidebar entries

**User selected:** Single page, stacked sections.

**Decision recorded as:** D-01 — Single `/motion` page with Email section on top, Broker below. Mirrors `pages/identity.tsx` pattern. Easiest to print for client deliverables. Sidebar icon left to Claude's discretion (lucide-react candidates: Activity, Radio, Send, Waves).

---

## Area 2: MotionFinding API schema

**Question:** What shape should `MotionFinding` take in the API contract?
**Options presented:**
- Motion-extended schema (Recommended) — base IdentityFinding fields + tls_version, cipher_suite, cert_not_after, plaintext_exposed, starttls_warning
- Strict mirror of IdentityFinding — UI parses description for evidence
- Two arrays (motion_findings + motion_endpoints) — strict-mirror plus a parallel endpoints array

**User selected:** Motion-extended schema.

**Decision recorded as:** D-02 — `MotionFinding` carries TLS evidence inline so the UI never parses description strings. `plaintext_exposed` and `starttls_warning` are non-optional booleans. `protocol` label is preserved verbatim, including the `AMQPS/Azure-ServiceBus` slash form (Phase 35 D-03 carry-forward).

---

## Area 3: Broker row grouping

**Question:** How should broker rows be grouped?
**Options presented:**
- Grouped sections per broker family (Recommended) — Kafka / AMQP (RabbitMQ+Azure) / Redis
- Flat sortable table with `type` column
- Pills + flat table (hybrid) — per-type pill strip on top, flat table below

**User selected:** Grouped sections per broker family.

**Decision recorded as:** D-03 — Three subsections in fixed order (Kafka, AMQP, Redis). Family detected from `protocol` prefix. Cloud variants (e.g., Azure Service Bus) shown as a `☁ Azure` chip on the row inside the AMQP section, derived by splitting protocol on `/`.

---

## Area 4: Status / warning badges

**Question:** How should the STARTTLS-warning and plaintext-exposed badges look?
**Options presented:**
- Reuse identity.tsx severity colors + glyphs (Recommended) — amber MEDIUM for STARTTLS, red HIGH for plaintext
- New motion-specific badge variants (striped/skull pattern in `badge.tsx`)
- Glyph-only (no color difference)

**User selected:** Reuse identity.tsx severity colors + glyphs.

**Decision recorded as:** D-04 — STARTTLS badge uses `bg-[hsl(38_92%_50%)] text-black` + `⚠ STARTTLS`; plaintext badge uses `bg-[hsl(24_95%_53%)] text-white` + `☠ PLAINTEXT`. No new variants in `components/ui/badge.tsx`. Healthy TLS rows show neutral text only.

---

## Area 5: Empty state (small wrap-up question)

**Question:** When a scan has no email or no broker endpoints, what should the Motion page show?
**Options presented:**
- Show section with empty-state message (Recommended)
- Hide empty sections entirely
- Show section with disabled-look skeleton

**User selected:** Show section with empty-state message.

**Decision recorded as:** D-05 — Both sections always render. Empty section shows a muted card teaching the user how to enable the relevant scanner. Layout is predictable across scans.

---

## Items at Claude's Discretion (deferred to planner)

- Sidebar icon choice from lucide-react.
- Whether broker subsections are accordion-collapsible or always-expanded (default: always-expanded).
- Whether to include the row → Sheet detail drawer (only if cheap and reuses existing components).
- Whether to add a top-of-page Motion KPI strip.
- RTL test file naming (`pages/__tests__/motion.test.tsx` likely).

## Deferred Ideas (preserved for future phases)

- DEF-36-A: Print page motion section (Phase 37 polish).
- DEF-36-B: Per-row Sheet detail drawer.
- DEF-36-C: Subscore key rename to roadmap-text names (v4.5+).
- DEF-36-D: Flat broker table at scale (revisit if real scans show 10+ endpoints/family).
- DEF-36-E: Top-of-page Motion KPI strip.
