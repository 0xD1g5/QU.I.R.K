# Phase 39: Data at Rest Dashboard Tab — Research

**Researched:** 2026-04-29
**Domain:** React dashboard tab (FastAPI backend schema + projection + frontend page)
**Confidence:** HIGH — all findings verified directly against repo source files.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add typed `dar_findings: List[DarFinding]` to `ScanLatestResponse`. Mirror Phase 36 `motion_findings` precedent exactly.
- **D-02:** `DarFinding` superset model with required `category` discriminator (`"database" | "object_storage" | "kubernetes" | "vault"`). Per-scanner optional fields; unused fields stay null.
- **D-03:** Optional DAR-specific fields (semantics locked; identifier names at Claude's discretion): `encryption_at_rest`, `tls_in_transit`, `encryption_mode`, `kms_key_id`, `public_access`, `versioning`, `namespace`, `secret_type`, `encryption_provider`, `seal_type`, `auto_unseal`, `mount_type`. Plus universal baseline: `host`, `port`, `severity`, `title`, `protocol`, `description`, `remediation`, `quantum_risk`, `source`.
- **D-04:** Projection logic in `quirk/dashboard/api/routes/scan.py` only. Scanner-side code NOT modified.
- **D-05:** Each category has its own table component with category-tuned columns. Shared `DarTable` primitive optional at planner discretion.
- **D-06:** Column sets per category — locked (see UI-SPEC §Table Column Specifications).
- **D-07:** Severity-sorted within every table using `SEV_ORDER` constant from `motion.tsx`.
- **D-08:** Fixed section order: Database · Object Storage · Kubernetes · Vault.
- **D-09:** No sub-card grouping. Single flat table per category with discriminator column.
- **D-10:** Per-section `EmptyStateCard` with category-specific message. Tab-level empty = all four sections empty.
- **D-11:** Route `/data-at-rest`. Nav order: Executive · Findings · Identity · Motion · **Data at Rest** · Certificates · CBOM · Roadmap · Trends.
- **D-12:** Sidebar icon: `HardDrive` from lucide-react.
- **D-13:** `ScoreGauge` at top of tab for `data_at_rest` subscore. `size={120}`, NOT `isOverall={true}`.

### Claude's Discretion
- Final field names on `DarFinding` (semantics in D-03 are locked).
- Whether to extract a shared `DarTable` primitive or four independent table components.
- Loading/skeleton component choice — match prevailing dashboard pattern.

### Deferred Ideas (OUT OF SCOPE)
- Cross-finding KMS key inventory view.
- Drill-down evidence panel (click row → raw JSON).
- Loading/skeleton polish, WCAG sweep, focus indicators (Phase 43).
- Automated UAT for DAR tab (Phase 44).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GAP-04 | User opens the dashboard and sees a "Data at Rest" tab alongside the existing tabs, listing DB / object storage / K8s secrets / Vault findings with the existing v4.3 data shape | Research maps exact scanner output fields → DarFinding projection; UI-SPEC defines column layout; motion.tsx precedent provides structural blueprint |
</phase_requirements>

---

## Summary

Phase 39 is a presentation-only feature: no new scanners, no scoring changes. The work is entirely
confined to (1) a new `DarFinding` Pydantic model + `dar_findings` field on `ScanLatestResponse`,
(2) a `_derive_dar_findings()` projection function in `scan.py` that reads `dat_scan_json` from
existing `CryptoEndpoint` rows, and (3) a new React page `src/dashboard/src/pages/data-at-rest.tsx`
wired into `App.tsx` and `sidebar.tsx`.

The Phase 36 motion tab is an exact structural precedent for all three layers. The motion
implementation is 255 lines of TSX and ~75 lines of Python projection; the DAR tab will be slightly
larger due to four category sections instead of two, but the architecture is isomorphic.

The critical research finding is the **scanner output shape mismatch**: DAR scanner categories
store context very differently. Database scanners (`db_connector.py`) store NO `dat_scan_json` at
all — encryption posture is encoded entirely in `service_detail` and `protocol`. Object Storage
(S3, Azure Blob), Kubernetes (EKS, GKE, AKS), and Vault ALL use `dat_scan_json`. The projection
function must handle per-protocol parsing logic rather than a uniform JSON read.

**Primary recommendation:** Implement `_derive_dar_findings()` as a single function in `scan.py`
with a per-protocol dispatch table (matching on `ep.protocol`), mirroring the `_derive_motion_findings`
structure. Extract `DarTable` as a shared primitive accepting `columns` + `rows` props to avoid
repeating Table boilerplate four times.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DAR finding schema | API / Backend | — | Pydantic model in `schemas.py`; TypeScript mirror in `api.ts` |
| DAR projection logic | API / Backend | — | `_derive_dar_findings()` in `routes/scan.py`; reads existing DB rows |
| React page component | Frontend (SPA) | — | New `data-at-rest.tsx` page |
| Routing + nav | Frontend (SPA) | — | `App.tsx` Routes + `sidebar.tsx` NAV_ITEMS |
| Score rendering | Frontend (SPA) | — | `ScoreGauge` with `data?.score.subscores.data_at_rest` |
| Data delivery | API / Backend | Frontend hook | `useScanData()` passes through; no hook changes needed |

---

## Standard Stack

All components already installed. Phase 39 installs nothing new.

### Core (Backend)
| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| FastAPI + Pydantic | existing | Schema definition, serialization | `quirk/dashboard/api/schemas.py` |
| SQLAlchemy | existing | CryptoEndpoint ORM model | `quirk/models.py` |

### Core (Frontend)
| Component | Import Path | Use |
|-----------|------------|-----|
| `Card`, `CardContent`, `CardHeader`, `CardTitle` | `@/components/ui/card` | Section containers, empty states |
| `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow` | `@/components/ui/table` | All four category tables |
| `Badge` | `@/components/ui/badge` | Severity + boolean field badges |
| `Skeleton` | `@/components/ui/skeleton` | Loading state (5x `h-10 w-full`) |
| `ScoreGauge` | `@/components/gauges/ScoreGauge` | DAR subscore at tab top |
| `HardDrive` | `lucide-react` | Sidebar nav icon |
| `useScanData` | `@/hooks/useScanData` | Data fetch hook (no changes) |

**No new installs required.** All shadcn primitives are pre-installed in
`src/dashboard/src/components/ui/`. [VERIFIED: directory listing]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser GET /data-at-rest
        │
        ▼
  DataAtRestPage (new)
  useScanData() hook
        │
        ▼ GET /api/scan/latest
  FastAPI route: get_scan_latest()
        │
        ├─ existing: findings, certificates, score, motion_findings ...
        │
        └─ NEW: dar_findings = _derive_dar_findings(endpoints)
                        │
                        ├─ protocol in {POSTGRESQL, MYSQL, RDS}
                        │   → parse service_detail string
                        │   → DarFinding(category="database", ...)
                        │
                        ├─ protocol in {S3}
                        │   → json.loads(ep.dat_scan_json)
                        │   → DarFinding(category="object_storage", ...)
                        │
                        ├─ protocol in {AZURE_BLOB}
                        │   → json.loads(ep.dat_scan_json)
                        │   → DarFinding(category="object_storage", ...)
                        │
                        ├─ protocol in {KUBERNETES}
                        │   → json.loads(ep.dat_scan_json)
                        │   → DarFinding(category="kubernetes", ...)
                        │
                        └─ protocol in {VAULT}
                            → json.loads(ep.dat_scan_json)
                            → DarFinding(category="vault", ...)

  DataAtRestPage receives dar_findings[]
        │
        ├─ ScoreGauge(score=data.score.subscores.data_at_rest)
        │
        ├─ Section "Database Encryption"
        │   dbFindings = dar_findings.filter(f => f.category === "database")
        │   → empty state or <DatabaseTable>
        │
        ├─ Section "Object Storage"
        │   objFindings = dar_findings.filter(f => f.category === "object_storage")
        │   → empty state or <ObjectStorageTable>
        │
        ├─ Section "Kubernetes Secrets"
        │   k8sFindings = dar_findings.filter(f => f.category === "kubernetes")
        │   → empty state or <KubernetesTable>
        │
        └─ Section "Vault"
            vaultFindings = dar_findings.filter(f => f.category === "vault")
            → empty state or <VaultTable>
```

### Recommended Project Structure

New files only:
```
quirk/dashboard/api/schemas.py          ← add DarFinding class, dar_findings on ScanLatestResponse
quirk/dashboard/api/routes/scan.py      ← add _derive_dar_findings(), wire into return statement
src/dashboard/src/
├── types/api.ts                        ← add DarFinding interface, dar_findings on ScanLatestResponse
├── pages/data-at-rest.tsx              ← NEW page (primary deliverable)
├── App.tsx                             ← add Route + import
└── components/sidebar.tsx              ← add NAV_ITEMS entry
```

---

## API Schema Sketch

### `DarFinding` (add to `quirk/dashboard/api/schemas.py` after `MotionFinding`)

Mirror lines 97-111 (`MotionFinding`) exactly. Verified pattern: [VERIFIED: quirk/dashboard/api/schemas.py:97-111]

```python
# ---- DAR Findings (Phase 39 GAP-04) ----

class DarFinding(BaseModel):
    # Universal baseline (matches MotionFinding baseline fields)
    host: str
    port: int
    severity: str                           # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None            # "database" / "object_storage" / "kubernetes" / "vault"

    # Discriminator (required — D-02)
    category: str                           # "database" | "object_storage" | "kubernetes" | "vault"

    # Database fields
    encryption_at_rest: Optional[bool] = None   # DB, Object Storage, K8s
    tls_in_transit: Optional[bool] = None        # DB only

    # Object Storage fields
    encryption_mode: Optional[str] = None        # SSE-S3 / SSE-KMS / CMK / none
    kms_key_id: Optional[str] = None             # Object Storage, RDS
    public_access: Optional[bool] = None         # Object Storage
    versioning: Optional[bool] = None            # Object Storage

    # Kubernetes fields
    namespace: Optional[str] = None
    secret_type: Optional[str] = None
    encryption_provider: Optional[str] = None    # etcd encryption-at-rest config

    # Vault fields
    seal_type: Optional[str] = None              # shamir / kms / transit
    auto_unseal: Optional[bool] = None
    mount_type: Optional[str] = None             # transit / pki / auth
```

### `ScanLatestResponse` update

Add after `motion_findings` at line 153: [VERIFIED: quirk/dashboard/api/schemas.py:153]

```python
    dar_findings: List[DarFinding] = []         # NEW — Phase 39 GAP-04
```

### TypeScript mirror (`src/dashboard/src/types/api.ts`)

Add after `MotionFinding` interface (currently ends at line 109): [VERIFIED: src/dashboard/src/types/api.ts:94-127]

```typescript
export interface DarFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  category: string            // "database" | "object_storage" | "kubernetes" | "vault"
  // Database
  encryption_at_rest?: boolean | null
  tls_in_transit?: boolean | null
  // Object Storage
  encryption_mode?: string | null
  kms_key_id?: string | null
  public_access?: boolean | null
  versioning?: boolean | null
  // Kubernetes
  namespace?: string | null
  secret_type?: string | null
  encryption_provider?: string | null
  // Vault
  seal_type?: string | null
  auto_unseal?: boolean | null
  mount_type?: string | null
}
```

Add `dar_findings: DarFinding[]` to `ScanLatestResponse` after `motion_findings`.

---

## Projection Logic — `_derive_dar_findings()`

This is the most complex research finding. The function signature mirrors `_derive_motion_findings`
exactly. [VERIFIED: quirk/dashboard/api/routes/scan.py:337-411]

### Protocol Dispatch Table

| `ep.protocol` | Category | Primary Data Source | Key Fields |
|---------------|----------|--------------------|-----------:|
| `POSTGRESQL` | database | `service_detail` string | `ssl-enforced` / `ssl-off` / `plaintext-connections-allowed` |
| `MYSQL` | database | `service_detail` string | `ssl-off` / `<cipher>-weak` / `<cipher>-ok` |
| `RDS` | database | `service_detail` string | `RDS/none` / `RDS/sse-rds` / `RDS/sse-kms-aws` / `RDS/sse-kms-cmk` |
| `S3` | object_storage | `dat_scan_json` | `{"bucket": ..., "service_detail": "S3/sse-s3", ...}` |
| `AZURE_BLOB` | object_storage | `dat_scan_json` | `{"account": ..., "container": ..., "key_source": ...}` |
| `KUBERNETES` | kubernetes | `dat_scan_json` | `{"namespace": ..., "secret_type_counts": ..., "provider": ..., "cluster": ...}` |
| `VAULT` | vault | `dat_scan_json` | `{"key_name": ..., "key_type": ..., "mount_point": ..., "auth_path": ..., "auth_type": ...}` |

### Per-Protocol Derivation Logic

**POSTGRESQL** [VERIFIED: quirk/scanner/db_connector.py:97-161]

`service_detail` patterns:
- `"PostgreSQL/ssl-enforced"` → `encryption_at_rest=True, tls_in_transit=True, severity="INFO"`
- `"PostgreSQL/ssl-off"` → `encryption_at_rest=False, tls_in_transit=False, severity="HIGH"`
- `"PostgreSQL/plaintext-connections-allowed (N non-SSL)"` → `encryption_at_rest=False, tls_in_transit=False, severity="HIGH"`

`dat_scan_json` is **NOT set** by `db_connector.py`. All signal comes from `service_detail`
and `ep.severity`. The projector must parse `service_detail` with simple prefix matching.

**MYSQL** [VERIFIED: quirk/scanner/db_connector.py:220-259]

`service_detail` patterns:
- `"MySQL/ssl-off"` → `encryption_at_rest=False, tls_in_transit=False, severity="HIGH"`
- `"MySQL/<cipher>-weak"` → `encryption_at_rest=True, tls_in_transit=True, severity="MEDIUM"`
- `"MySQL/<cipher>-ok"` → `encryption_at_rest=True, tls_in_transit=True, severity="INFO"`

No `dat_scan_json`. Same `service_detail`-only parsing approach as PostgreSQL.

**RDS** [VERIFIED: quirk/scanner/aws_connector.py:75-129]

`service_detail` patterns:
- `"RDS/none"` → `encryption_at_rest=False, kms_key_id=None, severity="HIGH"`
- `"RDS/sse-rds"` → `encryption_at_rest=True, kms_key_id=None`
- `"RDS/sse-kms-aws"` → `encryption_at_rest=True, kms_key_id="AWS-managed"` (exact key not stored)
- `"RDS/sse-kms-cmk"` → `encryption_at_rest=True, kms_key_id="CMK"` (exact key not stored)

No `dat_scan_json` on RDS endpoints. Severity is set on `ep.severity` (HIGH for `RDS/none`;
None for others). Key detail is lost at the endpoint level — the `service_detail` label is
the only signal. `kms_key_id` should be derived from the label (e.g., `"AWS-managed"`,
`"CMK"`, `None`).

**S3** [VERIFIED: quirk/scanner/aws_connector.py:283-312]

`dat_scan_json` payload: `{"bucket": "<name>", "service_detail": "S3/sse-s3" | "S3/sse-kms-aws" | "S3/sse-kms-cmk" | "S3/unencrypted", "severity": null | "HIGH" | "MEDIUM"}`

Derivation:
- `service_detail == "S3/unencrypted"` → `encryption_at_rest=False, encryption_mode="none"`
- `service_detail == "S3/sse-s3"` → `encryption_at_rest=True, encryption_mode="SSE-S3"`
- `service_detail == "S3/sse-kms-aws"` → `encryption_at_rest=True, encryption_mode="SSE-KMS"`, `kms_key_id="AWS-managed"`
- `service_detail == "S3/sse-kms-cmk"` → `encryption_at_rest=True, encryption_mode="SSE-KMS"`, `kms_key_id="CMK"`

Public access: NOT stored by the scanner (the S3 scanner does not probe ACLs). `public_access`
will always be `null` for S3 findings. Versioning: also not probed. Both must render `—` in the UI.

**AZURE_BLOB** [VERIFIED: quirk/scanner/azure_connector.py:205-219]

`dat_scan_json` payload: `{"account": "<name>", "container": "<name>", "key_source": "Microsoft.KeyVault" | "Microsoft.Storage" | "absent"}`

Derivation:
- `key_source == "microsoft.keyvault"` → `encryption_at_rest=True, encryption_mode="CMK"`
- otherwise → `encryption_at_rest=True, encryption_mode="SSE-S3"` (platform-managed; Azure always encrypts at rest)

`public_access`, `versioning`, `kms_key_id`: not stored. All `null`.
`host` = container resource ID (ARM path), `protocol` = `"AZURE_BLOB"`.
Provider column in UI should render as `"AZURE_BLOB"`.

**KUBERNETES** [VERIFIED: quirk/scanner/k8s_connector.py:128-350]

Three distinct `dat_scan_json` shapes co-exist under protocol `"KUBERNETES"`:

1. EKS path (`aws_connector._scan_eks_encryption`):
   `{"cluster": "<name>", "provider": "EKS", "encryptionConfig": [...]}`
   → `encryption_at_rest = (encryptionConfig includes secrets entry)`, `encryption_provider = "EKS/KMS"` if encrypted

2. GKE path (`k8s_connector._scan_gke_encryption`):
   `{"cluster": "<name>", "provider": "GKE", "current_state": 0|1|2, "key_name": "..."}`
   → `encryption_at_rest = (current_state == 2)`, `encryption_provider = "GKE/Cloud-KMS"` if encrypted

3. AKS path (`k8s_connector._scan_aks_encryption`):
   `{"cluster": "<name>", "provider": "AKS", "kv_kms_enabled": true|false}`
   → `encryption_at_rest = kv_kms_enabled`, `encryption_provider = "AKS/Key-Vault"` if enabled

4. Secret enumeration (`k8s_connector._enumerate_secret_types`):
   `{"namespace": "<name>", "secret_type_counts": {"Opaque": N, "kubernetes.io/tls": M, ...}}`
   → `namespace = parsed`, `secret_type = most common type from counts` (or comma-joined summary)

The projector must discriminate these cases by checking `dat_scan_json.provider` or presence of
`"namespace"` key. The safest approach: `if "namespace" in dat` → secret-enumeration shape;
`else` → cluster-encryption shape with `provider` field.

**VAULT** [VERIFIED: quirk/scanner/vault_connector.py:160-366]

Three distinct `dat_scan_json` shapes under protocol `"VAULT"`:

1. Transit keys (`_scan_transit_keys`):
   `{"key_name": "<name>", "key_type": "aes256-gcm96", "exportable": true|false, "latest_version": N, "remediation": "..." | null}`
   → `mount_type = "transit"`, `seal_type = null` (transit keys are not about the seal mechanism)

2. PKI mounts (`_scan_pki_mounts`):
   `{"mount_point": "<name>", "role": "root" | "intermediate-N", "sig_alg": "<alg>", "key_size": N, "finding": "<reason>"}`
   → `mount_type = "pki"`, `seal_type = null`

3. Auth methods (`_scan_auth_methods`):
   `{"auth_path": "token/", "auth_type": "token" | "ldap" | "userpass", "remediation": "..."}`
   → `mount_type = "auth"`, `seal_type = null`

**Critical gap:** `seal_type` and `auto_unseal` are NOT stored by any Vault scanner sub-path.
The vault connector probes transit keys, PKI mounts, and auth methods — it does NOT call
`sys/seal-status` or any unseal configuration API. These two DAR-specific fields will always
be `null` for the current scanner implementation. The UI-SPEC already handles this with `—`
rendering for null values. No schema change is needed; the projection simply leaves them null.

---

## Frontend — `motion.tsx` Structural Skeleton

[VERIFIED: src/dashboard/src/pages/motion.tsx:1-255]

The DAR page mirrors `motion.tsx` precisely. Key structural elements to replicate:

**Lines 11-17** — `SEVERITY_STYLES` constant (copy verbatim):
```typescript
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}
```

**Line 45** — `SEV_ORDER` constant (copy verbatim):
```typescript
const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 } as const
```

**Lines 35-43** — `EmptyStateCard` component (copy verbatim):
```typescript
function EmptyStateCard({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}
```

**Lines 209-218** — Loading + error states (copy verbatim):
```typescript
if (loading) {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}
if (error) return <p className="text-muted-foreground text-sm">{error}</p>
```

**Lines 193-198** — `useScanData()` wiring (adapt):
```typescript
export function DataAtRestPage() {
  const { data, loading, error } = useScanData()
  const darFindings: DarFinding[] = useMemo(() => data?.dar_findings ?? [], [data])
  // Category splits:
  const dbFindings = useMemo(() => darFindings.filter(f => f.category === "database"), [darFindings])
  const objFindings = useMemo(() => darFindings.filter(f => f.category === "object_storage"), [darFindings])
  const k8sFindings = useMemo(() => darFindings.filter(f => f.category === "kubernetes"), [darFindings])
  const vaultFindings = useMemo(() => darFindings.filter(f => f.category === "vault"), [darFindings])
```

**ScoreGauge wiring** (from `executive.tsx:151` pattern): [VERIFIED: src/dashboard/src/pages/executive.tsx:151]
```typescript
<ScoreGauge
  score={data?.score.subscores.data_at_rest ?? 0}
  label="Data at Rest"
  size={120}
/>
```

---

## Sidebar and App.tsx Insertion Points

### `src/dashboard/src/components/sidebar.tsx`

[VERIFIED: sidebar.tsx:20-28]

Current `NAV_ITEMS` array (lines 20-28):
```typescript
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/motion", label: "Motion", Icon: Activity },
  // INSERT HERE at index 4:
  // { path: "/data-at-rest", label: "Data at Rest", Icon: HardDrive },
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },
]
```

Changes required:
1. Add `HardDrive` to the lucide-react import (line 9-14 area — currently imports `LayoutDashboard, AlertTriangle, Shield, Database, GitBranch, Fingerprint, TrendingUp, Activity`).
2. Insert `{ path: "/data-at-rest", label: "Data at Rest", Icon: HardDrive }` between the Motion and Certificates entries (after line 24, before line 25 in the current file).

### `src/dashboard/src/App.tsx`

[VERIFIED: src/dashboard/src/App.tsx:1-47]

Changes required:
1. Add import: `import { DataAtRestPage } from "@/pages/data-at-rest"` (after line 10, alongside other page imports).
2. Add route (after line 33, Motion route, before Certificates):
   ```typescript
   <Route path="/data-at-rest" element={<DataAtRestPage />} />
   ```

Both changes MUST land in the same commit to keep routing and nav in lockstep (CONTEXT.md D-11).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Severity badge rendering | Custom badge component | `Badge` + `SEVERITY_STYLES` from `motion.tsx` | Already established project pattern |
| Boolean field badges | Custom renderer | Inline `Badge` with hardcoded `hsl()` classes per UI-SPEC §Boolean Badge Rendering | Matches UI-SPEC exactly |
| Data fetching | Custom fetch logic | `useScanData()` hook | Hook already handles cancellation, error state, scan selection |
| Score display | Custom gauge SVG | `ScoreGauge` component | Component already accepts `score` + `label` + `size` props |
| Table skeleton | Custom loading UI | `Skeleton` + `Array.from({length: 5})` pattern | Matches motion.tsx exactly, Phase 43 will polish |
| Empty states | Tab-level empty | Per-section `EmptyStateCard` | D-10 requires per-section granularity |

---

## Common Pitfalls

### Pitfall 1: DB Connectors Don't Write `dat_scan_json`
**What goes wrong:** Projector tries `json.loads(ep.dat_scan_json)` for POSTGRESQL/MYSQL endpoints and gets `AttributeError` or `None` parse error.
**Why it happens:** `db_connector.py` sets `service_detail` only — no `dat_scan_json`. This differs from S3, Azure Blob, K8s, and Vault which all write `dat_scan_json`.
**How to avoid:** Dispatch on `ep.protocol` first. For `POSTGRESQL` and `MYSQL`, parse `ep.service_detail` with string prefix checks. Only call `json.loads(ep.dat_scan_json)` for S3/AZURE_BLOB/KUBERNETES/VAULT after guarding with `ep.dat_scan_json`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute ...` in projection unit test fixtures.

