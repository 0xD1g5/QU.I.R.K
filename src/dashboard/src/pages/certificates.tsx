import { useMemo, useState } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table"
import { useScanData } from "@/hooks/useScanData"
import type { CertItem } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { AlertTriangle } from "lucide-react"
import { CertificatesSkeleton } from "./certificates.skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { extractCN } from "@/lib/cert-parse"
import { toDate, formatDateOnly } from "@/lib/datetime"

const QS_BADGE: Record<string, string> = {
  Safe: "bg-[hsl(142_71%_45%)] text-white",
  "At Risk": "bg-[hsl(38_92%_50%)] text-black",
  Vulnerable: "bg-[hsl(0_72%_51%)] text-white",
  Unknown: "bg-[hsl(240_5%_46%)] text-white",
}

export function CertificatesPage() {
  const { data, loading, error } = useScanData()
  const now = useMemo(() => new Date(), [])
  const [sorting, setSorting] = useState<SortingState>([])

  const certs = useMemo(() => data?.certificates ?? [], [data])

  // Phase 213 UIFIX-01: columns are memoized so TanStack's referential-stability
  // requirement holds — the array identity only changes when `now` or `certs` change.
  const columns = useMemo<ColumnDef<CertItem>[]>(() => [
    {
      id: "host",
      header: "Host",
      accessorFn: (cert) => cert.host,
      cell: ({ getValue }) => <span className="text-sm">{getValue<string>()}</span>,
    },
    {
      id: "port",
      header: "Port",
      accessorFn: (cert) => cert.port,
      cell: ({ getValue }) => <span className="text-sm">{getValue<number>()}</span>,
    },
    {
      id: "subjectCN",
      header: "Subject CN",
      accessorFn: (cert) => extractCN(cert.cert_subject),
      cell: ({ getValue }) => <span className="text-sm font-mono text-xs">{getValue<string>()}</span>,
    },
    {
      id: "issuerCN",
      header: "Issuer",
      accessorFn: (cert) => extractCN(cert.cert_issuer),
      cell: ({ getValue }) => <span className="text-sm">{getValue<string>()}</span>,
    },
    {
      id: "expiry",
      header: "Expiry",
      // cert_not_after is date-only, not an instant (schemas.py Optional[str]; SCORE-03
      // Pitfall 1) — dispositioned out of this phase's backend fix. toDate() here is the sort
      // key; formatDateOnly (below, fixed UTC) is a SEPARATE call used only for display, so the
      // sort key and the display string are different objects by construction (D-07).
      // `sortUndefined` only special-cases `undefined`, not `null` (TanStack
      // getSortedRowModel.ts) — `toDate()` returns `null` for unparseable/absent input, so the
      // `?? undefined` coercion below is required for Test 4's null-sorts-last behaviour.
      accessorFn: (cert) => toDate(cert.cert_not_after) ?? undefined,
      enableSorting: true,
      sortingFn: "datetime",
      sortUndefined: "last",
      // TanStack defaults "datetime" columns to a descending first click ("newest first").
      // UAT-7-12 / this plan's Test 5 expects the conventional none -> asc -> desc toggle.
      sortDescFirst: false,
      cell: ({ row }) => {
        const cert = row.original
        const expiry = toDate(cert.cert_not_after)
        const daysToExpiry = expiry ? Math.floor((expiry.getTime() - now.getTime()) / 86400000) : null
        const expiryClass = daysToExpiry !== null
          ? daysToExpiry < 0 ? "text-[hsl(0_72%_51%)]"
          : daysToExpiry < 30 ? "text-[hsl(0_72%_51%)]"
          : daysToExpiry < 90 ? "text-[hsl(38_92%_50%)]"
          : "text-muted-foreground"
          : "text-muted-foreground"

        return (
          <span className={`text-sm ${expiryClass} flex items-center gap-1`}>
            {(daysToExpiry !== null && daysToExpiry < 30) && <AlertTriangle className="h-3 w-3" />}
            {expiry ? formatDateOnly(cert.cert_not_after) : "—"}
          </span>
        )
      },
    },
    {
      id: "algorithm",
      header: "Algorithm",
      accessorFn: (cert) => `${cert.cert_pubkey_alg ?? "—"}${cert.cert_pubkey_size ? ` ${cert.cert_pubkey_size}b` : ""}`,
      cell: ({ row }) => {
        const cert = row.original
        return (
          <span className="text-xs font-mono">
            {cert.cert_pubkey_alg ?? "—"}
            {cert.cert_pubkey_size ? ` ${cert.cert_pubkey_size}b` : ""}
          </span>
        )
      },
    },
    {
      id: "quantumSafety",
      header: "Quantum Safety",
      accessorFn: (cert) => cert.quantum_safety,
      cell: ({ getValue }) => {
        const value = getValue<string | null | undefined>()
        return value ? (
          <Badge className={`${QS_BADGE[value] ?? ""} text-xs`}>{value}</Badge>
        ) : <span className="text-muted-foreground">—</span>
      },
    },
  ], [now])

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table returns non-memoizable functions; known React Compiler limitation
  const table = useReactTable({
    data: certs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    defaultColumn: { enableSorting: false },
  })

  if (loading) return <CertificatesSkeleton />
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  // Phase 194 DASH-09 / D-11 / D-13: excluded_cert_count is the server's
  // authoritative count of TLS endpoints removed as phantom rows (failed
  // handshake). Never re-derived or re-filtered from `certs` client-side.
  const excluded = data?.excluded_cert_count ?? 0

  const disclosure = excluded > 0 && (
    <p className="text-xs text-muted-foreground">
      {excluded} TLS endpoints failed handshake and are not shown.
    </p>
  )

  if (!certs.length) {
    return (
      <div className="space-y-4">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Certificate Inventory</h1>
        {disclosure}
        <EmptyStateCard message="No TLS certificates discovered in this scan." />
        <p className="text-muted-foreground text-sm">
          — verify scan targets include HTTPS or TLS services.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Certificate Inventory</h1>
      {disclosure}
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((h) => (
                  <TableHead
                    key={h.id}
                    scope="col"
                    aria-sort={h.column.getCanSort()
                      ? h.column.getIsSorted() === "asc" ? "ascending"
                      : h.column.getIsSorted() === "desc" ? "descending"
                      : "none"
                      : undefined}
                    className={`text-xs font-semibold${h.column.getCanSort() ? " cursor-pointer select-none" : ""}`}
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
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
