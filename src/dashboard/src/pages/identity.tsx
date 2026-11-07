import { useState, useMemo } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table"
import { useScanData } from "@/hooks/useScanData"
import { emptyStateFor, humanSkipReason, isPhaseError } from "@/lib/coverage-reason"
import type { IdentityFinding, ScanCoverageResponse } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { IdentitySkeleton } from "./identity.skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(var(--status-critical))] text-white",
  HIGH: "bg-[hsl(var(--risk-badge-high))] text-[hsl(var(--risk-badge-high-foreground))]",
  MEDIUM: "bg-[hsl(var(--status-warning))] text-[hsl(var(--status-warning-foreground))]",
  LOW: "bg-[hsl(var(--chart-tls))] text-[hsl(var(--chart-tls-foreground))]",
  INFO: "bg-[hsl(var(--status-neutral))] text-white",
}

const PROTOCOLS = ["KERBEROS", "SAML", "DNSSEC"] as const

// C-WR-08: the scan_phase_records row behind each protocol card.
const PROTOCOL_PHASES: Record<string, string> = {
  KERBEROS: "kerberos_scanning",
  SAML: "saml_scanning",
  DNSSEC: "dnssec_scanning",
}

/**
 * Card status for a protocol with no findings, read from the same coverage
 * record as the empty state (C-WR-08): Ran for a phase that ran, Skipped /
 * Failed with the recorded reason, Not Scanned only for disabled-by-config or
 * no record at all.
 */
function noFindingStatus(coverage: ScanCoverageResponse | null | undefined, protocol: string) {
  const notScanned = { count: 0, worst: null, label: "Not Scanned", note: null as string | null }
  if (!coverage || !coverage.recorded) return notScanned
  const p = coverage.phases.find((ph) => ph.phase_name === PROTOCOL_PHASES[protocol])
  if (!p || (p.status !== "ran" && p.reason === "disabled-by-config")) return notScanned
  if (p.status === "ran") return { ...notScanned, label: "Ran" }
  if (isPhaseError(p)) return { ...notScanned, label: "Failed", note: "the scanner stopped with an error" }
  return {
    ...notScanned,
    label: "Skipped",
    note: p.reason === "failed" ? "no target answered" : humanSkipReason(p.reason),
  }
}

function getProtocolStatus(
  findings: IdentityFinding[],
  protocol: string,
  coverage?: ScanCoverageResponse | null,
) {
  const pf = findings.filter((f) => f.protocol === protocol)
  if (pf.length === 0) return noFindingStatus(coverage, protocol)
  const hasCritical = pf.some((f) => f.severity === "CRITICAL")
  const hasHigh = pf.some((f) => f.severity === "HIGH")
  const hasMedium = pf.some((f) => f.severity === "MEDIUM")
  return {
    count: pf.length,
    worst: hasCritical ? "CRITICAL" : hasHigh ? "HIGH" : hasMedium ? "MEDIUM" : "LOW",
    label: hasCritical ? "Critical" : hasHigh ? "At Risk" : "Clean",
    note: null as string | null,
  }
}

const STATUS_BADGE_STYLES: Record<string, string> = {
  "Critical": "bg-[hsl(var(--status-critical))] text-white",
  "At Risk": "bg-[hsl(var(--risk-badge-high))] text-[hsl(var(--risk-badge-high-foreground))]",
  "Clean": "bg-[hsl(var(--qs-node-safe))] text-[hsl(var(--qs-node-safe-foreground))]",
  "Not Scanned": "bg-[hsl(var(--status-neutral))] text-white",
  "Ran": "bg-[hsl(var(--status-neutral))] text-white",
  "Skipped": "bg-[hsl(var(--status-neutral))] text-white",
  "Failed": "bg-[hsl(var(--status-critical))] text-white",
}

const PROTOCOL_LABELS: Record<string, string> = {
  KERBEROS: "Kerberos",
  SAML: "SAML/OIDC",
  DNSSEC: "DNSSEC",
}

