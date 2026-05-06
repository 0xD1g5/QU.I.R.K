# Phase 39: Data at Rest Dashboard Tab - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 39-data-at-rest-dashboard-tab
**Areas discussed:** API data shape, Per-finding columns, Section organization, Sidebar placement & subscore

---

## API Data Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Typed `dar_findings` array | New `DarFinding` model on `ScanLatestResponse`. Mirrors Phase 36 motion_findings precedent. Enables DAR-specific columns. Cost: schema + projection + frontend type. | ✓ |
| Filter existing `findings[]` client-side | Zero schema change. Dashboard filters by protocol set. Fastest path. Loses DAR-specific columns. | |
| Hybrid: filter now, type later | Ship Phase 39 with client-side filter; add typed array in Phase 42 or 43. Trade revisit cost for faster ship. | |

**User's choice:** Typed `dar_findings` array.
**Notes:** Recommended option taken. Locks consistency with Phase 36 and unlocks consultant-grade columns (encryption mode, KMS key id, public access, etc.) without parsing description text.

---

## Per-Finding Columns

| Option | Description | Selected |
|--------|-------------|----------|
| Per-category column sets | Each section has its own table with category-tuned columns. Mirrors motion.tsx EmailTable vs BrokerGroupedSections split. Highest consultant value. | ✓ |
| Unified table with optional columns | One table component, columns conditionally rendered. Less duplication; rows feel sparse and mixed-meaning. | |
| Generic columns only | Same as Findings tab. Simplest. Defers DAR-specific columns to a later phase. | |

**User's choice:** Per-category column sets.
**Notes:** Recommended option taken. Each of DB / Object Storage / Kubernetes / Vault gets its own column set tuned to the questions consultants actually ask of that category.

---

## Section Organization

Three sub-questions on whether each category subdivides further:

### Object Storage sub-grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Combined table with Provider column | One table, Provider column shows S3 / Azure Blob. Easier cross-provider posture scan. | ✓ |
| Sub-cards per provider (Kafka/AMQP precedent) | Separate sub-cards for S3 and Azure Blob. More vertical space. | |

### Kubernetes sub-grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Flat severity-sorted table | One table with Namespace column, severity-first ordering. | ✓ |
| Grouped by namespace | Collapsible sub-card per namespace. Hides severity at a glance. | |

### Database sub-grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Combined table with Engine column | One table, Engine column shows POSTGRESQL / MYSQL / RDS. | ✓ |
| Sub-cards per engine | Separate sub-cards. Symmetric with broker pattern but heavier. | |

**User's choice:** Combined-table-with-discriminator-column for all three.
**Notes:** Deliberate divergence from motion.tsx's BrokerGroupedSections. Brokers represent conceptually different services (Kafka ≠ AMQP ≠ Redis); DB engines and object-storage providers are doing the same thing with different vendors, so a discriminator column reads cleaner.

---

## Sidebar Placement & Subscore

### Nav slot

| Option | Description | Selected |
|--------|-------------|----------|
| After Motion | Pairs in-motion / at-rest visually. | ✓ |
| After Identity | Groups data-protection topics. Pushes Motion further down. | |
| After Certificates | Preserves Identity → Motion → Certificates flow. | |

### Icon

| Option | Description | Selected |
|--------|-------------|----------|
| HardDrive | Literal at-rest storage. Distinct from CBOM's Database icon. | ✓ |
| Lock | Encryption-at-rest emphasis. More generic. | |
| Archive | Stored / archived feel. Less common. | |
| ShieldCheck | Reads more compliance than storage. | |

### DAR subscore on tab

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — small ScoreGauge at top | One-glance posture read on tab landing. Mild duplication with Executive. | ✓ |
| No — Executive is single source | Pure findings detail, no duplication. | |

**User's choice:** After Motion · HardDrive · ScoreGauge at top.
**Notes:** All three recommended options. Route locked to `/data-at-rest` — Phase 43 success criterion #1 already names that path.

---

## Claude's Discretion

- Final field-name strings on `DarFinding` (semantics locked in CONTEXT D-03; identifiers can match scanner conventions).
- Whether to extract a shared `DarTable` primitive vs hand-rolling four table components.
- Loading/skeleton component choice — match prevailing pattern; Phase 43 will polish across all routes.

## Deferred Ideas

- Cross-finding KMS key inventory view (future Key Management tab or CBOM enhancement).
- Drill-down evidence panel (click row → raw scanner evidence JSON) — Phase 43 polish or new UX phase.
- Loading/skeleton polish, WCAG sweep, focus indicators — explicitly Phase 43 scope.
- Automated UAT for DAR tab — Phase 44 (UAT Debt Automation) scope.