### Pitfall 2: Three `dat_scan_json` Shapes Under `KUBERNETES`
**What goes wrong:** Projector assumes a uniform K8s payload and KeyErrors on `"namespace"` vs `"provider"` vs `"cluster"`.
**Why it happens:** EKS, GKE, AKS cluster-encryption endpoints (from `aws_connector` and `k8s_connector`) share `protocol="KUBERNETES"` with the per-namespace secret-enumeration endpoints. The JSON shapes are structurally different.
**How to avoid:** Discriminate by `"namespace" in dat_json` → secret enumeration shape. Otherwise → cluster-encryption shape (`"provider"` field distinguishes EKS/GKE/AKS).
**Warning signs:** `KeyError: 'namespace'` or `KeyError: 'provider'` during projection.

### Pitfall 3: Three `dat_scan_json` Shapes Under `VAULT`
**What goes wrong:** Projector assumes Vault has a single payload structure.
**Why it happens:** Transit keys, PKI mounts, and auth methods are all emitted with `protocol="VAULT"` but with structurally different JSON payloads.
**How to avoid:** Discriminate by key presence: `"key_name"` → transit, `"mount_point"` → PKI, `"auth_path"` → auth. `mount_type` field in `DarFinding` should reflect these sub-types.
**Warning signs:** `KeyError: 'mount_point'` when processing transit endpoints.