export function IdentityPage() {
  const { data, loading, error } = useScanData()
  const [sorting, setSorting] = useState<SortingState>([{ id: "severity", desc: false }])
  const [globalFilter, setGlobalFilter] = useState("")
  const [selectedFinding, setSelectedFinding] = useState<IdentityFinding | null>(null)

  const identityFindings = useMemo(() => {
    return data?.identity_findings ?? []
  }, [data])

  // D-25 (IN-03): memoize columns for stable reference identity across renders
  // (TanStack Table relies on referential stability of the columns array).
  // Cells only close over `row.original` / module-level constants — empty deps.
  const columns = useMemo<ColumnDef<IdentityFinding>[]>(() => [
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => (
        <Badge className={`${SEVERITY_STYLES[row.original.severity] ?? ""} font-semibold text-xs`}>
          {row.original.severity}
        </Badge>
      ),
    },
    { accessorKey: "protocol", header: "Protocol" },
    { accessorKey: "host", header: "Host" },
    { accessorKey: "port", header: "Port" },
    { accessorKey: "title", header: "Title" },
    { accessorKey: "algorithm", header: "Algorithm" },
  ], [])

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table returns non-memoizable functions; known React Compiler limitation
  const table = useReactTable({
    data: identityFindings,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  })

  if (loading) return <IdentitySkeleton />
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Identity Protocols</h1>

      {/* Per-protocol summary cards (D-10) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PROTOCOLS.map((proto) => {
          const status = getProtocolStatus(identityFindings, proto, data?.coverage)
          return (
            <Card key={proto}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {PROTOCOL_LABELS[proto]}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">{status.count}</span>
                  <Badge className={`${STATUS_BADGE_STYLES[status.label] ?? ""} text-xs`}>
                    {status.label}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {status.count === 1 ? "finding" : "findings"}
                </p>
                {status.note && (
                  <p className="text-xs text-muted-foreground mt-1">{status.note}</p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Identity findings table (D-11) */}
      {identityFindings.length === 0 ? (
        <EmptyStateCard emptyFor="scan-latest" message={emptyStateFor(data?.coverage, ["kerberos_scanning", "saml_scanning", "dnssec_scanning"], "No identity protocol findings in this scan — enable Kerberos, SAML, or DNSSEC scanners in config.yaml and run a scan.")} />
      ) : (
        <>
          <div className="flex gap-3 items-center">
            <Input
              placeholder="Search identity findings..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="max-w-xs"
              aria-label="Search identity findings"
            />
          </div>

          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((h) => (
                      <TableHead
                        key={h.id}
                        scope="col"
                        aria-sort={h.column.getIsSorted() === "asc" ? "ascending" : h.column.getIsSorted() === "desc" ? "descending" : "none"}
                        className="cursor-pointer select-none text-xs font-semibold"
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    className="cursor-pointer hover:bg-accent/5"
                    onClick={() => setSelectedFinding(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="text-sm py-2">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination controls */}
          {table.getPageCount() > 1 && (
            <div className="flex items-center justify-between text-sm text-muted-foreground mt-2">
              <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</Button>
                <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Finding detail Sheet (same pattern as findings.tsx) */}
      <Sheet open={!!selectedFinding} onOpenChange={(open) => !open && setSelectedFinding(null)}>
        <SheetContent style={{ width: 480 }}>
          {selectedFinding && (
            <>
              <SheetHeader>
                <SheetTitle className="text-base">{selectedFinding.title}</SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex gap-2 items-center">
                  <Badge className={`${SEVERITY_STYLES[selectedFinding.severity] ?? ""} text-xs`}>
                    {selectedFinding.severity}
                  </Badge>
                  <span className="text-muted-foreground">{selectedFinding.host}:{selectedFinding.port}</span>
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Protocol</p>
                  <p className="text-foreground">{selectedFinding.protocol}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Algorithm</p>
                  <p className="text-foreground font-mono">{selectedFinding.algorithm}</p>
                </div>
                {selectedFinding.description && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Description</p>
                    <p className="text-foreground">{selectedFinding.description}</p>
                  </div>
                )}
                {selectedFinding.remediation && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Remediation</p>
                    <p className="text-foreground">{selectedFinding.remediation}</p>
                  </div>
                )}
                {selectedFinding.quantum_risk && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Quantum Risk</p>
                    <p className="text-foreground">{selectedFinding.quantum_risk}</p>
                  </div>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
