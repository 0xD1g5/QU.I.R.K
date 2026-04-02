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
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

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
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null)

  const findings = useMemo(() => {
    if (!data?.findings) return []
    if (severityFilter === "ALL") return data.findings
    return data.findings.filter((f) => f.severity === severityFilter)
  }, [data, severityFilter])

  const columns: ColumnDef<FindingItem>[] = [
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
          "Safe": "bg-[hsl(142_71%_45%)] text-white",
        }
        return <Badge className={`${colors[qr] ?? ""} text-xs`}>{qr}</Badge>
      },
    },
    { accessorKey: "source", header: "Source" },
  ]

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

  if (loading) return <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  if (!data?.findings?.length) {
    return (
      <div className="text-center py-12">
        <h2 className="text-foreground font-semibold text-xl">No findings recorded</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          Run a scan first: <code className="font-mono bg-card px-1 rounded">quirk scan --target &lt;host&gt;</code>. Results will appear here automatically.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Findings</h1>
      <div className="flex gap-3 items-center">
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Severities</SelectItem>
            {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
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