### Pitfall 4: `seal_type` and `auto_unseal` Are Not Scanned
**What goes wrong:** Planner or implementer expects to populate `seal_type`/`auto_unseal` from scanner output and cannot find the data.
**Why it happens:** `vault_connector.py` does not call `sys/seal-status`. These fields were included in D-03 as aspirational but the scanner does not collect them.
**How to avoid:** Projection leaves `seal_type=None`, `auto_unseal=None` for all Vault findings. The UI-SPEC renders `null` as `—`. No workaround needed; this is acceptable per Phase 39 scope.
**Warning signs:** Any attempt to read `seal_type` from `dat_scan_json` will produce KeyError.

### Pitfall 5: RDS `kms_key_id` Is Not Stored at Endpoint Level
**What goes wrong:** Projector tries to extract the actual AWS KMS key ARN for RDS findings and finds nothing.
**Why it happens:** `aws_connector._scan_rds_encryption()` encodes encryption posture into `service_detail` string only (`"RDS/sse-kms-cmk"`) — the actual `KmsKeyId` from the boto3 response is not written to `dat_scan_json` or any field.
**How to avoid:** Derive `kms_key_id` from the `service_detail` label as a human-readable string: `"AWS-managed"` for `sse-kms-aws`, `"CMK"` for `sse-kms-cmk`, `None` for others.
**Warning signs:** Any attempt to find a KMS ARN string in `ep.dat_scan_json` for RDS will fail.

