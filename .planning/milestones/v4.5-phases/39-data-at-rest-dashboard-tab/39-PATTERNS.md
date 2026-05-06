# Phase 39: Data at Rest Dashboard Tab — Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/dashboard/src/pages/data-at-rest.tsx` | component (page) | request-response | `src/dashboard/src/pages/motion.tsx` | exact |
| `quirk/dashboard/api/schemas.py` | model | CRUD | `quirk/dashboard/api/schemas.py` lines 97-153 (`MotionFinding` + `ScanLatestResponse`) | exact |
| `quirk/dashboard/api/routes/scan.py` | service | request-response | same file, `_derive_motion_findings` (lines 337-411) + return block (lines 714-729) | exact |
| `src/dashboard/src/types/api.ts` | model | transform | same file, `MotionFinding` interface (lines 94-127) | exact |
| `src/dashboard/src/App.tsx` | config/routing | request-response | same file, `MotionPage` route (line 32-33) | exact |
| `src/dashboard/src/components/sidebar.tsx` | component | request-response | same file, `NAV_ITEMS` array (lines 20-29) | exact |
| `src/dashboard/src/components/gauges/ScoreGauge.tsx` | component | — | `src/dashboard/src/pages/executive.tsx` line 151 (reuse, no modification) | exact |
| `tests/test_dar_dashboard.py` | test | CRUD | `tests/test_dashboard_api.py` lines 97-135 (`_ep` fixture + `_derive_motion_findings` unit tests) | exact |

---

## Pattern Assignments

### `src/dashboard/src/pages/data-at-rest.tsx` (component, request-response)

**Analog:** `src/dashboard/src/pages/motion.tsx` (entire file, 255 lines)

**Imports pattern** (motion.tsx lines 1-9):
```typescript
import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { MotionFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
```
Adapt: replace `MotionFinding` import with `DarFinding`. `CardHeader`/`CardTitle` are only needed if `BrokerGroupedSections`-style sub-cards are used — DAR uses flat tables, so they can be omitted from individual table components. Keep them in scope for the section containers if needed.

**Severity styles constant** (motion.tsx lines 11-17 — copy verbatim):
```typescript
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}
```

**SEV_ORDER constant** (motion.tsx line 45 — copy verbatim):
```typescript
const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 } as const
```

**EmptyStateCard component** (motion.tsx lines 35-43 — copy verbatim):
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

**Table component structure** (motion.tsx `EmailTable`, lines 47-108 — adapt as `DatabaseTable`, `ObjectStorageTable`, `KubernetesTable`, `VaultTable`):
```typescript
function EmailTable({ findings }: { findings: MotionFinding[] }) {
  const rows = [...findings].sort(
    (a, b) =>
      (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 99) -
      (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 99) ||
      (a.port ?? 0) - (b.port ?? 0),
  )

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-semibold">Port</TableHead>
              {/* ... category-specific columns from UI-SPEC ... */}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{f.port}</TableCell>
                {/* ... */}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```
Per UI-SPEC: `TableHead className="text-xs font-semibold"`, `TableCell className="text-sm"`, `TableRow className="hover:bg-accent/5"`. `CardContent className="p-0"` so table fills edge-to-edge.

**Severity Badge rendering pattern** (motion.tsx line 77-80):
```typescript
<Badge className={`${SEVERITY_STYLES[f.severity] ?? ""} font-semibold text-xs`}>
  {f.severity}
</Badge>
```

**Boolean badge rendering** (DAR-specific, no exact analog in motion.tsx — define inline per UI-SPEC §Boolean Badge Rendering):
```typescript
// encryption_at_rest = true
<Badge className="bg-[hsl(142_71%_45%)] text-white text-xs">ENCRYPTED</Badge>
// encryption_at_rest = false
<Badge className="bg-[hsl(0_72%_51%)] text-white text-xs">UNENCRYPTED</Badge>
// null/missing
<span>—</span>
```
Full boolean badge table in UI-SPEC §Boolean Badge Rendering. These use hardcoded `hsl()` — matching the same established pattern as SEVERITY_STYLES.

