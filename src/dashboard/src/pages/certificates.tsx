import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { AlertTriangle } from "lucide-react"
import { CertificatesSkeleton } from "./certificates.skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"

const QS_BADGE: Record<string, string> = {
  Safe: "bg-[hsl(142_71%_45%)] text-white",
  "At Risk": "bg-[hsl(38_92%_50%)] text-black",
  Vulnerable: "bg-[hsl(0_72%_51%)] text-white",
  Unknown: "bg-[hsl(240_5%_46%)] text-white",
}

export function CertificatesPage() {
  const { data, loading, error } = useScanData()
  const now = useMemo(() => new Date(), [])

  if (loading) return <CertificatesSkeleton />
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  const certs = data?.certificates ?? []

  if (!certs.length) {
    return (
      <EmptyStateCard message="No TLS certificates discovered in this scan — verify scan targets include HTTPS or TLS services." />
    )
  }

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Certificate Inventory</h1>
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold">Host</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Port</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Subject CN</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Issuer</TableHead>
              <TableHead scope="col" className="text-xs font-semibold" aria-sort="ascending">Expiry</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Algorithm</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Quantum Safety</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {certs.map((cert, i) => {
              const expiry = cert.cert_not_after ? new Date(cert.cert_not_after) : null
              const daysToExpiry = expiry ? Math.floor((expiry.getTime() - now.getTime()) / 86400000) : null
              const expiryClass = daysToExpiry !== null
                ? daysToExpiry < 0 ? "text-[hsl(0_72%_51%)]"
                : daysToExpiry < 30 ? "text-[hsl(0_72%_51%)]"
                : daysToExpiry < 90 ? "text-[hsl(38_92%_50%)]"
                : "text-muted-foreground"
                : "text-muted-foreground"

              const subjectCN = cert.cert_subject
                ? (cert.cert_subject.match(/CN=([^,]+)/)?.[1] ?? cert.cert_subject)
                : "—"
              const issuerCN = cert.cert_issuer
                ? (cert.cert_issuer.match(/CN=([^,]+)/)?.[1] ?? cert.cert_issuer)
                : "—"

              return (
                <TableRow key={i}>
                  <TableCell className="text-sm">{cert.host}</TableCell>
                  <TableCell className="text-sm">{cert.port}</TableCell>
                  <TableCell className="text-sm font-mono text-xs">{subjectCN}</TableCell>
                  <TableCell className="text-sm">{issuerCN}</TableCell>
                  <TableCell className={`text-sm ${expiryClass} flex items-center gap-1`}>
                    {(daysToExpiry !== null && daysToExpiry < 30) && <AlertTriangle className="h-3 w-3" />}
                    {expiry ? expiry.toLocaleDateString("en-US", { dateStyle: "medium" }) : "—"}
                  </TableCell>
                  <TableCell className="text-xs font-mono">
                    {cert.cert_pubkey_alg ?? "—"}
                    {cert.cert_pubkey_size ? ` ${cert.cert_pubkey_size}b` : ""}
                  </TableCell>
                  <TableCell>
                    {cert.quantum_safety ? (
                      <Badge className={`${QS_BADGE[cert.quantum_safety] ?? ""} text-xs`}>
                        {cert.quantum_safety}
                      </Badge>
                    ) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
