import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import { useHardwareDrift } from "@/hooks/useHardwareDrift"
import { useVendorPqcTrends } from "@/hooks/useVendorPqcTrends"
import type { HardwareFinding } from "@/types/api"
import { modbusLabel, bacnetLabel, bridgeLabel, snmpLabel } from "./hardware-badge-labels"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { formatDateOnly } from "@/lib/datetime"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { LifecycleEventList } from "@/components/LifecycleEventList"
import { VendorTrendList } from "@/components/VendorTrendList"

// Tier badge colors — Tier 1 red, Tier 2 orange, Tier 3 blue, N/A gray
const TIER_STYLES: Record<string, string> = {
  "Tier 1":   "bg-[hsl(var(--status-critical))] text-white",
  "Tier 2":   "bg-[hsl(var(--risk-badge-high))] text-white",
  "Tier 3":   "bg-[hsl(var(--chart-tls))] text-black",
  "Tier N/A": "bg-[hsl(var(--status-neutral))] text-white",
}

// PQC status badge colors
const PQC_STYLES: Record<string, string> = {
  "supported":     "bg-[hsl(var(--qs-node-safe))] text-white",
  "partial":       "bg-[hsl(var(--status-warning))] text-black",
  "unsupported":   "bg-[hsl(var(--status-critical))] text-white",
  "VENDOR-SILENT": "bg-[hsl(var(--status-neutral))] text-white",
}

// Confidence badge colors
const CONF_STYLES: Record<string, string> = {
  "high":    "bg-[hsl(var(--qs-node-safe))] text-white",
  "medium":  "bg-[hsl(var(--status-warning))] text-black",
  "low":     "bg-[hsl(var(--risk-badge-high))] text-white",
  "unknown": "bg-[hsl(var(--status-neutral))] text-white",
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
  "v3 auth+priv":      "bg-[hsl(var(--qs-node-safe))] text-white",
  "v3 noAuthNoPriv":   "bg-[hsl(var(--status-warning))] text-black",
  "v2c":               "bg-[hsl(var(--status-neutral))] text-white",
  "v3 failed → v2c":   "bg-[hsl(var(--status-critical))] text-white",
  "v3 failed → none":  "bg-[hsl(var(--status-critical))] text-white",
  "No SNMP":           "bg-[hsl(var(--status-neutral))] text-white",
}

const SNMP_FAILED_TOOLTIP =
  "SNMPv3 was configured for this host but authentication failed; the scanner fell back to a lower tier. Verify credentials."

// Phase 140 BRIDGE-03 — bridge-status badge colors. Blue "SNMP-confirmed" must
// NEVER reuse the green success hue (hsl(var(--qs-node-safe))) — green implies a clean
// bill of health, which would misrepresent an advisory-only, topology-inferred
// confirmation. Amber "Partial (assumed)" matches the existing PQC_STYLES.partial
// / SNMP_STYLES."v3 noAuthNoPriv" amber convention.
const BRIDGE_STYLES: Record<string, string> = {
  "Partial (assumed)": "bg-[hsl(var(--status-warning))] text-black",
  "SNMP-confirmed":    "bg-[hsl(var(--chart-tls))] text-black",
}

// Verbatim Pitfall-3 caveat text (UI-SPEC Copywriting Contract) — must appear
// as both the badge tooltip and the persistent inline banner sentence below
// the table whenever any row is upstream_mitigated.
const BRIDGE_CAVEAT =
  "Based on SNMP-derived network-path evidence; not independently confirmed by traffic inspection."

const BRIDGE_CONFIRMED_TOOLTIP =
  `SNMP-confirmed: gateway ARP-table evidence shows this device is reachable behind a PQC-capable gateway. ${BRIDGE_CAVEAT}`

// Phase 141 OTICS-05 — Modbus/TCP + BACnet/IP fingerprint badge colors.
// Modbus (blue) and BACnet (purple) carry distinct hues per D-12 so the two
// protocol sources are visually distinguishable at a glance, and neither
// collides with the existing green/amber/gray badge hues. aborted_anomalous_response
// (red) must never look like no_response/no_match (gray) — D-13.
const MODBUS_STYLES: Record<string, string> = {
  "Modbus":         "bg-[hsl(var(--badge-modbus))] text-white",
  "No response":    "bg-[hsl(var(--status-neutral))] text-white",
  "No match":       "bg-[hsl(var(--status-neutral))] text-white",
  "Probe aborted":  "bg-[hsl(var(--status-critical))] text-white",
}

const BACNET_STYLES: Record<string, string> = {
  "BACnet":         "bg-[hsl(var(--badge-bacnet))] text-white",
  "No response":    "bg-[hsl(var(--status-neutral))] text-white",
  "No match":       "bg-[hsl(var(--status-neutral))] text-white",
  "Probe aborted":  "bg-[hsl(var(--status-critical))] text-white",
}

