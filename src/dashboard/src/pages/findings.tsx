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
import type { FindingItem } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { FindingsSkeleton } from "./findings.skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}

export function FindingsPage() {
  const { data, loading, error } = useScanData()
  const [sorting, setSorting] = useState<SortingState>([{ id: "severity", desc: false }])
  const [globalFilter, setGlobalFilter] = useState("")
  const [severityFilter, setSeverityFilter] = useState("ALL")
  const [protocolFilter, setProtocolFilter] = useState("ALL")
  const [segmentFilter, setSegmentFilter] = useState("all")
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null)

  // Derive sorted, deduped list of segments from findings
  const distinctSegments = useMemo(() => {
    if (!data?.findings) return []
    const segs = data.findings
      .map((f) => f.segment)
      .filter((s): s is string => typeof s === "string" && s.length > 0)
    return Array.from(new Set(segs)).sort()
  }, [data])

  const findings = useMemo(() => {
    if (!data?.findings) return []
    let filtered = data.findings
    if (severityFilter !== "ALL") {
      filtered = filtered.filter((f) => f.severity === severityFilter)
    }
    if (protocolFilter !== "ALL") {
      filtered = filtered.filter((f) => f.protocol === protocolFilter)
    }
    if (segmentFilter !== "all") {
      filtered = filtered.filter((f) => f.segment === segmentFilter)
    }
    return filtered
  }, [data, severityFilter, protocolFilter, segmentFilter])

  // D-25 (IN-03): memoize columns for stable reference identity across renders
  // (TanStack Table relies on referential stability of the columns array).
  // Cells only close over `row.original` / module-level constants — empty deps.
  const columns = useMemo<ColumnDef<FindingItem>[]>(() => [
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => (
        <Badge className={`${SEVERITY_STYLES[row.original.severity] ?? ""} font-semibold text-xs`}>
          {row.original.severity}
        </Badge>
      ),
    },
    { accessorKey: "host", header: "Host" },
    { accessorKey: "port", header: "Port" },
    { accessorKey: "title", header: "Title" },
    { accessorKey: "protocol", header: "Protocol" },
    {
      accessorKey: "quantum_risk",
      header: "Quantum Risk",
      cell: ({ row }) => {
        const qr = row.original.quantum_risk
        if (!qr) return <span className="text-muted-foreground">—</span>
        const colors: Record<string, string> = {
          "Vulnerable": "bg-[hsl(0_72%_51%)] text-white",
          "At Risk": "bg-[hsl(38_92%_50%)] text-black",
          "Safe": "bg-[hsl(142_71%_30%)] text-white",
        }
        return <Badge className={`${colors[qr] ?? ""} text-xs`}>{qr}</Badge>
      },
    },
    { accessorKey: "source", header: "Source" },
  ], [])

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table returns non-memoizable functions; known React Compiler limitation
  const table = useReactTable({
    data: findings,
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

  if (loading) return <FindingsSkeleton />
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  if (!data?.findings?.length) {
    return (
      <EmptyStateCard message="No findings recorded in this scan — run a scan first: quirk scan --target <host>. Results will appear here automatically." />
    )
  }

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Findings</h1>
      <div className="flex gap-3 items-center">
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-40" aria-label="Filter by severity">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Severities</SelectItem>
            {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={protocolFilter} onValueChange={setProtocolFilter}>
          <SelectTrigger className="w-40" aria-label="Filter by protocol">
            <SelectValue placeholder="Protocol" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Protocols</SelectItem>
            {["TLS", "SSH", "HTTP", "KERBEROS", "SAML", "DNSSEC"].map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={segmentFilter} onValueChange={setSegmentFilter}>
          <SelectTrigger className="w-40 h-8 text-sm" aria-label="Filter by segment">
            <SelectValue placeholder="All segments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All segments</SelectItem>
            {distinctSegments.map((seg) => (
              <SelectItem key={seg} value={seg}>{seg}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Search title or host..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="max-w-xs"
          aria-label="Search findings"
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

      {/* Finding detail Sheet */}
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
                    <p className="text-xs font-semibold text-muted-foreground uppercase mb-1">Quantum Context</p>
                    <p className="text-foreground">Algorithm classified as: <strong>{selectedFinding.quantum_risk}</strong></p>
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