**Page export and useScanData wiring** (motion.tsx lines 193-207 — adapt):
```typescript
export function MotionPage() {
  const { data, loading, error } = useScanData()

  const motionFindings: MotionFinding[] = useMemo(
    () => data?.motion_findings ?? [],
    [data],
  )
  const emailFindings = useMemo(
    () => motionFindings.filter(f => isEmailProtocol(f.protocol)),
    [motionFindings],
  )
  // ...
}
```
Adapt: export function `DataAtRestPage`, pull `data?.dar_findings ?? []`, split into `dbFindings`, `objFindings`, `k8sFindings`, `vaultFindings` by `f.category`.

**ScoreGauge wiring** (executive.tsx line 151):
```typescript
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
```
In `DataAtRestPage`: `<ScoreGauge score={data?.score.subscores.data_at_rest ?? 0} label="Data at Rest" size={120} />`. Do NOT pass `isOverall={true}`.

**Loading and error states** (motion.tsx lines 209-218 — copy verbatim):
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

**Page JSX structure** (motion.tsx lines 220-253 — adapt for 4 sections):
```typescript
return (
  <div className="space-y-6">
    <h1 style={{ fontSize: 20, fontWeight: 600 }}>Data at Rest</h1>

    {/* ScoreGauge — see wiring above */}

    <section aria-labelledby="dar-db-heading">
      <h2 id="dar-db-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
        Database Encryption
      </h2>
      {dbFindings.length === 0 ? (
        <EmptyStateCard message="No database endpoints scanned in this session — enable the DB scanner in your config or scan a database host." />
      ) : (
        <DatabaseTable findings={dbFindings} />
      )}
    </section>

    {/* repeat for Object Storage, Kubernetes, Vault */}
  </div>
)
```
Section heading IDs, h2 inline style, `mb-3` class, and `aria-labelledby` all copied from `motion.tsx` pattern (lines 224-237).

---

### `quirk/dashboard/api/schemas.py` — add `DarFinding` + `dar_findings` field (model, CRUD)

**Analog:** same file, `MotionFinding` class (lines 95-111) and `ScanLatestResponse` (lines 144-153)

**MotionFinding model pattern** (lines 95-111 — exact structure to mirror):
```python
# ---- Motion Findings (Phase 36 DASH-05) ----

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
    cert_not_after: Optional[str] = None    # ISO date string, not datetime
    plaintext_exposed: bool = False         # NON-OPTIONAL per D-02
    starttls_warning: bool = False          # NON-OPTIONAL per D-02
```

**New `DarFinding` class** — insert immediately after `MotionFinding` (after line 111), before `# ---- Roadmap ----`:
```python
# ---- DAR Findings (Phase 39 GAP-04) ----

class DarFinding(BaseModel):
    # Universal baseline (matches MotionFinding baseline fields)
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None

    # Discriminator (required — D-02)
    category: str                              # "database" | "object_storage" | "kubernetes" | "vault"

    # Database fields
    encryption_at_rest: Optional[bool] = None
    tls_in_transit: Optional[bool] = None

    # Object Storage fields
    encryption_mode: Optional[str] = None      # SSE-S3 / SSE-KMS / CMK / none
    kms_key_id: Optional[str] = None
    public_access: Optional[bool] = None
    versioning: Optional[bool] = None

    # Kubernetes fields
    namespace: Optional[str] = None
    secret_type: Optional[str] = None
    encryption_provider: Optional[str] = None

    # Vault fields
    seal_type: Optional[str] = None            # not probed — always null
    auto_unseal: Optional[bool] = None         # not probed — always null
    mount_type: Optional[str] = None           # transit / pki / auth
```

