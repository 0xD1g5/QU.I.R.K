# Phase 39: Data at Rest Dashboard Tab - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship the deferred DASH-05 "Data at Rest" tab in the React dashboard. The tab surfaces the existing v4.3 DAR scan output — Database (POSTGRESQL/MYSQL/RDS), Object Storage (S3/AZURE_BLOB), Kubernetes secrets, and Vault — through a dedicated route at `/data-at-rest`, accessible from the sidebar nav alongside Identity, Motion, Trends, and Findings. Phase scope is presentation only: the underlying scanners and scoring logic already exist and are unchanged. Empty state, zero-console-error gate, and dashboard nav integration are all in scope. Out of scope: new scanner work, scoring changes, evidence-schema changes beyond projecting existing fields into a typed API shape.

</domain>

<decisions>
## Implementation Decisions

### API Data Shape
- **D-01:** Add a typed `dar_findings: List[DarFinding]` array to `ScanLatestResponse` in `quirk/dashboard/api/schemas.py`. Mirrors the Phase 36 `motion_findings` precedent — same pattern, same place. Do NOT filter the existing `findings[]` client-side for DAR.
- **D-02:** `DarFinding` schema is a superset model with a required `category` discriminator (`"database" | "object_storage" | "kubernetes" | "vault"`) plus DAR-specific optional fields. Each scanner populates only the fields relevant to its category; unused fields stay null.
- **D-03:** Optional DAR-specific fields on `DarFinding` (planner picks final names; these are the locked semantics):
  - `encryption_at_rest` (bool / enum) — DB, Object Storage, K8s
  - `tls_in_transit` (bool) — DB
  - `encryption_mode` (e.g., `SSE-S3` / `SSE-KMS` / `CMK` / `none`) — Object Storage
  - `kms_key_id` (string) — Object Storage, RDS
  - `public_access` (bool) — Object Storage
  - `versioning` (bool) — Object Storage
  - `namespace` (string) — Kubernetes
  - `secret_type` (string) — Kubernetes
  - `encryption_provider` (string) — Kubernetes (etcd encryption-at-rest config)
  - `seal_type` (string, e.g., `shamir` / `kms` / `transit`) — Vault
  - `auto_unseal` (bool) — Vault
  - `mount_type` (string) — Vault
  - Plus the universal `host`, `port`, `severity`, `title`, `protocol`, `description`, `remediation`, `quantum_risk`, `source` (matches `MotionFinding` baseline)
- **D-04:** Projection logic in `quirk/dashboard/api/routes/scan.py` populates `dar_findings` from existing scanner output. Scanner-side code is NOT modified; only the API serializer changes.

### Per-Finding Columns (Frontend)
- **D-05:** Each of the four category sections renders its OWN table component with category-tuned columns. Mirrors `motion.tsx`'s split between `EmailTable` and `BrokerGroupedSections`. Planner may extract a small shared `DarTable` primitive with per-category column configs; either way the column sets must differ by category.
- **D-06:** Category-specific column sets:
  - **Database table:** Engine · Host · Port · Severity · Title · Encryption-at-Rest · TLS in Transit · Quantum Risk · Remediation
  - **Object Storage table:** Provider · Host · Severity · Title · Encryption Mode · Public Access · KMS Key · Versioning · Quantum Risk · Remediation
  - **Kubernetes table:** Namespace · Host · Severity · Title · Secret Type · Encryption Provider · Quantum Risk · Remediation
  - **Vault table:** Host · Severity · Title · Mount Type · Seal Type · Auto-Unseal · Quantum Risk · Remediation
- **D-07:** Severity-sorted within every table using the existing SEV_ORDER constant pattern from `motion.tsx` (CRITICAL → HIGH → MEDIUM → LOW → INFO).

### Section Organization
- **D-08:** Top-level structure: 4 sections, fixed order — **Database**, **Object Storage**, **Kubernetes**, **Vault**. Order locked by roadmap success criterion #2.
- **D-09:** No sub-card grouping inside any category. All sub-grouping is handled by a discriminator column inside one combined table per category:
  - Object Storage: combined table with **Provider** column (S3 / Azure Blob)
  - Kubernetes: flat severity-sorted table with **Namespace** column (no per-namespace cards)
  - Database: combined table with **Engine** column (POSTGRESQL / MYSQL / RDS)
  - Vault: single table — Vault is one product, no further subdivision needed
- **D-10:** Per-section empty states (NOT a single tab-level empty state). Reuse the `EmptyStateCard` pattern from `motion.tsx`. Each section's empty message names its category and points the user at the relevant scanner config (e.g., "No database endpoints scanned in this session — enable the DB scanner or scan a database host"). Tab-level empty state is implicitly the case where all four sections are empty.

