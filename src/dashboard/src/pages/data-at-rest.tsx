import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { DarFinding } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { ScoreGauge } from "@/components/gauges/ScoreGauge"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}
const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 } as const

function BoolBadge({
  value, trueLabel, trueClass, falseLabel, falseClass,
}: {
  value: boolean | null | undefined
  trueLabel: string; trueClass: string
  falseLabel: string; falseClass: string
}) {
  if (value === null || value === undefined) return <span>—</span>
  return (
    <Badge className={`${value ? trueClass : falseClass} text-xs`}>
      {value ? trueLabel : falseLabel}
    </Badge>
  )
}

function nullDash(v: string | null | undefined) {
  return v === null || v === undefined || v === "" ? "—" : v
}

function truncate(s: string | null | undefined, n = 60) {
  if (!s) return "—"
  return s.length > n ? `${s.slice(0, n - 1)}…` : s
}

function sortBySev(findings: DarFinding[]) {
  return [...findings].sort(
    (a, b) =>
      (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 99) -
      (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 99) ||
      a.host.localeCompare(b.host) ||
      (a.port ?? 0) - (b.port ?? 0),
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <Badge className={`${SEVERITY_STYLES[severity] ?? ""} font-semibold text-xs`}>
      {severity}
    </Badge>
  )
}