**ScanLatestResponse update** (lines 144-153 — add one field after `motion_findings` at line 153):
```python
class ScanLatestResponse(BaseModel):
    meta: ScanMeta
    score: ScoreData
    confidence: ConfidenceData
    findings: List[FindingItem]
    certificates: List[CertItem]
    cbom_components: List[CbomComponent]
    roadmap: RoadmapData
    identity_findings: List[IdentityFinding] = []
    motion_findings: List[MotionFinding] = []   # Phase 36 DASH-05
    dar_findings: List[DarFinding] = []         # Phase 39 GAP-04  ← ADD THIS LINE
```

**Import addition required:** Add `DarFinding` to the imports block in `quirk/dashboard/api/routes/scan.py` (same pattern as `MotionFinding` import at line 19).

---

### `quirk/dashboard/api/routes/scan.py` — add `_derive_dar_findings()` + wire into return (service, request-response)

**Analog:** same file, `_derive_motion_findings` (lines 337-411) and the `ScanLatestResponse` return statement (lines 714-729)

**Imports block** (lines 1-29 — add `DarFinding` alongside `MotionFinding`):
```python
from quirk.dashboard.api.schemas import (
    CbomComponent,
    CertItem,
    ConfidenceData,
    DarFinding,           # ADD — Phase 39 GAP-04
    FindingItem,
    IdentityFinding,
    MotionFinding,
    RoadmapData,
    RoadmapEdge,
    RoadmapNode,
    ScanLatestResponse,
    ScanMeta,
    ScanSession,
    ScoreData,
    SubScores,
)
```

**`_derive_motion_findings` function structure** (lines 337-411 — copy structure verbatim, adapt body):
```python
def _derive_motion_findings(endpoints) -> list[MotionFinding]:
    """Synthesize motion findings from email + broker CryptoEndpoints.
    ...
    """
    EMAIL_PROTOS = {...}
    BROKER_PLAIN = {...}
    MOTION_PROTOS = EMAIL_PROTOS | BROKER_PLAIN | BROKER_TLS

    results: list[MotionFinding] = []
    for ep in endpoints:
        proto = getattr(ep, "protocol", None) or ""
        if proto not in MOTION_PROTOS:
            continue
        # ... field extraction with getattr() guards ...
        results.append(MotionFinding(...))

    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return results
```
New function `_derive_dar_findings(endpoints) -> list[DarFinding]` mirrors this exactly:
- Protocol set constant: `DAR_PROTOCOLS = {"POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT"}`
- Per-protocol dispatch via `if proto in {...}` chain (see RESEARCH.md §Code Examples for full sketch)
- `getattr(ep, "dat_scan_json", None)` with `json.loads()` wrapped in `try/except` (guard against malformed JSON — V5 requirement)
- Skip endpoints where `ep.scan_error is not None` (RESEARCH.md Open Question 1 recommendation)
- Same severity sort at end

**`getattr` guard pattern** (lines 354-361 — replicate for every field access):
```python
proto = getattr(ep, "protocol", None) or ""
port = getattr(ep, "port", 0) or 0
tls_version = getattr(ep, "tls_version", None) or None
```

**Return statement update** (lines 714-729 — add `dar_findings` alongside `motion_findings`):
```python
return ScanLatestResponse(
    meta=ScanMeta(...),
    score=score,
    confidence=confidence,
    findings=findings,
    certificates=certificates,
    cbom_components=cbom_components,
    roadmap=roadmap,
    identity_findings=identity_findings,
    motion_findings=_derive_motion_findings(endpoints),   # Phase 36 DASH-05
    dar_findings=_derive_dar_findings(endpoints),         # Phase 39 GAP-04  ← ADD
)
```
**Placement:** Add `_derive_dar_findings` function immediately after `_derive_motion_findings` (after line 411), before `_derive_cbom` (line 414).

---

### `src/dashboard/src/types/api.ts` — add `DarFinding` interface + `dar_findings` field (model, transform)

