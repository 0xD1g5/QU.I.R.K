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
import type { IdentityFinding } from "@/types/api"
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
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}

const PROTOCOLS = ["KERBEROS", "SAML", "DNSSEC"] as const

function getProtocolStatus(findings: IdentityFinding[], protocol: string) {
  const pf = findings.filter((f) => f.protocol === protocol)
  if (pf.length === 0) return { count: 0, worst: null, label: "Not Scanned" }
  const hasCritical = pf.some((f) => f.severity === "CRITICAL")
  const hasHigh = pf.some((f) => f.severity === "HIGH")
  return {
    count: pf.length,
    worst: hasCritical ? "CRITICAL" : hasHigh ? "HIGH" : "MEDIUM",
    label: hasCritical ? "Critical" : hasHigh ? "At Risk" : "Clean",
  }
}

const STATUS_BADGE_STYLES: Record<string, string> = {
  "Critical": "bg-[hsl(0_72%_51%)] text-white",
  "At Risk": "bg-[hsl(24_95%_53%)] text-white",
  "Clean": "bg-[hsl(142_71%_45%)] text-white",
  "Not Scanned": "bg-[hsl(240_5%_46%)] text-white",
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

  const columns: ColumnDef<IdentityFinding>[] = [
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
  ]

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
          const status = getProtocolStatus(identityFindings, proto)
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
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Identity findings table (D-11) */}
      {identityFindings.length === 0 ? (
        <EmptyStateCard message="No identity protocol findings in this scan — enable Kerberos, SAML, or DNSSEC scanners in config.yaml and run a scan." />
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
          <div className="flex items-center justify-between text-sm text-muted-foreground mt-2">
            <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</Button>
              <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</Button>
            </div>
          </div>
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