### Sidebar & Subscore
- **D-11:** Route path: `/data-at-rest`. Nav order: **Executive · Findings · Identity · Motion · Data at Rest · Certificates · CBOM · Roadmap · Trends**. Insert after Motion to pair "in motion / at rest" visually.
- **D-12:** Sidebar icon: `HardDrive` from lucide-react. (Distinct from CBOM's `Database` icon.)
- **D-13:** Render the `data_at_rest` subscore at the top of the tab using the existing `ScoreGauge` component, sized similar to Executive's per-domain gauges. Mild duplication with Executive is acceptable — gives consultants a one-glance posture read for the DAR domain when they land on the tab.

### Claude's Discretion
- Final field names on `DarFinding` (semantics in D-03 are locked; exact identifiers can match scanner conventions).
- Whether to extract a shared `DarTable` primitive or hand-roll four table components — researcher/planner pick based on duplication cost.
- Loading/skeleton component choice — match the prevailing dashboard pattern. Phase 43 will sweep loading polish across all routes; don't over-engineer here.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 39: Data at Rest Dashboard Tab" — Goal, Success Criteria, GAP-04 reference, UI hint
- `.planning/REQUIREMENTS.md` — for GAP-04 and DASH-05 source requirements

### Closest Reference Pattern (Phase 36 Motion Tab)
- `.planning/phases/36-dashboard-motion-tab/` — directory of the most recent dashboard tab phase; researcher should read its plans/SUMMARY for prior decisions
- `src/dashboard/src/pages/motion.tsx` — primary frontend reference. Patterns: per-section empty state, severity-sorted tables, useScanData hook usage, family-grouped sub-cards (NOT used here), shadcn Card/Table/Badge composition

### Backend Schema Touchpoints
- `quirk/dashboard/api/schemas.py` — add `DarFinding` model and `dar_findings` field on `ScanLatestResponse` (mirror lines 95-112 `MotionFinding`)
- `quirk/dashboard/api/routes/scan.py` — projection logic for `dar_findings` (line 679 area is where subscores are projected; new projection sits alongside)

### Existing DAR Scanner Output (read-only — do not modify)
- `quirk/scanner/db_connector.py` — POSTGRESQL / MYSQL findings, with RDS variants
- `quirk/scanner/aws_connector.py` — S3, RDS, KUBERNETES (EKS), AWS-generic findings
- `quirk/scanner/azure_connector.py` — AZURE / AZURE_BLOB findings
- `quirk/scanner/k8s_connector.py` — KUBERNETES findings
- `quirk/scanner/vault_connector.py` — VAULT findings

### Frontend Touchpoints
- `src/dashboard/src/App.tsx` — add `<Route path="/data-at-rest" element={<DataAtRestPage />} />`
- `src/dashboard/src/components/sidebar.tsx` — insert nav entry between Motion and Certificates with `HardDrive` icon
- `src/dashboard/src/types/api.ts` — add `DarFinding` type matching backend schema
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — reused at top of tab
- `src/dashboard/src/pages/executive.tsx:151` — reference usage of `ScoreGauge` with `data_at_rest`

### Downstream Phases That Depend On This
- Phase 43 (Dashboard Polish) success criterion #1 names `/data-at-rest` explicitly — route path is locked

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/src/pages/motion.tsx` — closest pattern. Per-section empty state, SEV_ORDER constant, EmptyStateCard component, family-grouped (not used here) tables. Researcher/planner should read this end-to-end before designing the DAR page.
- `src/dashboard/src/hooks/useScanData.ts` — already returns `data?.findings` and `data?.motion_findings`; needs to return `data?.dar_findings` once schema is updated.
- `src/dashboard/src/components/ui/{card,table,badge,skeleton}.tsx` — shadcn primitives in use across all pages. SEVERITY_STYLES dict already established in motion.tsx (copy or extract).
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — reused at top of tab for `data_at_rest` subscore.
- `quirk/dashboard/api/schemas.py` lines 95-112 (`MotionFinding`) — exact precedent for `DarFinding` schema definition.

### Established Patterns
- **Phase 36 typed-array precedent:** New domain-specific findings get a typed array on `ScanLatestResponse`, populated by API projection from existing scanner output. We follow this verbatim.
- **CSS variable color tokens:** Sidebar.tsx header comment (line 1-3) calls out the D-13 color audit — all dashboard color tokens use CSS variables, not hardcoded `hsl()`. Phase 39 must comply.
- **Per-section empty states:** motion.tsx renders `<EmptyStateCard>` per section. Phase 39 follows the same idiom for all 4 categories.
- **Severity-sorted tables:** SEV_ORDER constant pattern from motion.tsx — CRITICAL/HIGH/MEDIUM/LOW/INFO ordering.
- **Sidebar nav order:** Sidebar.tsx NAV_ITEMS array; touch-target min-height 44px; lucide icon per item.

### Integration Points
- API: `ScanLatestResponse.dar_findings` (new) → `useScanData()` (no change needed — passes through) → `<DataAtRestPage>` (new)
- Routing: `App.tsx` Routes block + `Sidebar.tsx` NAV_ITEMS array (both must change in lockstep)
- Score: `score.subscores.data_at_rest` already exists end-to-end — only the rendering location is new

</code_context>

<specifics>
## Specific Ideas

- The user explicitly called out (in the saved DAR memory) that this tab is the realization of DASH-05 deferred from Phase 27 — it has been on the radar since v4.3 and is a "must-add."
- Consultants reviewing DAR posture want to know: *is the data encrypted, with what algorithm/mode, who controls the key, and is it exposed to the public?* The locked column sets answer all four questions per category.

</specifics>

<deferred>
## Deferred Ideas

- **Cross-finding KMS key inventory view** — a consolidated view of all KMS keys observed across S3, RDS, etc. Could be a future "Key Management" tab or a CBOM enhancement. Not in Phase 39 scope.
- **Drill-down evidence panel** (click a row → see raw scanner evidence JSON) — not in Phase 39; could be a Phase 43 polish item or its own UX phase.
- **Loading/skeleton polish, WCAG sweep, focus indicators** — explicitly Phase 43 (Dashboard Polish) scope. Phase 39 ships functional loading + empty states; Phase 43 hardens them.
- **Automated UAT for DAR tab** — Phase 44 (UAT Debt Automation) covers this.

</deferred>

---

*Phase: 39-data-at-rest-dashboard-tab*
*Context gathered: 2026-04-29*