**Analog:** same file, `MotionFinding` interface (lines 94-109) and `ScanLatestResponse` (lines 117-127)

**MotionFinding interface pattern** (lines 94-109 — exact structure to mirror):
```typescript
export interface MotionFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  tls_version?: string
  cipher_suite?: string
  cert_not_after?: string
  plaintext_exposed: boolean
  starttls_warning: boolean
}
```

**New `DarFinding` interface** — insert immediately after `MotionFinding` (after line 109), before `ScanSession` (line 111):
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

**ScanLatestResponse update** (lines 117-127 — add `dar_findings` field after `motion_findings`):
```typescript
export interface ScanLatestResponse {
  meta: ScanMeta
  score: ScoreData
  confidence: ConfidenceData
  findings: FindingItem[]
  certificates: CertItem[]
  cbom_components: CbomComponent[]
  roadmap: RoadmapData
  identity_findings: IdentityFinding[]
  motion_findings: MotionFinding[]
  dar_findings: DarFinding[]    // ← ADD — Phase 39 GAP-04
}
```

---

### `src/dashboard/src/App.tsx` — add route (config/routing, request-response)

**Analog:** same file, `MotionPage` import (line 10) and route (line 32)

**Import pattern** (lines 7-14 — add one line after `MotionPage` import):
```typescript
import { ExecutivePage } from "@/pages/executive"
import { FindingsPage } from "@/pages/findings"
import { IdentityPage } from "@/pages/identity"
import { MotionPage } from "@/pages/motion"
import { DataAtRestPage } from "@/pages/data-at-rest"    // ← ADD
import { CertificatesPage } from "@/pages/certificates"
import { CbomPage } from "@/pages/cbom"
import { RoadmapPage } from "@/pages/roadmap"
import { TrendsPage } from "@/pages/trends"
```

**Route block** (lines 28-38 — add one `<Route>` between `/motion` and `/certificates`):
```typescript
<Routes>
  <Route path="/" element={<ExecutivePage />} />
  <Route path="/findings" element={<FindingsPage />} />
  <Route path="/identity" element={<IdentityPage />} />
  <Route path="/motion" element={<MotionPage />} />
  <Route path="/data-at-rest" element={<DataAtRestPage />} />     {/* ← ADD */}
  <Route path="/certificates" element={<CertificatesPage />} />
  <Route path="/cbom" element={<CbomPage />} />
  <Route path="/roadmap" element={<RoadmapPage />} />
  <Route path="/trends" element={<TrendsPage />} />
  <Route path="/print" element={<PrintPage />} />
</Routes>
```
**Critical:** This change and the `sidebar.tsx` NAV_ITEMS change must land together (CONTEXT.md D-11, RESEARCH.md Pitfall 7).

---

### `src/dashboard/src/components/sidebar.tsx` — add NAV_ITEMS entry (component, request-response)

**Analog:** same file, existing `NAV_ITEMS` array (lines 20-29) and lucide-react import (lines 5-14)

**Current lucide-react import** (lines 5-14):
```typescript
import {
  LayoutDashboard,
  AlertTriangle,
  Shield,
  Database,
  GitBranch,
  Fingerprint,
  TrendingUp,
  Activity,
} from "lucide-react"
```
Add `HardDrive` to this import block.

**Current NAV_ITEMS array** (lines 20-29 — insert at index 4, between Motion and Certificates):
```typescript
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/motion", label: "Motion", Icon: Activity },
  { path: "/data-at-rest", label: "Data at Rest", Icon: HardDrive },   // ← ADD
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },
]
```