function DatabaseTable({ findings }: { findings: DarFinding[] }) {
  const rows = sortBySev(findings)
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-semibold">Engine</TableHead>
              <TableHead className="text-xs font-semibold">Host</TableHead>
              <TableHead className="text-xs font-semibold">Port</TableHead>
              <TableHead className="text-xs font-semibold">Severity</TableHead>
              <TableHead className="text-xs font-semibold">Title</TableHead>
              <TableHead className="text-xs font-semibold">Encryption at Rest</TableHead>
              <TableHead className="text-xs font-semibold">TLS in Transit</TableHead>
              <TableHead className="text-xs font-semibold">Quantum Risk</TableHead>
              <TableHead className="text-xs font-semibold">Remediation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{nullDash(f.protocol)}</TableCell>
                <TableCell className="text-sm">{f.host}</TableCell>
                <TableCell className="text-sm">{f.port}</TableCell>
                <TableCell className="text-sm"><SeverityBadge severity={f.severity} /></TableCell>
                <TableCell className="text-sm">{f.title}</TableCell>
                <TableCell className="text-sm">
                  <BoolBadge value={f.encryption_at_rest}
                    trueLabel="ENCRYPTED" trueClass="bg-[hsl(142_71%_45%)] text-white"
                    falseLabel="UNENCRYPTED" falseClass="bg-[hsl(0_72%_51%)] text-white" />
                </TableCell>
                <TableCell className="text-sm">
                  <BoolBadge value={f.tls_in_transit}
                    trueLabel="TLS ON" trueClass="bg-[hsl(142_71%_45%)] text-white"
                    falseLabel="TLS OFF" falseClass="bg-[hsl(0_72%_51%)] text-white" />
                </TableCell>
                <TableCell className="text-sm">{nullDash(f.quantum_risk)}</TableCell>
                <TableCell className="text-sm">{truncate(f.remediation)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function ObjectStorageTable({ findings }: { findings: DarFinding[] }) {
  const rows = sortBySev(findings)
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-semibold">Provider</TableHead>
              <TableHead className="text-xs font-semibold">Host</TableHead>
              <TableHead className="text-xs font-semibold">Severity</TableHead>
              <TableHead className="text-xs font-semibold">Title</TableHead>
              <TableHead className="text-xs font-semibold">Encryption Mode</TableHead>
              <TableHead className="text-xs font-semibold">Public Access</TableHead>
              <TableHead className="text-xs font-semibold">KMS Key</TableHead>
              <TableHead className="text-xs font-semibold">Versioning</TableHead>
              <TableHead className="text-xs font-semibold">Quantum Risk</TableHead>
              <TableHead className="text-xs font-semibold">Remediation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{nullDash(f.protocol)}</TableCell>
                <TableCell className="text-sm">{f.host}</TableCell>
                <TableCell className="text-sm"><SeverityBadge severity={f.severity} /></TableCell>
                <TableCell className="text-sm">{f.title}</TableCell>
                <TableCell className="text-sm">
                  {f.encryption_mode === null || f.encryption_mode === undefined ? (
                    <span>—</span>
                  ) : f.encryption_mode === "none" ? (
                    <Badge className="bg-[hsl(0_72%_51%)] text-white text-xs">none</Badge>
                  ) : (
                    f.encryption_mode
                  )}
                </TableCell>
                <TableCell className="text-sm">
                  <BoolBadge value={f.public_access}
                    trueLabel="PUBLIC" trueClass="bg-[hsl(0_72%_51%)] text-white"
                    falseLabel="PRIVATE" falseClass="bg-[hsl(240_5%_46%)] text-white" />
                </TableCell>
                <TableCell className="text-sm">
                  <span className="font-mono text-xs">{truncate(f.kms_key_id, 20)}</span>
                </TableCell>
                <TableCell className="text-sm">
                  <BoolBadge value={f.versioning}
                    trueLabel="ON" trueClass="bg-[hsl(213_94%_68%)] text-black"
                    falseLabel="OFF" falseClass="bg-[hsl(240_5%_46%)] text-white" />
                </TableCell>
                <TableCell className="text-sm">{nullDash(f.quantum_risk)}</TableCell>
                <TableCell className="text-sm">{truncate(f.remediation)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function KubernetesTable({ findings }: { findings: DarFinding[] }) {
  const rows = sortBySev(findings)
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-semibold">Namespace</TableHead>
              <TableHead className="text-xs font-semibold">Host</TableHead>
              <TableHead className="text-xs font-semibold">Severity</TableHead>
              <TableHead className="text-xs font-semibold">Title</TableHead>
              <TableHead className="text-xs font-semibold">Secret Type</TableHead>
              <TableHead className="text-xs font-semibold">Encryption Provider</TableHead>
              <TableHead className="text-xs font-semibold">Quantum Risk</TableHead>
              <TableHead className="text-xs font-semibold">Remediation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{nullDash(f.namespace)}</TableCell>
                <TableCell className="text-sm">{f.host}</TableCell>
                <TableCell className="text-sm"><SeverityBadge severity={f.severity} /></TableCell>
                <TableCell className="text-sm">{f.title}</TableCell>
                <TableCell className="text-sm">{nullDash(f.secret_type)}</TableCell>
                <TableCell className="text-sm">{nullDash(f.encryption_provider)}</TableCell>
                <TableCell className="text-sm">{nullDash(f.quantum_risk)}</TableCell>
                <TableCell className="text-sm">{truncate(f.remediation)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function VaultTable({ findings }: { findings: DarFinding[] }) {
  const rows = sortBySev(findings)
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-semibold">Host</TableHead>
              <TableHead className="text-xs font-semibold">Severity</TableHead>
              <TableHead className="text-xs font-semibold">Title</TableHead>
              <TableHead className="text-xs font-semibold">Mount Type</TableHead>
              <TableHead className="text-xs font-semibold">Seal Type</TableHead>
              <TableHead className="text-xs font-semibold">Auto-Unseal</TableHead>
              <TableHead className="text-xs font-semibold">Quantum Risk</TableHead>
              <TableHead className="text-xs font-semibold">Remediation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{f.host}</TableCell>
                <TableCell className="text-sm"><SeverityBadge severity={f.severity} /></TableCell>
                <TableCell className="text-sm">{f.title}</TableCell>
                <TableCell className="text-sm">{nullDash(f.mount_type)}</TableCell>
                <TableCell className="text-sm">{nullDash(f.seal_type)}</TableCell>
                <TableCell className="text-sm">
                  <BoolBadge value={f.auto_unseal}
                    trueLabel="YES" trueClass="bg-[hsl(142_71%_45%)] text-white"
                    falseLabel="NO" falseClass="bg-[hsl(240_5%_46%)] text-white" />
                </TableCell>
                <TableCell className="text-sm">{nullDash(f.quantum_risk)}</TableCell>
                <TableCell className="text-sm">{truncate(f.remediation)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export function DataAtRestPage() {
  const { data, loading, error } = useScanData()

  const darFindings: DarFinding[] = useMemo(
    () => data?.dar_findings ?? [],
    [data],
  )
  const dbFindings = useMemo(
    () => darFindings.filter((f) => f.category === "database"),
    [darFindings],
  )
  const objFindings = useMemo(
    () => darFindings.filter((f) => f.category === "object_storage"),
    [darFindings],
  )
  const k8sFindings = useMemo(
    () => darFindings.filter((f) => f.category === "kubernetes"),
    [darFindings],
  )
  const vaultFindings = useMemo(
    () => darFindings.filter((f) => f.category === "vault"),
    [darFindings],
  )

  if (loading) {
    return (
      <div role="status" aria-label="Loading data at rest" className="space-y-6">
        <span className="sr-only">Loading...</span>
        <Skeleton className="h-7 w-32" />
        {Array.from({ length: 4 }).map((_, s) => (
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

  const darScore = data?.score.subscores.data_at_rest ?? 0

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Data at Rest</h1>

      <div>
        <ScoreGauge score={darScore} label="Data at Rest" size={120} />
      </div>

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

      <section aria-labelledby="dar-obj-heading">
        <h2 id="dar-obj-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Object Storage
        </h2>
        {objFindings.length === 0 ? (
          <EmptyStateCard message="No object storage buckets scanned in this session — enable the object storage scanner or configure cloud credentials." />
        ) : (
          <ObjectStorageTable findings={objFindings} />
        )}
      </section>

      <section aria-labelledby="dar-k8s-heading">
        <h2 id="dar-k8s-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Kubernetes Secrets
        </h2>
        {k8sFindings.length === 0 ? (
          <EmptyStateCard message="No Kubernetes secrets scanned in this session — enable the Kubernetes scanner or configure cluster access." />
        ) : (
          <KubernetesTable findings={k8sFindings} />
        )}
      </section>

      <section aria-labelledby="dar-vault-heading">
        <h2 id="dar-vault-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Vault
        </h2>
        {vaultFindings.length === 0 ? (
          <EmptyStateCard message="No Vault mounts scanned in this session — enable the Vault connector or configure a Vault address." />
        ) : (
          <VaultTable findings={vaultFindings} />
        )}
      </section>
    </div>
  )
}