const MODBUS_ABORT_TOOLTIP =
  "Modbus probe aborted — anomalous response. The device returned a malformed frame, reset the connection, or timed out; QU.I.R.K. stopped probing this host per its one-strike safety policy. Worth a closer manual look."

const BACNET_ABORT_TOOLTIP =
  "BACnet probe aborted — anomalous response. The device returned a malformed frame, reset the connection, or timed out; QU.I.R.K. stopped probing this host per its one-strike safety policy. Worth a closer manual look."

// Phase 142 CVE-01/D-14 — single neutral CVE-count badge color, regardless of
// match count or severity. NEVER green (hsl(var(--qs-node-safe))) or a red severity
// hue — the badge is advisory-only, not a severity signal (T-142-CVE01).
// Amber, not blue: the original hsl(213...) sat in the same hue family as the
// per-CVE NVD links rendered directly beneath it, so the badge didn't read as
// a distinct element (human UAT, 142-06).
const CVE_BADGE_STYLE = "bg-[hsl(var(--status-warning))] text-black"

export function HardwarePage() {
  const { data, loading, error } = useScanData()
  const { data: drift, loading: driftLoading, error: driftError } = useHardwareDrift()
  const { data: vendorTrends, loading: vendorTrendsLoading, error: vendorTrendsError } = useVendorPqcTrends()

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
                  <TableHead scope="col" className="text-xs font-semibold">Modbus</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">BACnet</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">Bridge Status</TableHead>
                  <TableHead scope="col" className="text-xs font-semibold">CVEs</TableHead>
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
                      {/* eol_date is date-only, not an instant (schemas.py Optional[str];
                          SCORE-03 Pitfall 1) — dispositioned out of this phase's backend fix. */}
                      {f.eol_date ? formatDateOnly(f.eol_date) : "—"}
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
                        const label = modbusLabel(f)
                        if (label === "—") {
                          return <span className="text-muted-foreground">—</span>
                        }
                        const isIdentified = label === "Modbus"
                        const title = label === "Probe aborted"
                          ? MODBUS_ABORT_TOOLTIP
                          : (isIdentified && (f.modbus_vendor || f.modbus_model))
                            ? `${f.modbus_vendor ?? ""} ${f.modbus_model ?? ""}`.trim()
                            : undefined
                        return (
                          <Badge
                            className={`${MODBUS_STYLES[label] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}
                            title={title}
                          >
                            {label}
                          </Badge>
                        )
                      })()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {(() => {
                        const label = bacnetLabel(f)
                        if (label === "—") {
                          return <span className="text-muted-foreground">—</span>
                        }
                        const isIdentified = label === "BACnet"
                        const title = label === "Probe aborted"
                          ? BACNET_ABORT_TOOLTIP
                          : (isIdentified && (f.bacnet_vendor || f.bacnet_model))
                            ? `${f.bacnet_vendor ?? ""} ${f.bacnet_model ?? ""}`.trim()
                            : undefined
                        return (
                          <Badge
                            className={`${BACNET_STYLES[label] ?? "bg-muted text-muted-foreground"} font-semibold text-xs`}
                            title={title}
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
                    <TableCell className="text-sm">
                      {f.cve_matches?.length ? (
                        <Collapsible>
                          <CollapsibleTrigger asChild>
                            <button type="button" className="cursor-pointer">
                              <Badge className={`${CVE_BADGE_STYLE} font-semibold text-xs`}>
                                {f.cve_matches.length} CVEs
                              </Badge>
                            </button>
                          </CollapsibleTrigger>
                          <CollapsibleContent>
                            <ul className="mt-1 space-y-0.5 text-xs">
                              {f.cve_matches.map((m) => (
                                <li key={m.cve_id}>
                                  <a
                                    href={m.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-600 dark:text-blue-400 underline"
                                  >
                                    {m.cve_id}
                                  </a>
                                  {f.cve_confidence ? ` (${f.cve_confidence} confidence)` : ""}
                                </li>
                              ))}
                            </ul>
                          </CollapsibleContent>
                        </Collapsible>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <LifecycleEventList
        events={drift?.latest_events ?? []}
        historicalEvents={drift?.historical_events ?? []}
        historicalTruncated={drift?.historical_truncated ?? false}
        hasPriorScan={drift?.has_prior_scan ?? false}
        lastScanDate={drift?.latest_scan_at ?? null}
        loading={driftLoading}
        error={driftError}
      />

      <VendorTrendList
        events={vendorTrends?.events ?? []}
        truncated={vendorTrends?.truncated ?? false}
        loading={vendorTrendsLoading}
        error={vendorTrendsError}
      />
    </div>
  )
}