**Nav item render pattern** (lines 56-82 — unchanged, already handles any NAV_ITEMS entry):
```typescript
{NAV_ITEMS.map(({ path, label, Icon }) => {
  const isActive = location.pathname === path
  return (
    <Tooltip key={path}>
      <TooltipTrigger asChild>
        <Link
          to={path}
          aria-label={label}
          className={cn(
            "flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors",
            "min-h-[44px]",
            isActive
              ? "text-foreground border-b-2 lg:border-b-0 lg:border-l-2 border-accent bg-accent/10"
              : "text-muted-foreground hover:text-foreground hover:bg-accent/5",
          )}
        >
          <Icon className="h-5 w-5 flex-shrink-0" />
          <span className="hidden lg:block">{label}</span>
        </Link>
      </TooltipTrigger>
      <TooltipContent side="right" className="lg:hidden">
        {label}
      </TooltipContent>
    </Tooltip>
  )
})}
```
No changes needed to the render loop — only the `NAV_ITEMS` array and the lucide-react import change.

---

### `src/dashboard/src/components/gauges/ScoreGauge.tsx` — reuse only, no modification

**Analog:** `src/dashboard/src/pages/executive.tsx` line 151

**Props interface** (ScoreGauge.tsx lines 1-7 — read-only reference):
```typescript
interface ScoreGaugeProps {
  score: number          // 0-100
  label: string
  size?: number          // diameter in px; default 120 (sub-gauge), 160 (overall)
  strokeColor?: string   // CSS color string; defaults to score-based color
  isOverall?: boolean    // true = accent stroke, larger label
}
```

**Usage pattern** (executive.tsx line 151):
```typescript
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
```

**In DataAtRestPage** (access via `data?.score.subscores.data_at_rest ?? 0`):
```typescript
<ScoreGauge
  score={data?.score.subscores.data_at_rest ?? 0}
  label="Data at Rest"
  size={120}
/>
```
Do NOT modify `ScoreGauge.tsx`. Do NOT pass `isOverall={true}` — reserved for Executive tab's overall gauge (RESEARCH.md Pitfall 8).

---

### `tests/test_dar_dashboard.py` — new test file (test, CRUD)

**Analog:** `tests/test_dashboard_api.py` lines 97-135 — `_ep` SimpleNamespace fixture factory + `_derive_motion_findings` unit tests

**Fixture factory pattern** (test_dashboard_api.py lines 100-104 — copy verbatim, extend fields):
```python
from types import SimpleNamespace

def _ep(**kw):
    defaults = dict(host="example.com", port=0, protocol="", tls_version=None,
                    cipher_suite=None, cert_not_after=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)
```
Extend `defaults` with DAR-relevant fields: `service_detail=None`, `dat_scan_json=None`, `scan_error=None`, `severity="INFO"`.

**Unit test pattern** (test_dashboard_api.py lines 107-135):
```python
def test_derive_motion_findings_plaintext():
    """DASH-05: KAFKA-PLAIN endpoint -> HIGH severity, plaintext_exposed=True."""
    from quirk.dashboard.api.routes.scan import _derive_motion_findings
    out = _derive_motion_findings([_ep(host="kafka.test", port=9092, protocol="KAFKA-PLAIN")])
    assert len(out) == 1
    assert out[0].severity == "HIGH"
    assert out[0].plaintext_exposed is True
```
Replicate pattern for each DAR test case — single-function import, fixture list, assert on result fields.

**Integration test pattern** (test_dashboard_api.py lines 77-84 — `dashboard_client` fixture):
```python
def test_motion_findings_endpoint(dashboard_client):
    """DASH-05: GET /api/scan/latest includes motion_findings list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "motion_findings" in data
        assert isinstance(data["motion_findings"], list)
```
Replicate for `dar_findings` key check and empty-list guarantee.