### Pitfall 6: S3 `public_access` and `versioning` Are Not Scanned
**What goes wrong:** UI columns for Public Access and Versioning never show anything other than `—` for S3.
**Why it happens:** `_scan_s3_encryption()` in `aws_connector.py` only calls `get_bucket_encryption()`. It does not probe `get_bucket_acl()`, `get_bucket_policy_status()`, or `get_bucket_versioning()`.
**How to avoid:** Accept `null` for these fields. The UI-SPEC already specifies `—` for null. Document in PLAN.md that these columns will show `—` for all current scan data until a future scanner phase adds these probes.
**Warning signs:** `KeyError: 'public_access'` if projector attempts to read from `dat_scan_json`.

### Pitfall 7: `App.tsx` and `sidebar.tsx` Must Change in Lockstep
**What goes wrong:** Route exists but nav entry is missing (or vice versa) — user sees broken navigation.
**How to avoid:** Single plan task covering both files, verified together before commit.

### Pitfall 8: `isOverall={true}` on ScoreGauge
**What goes wrong:** Using `isOverall={true}` causes the gauge to render at larger stroke width and accent color (reserved for Executive tab's overall score).
**How to avoid:** Use `size={120}` with default `isOverall={false}`. See `ScoreGauge.tsx` lines 1-7.

---

## Code Examples

### `_derive_dar_findings()` — Full Structure

```python
# Source: mirrors _derive_motion_findings at scan.py:337-411

DAR_PROTOCOLS = {"POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT"}

def _derive_dar_findings(endpoints) -> list[DarFinding]:
    """Synthesize DAR findings from CryptoEndpoints with dat_scan_json or service_detail.
    Mirrors _derive_motion_findings (Phase 36). Protocol dispatch handles per-scanner shape variance.
    """
    results: list[DarFinding] = []
    for ep in endpoints:
        proto = (getattr(ep, "protocol", None) or "").upper()
        if proto not in DAR_PROTOCOLS:
            continue

        service_detail = getattr(ep, "service_detail", None) or ""
        dat_raw = getattr(ep, "dat_scan_json", None)
        dat: dict = {}
        if dat_raw:
            try:
                dat = json.loads(dat_raw)
            except Exception:
                dat = {}

        severity = getattr(ep, "severity", None) or "INFO"
        host = getattr(ep, "host", "") or ""
        port = getattr(ep, "port", 0) or 0

        # --- per-protocol dispatch ---
        if proto in {"POSTGRESQL", "MYSQL"}:
            finding = _dar_db(host, port, proto, severity, service_detail)
        elif proto == "RDS":
            finding = _dar_rds(host, port, severity, service_detail)
        elif proto == "S3":
            finding = _dar_s3(host, port, severity, service_detail, dat)
        elif proto == "AZURE_BLOB":
            finding = _dar_azure_blob(host, port, severity, service_detail, dat)
        elif proto == "KUBERNETES":
            finding = _dar_k8s(host, port, severity, service_detail, dat)
        elif proto == "VAULT":
            finding = _dar_vault(host, port, severity, service_detail, dat)
        else:
            continue

        if finding:
            results.append(finding)

    _sev_ord = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _sev_ord.get(f.severity, 99))
    return results
```

### Kubernetes Discriminator Pattern

```python
# Source: derived from k8s_connector.py:289-350 (dat_scan_json shapes)

def _dar_k8s(host, port, severity, service_detail, dat) -> Optional[DarFinding]:
    if "namespace" in dat:
        # Secret enumeration shape: {"namespace": ..., "secret_type_counts": {...}}
        ns = dat.get("namespace", "")
        type_counts = dat.get("secret_type_counts", {})
        secret_type = ", ".join(
            f"{t}:{c}" for t, c in sorted(type_counts.items(), key=lambda x: -x[1])
        )
        return DarFinding(
            host=host, port=port, severity=severity,
            title=f"K8s secrets in namespace {ns}",
            category="kubernetes",
            namespace=ns,
            secret_type=secret_type or None,
            encryption_provider=None,    # cluster-level; unknown from this endpoint
            source="kubernetes",
        )
    else:
        # Cluster encryption shape: {"cluster": ..., "provider": ..., ...}
        provider = dat.get("provider", "")
        cluster = dat.get("cluster", "")
        encrypted = _k8s_encrypted(provider, dat)
        enc_provider = _k8s_enc_provider(provider, dat) if encrypted else None
        return DarFinding(
            host=host, port=port, severity=severity,
            title=f"{provider} cluster etcd encryption: {'encrypted' if encrypted else 'unencrypted'}",
            category="kubernetes",
            namespace=None,
            secret_type=None,
            encryption_at_rest=encrypted,
            encryption_provider=enc_provider,
            source="kubernetes",
        )
```

### Vault Discriminator Pattern

```python
# Source: derived from vault_connector.py:160-366 (dat_scan_json shapes)

def _dar_vault(host, port, severity, service_detail, dat) -> Optional[DarFinding]:
    if "key_name" in dat:
        mount_type = "transit"
        title = f"Vault transit key: {dat.get('key_type', '')}"
    elif "mount_point" in dat:
        mount_type = "pki"
        title = f"Vault PKI: {dat.get('mount_point', '')} ({dat.get('role', '')})"
    elif "auth_path" in dat:
        mount_type = "auth"
        title = f"Vault auth: {dat.get('auth_type', '')}"
    else:
        mount_type = None
        title = "Vault endpoint"

    return DarFinding(
        host=host, port=port, severity=severity,
        title=title,
        category="vault",
        mount_type=mount_type,
        seal_type=None,       # not probed by scanner
        auto_unseal=None,     # not probed by scanner
        remediation=dat.get("remediation"),
        source="vault",
    )
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| Client-side filter of `findings[]` for DAR | Typed `dar_findings[]` array (D-01) | Type safety; columns per category |
| No DAR tab | `/data-at-rest` route (Phase 39) | Closes DASH-05 deferred from Phase 27 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|--------------|
| A1 | `public_access` and `versioning` are never populated by S3 scanner | Projection Logic | Columns always show `—`; could add scanner probe later |
| A2 | `seal_type` and `auto_unseal` are never populated by Vault scanner | Projection Logic | Vault columns show `—` for these; acceptable per Phase 39 scope |
| A3 | RDS `kms_key_id` is not the actual ARN, only derived from `service_detail` label | Projection Logic | KMS Key column for RDS shows `"AWS-managed"` / `"CMK"` not actual ARN |

All three assumptions are [VERIFIED] from reading the scanner source files directly. They are
documented as assumptions because the UI-SPEC columns imply this data may be present — the
research confirms it will be `null` in the current scanner implementation.

---

## Open Questions

1. **`scan_error` endpoints in projection scope**
   - What we know: Endpoints with `scan_error` set have `severity=None` or absent (e.g., POSTGRESQL `"insufficient-privilege"` endpoint). These are also in the `endpoints` list.
   - What's unclear: Should `_derive_dar_findings()` include `scan_error` endpoints in the DAR tab? Motion tab skips them (protocol filter handles it implicitly).
   - Recommendation: Skip endpoints where `ep.scan_error` is not None. These represent scanner failures, not cryptographic posture findings. Planner should confirm.

2. **Engine column source for Database table**
   - What we know: D-06 specifies an "Engine" column populated from `category` + `protocol`. The `protocol` field on the endpoint is `"POSTGRESQL"`, `"MYSQL"`, or `"RDS"`.
   - What's unclear: The UI-SPEC says "Derived: POSTGRESQL / MYSQL / RDS" — this maps directly from `protocol`. No derivation needed; the `DarFinding.protocol` field carries this value.
   - Recommendation: `protocol` field doubles as engine label for DB table. No additional field required.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 39 is a pure code/schema change. No external tools, services, or CLIs are required beyond the existing project toolchain (`python`, `npm`, `pytest`).

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` or `setup.cfg` (existing) |
| Quick run command | `pytest tests/test_dar_dashboard.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|------------------|-------------|
| GAP-04 | `_derive_dar_findings()` returns `DarFinding` list from mixed CryptoEndpoint fixtures | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_findings_db -x` | ❌ Wave 0 |
| GAP-04 | POSTGRESQL `service_detail` → correct `encryption_at_rest` + `tls_in_transit` values | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_db_postgresql -x` | ❌ Wave 0 |
| GAP-04 | S3 `dat_scan_json` → correct `encryption_mode` values | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_s3 -x` | ❌ Wave 0 |
| GAP-04 | KUBERNETES mixed shapes (cluster vs. namespace) dispatch correctly | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_k8s_dispatch -x` | ❌ Wave 0 |
| GAP-04 | VAULT mixed shapes (transit vs. PKI vs. auth) dispatch correctly | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_vault_dispatch -x` | ❌ Wave 0 |
| GAP-04 | `GET /api/scan/latest` response includes `dar_findings` key (API contract) | integration | `pytest tests/test_dar_dashboard.py::test_api_dar_findings_key -x` | ❌ Wave 0 |
| GAP-04 | `dar_findings` is empty list (not absent) when no DAR endpoints exist | integration | `pytest tests/test_dar_dashboard.py::test_api_dar_findings_empty -x` | ❌ Wave 0 |
| GAP-04 | `scan_error` endpoints are excluded from DAR findings | unit | `pytest tests/test_dar_dashboard.py::test_derive_dar_scan_error_excluded -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_dar_dashboard.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Frontend Validation (manual + console gate)

The zero-console-error gate (CONTEXT.md phase boundary) requires manual verification:
1. `npm run dev` in `src/dashboard/`
2. Navigate to `/data-at-rest`
3. Verify browser DevTools console shows zero errors and zero React warnings
4. Verify empty state renders for sections with no data
5. Verify `ScoreGauge` renders without NaN (passes `0` when `data_at_rest` subscore absent)

There is no automated frontend test suite in this project (confirmed: no `jest.config.*`,
`vitest.config.*`, or `*.test.tsx` files found in `src/dashboard/`).

### Wave 0 Gaps
- [ ] `tests/test_dar_dashboard.py` — all 8 test cases above; use `DashboardClient` fixture pattern from `tests/conftest.py`
- [ ] Fixture: `CryptoEndpoint` instances covering all 7 protocol variants (POSTGRESQL, MYSQL, RDS, S3, AZURE_BLOB, KUBERNETES×2, VAULT×3)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | read-only dashboard tab |
| V3 Session Management | no | no new session state |
| V4 Access Control | no | DAR findings are read-only; same access as all other tabs |
| V5 Input Validation | yes | `json.loads(dat_scan_json)` with try/except guard; Pydantic serialization validates output |
| V6 Cryptography | no | no new crypto operations |

**Key V5 note:** Every `dat_scan_json` parse in `_derive_dar_findings()` must be wrapped in
`try/except` with fallback to `dat = {}`. Malformed JSON in one endpoint must not abort
projection of all other endpoints. This mirrors the error isolation pattern already used in
`_derive_motion_findings()` (getattr guards throughout).

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/schemas.py` — `MotionFinding` (lines 97-111), `ScanLatestResponse` (lines 144-153)
- `quirk/dashboard/api/routes/scan.py` — `_derive_motion_findings` (lines 337-411), return statement (lines 714-729)
- `src/dashboard/src/pages/motion.tsx` — full structural precedent (lines 1-255)
- `src/dashboard/src/components/sidebar.tsx` — `NAV_ITEMS` array (lines 20-28)
- `src/dashboard/src/App.tsx` — Routes block (lines 28-39)
- `src/dashboard/src/types/api.ts` — `ScanLatestResponse` (lines 117-127), `MotionFinding` (lines 94-109)
- `src/dashboard/src/hooks/useScanData.ts` — hook signature (lines 1-58)
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — props interface (lines 1-7)
- `quirk/scanner/db_connector.py` — POSTGRESQL/MYSQL scanner output (lines 97-259)
- `quirk/scanner/aws_connector.py` — RDS/EKS/S3 scanner output (lines 75-312)
- `quirk/scanner/azure_connector.py` — AZURE_BLOB scanner output (lines 120-226)
- `quirk/scanner/k8s_connector.py` — KUBERNETES scanner output (lines 96-350)
- `quirk/scanner/vault_connector.py` — VAULT scanner output (lines 118-366)
- `quirk/models.py` — `CryptoEndpoint.dat_scan_json` field (line 79)

### Secondary (MEDIUM confidence)
- `src/dashboard/src/pages/executive.tsx:151` — `ScoreGauge` usage pattern for `data_at_rest` subscore
- `tests/test_dashboard_api.py` — existing dashboard integration test fixture pattern
- `.planning/phases/39-data-at-rest-dashboard-tab/39-UI-SPEC.md` — design contract (approved)
- `.planning/phases/39-data-at-rest-dashboard-tab/39-CONTEXT.md` — locked decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components verified as pre-installed in codebase
- Architecture: HIGH — exact precedent in Phase 36 motion tab; scanner output shapes verified from source
- Pitfalls: HIGH — each pitfall derived from reading actual scanner implementation; no speculation
- Projection field mapping: HIGH — every field verified against scanner source; gaps (seal_type, public_access) explicitly confirmed absent

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (stable codebase; no planned scanner changes this milestone)
