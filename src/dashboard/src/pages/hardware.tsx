import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { HardwareFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { EmptyStateCard } from "@/components/EmptyStateCard"

// Tier badge colors — Tier 1 red, Tier 2 orange, Tier 3 blue, N/A gray
const TIER_STYLES: Record<string, string> = {
  "Tier 1":   "bg-[hsl(0_72%_51%)] text-white",
  "Tier 2":   "bg-[hsl(24_95%_53%)] text-white",
  "Tier 3":   "bg-[hsl(213_94%_68%)] text-black",
  "Tier N/A": "bg-[hsl(240_5%_46%)] text-white",
}

// PQC status badge colors
const PQC_STYLES: Record<string, string> = {
  "supported":     "bg-[hsl(142_71%_45%)] text-white",
  "partial":       "bg-[hsl(38_92%_50%)] text-black",
  "unsupported":   "bg-[hsl(0_72%_51%)] text-white",
  "VENDOR-SILENT": "bg-[hsl(240_5%_46%)] text-white",
}

// Confidence badge colors
const CONF_STYLES: Record<string, string> = {
  "high":    "bg-[hsl(142_71%_45%)] text-white",
  "medium":  "bg-[hsl(38_92%_50%)] text-black",
  "low":     "bg-[hsl(24_95%_53%)] text-white",
  "unknown": "bg-[hsl(240_5%_46%)] text-white",
}

const TIER_ORDER: Record<string, number> = {
  "Tier 1":   0,
  "Tier 2":   1,
  "Tier 3":   2,
  "Tier N/A": 3,
}

const METHOD_LABEL: Record<string, string> = {
  "ssh_banner": "SSH Banner",
  "http_mgmt":  "HTTP Mgmt",
}

// Phase 139 SNMPV3-02 — SNMP version/security-level badge colors.
// noAuthNoPriv (amber) must never render identically to auth+priv (green) — D-04.
const SNMP_STYLES: Record<string, string> = {
  "v3 auth+priv":      "bg-[hsl(142_71%_45%)] text-white",
  "v3 noAuthNoPriv":   "bg-[hsl(38_92%_50%)] text-black",
  "v2c":               "bg-[hsl(240_5%_46%)] text-white",
  "v3 failed → v2c":   "bg-[hsl(0_72%_51%)] text-white",
  "v3 failed → none":  "bg-[hsl(0_72%_51%)] text-white",
  "No SNMP":           "bg-[hsl(240_5%_46%)] text-white",
}

const SNMP_FAILED_TOOLTIP =
  "SNMPv3 was configured for this host but authentication failed; the scanner fell back to a lower tier. Verify credentials."

// Phase 140 BRIDGE-03 — bridge-status badge colors. Blue "SNMP-confirmed" must
// NEVER reuse the green success hue (hsl(142_71%_45%)) — green implies a clean
// bill of health, which would misrepresent an advisory-only, topology-inferred
// confirmation. Amber "Partial (assumed)" matches the existing PQC_STYLES.partial
// / SNMP_STYLES."v3 noAuthNoPriv" amber convention.
const BRIDGE_STYLES: Record<string, string> = {
  "Partial (assumed)": "bg-[hsl(38_92%_50%)] text-black",
  "SNMP-confirmed":    "bg-[hsl(213_94%_68%)] text-black",
}

// Verbatim Pitfall-3 caveat text (UI-SPEC Copywriting Contract) — must appear
// as both the badge tooltip and the persistent inline banner sentence below
// the table whenever any row is upstream_mitigated.
const BRIDGE_CAVEAT =
  "Based on SNMP-derived network-path evidence; not independently confirmed by traffic inspection."

const BRIDGE_CONFIRMED_TOOLTIP =
  `SNMP-confirmed: gateway ARP-table evidence shows this device is reachable behind a PQC-capable gateway. ${BRIDGE_CAVEAT}`

// Maps the raw wire bridge_status to the verbatim UI-SPEC label. Returns ""
// for null/absent (not a detected bridge pair) — the table cell renders a
// muted em-dash for that case, matching the existing SNMP-column convention.
function bridgeLabel(f: HardwareFinding): string {
  switch (f.bridge_status) {
    case "upstream_mitigated":
      return "SNMP-confirmed"
    case "partial_only":
      return "Partial (assumed)"
    default:
      return ""
  }
}

// Maps the raw wire snmp_version to the verbatim UI-SPEC label. Returns "—"
// (never attempted) for null/undefined; mirrors quirk/reports/html_renderer.py
// and docx_renderer.py's `_snmp_badge_label` raw-fallback so an unmapped state
// (e.g. "v3-protocol-mismatch") renders its raw value rather than going blank.
function snmpLabel(f: HardwareFinding): string {
  const raw = f.snmp_version
  if (!raw) return "—"
  switch (raw) {
    case "v3 auth+priv":
      return "v3 auth+priv"
    case "v3 noAuthNoPriv":
      return "v3 noAuthNoPriv"
    case "v2c":
      return "v2c"
    case "v3-failed-fell-back":
      return "v3 failed → v2c"
    case "none":
      return "No SNMP"
    default:
      return raw
  }
}

export function HardwarePage() {
  const { data, loading, error } = useScanData()

  const sorted: HardwareFinding[] = useMemo(() => {
    const findings = data?.hardware_findings ?? []
    return [...findings].sort(
      (a, b) =>
        (TIER_ORDER[a.remediation_tier] ?? 99) - (TIER_ORDER[b.remediation_tier] ?? 99) ||
        a.vendor.localeCompare(b.vendor),
    )
  }, [data])

  // Phase 140 BRIDGE-03 — drives the persistent inline caveat banner (D-06:
  // caveat must not be tooltip-only).
  const hasBridgeConfirmed = useMemo(
    () => sorted.some((f) => f.bridge_status === "upstream_mitigated"),
    [sorted],
  )

  if (loading) {
    return (
      <div role="status" aria-label="Loading hardware findings" className="space-y-6">
        <span className="sr-only">Loading...</span>
        {Array.from({ length: 3 }).map((_, s) => (
          <div key={s} className="space-y-2">
            <Skeleton className="h-5 w-48" />
            {Array.from({ length: 4 }).map((_, r) => (
              <Skeleton key={r} className="h-10 w-full" />
            ))}
          </div>
        ))}
      </div>
    )
  }

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Hardware Compatibility</h1>
        <p className="text-muted-foreground text-sm mt-1">
          PQC readiness of identified network devices
        </p>
      </div>

      <div
        role="note"
        className="rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-700 dark:text-yellow-300"
      >
        Hardware findings are advisory-only and do not affect the readiness score.
      </div>

      {hasBridgeConfirmed && (
        <div
          role="note"
          className="rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-700 dark:text-yellow-300"
        >
          {BRIDGE_CAVEAT}
        </div>
      )}

      {sorted.length === 0 ? (
        <EmptyStateCard message="No hardware devices detected. Run a scan with SSH targets to fingerprint hardware." />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col" className="text-xs font-semibold">Tier</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Vendor</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Model</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Host:Port</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">PQC Status</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Confidence</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">EOL Date</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Method</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">SNMP</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Bridge Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((f, i) => (
                  <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                    <TableCell className="text-sm">
                      <Badge className={`${TIER_STYLES[f.remediation_tier] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}>
                        {f.remediation_tier}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{f.vendor}</TableCell>
                    <TableCell className="text-sm">{f.model ?? "Unknown"}</TableCell>
                    <TableCell className="text-sm font-mono">{f.host}:{f.port}</TableCell>
                    <TableCell className="text-sm">
                      <Badge className={`${PQC_STYLES[f.pqc_status] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}>
                        {f.pqc_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      <Badge className={`${CONF_STYLES[f.confidence] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}>
                        {f.confidence}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {f.eol_date
                        ? new Date(f.eol_date).toLocaleDateString("en-US", { dateStyle: "medium" })
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {METHOD_LABEL[f.fingerprint_method] ?? f.fingerprint_method}
                    </TableCell>
                    <TableCell className="text-sm">
                      {(() => {
                        const label = snmpLabel(f)
                        if (label === "—") {
                          return <span className="text-muted-foreground">—</span>
                        }
                        return (
                          <Badge
                            className={`${SNMP_STYLES[label] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}
                            title={label === "v3 failed → v2c" || label === "v3 failed → none" ? SNMP_FAILED_TOOLTIP : undefined}
                          >
                            {label}
                          </Badge>
                        )
                      })()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {(() => {
                        const label = bridgeLabel(f)
                        if (!label) {
                          return <span className="text-muted-foreground">—</span>
                        }
                        return (
                          <Badge
                            className={`${BRIDGE_STYLES[label] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}
                            title={label === "SNMP-confirmed" ? BRIDGE_CONFIRMED_TOOLTIP : BRIDGE_CAVEAT}
                          >
                            {label}
                          </Badge>
                        )
                      })()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