**Full test list to implement** (from RESEARCH.md §Validation Architecture):
- `test_derive_dar_findings_db` — POSTGRESQL fixture → `DarFinding` with `category="database"`
- `test_derive_dar_db_postgresql` — `service_detail="PostgreSQL/ssl-off"` → `encryption_at_rest=False, tls_in_transit=False`
- `test_derive_dar_s3` — `dat_scan_json='{"service_detail":"S3/sse-s3"}'` → `encryption_mode="SSE-S3"`
- `test_derive_dar_k8s_dispatch` — namespace shape vs. cluster-encryption shape dispatch
- `test_derive_dar_vault_dispatch` — transit/PKI/auth key-presence discrimination
- `test_api_dar_findings_key` — API contract: `dar_findings` key present
- `test_api_dar_findings_empty` — empty list (not absent) when no DAR endpoints
- `test_derive_dar_scan_error_excluded` — `scan_error` set → endpoint excluded from results

---

## Shared Patterns

### getattr Guards (Python projection functions)
**Source:** `quirk/dashboard/api/routes/scan.py` lines 354-361
**Apply to:** all field reads inside `_derive_dar_findings()` and sub-dispatch helpers
```python
proto = getattr(ep, "protocol", None) or ""
port = getattr(ep, "port", 0) or 0
service_detail = getattr(ep, "service_detail", None) or ""
dat_raw = getattr(ep, "dat_scan_json", None)
```
Use `getattr(ep, field, default)` for every CryptoEndpoint field access — never direct attribute access. This protects against test SimpleNamespace fixtures and schema evolution.

### JSON parse guard (Python)
**Source:** RESEARCH.md §Security Domain (V5 requirement)
**Apply to:** every `dat_scan_json` read in `_derive_dar_findings()`
```python
dat: dict = {}
if dat_raw:
    try:
        dat = json.loads(dat_raw)
    except Exception:
        dat = {}
```
Malformed JSON in one endpoint must not abort projection of all others.

### Severity sort (Python)
**Source:** `quirk/dashboard/api/routes/scan.py` lines 409-411
**Apply to:** end of `_derive_dar_findings()`
```python
_severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
results.sort(key=lambda f: _severity_order.get(f.severity, 99))
return results
```

### Severity sort (TypeScript)
**Source:** `src/dashboard/src/pages/motion.tsx` lines 48-52
**Apply to:** every DAR table component's row sort
```typescript
const rows = [...findings].sort(
  (a, b) =>
    (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 99) -
    (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 99),
)
```

### CSS variable color rule
**Source:** `src/dashboard/src/components/sidebar.tsx` lines 1-3 (D-13 audit comment)
**Apply to:** all new TSX in Phase 39
All non-severity colors must use `hsl(var(--token))` CSS variable form. Exceptions: `SEVERITY_STYLES` hardcoded `hsl()` values and boolean badge `hsl()` values — both are the established project pattern from `motion.tsx` and are intentionally kept hardcoded.

### Null rendering
**Source:** UI-SPEC §Table Column Specifications
**Apply to:** all optional fields in DAR table cells
Render `null` / `undefined` / missing values as `—` (em dash, plain text, no badge). Example: `{f.seal_type ?? "—"}`, `{f.namespace ?? "—"}`.

---

## No Analog Found

All 8 files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `src/dashboard/src/`, `quirk/dashboard/api/`, `tests/`
**Files scanned:** 10 source files read directly
**Pattern extraction date:** 2026-04-29

**Key pitfall cross-references** (from RESEARCH.md — planner must document in PLAN.md):
- Pitfall 1: DB connectors write no `dat_scan_json` — parse `service_detail` only for POSTGRESQL/MYSQL/RDS
- Pitfall 2: Three `dat_scan_json` shapes under `KUBERNETES` — discriminate by `"namespace" in dat`
- Pitfall 3: Three `dat_scan_json` shapes under `VAULT` — discriminate by `"key_name"` / `"mount_point"` / `"auth_path"`
- Pitfall 4: `seal_type` / `auto_unseal` not scanned — leave null always
- Pitfall 7: `App.tsx` + `sidebar.tsx` must change in lockstep (same plan task)
- Pitfall 8: Do not use `isOverall={true}` on `ScoreGauge` for the DAR tab gauge
